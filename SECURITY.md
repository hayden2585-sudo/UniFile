# Security status

Unifile processes user-supplied files and may fetch public conversation-share URLs. Treat it as experimental software until a security review and the full test suite have been completed. Do not expose it directly to the public internet or submit sensitive files to an untrusted deployment.

## Current safeguards and limitations

- The HTTP server defaults to loopback binding when launched through the CLI or module entry point. Container deployment explicitly binds to all interfaces; put it behind an appropriately configured trusted network boundary.
- CORS defaults to localhost origins. Credentialed CORS is opt-in and disabled when wildcard origins are configured.
- The network guard checks an allowlist, DNS answers, redirect destinations, and streamed response size. **DNS validation and the later HTTP connection are not pinned to the same resolved IP**, so DNS rebinding is not fully mitigated. Do not treat the URL fetcher as production-grade SSRF protection until this is fixed and tested.
- Read-only behavior is an application-level contract, not a sandbox. Run with least privilege and do not grant the service write access to sensitive directories.
- No independent penetration test or comprehensive dependency audit is claimed by this repository.

## Reporting

Please do not publish exploit details involving private user data. Report suspected vulnerabilities privately to the repository maintainer and include reproduction steps with non-sensitive test data.
