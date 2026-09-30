"""
Shared SSRF guard for any code path that sends a request to an
admin- or visitor-supplied URL: knowledge-base URL ingestion
(knowledge_extract.py) and outbound webhook delivery
(webhook_service.py) both go through this. Resolves the hostname and
rejects anything that lands on a private, loopback, link-local,
reserved, or multicast address.

"Trusted admin" is not a reason to skip this — an admin account can
be compromised, or a well-meaning admin can register a URL without
realizing where it points. This is reasonable defense-in-depth, not a
complete guarantee: it doesn't defend against DNS rebinding (resolving
safely at check time, then differently at request time), which would
need a proxy or a strict allowlist to fully close. For webhook
delivery specifically — where the same URL is hit repeatedly over the
webhook's whole lifetime, not just once — callers should re-run this
check on every delivery attempt, not only at create/update time, so a
URL that starts out public but later gets re-pointed at an internal
address (DNS change post-registration) is still caught.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

_BLOCKED_HOSTNAMES = {"localhost"}


class UnsafeUrlError(Exception):
    """Raised when a URL fails the public-reachability check: a
    disallowed scheme, an unresolvable host, or an address that isn't
    safely public (private/loopback/link-local/reserved/multicast)."""


def assert_public_http_url(url: str) -> None:
    """Raises UnsafeUrlError unless `url` is http(s) and resolves only
    to public addresses. Checks *every* address a hostname resolves to
    (a name can have multiple A/AAAA records) — all must be public."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeUrlError("Only http:// and https:// URLs are supported.")
    if not parsed.hostname:
        raise UnsafeUrlError("That doesn't look like a valid URL.")
    if parsed.hostname.lower() in _BLOCKED_HOSTNAMES:
        raise UnsafeUrlError("That address isn't allowed.")

    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as e:
        raise UnsafeUrlError(f"Could not resolve host: {e}") from e

    for _family, _type, _proto, _canonname, sockaddr in infos:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise UnsafeUrlError("That address resolves to a non-public location and isn't allowed.")
