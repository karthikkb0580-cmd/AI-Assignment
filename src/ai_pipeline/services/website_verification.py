import asyncio
import ipaddress
import re
import socket

from dataclasses import dataclass
from html import unescape
from urllib.parse import urljoin, urlsplit

import aiohttp
from aiohttp.abc import AbstractResolver


MAX_REDIRECTS = 5
MAX_RESPONSE_BYTES = 1_000_000
REQUEST_TIMEOUT = 10


@dataclass
class WebsiteEvidence:
    url: str
    reachable: bool
    status_code: int | None
    final_url: str | None
    title: str | None
    error: str | None


def is_safe_ip(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
        return address.is_global
    except ValueError:
        return False


def is_valid_public_url(url: str | None) -> bool:
    if not isinstance(url, str):
        return False

    if not url or url != url.strip():
        return False

    if any(ord(char) < 32 or ord(char) == 127 for char in url):
        return False

    try:
        parsed = urlsplit(url)

        if parsed.scheme not in {"http", "https"}:
            return False

        if not parsed.hostname:
            return False

        if parsed.username is not None or parsed.password is not None:
            return False

        if parsed.fragment:
            return False

        if parsed.hostname.lower().rstrip(".") == "localhost":
            return False

        port = parsed.port

        if port is not None and port not in {80, 443}:
            return False

        hostname = parsed.hostname

        try:
            address = ipaddress.ip_address(hostname)
            return address.is_global
        except ValueError:
            pass

        if "." not in hostname:
            return False

        hostname.encode("idna")

        return True

    except (ValueError, UnicodeError):
        return False


def extract_title(html: str) -> str | None:
    match = re.search(
        r"<title\b[^>]*>(.*?)</title\s*>",
        html,
        re.IGNORECASE | re.DOTALL,
    )

    if not match:
        return None

    return " ".join(unescape(match.group(1)).split()) or None


async def resolve_public_ips(hostname: str) -> list[str]:
    loop = asyncio.get_running_loop()

    results = await loop.getaddrinfo(
        hostname,
        None,
        type=socket.SOCK_STREAM,
    )

    addresses = sorted(
        {result[4][0] for result in results}
    )

    if not addresses:
        raise ValueError("DNS returned no addresses")

    if not all(is_safe_ip(address) for address in addresses):
        raise ValueError("DNS resolved to a non-public IP")

    return addresses


class PublicOnlyResolver(AbstractResolver):
    """
    Resolve hostnames and return only validated public IPs.

    aiohttp's TCPConnector uses these resolved addresses for
    the actual connection, avoiding a separate DNS lookup
    between validation and connection.
    """

    async def resolve(
        self,
        host: str,
        port: int = 0,
        family: int = socket.AF_UNSPEC,
    ) -> list[dict]:

        addresses = await resolve_public_ips(host)

        return [
            {
                "hostname": host,
                "host": address,
                "port": port,
                "family": (
                    socket.AF_INET6
                    if ":" in address
                    else socket.AF_INET
                ),
                "proto": socket.IPPROTO_TCP,
                "flags": socket.AI_NUMERICHOST,
            }
            for address in addresses
        ]

    async def close(self) -> None:
        pass


async def collect_website_evidence(
    url: str | None,
) -> WebsiteEvidence:

    original_url = url or ""

    if not is_valid_public_url(url):
        return WebsiteEvidence(
            url=original_url,
            reachable=False,
            status_code=None,
            final_url=None,
            title=None,
            error="Invalid or unsafe URL",
        )

    assert url is not None

    current_url = url

    timeout = aiohttp.ClientTimeout(
        total=REQUEST_TIMEOUT,
        connect=5,
        sock_read=5,
    )

    connector = aiohttp.TCPConnector(
        resolver=PublicOnlyResolver(),
        use_dns_cache=False,
        ssl=True,
        limit=10,
        force_close=True,
    )

    try:
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            trust_env=False,
            auto_decompress=False,
            headers={
                "User-Agent": "AI-Intelligence-Pipeline/0.1",
                "Accept": "text/html",
                "Accept-Encoding": "identity",
            },
        ) as session:

            for redirect_number in range(MAX_REDIRECTS + 1):

                if not is_valid_public_url(current_url):
                    raise ValueError("Unsafe redirect destination")

                async with session.get(
                    current_url,
                    allow_redirects=False,
                ) as response:

                    if response.status in {
                        301, 302, 303, 307, 308
                    }:
                        if redirect_number >= MAX_REDIRECTS:
                            raise ValueError(
                                "Maximum redirects exceeded"
                            )

                        location = response.headers.get("Location")

                        if not location:
                            raise ValueError(
                                "Redirect missing Location header"
                            )

                        current_url = urljoin(
                            current_url,
                            location,
                        )

                        if not is_valid_public_url(current_url):
                            raise ValueError(
                                "Unsafe redirect destination"
                            )

                        continue

                    content_type = response.headers.get(
                        "Content-Type", ""
                    ).lower()

                    if not (
                        content_type.startswith("text/html")
                        or content_type.startswith("application/xhtml+xml")
                    ):
                        return WebsiteEvidence(
                            url=original_url,
                            reachable=200 <= response.status < 400,
                            status_code=response.status,
                            final_url=str(response.url),
                            title=None,
                            error=None,
                        )

                    content = bytearray()

                    async for chunk in response.content.iter_chunked(8192):
                        content.extend(chunk)

                        if len(content) > MAX_RESPONSE_BYTES:
                            raise ValueError(
                                "Website response too large"
                            )

                    html = content.decode(
                        "utf-8",
                        errors="replace",
                    )

                    return WebsiteEvidence(
                        url=original_url,
                        reachable=200 <= response.status < 400,
                        status_code=response.status,
                        final_url=str(response.url),
                        title=extract_title(html),
                        error=None,
                    )

            raise ValueError("Maximum redirects exceeded")

    except (
        aiohttp.ClientError,
        asyncio.TimeoutError,
        ValueError,
        OSError,
    ) as exc:

        return WebsiteEvidence(
            url=original_url,
            reachable=False,
            status_code=None,
            final_url=current_url,
            title=None,
            error=type(exc).__name__ + ": " + str(exc),
        )