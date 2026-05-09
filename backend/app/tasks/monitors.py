"""
Active monitoring tasks.

Check types:
  - http:  HTTP(S) request; evaluates response code + response time.
  - tcp:   TCP connection to host:port; evaluates connection time.
  - icmp:  Ping (subprocess); evaluates packet loss % + average round-trip time.

Status determination (worst wins):
  Thresholds are sorted ascending by their limit value.
  The first threshold whose limit >= measured value is used.
  If no threshold matches the status falls back to `failure_status`.

ICMP note:
  Requires the `ping` binary and, on Linux, either root or
  the cap_net_raw capability (add `cap_add: [NET_RAW]` to docker-compose).
"""

import re
import socket
import subprocess
import time
from datetime import datetime

import requests as _requests

from app.extensions import celery
from app.models import Service, StatusSnapshot
from app.models.monitor import Monitor

_STATUS_PRIORITY = {
    "operational": 1,
    "unknown": 2,
    "under_maintenance": 3,
    "performance_issues": 4,
    "partial_outage": 5,
    "major_outage": 6,
}


def _compute_service_status(service, source_monitor=None, source_status=None):
    """Compute the rolled-up service status across all active monitors.

    For each active monitor on the service, take the worst status (per
    _STATUS_PRIORITY). When `source_monitor` is provided, that monitor
    contributes `source_status` rather than its stored last_status —
    useful from inside run_single_monitor where the source monitor's
    last_status has been updated in-memory but not yet persisted.

    Monitors with no last_status yet (never run) are ignored.
    """
    aggregated = source_status
    for m in Monitor.objects(service=service, active=True):
        if source_monitor is not None and m.id == source_monitor.id:
            contribution = source_status
        else:
            contribution = m.last_status
        if contribution:
            aggregated = _worst(aggregated, contribution)
    return aggregated


def _resolve_response_time(thresholds, response_ms, failure_status):
    """Map a measured response time to a status via sorted thresholds."""
    for t in sorted(thresholds, key=lambda x: x.max_ms):
        if response_ms <= t.max_ms:
            return t.status
    return failure_status


def _resolve_packet_loss(thresholds, loss_percent, failure_status):
    """Map a measured packet-loss percentage to a status via sorted thresholds."""
    for t in sorted(thresholds, key=lambda x: x.max_percent):
        if loss_percent <= t.max_percent:
            return t.status
    return failure_status


# ── Probe implementations ─────────────────────────────────────────────────────

def _check_http(monitor):
    """Perform an HTTP GET and return a result dict."""
    result = {"type": "http", "url": monitor.url}
    proxies = None
    if monitor.proxy_host and monitor.proxy_port:
        proxy_url = f"http://{monitor.proxy_host}:{monitor.proxy_port}"
        proxies = {"http": proxy_url, "https": proxy_url}
        result["proxy"] = f"{monitor.proxy_host}:{monitor.proxy_port}"
    try:
        t0 = time.time()
        resp = _requests.get(
            monitor.url,
            timeout=monitor.timeout_seconds,
            allow_redirects=True,
            proxies=proxies,
            verify=monitor.verify_ssl,
        )
        response_ms = (time.time() - t0) * 1000
        result["response_ms"] = round(response_ms, 2)
        result["status_code"] = resp.status_code

        if resp.status_code not in monitor.expected_status_codes:
            result["error"] = f"Unexpected HTTP {resp.status_code}"
            result["resolved_status"] = monitor.failure_status
        else:
            resolved = _resolve_response_time(
                monitor.response_time_thresholds, response_ms, monitor.failure_status
            )
            if monitor.body_regex:
                try:
                    match = bool(re.search(monitor.body_regex, resp.text))
                except re.error as exc:
                    match = False
                    result["body_regex_error"] = str(exc)
                result["body_regex_match"] = match
                if not match:
                    result["error"] = f"Body did not match /{monitor.body_regex}/"
                    resolved = monitor.failure_status
            result["resolved_status"] = resolved
    except _requests.Timeout:
        result["error"] = "timeout"
        result["resolved_status"] = monitor.failure_status
    except _requests.RequestException as exc:
        result["error"] = str(exc)
        result["resolved_status"] = monitor.failure_status
    return result


def _check_tcp(monitor):
    """Open a TCP connection and return a result dict."""
    result = {"type": "tcp", "host": monitor.host, "port": monitor.port}
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(monitor.timeout_seconds)
    t0 = time.time()
    try:
        sock.connect((monitor.host, monitor.port))
        response_ms = (time.time() - t0) * 1000
        result["response_ms"] = round(response_ms, 2)
        result["resolved_status"] = _resolve_response_time(
            monitor.response_time_thresholds, response_ms, monitor.failure_status
        )
    except socket.timeout:
        result["error"] = "timeout"
        result["resolved_status"] = monitor.failure_status
    except (ConnectionRefusedError, OSError) as exc:
        result["error"] = str(exc)
        result["resolved_status"] = monitor.failure_status
    finally:
        sock.close()
    return result


