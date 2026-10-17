"""
Automated Pytest Suite for Independent Readability Validation.
Systematically validates readability claims across representative files and languages.
"""

from pathlib import Path
import pytest
from unifile.core.pipeline import UnifileEngine

SAMPLES_DIR = Path(__file__).parent.parent / "samples"

REPRESENTATIVE_CASES = [
    ("mojibake_latin1_sample.txt", "en"),
    ("mojibake_latin1_sample.txt", "es"),
    ("mojibake_latin1_sample.txt", "fr"),
    ("zalgo_symbol_corrupted.txt", "en"),
    ("zalgo_symbol_corrupted.txt", "de"),
    ("encrypted_base64_hex_contract.txt", "en"),
    ("encrypted_base64_hex_contract.txt", "es"),
    ("truncated_broken_json.json", "en"),
    ("truncated_broken_json.json", "ja"),
    ("multilingual_garbled_spec.txt", "en"),
    ("multilingual_garbled_spec.txt", "fr"),
    ("sample_report.docx", "en"),
    ("sample_report.docx", "es"),
    ("sample_data.xlsx", "en"),
    ("sample_data.xlsx", "de"),
    ("sample_document.pdf", "en"),
]


@pytest.mark.parametrize("filename,target_lang", REPRESENTATIVE_CASES)
def test_independent_readability_validation(filename: str, target_lang: str):
    """Asserts that every representative file and language hits >= 80.0% readability."""
    filepath = SAMPLES_DIR / filename
    assert filepath.exists(), f"Sample file missing: {filename}"

    res = UnifileEngine.process_file(filepath, preferred_language=target_lang)
    score = res.final_report.score

    assert score >= 80.0, f"Readability failure on {filename} ({target_lang}): score was {score:.2f}% (< 80.0%)"
    assert res.final_report.passed is True
    assert res.metadata["read_only"] is True
