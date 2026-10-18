"""
Unifile by Soniscorett - Network Security & SSRF Protection Guard
Validates outbound destinations, blocks internal/reserved IP ranges,
and securely handles redirects to prevent Server-Side Request Forgery (SSRF).
"""

from __future__ import annotations

import ipaddress
import os
import socket
import ssl
import urllib.parse

import httpcore
import httpx


class _PinnedDNSBackend(httpcore.SyncBackend):
    """Validate every DNS answer and connect to a numeric IP to prevent re-resolution races."""

    def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        try:
            answers = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise SecurityValidationError(f"DNS resolution failed for '{host}': {exc}") from exc
        if not answers:
            raise SecurityValidationError(f"DNS resolution returned no addresses for '{host}'.")

        addresses = []
        seen = set()
        for family, socktype, proto, canonname, sockaddr in answers:
            ip_str = sockaddr[0]
            if NetworkGuard.is_ip_blocked(ip_str):
                raise SecurityValidationError(
                    f"Connection blocked: '{host}' resolved to prohibited IP address '{ip_str}'."
                )
            if ip_str not in seen:
                seen.add(ip_str)
                addresses.append((family, ip_str))

        # Connect to the vetted numeric address. httpcore still uses the URL hostname
        # for TLS SNI and certificate hostname verification after the TCP connection.
        family, pinned_ip = addresses[0]
        return super().connect_tcp(
            host=pinned_ip,
            port=port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )


def _guarded_transport():
    """Build an HTTPX transport with DNS validation at the actual socket boundary."""
    ssl_context = ssl.create_default_context()
    pool = httpcore.ConnectionPool(
        ssl_context=ssl_context,
        max_connections=20,
        max_keepalive_connections=5,
        keepalive_expiry=5.0,
        network_backend=_PinnedDNSBackend(),
    )
    transport = httpx.HTTPTransport(trust_env=False)
    transport._pool.close()
    transport._pool = pool
    return transport


# Permitted public AI conversation share platforms
ALLOWED_SHARE_DOMAINS: set[str] = {
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


class NetworkGuard:
    """Outbound request validator enforcing zero-trust SSRF defense."""

    @classmethod
    def get_allowed_domains(cls) -> set[str]:
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

        # Block localhost variants directly; 0.0.0.0 is a prohibited target, not a bind address.
        if hostname in ("localhost", "127.0.0.1", "::1", "0.0.0.0", "instance-data"):  # nosec B104
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
            raise SecurityValidationError(f"DNS resolution failed for '{hostname}': {e!s}")

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
    ) -> tuple[str, str]:
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

        # Disable environment proxies so requests cannot bypass the guarded socket transport.
        with httpx.Client(
            timeout=httpx.Timeout(10.0, connect=5.0),
            trust_env=False,
            transport=_guarded_transport(),
        ) as client:
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
