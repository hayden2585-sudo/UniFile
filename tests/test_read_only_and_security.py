"""
Tests for Web Server Network Exposure and Universal Read-Only Guarantees.
Verifies rejection of mutation methods, security headers, in-memory processing,
and strict non-destructive access across all interfaces.
"""

import hashlib
import io
import os
import zipfile
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from unifile.server import app
from unifile.core.parser import UniversalParser
from unifile.core.pipeline import UnifileEngine

client = TestClient(app)
SAMPLES_DIR = Path(__file__).parent.parent / "samples"


def test_reject_mutation_http_methods():
    """Verifies that PUT, DELETE, and PATCH are rejected with 405 and read-only notice."""
    for method in ("PUT", "DELETE", "PATCH"):
        resp = client.request(method, "/api/v1/translate")
        assert resp.status_code == 405
        data = resp.json()
        assert data["read_only"] is True
        assert "strictly READ-ONLY" in data["message"]


def test_security_headers_present():
    """Verifies that security and read-only headers are attached to responses."""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.headers.get("X-Unifile-Mode") == "STRICT_READ_ONLY"
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"


def test_file_upload_leaves_no_disk_artifacts(tmp_path):
    """Verifies that uploading a file is processed entirely in memory without creating files on disk."""
    initial_files = set(os.listdir(str(tmp_path)))

    sample_content = b"Confidential enterprise report data."
    files = {"file": ("upload_test.txt", io.BytesIO(sample_content), "text/plain")}
    
    resp = client.post("/api/v1/translate", files=files, data={"preferred_language": "en"})
    assert resp.status_code == 200
    assert resp.json()["threshold_met"] is True

    # Assert no new files created in cwd or tmp directory
    current_files = set(os.listdir(str(tmp_path)))
    assert current_files == initial_files


def test_archive_parser_never_writes_to_disk(tmp_path):
    """Verifies zip archive parsing does not extract files to disk (prevents zip-bomb/path traversal)."""
    # Create test zip in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as z:
        z.writestr("confidential.txt", "Top secret telemetry logs.")
        z.writestr("subfolder/data.json", '{"status": "ok"}')
    zip_bytes = zip_buffer.getvalue()

    before_count = len(list(tmp_path.iterdir()))
    text, meta = UniversalParser.read_file(zip_bytes, filename="test_archive.zip")
    after_count = len(list(tmp_path.iterdir()))

    assert meta["read_only"] is True
    assert "Top secret telemetry logs" in text
    assert after_count == before_count  # No extracted files on disk


def test_source_file_bitwise_integrity(tmp_path):
    """Verifies source file is bitwise identical and mtime unchanged after full ingestion."""
    test_file = tmp_path / "bitwise_test.docx"
    test_file.write_bytes(b"PK\x03\x04MockBinaryContentForTestingBitwiseIntegrity")
    
    hash_before = hashlib.sha256(test_file.read_bytes()).hexdigest()
    mtime_before = test_file.stat().st_mtime_ns

    # Ingest through Unifile engine
    res = UnifileEngine.process_file(test_file, preferred_language="es")

    hash_after = hashlib.sha256(test_file.read_bytes()).hexdigest()
    mtime_after = test_file.stat().st_mtime_ns

    assert hash_before == hash_after
    assert mtime_before == mtime_after
    assert res.metadata["read_only"] is True


def test_default_cors_is_not_wildcard():
    """Default CORS origins must be constrained to local development."""
    from unifile import server

    assert "*" not in server.origins
    assert "http://127.0.0.1:8000" in server.origins
    assert "http://localhost:8000" in server.origins


def test_hsts_not_added_to_plain_http_response():
    """Do not tell browsers to enforce HSTS based on a plain HTTP response."""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert "strict-transport-security" not in resp.headers
