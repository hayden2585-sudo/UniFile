"""
Tests for Network Security and Server-Side Request Forgery (SSRF) Defense.
Validates blocking of private IPs, loopback, link-local/cloud metadata, and non-whitelisted domains.
"""

import http.server
import socket
import ssl
import threading

import httpcore
import pytest
from fastapi.testclient import TestClient
from httpcore._sync.connection import HTTPConnection

from unifile.core.network_guard import (
    NetworkGuard,
    SecurityValidationError,
    _PinnedDNSBackend,
)
from unifile.server import app

client = TestClient(app)

def test_pinned_backend_connects_to_numeric_validated_ip(monkeypatch):
    """The socket backend must receive the validated numeric IP, not the hostname."""
    def fake_getaddrinfo(host, port, family, socktype):
        assert host == "chatgpt.com"
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", port))]

    observed = {}
    def fake_connect(self, host, port, timeout=None, local_address=None, socket_options=None):
        observed["host"] = host
        observed["port"] = port
        return "mock-stream"

    monkeypatch.setattr("unifile.core.network_guard.socket.getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(httpcore.SyncBackend, "connect_tcp", fake_connect)
    stream = _PinnedDNSBackend().connect_tcp("chatgpt.com", 443)
    assert stream == "mock-stream"
    assert observed == {"host": "93.184.216.34", "port": 443}


def test_pinned_backend_rejects_mixed_public_and_private_dns(monkeypatch):
    """A mixed DNS response must be rejected before any socket connection."""
    def fake_getaddrinfo(host, port, family, socktype):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", port)),
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("10.0.0.8", port)),
        ]

    def forbidden_connect(*args, **kwargs):
        pytest.fail("socket connection must not be attempted for mixed public/private DNS")

    monkeypatch.setattr("unifile.core.network_guard.socket.getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(httpcore.SyncBackend, "connect_tcp", forbidden_connect)
    with pytest.raises(SecurityValidationError, match="10.0.0.8"):
        _PinnedDNSBackend().connect_tcp("chatgpt.com", 443)


def test_safe_fetch_uses_guarded_transport_end_to_end(monkeypatch):
    """Exercise HTTPX through the guarded backend without external network access."""
    from unifile.core import network_guard as guard_module

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = b"pinned-transport-ok"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    original_getaddrinfo = socket.getaddrinfo
    original_connect = httpcore.SyncBackend.connect_tcp
    seen_hosts = []

    def fake_getaddrinfo(host, port, family, socktype):
        if host == "chatgpt.com":
            return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", port))]
        return original_getaddrinfo(host, port, family, socktype)

    def local_socket_for_pinned_ip(self, host, port, timeout=None, local_address=None, socket_options=None):
        seen_hosts.append(host)
        target = "127.0.0.1" if host == "93.184.216.34" else host
        return original_connect(self, target, port, timeout, local_address, socket_options)

    monkeypatch.setattr(guard_module.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(httpcore.SyncBackend, "connect_tcp", local_socket_for_pinned_ip)
    try:
        body, final_url = NetworkGuard.safe_fetch(
            f"http://chatgpt.com:{server.server_port}/test", user_agent="security-test"
        )
        assert body == "pinned-transport-ok"
        assert final_url.endswith("/test")
        assert "93.184.216.34" in seen_hosts
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_https_connection_keeps_original_hostname_for_sni_and_verification():
    """Pinned TCP destinations must retain the URL hostname for TLS identity checks."""
    class FakeStream:
        def __init__(self):
            self.tls_kwargs = None

        def start_tls(self, **kwargs):
            self.tls_kwargs = kwargs
            return self

    class FakeBackend:
        def __init__(self):
            self.stream = FakeStream()
            self.connected_host = None

        def connect_tcp(self, **kwargs):
            self.connected_host = kwargs["host"]
            return self.stream

    backend = FakeBackend()
    context = ssl.create_default_context()
    connection = HTTPConnection(
        origin=httpcore.Origin(scheme=b"https", host=b"chatgpt.com", port=443),
        ssl_context=context,
        network_backend=backend,
    )
    connection._connect(httpcore.Request("GET", "https://chatgpt.com/share/test"))

    assert backend.connected_host == "chatgpt.com"
    assert backend.stream.tls_kwargs["server_hostname"] == "chatgpt.com"
    assert backend.stream.tls_kwargs["ssl_context"].verify_mode == ssl.CERT_REQUIRED
    assert backend.stream.tls_kwargs["ssl_context"].check_hostname is True


PROHIBITED_SSRF_URLS = [
    ("http://127.0.0.1:8000/api/v1/health", "loopback IPv4"),
    ("http://localhost:8080/admin", "localhost hostname"),
    ("http://0.0.0.0:80/internal", "unspecified 0.0.0.0"),
    ("http://169.254.169.254/latest/meta-data/", "cloud instance metadata service"),
    ("http://10.0.0.1/internal-network", "RFC 1918 private 10.x.x.x"),
    ("http://192.168.1.1/router-config", "RFC 1918 private 192.168.x.x"),
    ("http://172.16.0.1/private-service", "RFC 1918 private 172.16.x.x"),
    ("file:///etc/passwd", "file URI scheme"),
    ("gopher://127.0.0.1:6379/_flushall", "gopher protocol"),
    ("https://malicious-attacker-domain.com/steal", "unapproved external domain"),
]


def test_dns_answer_with_mixed_public_and_private_addresses_is_rejected(monkeypatch):
    """Reject a hostname if any returned DNS address is private, even alongside a public address."""
    def fake_getaddrinfo(host, port, family, socktype):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", port)),
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("10.0.0.8", port)),
        ]

    monkeypatch.setattr("unifile.core.network_guard.socket.getaddrinfo", fake_getaddrinfo)
    with pytest.raises(SecurityValidationError, match="10.0.0.8"):
        NetworkGuard.validate_url("https://chatgpt.com/share/test-id")


