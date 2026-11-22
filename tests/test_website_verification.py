import pytest

from ai_pipeline.services.website_verification import (
    is_safe_ip,
    is_valid_public_url,
    resolve_public_ips,
    collect_website_evidence,
)


def test_private_ipv4_rejected():
    assert is_safe_ip("192.168.1.1") is False
    assert is_safe_ip("10.0.0.1") is False
    assert is_safe_ip("172.16.0.1") is False


def test_loopback_ipv4_rejected():
    assert is_safe_ip("127.0.0.1") is False


def test_link_local_rejected():
    assert is_safe_ip("169.254.169.254") is False


def test_private_ipv6_rejected():
    assert is_safe_ip("fc00::1") is False
    assert is_safe_ip("::1") is False


def test_public_ip_accepted():
    assert is_safe_ip("8.8.8.8") is True
    assert is_safe_ip("1.1.1.1") is True


def test_invalid_ip_rejected():
    assert is_safe_ip("not-an-ip") is False


def test_private_ip_url_rejected():
    assert is_valid_public_url(
        "http://192.168.1.1"
    ) is False


def test_cloud_metadata_url_rejected():
    assert is_valid_public_url(
        "http://169.254.169.254/latest/meta-data/"
    ) is False


def test_unsafe_port_rejected():
    assert is_valid_public_url(
        "http://example.com:8080"
    ) is False


def test_credentials_in_url_rejected():
    assert is_valid_public_url(
        "https://user:password@example.com"
    ) is False


@pytest.mark.asyncio
async def test_invalid_url_returns_evidence():
    result = await collect_website_evidence(
        "http://127.0.0.1"
    )

    assert result.reachable is False
    assert result.error is not None


@pytest.mark.asyncio
async def test_dns_resolution_rejects_private_ip(monkeypatch):

    async def fake_getaddrinfo(
        hostname,
        port,
        type,
    ):
        return [
            (
                2,
                1,
                6,
                "",
                ("192.168.1.10", 0),
            )
        ]

    loop = __import__("asyncio").get_running_loop()

    monkeypatch.setattr(
        loop,
        "getaddrinfo",
        fake_getaddrinfo,
    )

    with pytest.raises(
        ValueError,
        match="non-public",
    ):
        await resolve_public_ips("example.com")