def _check_icmp(monitor):
    """
    Run `ping -c <count> -W <timeout> <host>` and parse the output.
    Evaluates both packet loss and average RTT.
    """
    count = 3
    result = {"type": "icmp", "host": monitor.host}
    try:
        cmd = [
            "ping",
            "-c", str(count),
            "-W", str(monitor.timeout_seconds),
            monitor.host,
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=monitor.timeout_seconds * count + 10,
        )
        output = proc.stdout + proc.stderr

        # Packet loss: "X% packet loss"
        loss_match = re.search(r"(\d+(?:\.\d+)?)%\s+packet loss", output)
        loss_percent = float(loss_match.group(1)) if loss_match else 100.0
        result["packet_loss_percent"] = loss_percent

        # Average RTT: "rtt min/avg/max/mdev = X/X/X/X ms"
        rtt_match = re.search(r"min/avg/max(?:/mdev)?\s*=\s*[\d.]+/([\d.]+)/", output)
        avg_ms = float(rtt_match.group(1)) if rtt_match else None
        if avg_ms is not None:
            result["response_ms"] = avg_ms

        if loss_percent == 100.0:
            result["error"] = "100% packet loss"
            result["resolved_status"] = monitor.failure_status
        else:
            # Evaluate packet loss first
            loss_status = _resolve_packet_loss(
                monitor.packet_loss_thresholds, loss_percent, monitor.failure_status
            )
            # Then response time (if available)
            rtt_status = None
            if avg_ms is not None and monitor.response_time_thresholds:
                rtt_status = _resolve_response_time(
                    monitor.response_time_thresholds, avg_ms, monitor.failure_status
                )
            result["resolved_status"] = _worst(loss_status, rtt_status) or loss_status

    except subprocess.TimeoutExpired:
        result["error"] = "ping timeout"
        result["resolved_status"] = monitor.failure_status
    except FileNotFoundError:
        result["error"] = "ping binary not found"
        result["resolved_status"] = monitor.failure_status
    except Exception as exc:
        result["error"] = str(exc)
        result["resolved_status"] = monitor.failure_status
    return result


def _check_dns(monitor):
    """
    Resolve a DNS name using dnspython and return a result dict.

    Checks:
      1. Resolution succeeds within timeout → otherwise failure_status
      2. If dns_expected_values is configured, every expected value must appear
         in the answer set (case-insensitive for names, exact for IPs/text) →
         otherwise failure_status
      3. Response-time thresholds applied to query latency
    """
    import dns.resolver
    import dns.exception

    record_type = (monitor.dns_record_type or "A").upper()
    result = {
        "type": "dns",
        "host": monitor.host,
        "record_type": record_type,
        "dns_server": monitor.dns_server or None,
    }

    resolver = dns.resolver.Resolver()
    if monitor.dns_server:
        resolver.nameservers = [monitor.dns_server]
    resolver.timeout  = monitor.timeout_seconds
    resolver.lifetime = monitor.timeout_seconds

    try:
        t0 = time.time()
        answers = resolver.resolve(monitor.host, record_type)
        response_ms = (time.time() - t0) * 1000

        result["response_ms"] = round(response_ms, 2)

        # Collect answer values as strings
        resolved = [str(r).rstrip(".") for r in answers]
        result["resolved_values"] = resolved

        # Check expected values (all must appear)
        expected = [v.strip().rstrip(".") for v in (monitor.dns_expected_values or []) if v.strip()]
        if expected:
            resolved_lower = [v.lower() for v in resolved]
            missing = [e for e in expected if e.lower() not in resolved_lower]
            if missing:
                result["error"] = f"Expected {missing} not in answer {resolved}"
                result["resolved_status"] = monitor.failure_status
                return result

        result["resolved_status"] = _resolve_response_time(
            monitor.response_time_thresholds, response_ms, monitor.failure_status
        )

    except dns.resolver.NXDOMAIN:
        result["error"] = "NXDOMAIN"
        result["resolved_status"] = monitor.failure_status
    except dns.resolver.NoAnswer:
        result["error"] = f"No {record_type} record"
        result["resolved_status"] = monitor.failure_status
    except dns.resolver.NoNameservers:
        result["error"] = "No nameservers available"
        result["resolved_status"] = monitor.failure_status
    except dns.exception.Timeout:
        result["error"] = "timeout"
        result["resolved_status"] = monitor.failure_status
    except Exception as exc:
        result["error"] = str(exc)
        result["resolved_status"] = monitor.failure_status

    return result


_CHECKERS = {
    "http": _check_http,
    "tcp":  _check_tcp,
    "icmp": _check_icmp,
    "dns":  _check_dns,
}


# ── Celery tasks ──────────────────────────────────────────────────────────────

def _trigger_str(result):
    """Build a concise human-readable string of the measured values that caused
    the status change, for inclusion in the StatusSnapshot note."""
    if not result:
        return ""
    parts = []
    if result.get("status_code") is not None:
        parts.append(f"HTTP {result['status_code']}")
    if result.get("response_ms") is not None:
        parts.append(f"{result['response_ms']} ms")
    if result.get("packet_loss_percent") is not None:
        parts.append(f"{result['packet_loss_percent']}% packet loss")
    if result.get("body_regex_match") is False:
        parts.append("body regex: no match")
    if result.get("resolved_values"):
        parts.append(f"resolved: {', '.join(result['resolved_values'])}")
    if result.get("error"):
        parts.append(result["error"])
    return ", ".join(parts)


