"""
SIEM-compatible structured security event logger.
Satisfies CTRL-0000001356 (security monitoring / SOC/SIEM integration).

Writes JSON-structured security events to a rotating log file that can be
ingested by any SIEM agent (Splunk Universal Forwarder, Elastic Filebeat,
Microsoft Sentinel agent, etc.).

The log file location is controlled by the SIEM_LOG_DIR environment variable
(defaults to <BASE_DIR>/logs/). SIEM agents should be pointed at:
    <SIEM_LOG_DIR>/security.json

Event schema:
{
  "timestamp":   ISO-8601 UTC,
  "event_type":  action_type string (e.g. "login_success"),
  "user":        email or "system",
  "user_id":     UUID string or null,
  "ip_address":  string or null,
  "entity_type": string,
  "entity_id":   string,
  "description": human-readable string
}
"""

import json
import logging
from django.utils import timezone

siem_logger = logging.getLogger('security.siem')


def log_security_event(
    action_type: str,
    description: str,
    user=None,
    ip_address: str | None = None,
    entity_type: str = '',
    entity_id: str = '',
) -> None:
    """
    Emit a structured JSON security event to the SIEM log.

    Called automatically by AdminActionLog.log_action() so all audit
    events are forwarded to the SIEM log file without extra callsites.

    Args:
        action_type:  Matches AdminActionLog.ACTION_TYPES key.
        description:  Human-readable event description.
        user:         User instance (may be None for unauthenticated events).
        ip_address:   Source IP address string.
        entity_type:  Type of affected entity (e.g. 'User', 'TravelRequest').
        entity_id:    ID of the affected entity.
    """
    event = {
        'timestamp': timezone.now().isoformat(),
        'event_type': action_type,
        'user': user.email if user else 'system',
        'user_id': str(user.id) if user else None,
        'ip_address': ip_address,
        'entity_type': entity_type,
        'entity_id': entity_id,
        'description': description,
    }
    siem_logger.info(json.dumps(event))
