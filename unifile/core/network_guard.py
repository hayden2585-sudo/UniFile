"""
Unifile by Soniscorett - Network Security & SSRF Protection Guard
Validates outbound destinations, blocks internal/reserved IP ranges,
and securely handles redirects to prevent Server-Side Request Forgery (SSRF).
"""

from __future__ import annotations
import ipaddress
import os
import socket
import urllib.parse
from typing import Tuple, Optional, Set, List
import httpx

# Permitted public AI conversation share platforms
ALLOWED_SHARE_DOMAINS: Set[str] = {
    "chatgpt.com",
    "chat.openai.com",
    "claude.ai",
    "perplexity.ai",
    "www.perplexity.ai",
    "gemini.google.com",
}

# Maximum allowed response size for retrieved share conversations (5 MB)
MAX_SHARE_PAYLOAD_BYTES = 5 * 1024 * 1024
MAX_REDIRECT_HOPS = 3


class SecurityValidationError(ValueError):
    """Raised when an outbound URL fails security / SSRF validation."""
    pass


class NetworkGuard:
    """Outbound request validator enforcing zero-trust SSRF defense."""

    @classmethod
    def get_allowed_domains(cls) -> Set[str]:
        """Returns allowed domains, incorporating any optional UNIFILE_ALLOWED_DOMAINS env var."""
        domains = set(ALLOWED_SHARE_DOMAINS)
        custom = os.environ.get("UNIFILE_ALLOWED_DOMAINS")
        if custom:
            for d in custom.split(","):
                d = d.strip().lower()
                if d:
                    domains.add(d)
        return domains

    @classmethod
    def is_ip_blocked(cls, ip_str: str) -> bool:
        """
        Checks whether an IP address belongs to private, loopback, link-local,
        cloud metadata (169.254.169.254), or reserved ranges.
        """
        try:
            ip = ipaddress.ip_address(ip_str)
            return (
                ip.is_private or
                ip.is_loopback or
                ip.is_link_local or
                ip.is_reserved or
                ip.is_multicast or
                ip.is_unspecified
            )
        except ValueError:
            return True

    @classmethod
    def validate_url(cls, url: str, enforce_domain_allowlist: bool = True) -> urllib.parse.ParseResult:
        """
        Validates URL scheme, domain allowlist, and DNS resolution against SSRF.
        Raises SecurityValidationError if destination is suspicious or prohibited.
        """
        parsed = urllib.parse.urlparse(url.strip())

        # 1. Scheme Validation
        if parsed.scheme.lower() not in ("http", "https"):
            raise SecurityValidationError(f"Invalid URL scheme '{parsed.scheme}'. Only HTTP and HTTPS are permitted.")

        # 2. Hostname Validation
        hostname = (parsed.hostname or "").lower()
        if not hostname:
            raise SecurityValidationError("URL must include a valid hostname.")

        # Block localhost variants directly
        if hostname in ("localhost", "127.0.0.1", "::1", "0.0.0.0", "instance-data"):
            raise SecurityValidationError(f"Access to '{hostname}' is prohibited (loopback/local host).")

        # 3. Domain Allowlist Check
        if enforce_domain_allowlist:
            allowed_domains = cls.get_allowed_domains()
            matched = False
            for allowed in allowed_domains:
                if hostname == allowed or hostname.endswith("." + allowed):
                    matched = True
                    break
            if not matched:
                raise SecurityValidationError(
                    f"Domain '{hostname}' is not in the permitted AI conversation platform allowlist. "
                    f"Permitted platforms: {', '.join(sorted(allowed_domains))}."
                )

        # 4. DNS Resolution & Private IP Range Validation
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        try:
            addr_info = socket.getaddrinfo(hostname, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        except socket.gaierror as e:
            raise SecurityValidationError(f"DNS resolution failed for '{hostname}': {str(e)}")

        for family, socktype, proto, canonname, sockaddr in addr_info:
            ip_str = sockaddr[0]
            if cls.is_ip_blocked(ip_str):
                raise SecurityValidationError(
                    f"Destination '{hostname}' resolved to prohibited IP address '{ip_str}' "
                    "(private/internal/cloud-metadata network blocked)."
                )

        return parsed

    @classmethod
    def safe_fetch(
        cls,
        url: str,
        user_agent: str,
        enforce_domain_allowlist: bool = True,
        max_bytes: int = MAX_SHARE_PAYLOAD_BYTES
    ) -> Tuple[str, str]:
        """
        Executes a secure outbound HTTP GET request with hop-by-hop redirect validation,
        size capping, and SSRF defense.
        Returns: (response_text, final_resolved_url)
        """
        current_url = url
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9",
        }

        with httpx.Client(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
            for hop in range(MAX_REDIRECT_HOPS + 1):
                # Validate URL before every request (including redirects)
                cls.validate_url(current_url, enforce_domain_allowlist=enforce_domain_allowlist)

                # Stream the response so the byte cap is enforced before the full body
                # is buffered in memory. Redirects are inspected before consuming a body.
                with client.stream(
                    "GET",
                    current_url,
                    headers=headers,
                    follow_redirects=False,  # Manually inspect redirects
                ) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise SecurityValidationError("Redirect response missing Location header.")
                        current_url = urllib.parse.urljoin(current_url, location)
                        continue

                    response.raise_for_status()
                    chunks = []
                    total_bytes = 0
                    for chunk in response.iter_bytes():
                        total_bytes += len(chunk)
                        if total_bytes > max_bytes:
                            raise SecurityValidationError(
                                f"Response payload exceeds maximum safe limit ({max_bytes} bytes)."
                            )
                        chunks.append(chunk)
                    content_bytes = b"".join(chunks)
                    encoding = response.encoding or "utf-8"

                return content_bytes.decode(encoding, errors="replace"), current_url

            raise SecurityValidationError(f"Exceeded maximum redirect limit ({MAX_REDIRECT_HOPS} hops).")
