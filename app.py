#!/usr/bin/env python3

import base64
import json
import os
import time
import hmac
import ssl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = int(os.environ["LISTEN_PORT"])

NEXTCLOUD_URL = os.environ["NEXTCLOUD_URL"].rstrip("/")
NEXTCLOUD_USER = os.environ["NEXTCLOUD_USER"]
NEXTCLOUD_APP_PASSWORD = os.environ["NEXTCLOUD_APP_PASSWORD"]
NEXTCLOUD_TLS_VERIFY = os.environ["NEXTCLOUD_TLS_VERIFY"].lower() in ("1", "true", "yes")
TALK_TOKEN = os.environ["TALK_TOKEN"]
WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]

# TLS certificate verification for the InfluxDB connection
if NEXTCLOUD_TLS_VERIFY:
    SSL_CONTEXT = ssl.create_default_context()
else:
    # Disable TLS verification for InfluxDB certificate
    SSL_CONTEXT = ssl._create_unverified_context()


def send_to_talk(message):
    url = (
        f"{NEXTCLOUD_URL}"
        f"/ocs/v2.php/apps/spreed/api/v1/chat/{TALK_TOKEN}"
    )

    payload = json.dumps({
        "message": message
    }).encode("utf-8")

    credentials = (
        f"{NEXTCLOUD_USER}:{NEXTCLOUD_APP_PASSWORD}"
    ).encode("utf-8")

    auth = base64.b64encode(credentials).decode("ascii")

    request = Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "OCS-APIRequest": "true",
        },
    )

    with urlopen(
        request,
        timeout=15,
        context=SSL_CONTEXT
    ) as response:

        body = response.read().decode(
            "utf-8",
            errors="replace"
        )

        print(
            f"Nextcloud: HTTP {response.status}: {body}",
            flush=True
        )

        if response.status not in (200, 201):
            raise RuntimeError(
                f"Nextcloud returned HTTP {response.status}"
            )


def status_icon(status):
    if str(status).lower() == "firing":
        return "🚨"

    if str(status).lower() == "resolved":
        return "✅"

    return "🔔"


def format_message(data):

    status = str(
        data.get("status", "unknown")
    ).lower()

    alerts = data.get("alerts") or []

    common_labels = data.get("commonLabels") or {}
    common_annotations = data.get("commonAnnotations") or {}

    alert_name = common_labels.get(
        "alertname",
        "Grafana Alert"
    )

    lines = []

    lines.append(
        f"{status_icon(status)} **Grafana Alert: {alert_name}**"
    )

    lines.append("")

    lines.append(
        f"**Status:** `{status}`"
    )

    # Use the first alert in the notification group.
    if alerts:
        alert = alerts[0]

        labels = alert.get("labels") or {}
        annotations = alert.get("annotations") or {}

        if labels.get("alertname"):
            alert_name = labels["alertname"]

        summary = (
            annotations.get("summary")
            or common_annotations.get("summary")
        )

        description = (
            annotations.get("description")
            or common_annotations.get("description")
        )

        if summary:
            lines.append(
                f"**Zusammenfassung:** {summary}"
            )

        if description:
            lines.append(
                f"**Meldung:** {description}"
            )

        starts_at = alert.get("startsAt")

        if starts_at:
            lines.append(
                f"**Beginn:** `{starts_at}`"
            )

    else:
        summary = common_annotations.get("summary")
        description = common_annotations.get("description")

        if summary:
            lines.append(
                f"**Zusammenfassung:** {summary}"
            )

        if description:
            lines.append(
                f"**Meldung:** {description}"
            )

    return "\n".join(lines)


class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print(
            f"{self.client_address[0]} - "
            f"{fmt % args}",
            flush=True
        )

    def send_json(self, status, data):

        payload = json.dumps(
            data
        ).encode("utf-8")

        self.send_response(status)

        self.send_header(
            "Content-Type",
            "application/json"
        )

        self.send_header(
            "Content-Length",
            str(len(payload))
        )

        self.end_headers()

        self.wfile.write(payload)

    def do_GET(self):

        if self.path == "/health":

            self.send_json(
                200,
                {
                    "status": "ok"
                }
            )

            return

        self.send_json(
            404,
            {
                "error": "not found"
            }
        )

    def do_POST(self):

        if self.path != "/grafana":

            self.send_json(
                404,
                {
                    "error": "not found"
                }
            )

            return

        try:
            length = int(
                self.headers.get(
                    "Content-Length",
                    "0"
                )
            )

        except ValueError:
            length = 0

        if length <= 0 or length > 1024 * 1024:

            self.send_json(
                400,
                {
                    "error": "invalid content length"
                }
            )

            return

        body = self.rfile.read(length)

        supplied_secret = self.headers.get(
            "X-Grafana-Webhook-Secret",
            ""
        )

        if not hmac.compare_digest(
            supplied_secret,
            WEBHOOK_SECRET
        ):

            print(
                "Rejected webhook: invalid secret",
                flush=True
            )

            self.send_json(
                401,
                {
                    "error": "unauthorized"
                }
            )

            return

        try:

            data = json.loads(
                body.decode("utf-8")
            )

        except Exception as e:

            print(
                f"Invalid JSON: {e}",
                flush=True
            )

            self.send_json(
                400,
                {
                    "error": "invalid json"
                }
            )

            return

        print(
            "Received Grafana notification:",
            json.dumps(
                data,
                indent=2
            ),
            flush=True
        )

        try:

            message = format_message(
                data
            )

            send_to_talk(
                message
            )

            self.send_json(
                200,
                {
                    "status": "sent"
                }
            )

        except Exception as e:

            print(
                f"Failed to send Talk message: {e}",
                flush=True
            )

            self.send_json(
                502,
                {
                    "error":
                    "failed to send to Nextcloud Talk"
                }
            )


if __name__ == "__main__":

    print(
        "Grafana → Nextcloud Talk bridge "
        f"listening on {LISTEN_HOST}:{LISTEN_PORT}",
        flush=True
    )

    server = ThreadingHTTPServer(
        (LISTEN_HOST, LISTEN_PORT),
        Handler
    )

    server.serve_forever()
