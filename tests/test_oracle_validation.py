"""
Tests for Independent Ground-Truth Evaluation Oracle.
Verifies restoration correctness against verified reference outputs using standard NLP
metrics (Token F1, Character Similarity, Entity Recovery) completely independent of the
internal readability scoring heuristic.
"""

from pathlib import Path
import pytest
from unifile.core.pipeline import UnifileEngine
from unifile.core.evaluation_oracle import EvaluationOracle

SAMPLES_DIR = Path(__file__).parent.parent / "samples"
GT_DIR = SAMPLES_DIR / "ground_truth"

GROUND_TRUTH_CASES = [
    (
        "zalgo_symbol_corrupted.txt",
        "zalgo_symbol_reference.txt",
        "en",
        ["Restoration Protocol", "operational parameters", "Authentication", "telemetry"]
    ),
    (
        "encrypted_base64_hex_contract.txt",
        "encrypted_contract_reference.txt",
        "en",
        ["CONTRACT-2026-ALPHA", "CONFIDENTIAL PARTNERSHIP AGREEMENT", "Healthy System Status OK", "MIT"]
    ),
    (
        "truncated_broken_json.json",
        "truncated_json_reference.txt",
        "en",
        ["Soniscorett Unifile Universal Connector", "us-east-1a", "eu-central-1", "ap-southeast-1"]
    ),
    (
        "mojibake_latin1_sample.txt",
        "mojibake_latin1_reference.txt",
        "fr",
        ["120 000", "RGPD", "SÉCURITÉ", "100%"]
    ),
    (
        "multilingual_garbled_spec.txt",
        "multilingual_spec_reference.txt",
        "es",
        ["ESPECIFICACIÓN", "UNIFILE", "SONISCORETT", "80%"]
    ),
    (
        "sample_report.docx",
        "sample_report_reference.txt",
        "fr",
        ["MOD-01", "MOD-02", "Mojibake & Distortion Healer", "Universal Parser Read-Only"]
    ),
    (
        "sample_data.xlsx",
        "sample_data_reference.txt",
        "en",
        ["T-101", "T-102", "T-103", "T-104"]
    ),
    (
        "sample_document.pdf",
        "sample_document_reference.txt",
        "en",
        ["Unifile", "Soniscorett", "Telemetry"]
    ),
]


@pytest.mark.parametrize("corrupt_file,reference_file,lang,critical_entities", GROUND_TRUTH_CASES)
def test_ground_truth_restoration_oracle(corrupt_file, reference_file, lang, critical_entities):
    """
    Evaluates candidate restoration against verified ground truth.
    Asserts composite accuracy >= 80% and passed_oracle is True.
    """
    corrupt_path = SAMPLES_DIR / corrupt_file
    ref_path = GT_DIR / reference_file

    assert corrupt_path.exists(), f"Corrupt file missing: {corrupt_file}"
    assert ref_path.exists(), f"Ground-truth reference file missing: {reference_file}"

    reference_text = ref_path.read_text(encoding="utf-8")
    result = UnifileEngine.process_file(corrupt_path, preferred_language=lang)

    evaluation = EvaluationOracle.evaluate_against_ground_truth(
        restored_text=result.cleaned_text,
        reference_text=reference_text,
        critical_entities=critical_entities
    )

    acc = evaluation["composite_accuracy"]
    assert acc >= 80.0, (
        f"Ground-truth accuracy below 80% on {corrupt_file}: "
        f"Composite Accuracy: {acc:.2f}%, Token F1: {evaluation['token_f1']}%, "
        f"Char Sim: {evaluation['character_similarity']}%, "
        f"Entity Recovery: {evaluation['entity_recovery_rate']}%"
    )
    assert evaluation["passed_oracle"] is True