def _apply_service_status(service, new_status, monitor_name, result=None):
    """Write status + snapshot to the linked service.

    The snapshot note contains the monitor name plus the measured trigger
    values (response time, packet loss, HTTP code, etc.) so the status log
    shows exactly what caused the status change.
    """
    old_status = service.status
    service.status            = new_status
    service.updated_at        = datetime.utcnow()
    service.status_updated_at = datetime.utcnow()
    service.save()
    trigger = _trigger_str(result)
    note    = f"[monitor:{monitor_name}]" + (f" {trigger}" if trigger else "")
    StatusSnapshot(service=service, status=new_status, note=note.strip()).save()
    try:
        from app.tasks.notifications import fire_rules
        section_name = ""
        try:
            section_name = service.section.name if service.section else ""
        except Exception:
            pass
        fire_rules("monitor_status_change", {
            "service_name": service.name,
            "service_slug": service.slug,
            "section_name": section_name,
            "prev_status":  old_status,
            "status":       new_status,
            "monitor_name": monitor_name,
        })
    except Exception:
        pass
    return f"{monitor_name}: {old_status} → {new_status}"


@celery.task(name="app.tasks.monitors.run_single_monitor")
def run_single_monitor(monitor_id: str):
    """Run the check for a single monitor and update the linked service.

    Confirmation logic:
      If confirm_seconds > 0, a new candidate status must be observed
      continuously for at least confirm_seconds before it is applied to
      the linked service.  Each check that disagrees with the current service
      status starts (or continues) a confirmation window.  If the candidate
      status changes during the window the timer resets.  Once the window
      elapses the status is applied and the pending state is cleared.
    """
    monitor = Monitor.objects(id=monitor_id).first()
    if not monitor or not monitor.active:
        return "skipped"

    checker = _CHECKERS.get(monitor.type)
    if not checker:
        return f"unknown type: {monitor.type}"

    result = checker(monitor)
    candidate = result.get("resolved_status", monitor.failure_status)
    now = datetime.utcnow()

    monitor.last_result = result
    monitor.last_status = candidate
    monitor.last_checked_at = now

    service = monitor.service
    action = f"{monitor.name}: {candidate} (unchanged)"

    if service:
        current = service.status

        # If the service is currently under maintenance, do not let the monitor
        # override that status.  Clear any pending confirmation window and stop.
        if current == "under_maintenance":
            monitor.pending_status = None
            monitor.pending_since = None
            monitor.save()
            return f"{monitor.name}: skipped (service under maintenance)"

        if candidate == current:
            # Situation matches current service status — reset any pending window.
            monitor.pending_status = None
            monitor.pending_since = None
        elif monitor.confirm_seconds == 0:
            # Immediate mode: aggregate across all active monitors before applying.
            aggregated = _compute_service_status(service, monitor, candidate)
            if aggregated != current:
                action = _apply_service_status(
                    service, aggregated, monitor.name, result
                )
            else:
                action = (
                    f"{monitor.name}: {candidate} "
                    f"(service unchanged, aggregated={aggregated})"
                )
            monitor.pending_status = None
            monitor.pending_since = None
        else:
            # Confirmation mode.
            if monitor.pending_status != candidate:
                # New candidate — start (or restart) the confirmation window.
                monitor.pending_status = candidate
                monitor.pending_since = now
                action = (
                    f"{monitor.name}: pending {candidate} "
                    f"(need {monitor.confirm_seconds}s, just started)"
                )
            else:
                # Same candidate — check if the window has elapsed.
                elapsed = (now - monitor.pending_since).total_seconds()
                if elapsed >= monitor.confirm_seconds:
                    aggregated = _compute_service_status(service, monitor, candidate)
                    if aggregated != current:
                        action = _apply_service_status(
                            service, aggregated, monitor.name, result
                        )
                    else:
                        action = (
                            f"{monitor.name}: {candidate} confirmed "
                            f"(service unchanged, aggregated={aggregated})"
                        )
                    monitor.pending_status = None
                    monitor.pending_since = None
                else:
                    remaining = int(monitor.confirm_seconds - elapsed)
                    action = (
                        f"{monitor.name}: pending {candidate} "
                        f"({remaining}s remaining)"
                    )

    monitor.save()
    return action


@celery.task(name="app.tasks.monitors.run_due_monitors")
def run_due_monitors():
    """
    Dispatched every minute by Celery Beat.
    Finds monitors whose next-check time has passed and queues them.
    """
    now = datetime.utcnow()
    queued = 0
    for monitor in Monitor.objects(active=True):
        if monitor.last_checked_at is None:
            due = True
        else:
            elapsed = (now - monitor.last_checked_at).total_seconds()
            due = elapsed >= monitor.interval_seconds
        if due:
            run_single_monitor.delay(str(monitor.id))
            queued += 1
    return f"Queued {queued} monitor checks"