def test_dns_answer_with_ipv6_unique_local_address_is_rejected(monkeypatch):
    """Reject IPv6 unique-local DNS answers."""
    def fake_getaddrinfo(host, port, family, socktype):
        return [(socket.AF_INET6, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("fd00::1", port, 0, 0))]

    monkeypatch.setattr("unifile.core.network_guard.socket.getaddrinfo", fake_getaddrinfo)
    with pytest.raises(SecurityValidationError, match="fd00::1"):
        NetworkGuard.validate_url("https://chatgpt.com/share/test-id")


@pytest.mark.parametrize("url,description", PROHIBITED_SSRF_URLS)
def test_network_guard_blocks_ssrf(url, description):
    """Asserts that NetworkGuard rejects SSRF target URLs."""
    with pytest.raises(SecurityValidationError) as exc_info:
        NetworkGuard.validate_url(url, enforce_domain_allowlist=True)
    assert any(term in str(exc_info.value).lower() for term in ("prohibited", "allowlist", "invalid", "blocked"))


@pytest.mark.parametrize("url,description", PROHIBITED_SSRF_URLS[:5])
def test_context_retrieve_endpoint_blocks_ssrf(url, description):
    """Asserts that /api/v1/context/retrieve returns 400 with SSRF security rejection notice."""
    resp = client.post("/api/v1/context/retrieve", json={
        "source": url,
        "preferred_language": "en"
    })
    assert resp.status_code == 400
    detail = resp.json().get("detail", "")
    assert "Security Policy Rejection (SSRF Defense)" in detail or "prohibited" in detail.lower()


def test_allowed_share_domain_acceptance():
    """Asserts that legitimate public AI conversation platforms pass validation."""
    for domain in ("chatgpt.com", "claude.ai", "perplexity.ai", "gemini.google.com"):
        url = f"https://{domain}/share/valid-share-id"
        # URL parsing and allowlist check should succeed
        parsed = NetworkGuard.validate_url(url, enforce_domain_allowlist=True)
        assert parsed.netloc == domain
