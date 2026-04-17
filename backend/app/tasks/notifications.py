"""
Notification dispatch.

fire_rules(trigger, context)
  — Call from admin endpoints and Celery tasks.
  — Finds all active NotificationRule documents whose trigger matches,
    applies optional filters, then dispatches each to its destination
    via a Celery task (fire-and-forget).

Context dict keys (all optional; omit what is not applicable):
  service_name, service_slug, section_name
  status, prev_status
  title, description
  starts_at, ends_at
  message, monitor_name
  timestamp
"""

import json
import re
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText

import requests as _requests

from app.extensions import celery


# ── Template rendering ────────────────────────────────────────────────────────

def _sub(template: str, ctx: dict) -> str:
    """Replace {{key}} placeholders with ctx values."""
    def _repl(m):
        return str(ctx.get(m.group(1).strip(), ""))
    return re.sub(r"\{\{(\w+)\}\}", _repl, template or "")


# ── Delivery ──────────────────────────────────────────────────────────────────

def _send_webhook(dest, ctx):
    method  = (dest.method or "POST").upper()
    headers = dict(dest.headers or {})
    headers.setdefault("Content-Type", "application/json")

    raw = _sub(dest.body_template or "{}", ctx)
    try:
        payload = json.dumps(json.loads(raw))
    except json.JSONDecodeError:
        payload = raw  # send as-is if template produced invalid JSON

    _requests.request(method, dest.url, data=payload, headers=headers, timeout=10)


def _send_email(dest, ctx):
    from app.models.settings import Settings
    cfg = Settings.get_or_create()

    if not cfg.smtp_host:
        return  # SMTP not configured — skip silently

    subject = _sub(dest.email_subject_template, ctx) or "MOSSBoard Notification"
    body    = _sub(dest.email_body_template, ctx)
    from_   = cfg.smtp_from or cfg.smtp_username or "mossboard@localhost"

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"]    = from_
    msg["To"]      = dest.email_to

    port = cfg.smtp_port or 587

    if cfg.smtp_use_tls:
        smtp = smtplib.SMTP(cfg.smtp_host, port, timeout=15)
        smtp.starttls()
    elif port == 465:
        smtp = smtplib.SMTP_SSL(cfg.smtp_host, port, timeout=15)
    else:
        smtp = smtplib.SMTP(cfg.smtp_host, port, timeout=15)

    if cfg.smtp_username and cfg.smtp_password:
        smtp.login(cfg.smtp_username, cfg.smtp_password)

    smtp.sendmail(from_, [dest.email_to], msg.as_string())
    smtp.quit()


# ── Celery task ───────────────────────────────────────────────────────────────

@celery.task(name="app.tasks.notifications.dispatch_notification", bind=True, max_retries=3)
def dispatch_notification(self, dest_id: str, ctx: dict):
    """Look up destination and deliver. Retries up to 3 times on failure."""
    from app.models.notification import NotificationDestination
    dest = NotificationDestination.objects(id=dest_id, active=True).first()
    if not dest:
        return "destination not found or inactive"
    try:
        if dest.type == "webhook":
            _send_webhook(dest, ctx)
        elif dest.type == "email":
            _send_email(dest, ctx)
        return f"sent to {dest.name} ({dest.type})"
    except Exception as exc:
        try:
            raise self.retry(exc=exc, countdown=30)
        except self.MaxRetriesExceededError:
            return f"failed after retries: {exc}"


# ── Public entry point ────────────────────────────────────────────────────────

def fire_rules(trigger: str, ctx: dict):
    """
    Find active rules for this trigger, apply filters, enqueue delivery.
    Safe to call from both request context and Celery tasks.
    """
    from app.models.notification import NotificationRule

    ctx = dict(ctx)
    ctx.setdefault("timestamp", datetime.now(timezone.utc).isoformat())

    try:
        rules = list(NotificationRule.objects(trigger=trigger, active=True))
    except Exception:
        return

    for rule in rules:
        try:
            # ── Monitor status-change filters ──────────────────────────────
            if trigger == "monitor_status_change":
                from_f = rule.filter_from_status or ""
                to_f   = rule.filter_to_status   or ""
                if from_f and from_f != ctx.get("prev_status", ""):
                    continue
                if to_f and to_f != ctx.get("status", ""):
                    continue

            # ── Service filter ─────────────────────────────────────────────
            if rule.services:
                target_slug = ctx.get("service_slug", "")
                slugs = set()
                for svc in rule.services:
                    try:
                        slugs.add(svc.slug)
                    except Exception:
                        pass
                if target_slug and target_slug not in slugs:
                    continue

            dest = rule.destination
            dispatch_notification.delay(str(dest.id), ctx)
        except Exception:
            pass
