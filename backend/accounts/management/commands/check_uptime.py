"""
Lightweight external uptime check.

Hits the site through the real nginx+gunicorn stack (the same path a
browser takes) rather than checking from inside the Django process, because
the Aug 2026 outage proved those aren't the same thing: tms.service stayed
"active (running)" the entire 3 days while every request 500'd on a
Postgres connection-pool exhaustion. Nothing was polling for "is the site
actually serving requests", only for "is the process alive", so the outage
sat unnoticed over a weekend until someone happened to log in.

Alerts only after FAILURE_THRESHOLD consecutive failed runs (avoids paging
on one transient blip) and only once per outage (state file), then sends a
single recovery email when it comes back - not a fresh alert every run.

Install via `python manage.py install_cron` (see install_cron.py).
"""

import json
from pathlib import Path

import requests
import urllib3
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand

# The site's cert doesn't chain to a trusted root (self-signed/internal CA),
# so verification is off below - acceptable here since this only ever talks
# to the one known internal host, not arbitrary third parties.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CHECK_URL = "https://tms.petronastm.net/api/settings/?public=true"
REQUEST_TIMEOUT_SECONDS = 10
FAILURE_THRESHOLD = 2
STATE_FILE = Path(settings.BASE_DIR) / "logs" / ".uptime_check_state.json"


class Command(BaseCommand):
    help = (
        "Poll the live site and email UPTIME_ALERT_EMAIL after "
        f"{FAILURE_THRESHOLD} consecutive failed checks; email again once "
        "when it recovers."
    )

    def handle(self, *args, **options):
        if not settings.UPTIME_ALERT_EMAIL:
            self.stdout.write(
                self.style.WARNING("UPTIME_ALERT_EMAIL is not set - skipping (no-op).")
            )
            return

        ok, detail = self._check()
        state = self._load_state()
        was_alerted = state.get("alerted", False)

        if ok:
            self.stdout.write(self.style.SUCCESS(f"OK - {detail}"))
            if was_alerted:
                self._send_mail(
                    subject="[TMS] Site recovered",
                    message=f"The site is responding again.\n\n{detail}\n\nChecked: {CHECK_URL}",
                )
                self.stdout.write("Recovery notified.")
            self._save_state({"consecutive_failures": 0, "alerted": False})
            return

        failures = state.get("consecutive_failures", 0) + 1
        self.stdout.write(self.style.WARNING(f"FAILED ({failures}x) - {detail}"))

        if failures >= FAILURE_THRESHOLD and not was_alerted:
            self._send_mail(
                subject="[TMS] Site is down",
                message=(
                    f"The site failed {failures} consecutive uptime checks.\n\n"
                    f"{detail}\n\nChecked: {CHECK_URL}"
                ),
            )
            self.stdout.write(self.style.ERROR("Alert sent."))
            self._save_state({"consecutive_failures": failures, "alerted": True})
        else:
            self._save_state({"consecutive_failures": failures, "alerted": was_alerted})

    def _check(self):
        try:
            # Cert doesn't chain to a trusted root (self-signed/internal CA);
            # accepted here since this only ever talks to the one known
            # internal host (CHECK_URL above), not arbitrary third parties.
            resp = requests.get(
                CHECK_URL, timeout=REQUEST_TIMEOUT_SECONDS, verify=False
            )  # nosec B501
        except requests.RequestException as exc:
            return False, f"Request failed: {exc}"

        if resp.status_code == 200:
            return (
                True,
                f"HTTP {resp.status_code} in {resp.elapsed.total_seconds():.2f}s",
            )
        return False, f"HTTP {resp.status_code}: {resp.text[:300]}"

    def _send_mail(self, subject, message):
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.UPTIME_ALERT_EMAIL],
            fail_silently=False,
        )

    def _load_state(self):
        try:
            return json.loads(STATE_FILE.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_state(self, state):
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state))
