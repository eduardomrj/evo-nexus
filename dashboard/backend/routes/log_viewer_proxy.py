"""Proxy HTTP traffic to the local log-viewer server (port 8082).

The log-viewer is a standalone Python HTTP server that binds to 0.0.0.0:8082.
This blueprint mounts it at /log-viewer/* on the main Flask app (port 8080),
so it is reachable through the same reverse proxy entry point (Traefik →
nexus.myworkhome.com.br) without needing a separate Traefik routing rule or
an additional exposed port.

Strip-prefix behavior: Traefik forwards the full path to the Flask app
(/log-viewer/...), and this blueprint strips /log-viewer before forwarding to
the upstream server, which already expects its own BASE_PATH=/logs at root.
The log-viewer server's BASE_PATH env var must be set to /logs (its default),
because after stripping /log-viewer the path it receives starts with /logs.

Wait — actually: the log-viewer already handles BASE_PATH stripping internally.
We forward /log-viewer/... → http://localhost:8082/log-viewer/... so the
log-viewer strips its own BASE_PATH (/logs) from the path. That means the
log-viewer needs BASE_PATH=/log-viewer to match what the proxy forwards.

Simpler approach: proxy /log-viewer/* transparently, passing the full path
as-is to the log-viewer, and set BASE_PATH=/log-viewer on the log-viewer.
"""

from __future__ import annotations

import logging
import os

import requests
from flask import Blueprint, Response, request, stream_with_context
from flask_login import current_user, login_required

log = logging.getLogger(__name__)

bp = Blueprint("log_viewer_proxy", __name__)

LOG_VIEWER_HOST = os.environ.get("LOG_VIEWER_HOST", "127.0.0.1")
LOG_VIEWER_PORT = int(os.environ.get("LOG_VIEWER_PORT", "8082"))
LOG_VIEWER_BASE = f"http://{LOG_VIEWER_HOST}:{LOG_VIEWER_PORT}"

# Hop-by-hop headers that must not be forwarded (RFC 7230 §6.1).
_HOP_BY_HOP = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
    }
)


def _forward_headers(src: dict[str, str]) -> dict[str, str]:
    return {k: v for k, v in src.items() if k.lower() not in _HOP_BY_HOP}


@bp.route(
    "/log-viewer/<path:subpath>",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
@bp.route("/log-viewer/", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
@bp.route("/log-viewer", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
@login_required
def proxy_http(subpath: str = ""):
    """Forward HTTP traffic to the local log-viewer server."""
    # Reconstruct path: forward the full /log-viewer/... path so that the
    # log-viewer (running with BASE_PATH=/log-viewer) can strip it itself.
    upstream_path = f"/log-viewer/{subpath}" if subpath else "/log-viewer"
    target = f"{LOG_VIEWER_BASE}{upstream_path}"
    if request.query_string:
        target = f"{target}?{request.query_string.decode('latin-1')}"

    log.debug("log_viewer_proxy → %s %s", request.method, target)

    try:
        upstream = requests.request(
            method=request.method,
            url=target,
            headers=_forward_headers(dict(request.headers)),
            data=request.get_data(),
            allow_redirects=False,
            stream=True,
            timeout=15,
        )
    except requests.exceptions.ConnectionError:
        return (
            "Log Viewer is not running. Start it via "
            "`bash /home/evonexus/evo-projects/log-viewer/start.sh`.",
            503,
        )
    except requests.exceptions.Timeout:
        return "Log Viewer timed out.", 504

    response = Response(
        stream_with_context(upstream.iter_content(chunk_size=8192)),
        status=upstream.status_code,
    )
    for key, value in upstream.headers.items():
        if key.lower() not in _HOP_BY_HOP:
            response.headers[key] = value

    return response
