"""
Unit and Integration Tests for Unifile by Soniscorett.
Validates the >= 80% Readability Guarantee on distorted, encrypted, truncated, symbol, and garbled inputs.
"""

import base64
import json
import pytest
from pathlib import Path
from unifile.core.pipeline import UnifileEngine
from unifile.core.readability import assess_readability
from unifile.core.sanitizer import Sanitizer
from unifile.core.mojibake_healer import MojibakeHealer
from unifile.core.deobfuscator import Deobfuscator
from unifile.core.syntax_healer import SyntaxHealer
from unifile.core.translator import UniversalTranslator

SAMPLES_DIR = Path(__file__).parent.parent / "samples"


def test_mojibake_healing():
    """Verifies recovery of double-encoded Latin-1/UTF-8 mojibake."""
    mojibake_input = "L'Ã©quipe d'ingÃ©nierie a dÃ©tectÃ© des problÃ¨mes majeurs."
    res = UnifileEngine.process_text(mojibake_input, preferred_language="en")
    assert res.final_report.passed, f"Expected >= 80%, got {res.final_report.score}%"
    assert res.final_report.score >= 80.0
    assert "équipe" in res.cleaned_text or "team" in res.cleaned_text.lower() or "engineering" in res.cleaned_text.lower()


def test_zalgo_and_symbol_noise_cleaning():
    """Verifies stripping of Zalgo diacritics, zero-width characters, and symbol stutters."""
    zalgo_input = "T\u200bh\u200be̷ ̵s̴y̵s̴t̵e̵m̴ ̷i̵s̴ ̵o̴p̸e̷r̸a̷t̵i̸o̵n̸a̴l̸ a*n*d* *v*e*r*i*f*i*e*d."
    res = UnifileEngine.process_text(zalgo_input, preferred_language="en")
    assert res.final_report.score >= 80.0
    assert "system" in res.cleaned_text.lower()
    assert "operational" in res.cleaned_text.lower()


def test_base64_and_hex_deobfuscation():
    """Verifies unwrapping of embedded and full base64/hex ciphers."""
    secret = "The universal connector provides secure read-only document ingestion for artificial intelligence models."
    b64 = base64.b64encode(secret.encode("utf-8")).decode("ascii")
    raw = f"Audit log header:\ndata:text/plain;base64,{b64}\nEnd of transmission."

    res = UnifileEngine.process_text(raw, preferred_language="en")
    assert res.final_report.score >= 80.0
    assert "universal connector" in res.cleaned_text.lower()
    assert "read-only" in res.cleaned_text.lower()


def test_rot13_cipher_solving():
    """Verifies automated Caesar/ROT-13 frequency analysis and decryption."""
    # ROT-13 of "The security model guarantees eighty percent readability."
    # T -> G, h -> u, e -> r ...
    cipher = "Gur frphevgl zbqry thnenngrrf rvtugl creprag ernqnovyvgl."
    decrypted, act = Deobfuscator.decode_caesar_or_rot(cipher)
    assert act is not None
    assert "security model" in decrypted.lower()
    assert "eighty percent" in decrypted.lower()


def test_truncated_json_healing():
    """Verifies healing of truncated and severed JSON files."""
    broken_json = '{"system": "Soniscorett", "status": "active", "items": [{"id": 101, "name": "Telemetry'
    healed, act = SyntaxHealer.heal_truncated_json(broken_json)
    assert act is not None
    # Must be valid parseable JSON
    parsed = json.loads(healed)
    assert parsed["system"] == "Soniscorett"
    assert parsed["status"] == "active"


def test_multilingual_spanish_translation_guarantee():
    """Verifies translation from garbled Spanish to English hits >= 80% readability."""
    spanish_input = (
        "El sistema universal Unifile por Soniscorett permite a los modelos de inteligencia artificial "
        "procesar cualquier archivo de solo lectura con alta precisiÃ³n y seguridad garantizada."
    )
    res = UnifileEngine.process_text(spanish_input, preferred_language="en")
    assert res.final_report.score >= 80.0
    assert res.final_report.passed
    assert "system" in res.cleaned_text.lower() or "universal" in res.cleaned_text.lower()


def test_sample_files_ingestion():
    """Tests processing of all sample files in samples directory."""
    for sample_file in SAMPLES_DIR.glob("*"):
        if sample_file.suffix in (".txt", ".json", ".docx", ".xlsx", ".pdf"):
            res = UnifileEngine.process_file(sample_file, preferred_language="en")
            assert res.final_report.score >= 80.0, f"Failed on {sample_file.name}: score was {res.final_report.score}%"
            assert res.metadata["read_only"] is True


def test_read_only_safety_guarantee(tmp_path):
    """Verifies source files are never modified or written to (strictly read-only)."""
    test_file = tmp_path / "immutable.txt"
    original_content = "This original source file must remain 100% untouched and unchanged."
    test_file.write_text(original_content, encoding="utf-8")
    mtime_before = test_file.stat().st_mtime

    res = UnifileEngine.process_file(test_file, preferred_language="es")
    assert res.final_report.score >= 80.0
    assert test_file.read_text(encoding="utf-8") == original_content
    assert test_file.stat().st_mtime == mtime_before
