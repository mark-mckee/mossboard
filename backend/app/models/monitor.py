from datetime import datetime
from mongoengine import (
    Document, EmbeddedDocument, StringField, IntField, FloatField,
    BooleanField, DateTimeField, ReferenceField, CASCADE,
    EmbeddedDocumentListField, ListField, DictField,
)
from .service import Service, STATUS_CHOICES

MONITOR_TYPES = ["http", "icmp", "tcp", "dns"]

DNS_RECORD_TYPES = ["A", "AAAA", "CNAME", "MX", "TXT", "NS", "PTR"]


class ResponseTimeThreshold(EmbeddedDocument):
    """If measured response time <= max_ms → assign this status.
    Thresholds should be stored sorted ascending by max_ms; first match wins."""
    max_ms = FloatField(required=True)
    status = StringField(choices=STATUS_CHOICES, required=True)


class PacketLossThreshold(EmbeddedDocument):
    """ICMP only: if packet loss % <= max_percent → assign this status.
    Thresholds should be stored sorted ascending by max_percent; first match wins."""
    max_percent = FloatField(required=True)
    status = StringField(choices=STATUS_CHOICES, required=True)


class Monitor(Document):
    """Active monitor that checks a host/URL and updates the linked service status."""

    service = ReferenceField(Service, reverse_delete_rule=CASCADE)
    name = StringField(required=True)
    type = StringField(choices=MONITOR_TYPES, required=True)

    # --- Target ---
    # HTTP:  url
    # TCP:   host + port
    # ICMP:  host
    # DNS:   host (name to resolve) + dns_server (optional) + dns_record_type
    url = StringField(default="")
    host = StringField(default="")
    port = IntField()

    # --- HTTP proxy (optional) ---
    proxy_host = StringField(default="")   # proxy hostname or IP; empty = no proxy
    proxy_port = IntField(null=True)        # proxy port (required when proxy_host is set)

    # --- DNS-specific ---
    dns_record_type    = StringField(choices=DNS_RECORD_TYPES, default="A")
    dns_server         = StringField(default="")   # custom resolver IP; empty = system default
    dns_expected_values = ListField(StringField())  # all must appear in the answer; empty = skip

    # --- Thresholds ---
    # Sorted ascending (lowest max first). First match wins.
    # If no threshold matches → failure_status is used.
    response_time_thresholds = EmbeddedDocumentListField(ResponseTimeThreshold)
    # ICMP only: packet loss thresholds
    packet_loss_thresholds = EmbeddedDocumentListField(PacketLossThreshold)

    # HTTP: which status codes count as a successful response
    expected_status_codes = ListField(IntField(), default=[200])
    # HTTP: optional regex that must match the response body; empty = skip
    body_regex = StringField(default="")

    # Status assigned on connection failure / timeout / unexpected HTTP code
    failure_status = StringField(choices=STATUS_CHOICES, default="major_outage")

    # --- Schedule ---
    interval_seconds = IntField(default=60)
    timeout_seconds = IntField(default=10)

    # --- Confirmation period ---
    # How many seconds a new candidate status must be observed continuously before
    # the linked service status is actually changed.  0 = change immediately.
    confirm_seconds = IntField(default=0)
    # Tracks the status that is "pending" confirmation (not yet applied).
    pending_status = StringField(choices=STATUS_CHOICES, null=True)
    # When the current pending_status was first observed.
    pending_since = DateTimeField(null=True)

    # --- State ---
    active = BooleanField(default=True)
    last_checked_at = DateTimeField(null=True)
    last_result = DictField()   # raw result from last check
    last_status = StringField(choices=STATUS_CHOICES, null=True)

    created_at = DateTimeField(default=datetime.utcnow)

    meta = {"ordering": ["name"]}
