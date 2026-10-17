# UniFile by SoniscoreTT

**Experimental, read-only file inspection and text-recovery tools for AI workflows.** UniFile provides a Python library, command-line interface, REST API, MCP connector, and browser dashboard for parsing supported file formats and attempting to recover text affected by encoding or structural corruption.

> **Status:** Experimental. The test suite passes locally, but this project has not had an independent security audit. Do not expose the service directly to the public internet or use it as a security boundary.

## Features

- Parse common document, spreadsheet, presentation, text, markup, archive, and image formats where supported by the installed dependencies.
- Attempt recovery of mojibake, Unicode noise, common obfuscations, and malformed/truncated structures.
- Provide REST endpoints, a command-line interface, and MCP tooling.
- Inspect shared conversation URLs from a limited allowlist of AI platforms.
- Return readability diagnostics intended to help downstream applications evaluate recovered text.

Recovery is heuristic. Translation coverage, file support, and readability scores depend on input content and processing paths; no universal recovery or readability percentage is guaranteed.

## Requirements

- Python 3.9 or newer
- Installable dependencies listed in `pyproject.toml`

## Install for development

```bash
python -m pip install -e ".[test]"
python -m pytest -q
```

## Run

Read a file from the command line:

```bash
unifile path/to/file.txt
```

Start the local API and dashboard:

```bash
unifile --server --host 127.0.0.1 --port 8000
```

The server defaults to loopback binding when started from the CLI. Only bind to `0.0.0.0` when you intentionally need network access and have configured appropriate network controls. Container deployment binds to all interfaces; review `Dockerfile`, `docker-compose.yml`, and `SECURITY.md` before deploying.

Health endpoint: `GET http://127.0.0.1:8000/api/v1/health`

## Security notes

Read [SECURITY.md](SECURITY.md) before enabling network access or using conversation URL retrieval. The URL fetcher has allowlist, DNS, redirect, and response-size checks, but DNS validation is not pinned to the subsequent HTTP connection; DNS rebinding is therefore not fully mitigated. The project is not an independently audited sandbox. Run with least privilege and avoid processing sensitive material in an untrusted deployment.

The API defaults to localhost CORS origins. Credentialed CORS is disabled unless explicitly enabled with `UNIFILE_CORS_ALLOW_CREDENTIALS=true` and a non-wildcard origin list is configured through `UNIFILE_CORS_ORIGINS`.

## Tests

Run `python -m pytest -q`. The suite covers core processing, connectors, read-only expectations, and selected network-guard cases. Passing tests do not establish that the application is free of security vulnerabilities.

## Samples and reports

- `samples/` contains test inputs and generated fixtures.
- `samples/ground_truth/` contains reference outputs used by selected tests.
- `READABILITY_VALIDATION_REPORT.md` records project-specific readability validation. Treat its results as scoped to the described data and methodology, not as an independent audit.

## License

MIT. See [LICENSE](LICENSE).
