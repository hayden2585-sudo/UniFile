"""
Tests for Network Security and Server-Side Request Forgery (SSRF) Defense.
Validates blocking of private IPs, loopback, link-local/cloud metadata, and non-whitelisted domains.
"""

import pytest
from fastapi.testclient import TestClient

from unifile.core.network_guard import NetworkGuard, SecurityValidationError
from unifile.core.ai_context_bridge import AIContextBridge
from unifile.server import app

client = TestClient(app)

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
