"""Fetch HTML from a URL with SSRF protection and size limits."""
import ipaddress
import socket
from typing import Tuple
from urllib.parse import urlparse

import httpx

from app.config import get_settings


class FetchError(Exception):
    """Custom exception for URL fetching errors."""
    pass


# Schemes we accept
ALLOWED_SCHEMES = {"http", "https"}

# Networks we refuse to fetch from (SSRF protection)
BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

MAX_URL_LENGTH = 2048


def _is_blocked_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True
    return any(ip in net for net in BLOCKED_NETWORKS)


def _validate_url(url: str) -> str:
    """Reject obviously malicious URLs before we touch the network."""
    if len(url) > MAX_URL_LENGTH:
        raise FetchError(f"URL exceeds {MAX_URL_LENGTH} character limit")

    parsed = urlparse(url)
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise FetchError(f"Only http(s) URLs are allowed (got: {parsed.scheme})")

    hostname = parsed.hostname
    if not hostname:
        raise FetchError("URL is missing a hostname")

    lowered = hostname.lower()
    if lowered in {"localhost", "ip6-localhost", "ip6-loopback"}:
        raise FetchError("Refusing to fetch localhost")

    if lowered.endswith(".local") or lowered.endswith(".internal"):
        raise FetchError("Refusing to fetch internal hostnames")

    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise FetchError(f"DNS resolution failed: {e}")

    for info in infos:
        ip = info[4][0]
        if _is_blocked_ip(ip):
            raise FetchError(f"Refusing to fetch private/reserved address ({ip})")

    return hostname


async def fetch_url(url: str, timeout: int = 15) -> Tuple[str, int]:
    """Fetch HTML content from a URL with safety guards."""
    _validate_url(url)
    settings = get_settings()
    max_bytes = settings.max_html_bytes

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; SchematoAIO/1.0; +https://schematoaio.kikib.zocomputer.io)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, max_redirects=5) as client:
            async with client.stream("GET", url, headers=headers) as response:
                response.raise_for_status()

                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > max_bytes:
                    raise FetchError(f"Response too large ({content_length} bytes)")

                buf = bytearray()
                async for chunk in response.aiter_bytes():
                    buf.extend(chunk)
                    if len(buf) > max_bytes:
                        raise FetchError(f"Response exceeded {max_bytes} bytes during download")

                encoding = response.encoding or "utf-8"
                try:
                    text = buf.decode(encoding, errors="replace")
                except LookupError:
                    text = buf.decode("utf-8", errors="replace")
                return text, response.status_code

    except FetchError:
        raise
    except httpx.TimeoutException:
        raise FetchError(f"Request timeout after {timeout} seconds")
    except httpx.HTTPStatusError as e:
        raise FetchError(f"HTTP {e.response.status_code}: {e.response.reason_phrase}")
    except httpx.RequestError as e:
        raise FetchError(f"Request failed: {str(e)}")
    except Exception as e:
        raise FetchError(f"Unexpected error: {str(e)}")
