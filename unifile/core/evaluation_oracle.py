"""
Unifile by Soniscorett - Independent Correctness Oracle & Evaluation Engine
Evaluates restoration accuracy against known ground-truth reference outputs using
standard NLP metrics (Token F1, Character Levenshtein Similarity, Entity Recovery)
completely independent of the internal readability heuristic.
"""

from __future__ import annotations
import difflib
import math
import re
from typing import Dict, Any, List, Set, Tuple


class EvaluationOracle:
    """Independent ground-truth correctness oracle."""

    @classmethod
    def tokenize(cls, text: str) -> List[str]:
        """Extracts normalized alphanumeric tokens."""
        return re.findall(r"\b[^\W_]+\b", text.lower())

    @classmethod
    def compute_token_f1(cls, candidate: str, reference: str) -> Dict[str, float]:
        """
        Computes Token Precision, Recall, and F1 score of candidate against reference.
        """
        cand_tokens = cls.tokenize(candidate)
        ref_tokens = cls.tokenize(reference)

        if not cand_tokens and not ref_tokens:
            return {"precision": 100.0, "recall": 100.0, "f1": 100.0}
        if not cand_tokens or not ref_tokens:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

        cand_set = set(cand_tokens)
        ref_set = set(ref_tokens)

        overlap = cand_set.intersection(ref_set)
        precision = (len(overlap) / len(cand_set)) * 100.0
        recall = (len(overlap) / len(ref_set)) * 100.0

        if precision + recall == 0:
            f1 = 0.0
        else:
            f1 = 2 * (precision * recall) / (precision + recall)

        return {
            "precision": round(precision, 2),
            "recall": round(recall, 2),
            "f1": round(f1, 2)
        }

    @classmethod
    def compute_character_similarity(cls, candidate: str, reference: str) -> float:
        """
        Computes Normalized Sequence Matcher / Levenshtein Ratio (0.0 to 100.0%).
        """
        matcher = difflib.SequenceMatcher(None, candidate.strip(), reference.strip())
        return round(matcher.ratio() * 100.0, 2)

    @classmethod
    def compute_coleman_liau_index(cls, text: str) -> float:
        """
        Computes standard independent Coleman-Liau Readability Index.
        L = average letters per 100 words, S = average sentences per 100 words.
        """
        words = cls.tokenize(text)
        if len(words) < 5:
            return 8.0  # neutral grade baseline

        letter_count = sum(len(w) for w in words)
        sentence_count = max(1, len(re.findall(r"[.!?]+(?:\s|$)", text)))

        L = (letter_count / len(words)) * 100.0
        S = (sentence_count / len(words)) * 100.0

        cli = (0.0588 * L) - (0.296 * S) - 15.8
        return round(cli, 2)

    @classmethod
    def evaluate_against_ground_truth(
        cls,
        restored_text: str,
        reference_text: str,
        critical_entities: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive independent evaluation comparing restored output to ground truth.
        """
        f1_metrics = cls.compute_token_f1(restored_text, reference_text)
        char_sim = cls.compute_character_similarity(restored_text, reference_text)
        cli_grade = cls.compute_coleman_liau_index(restored_text)

        # Entity recovery check
        entities_found = 0
        total_entities = 0
        if critical_entities:
            total_entities = len(critical_entities)
            restored_lower = restored_text.lower()
            for ent in critical_entities:
                if ent.lower() in restored_lower:
                    entities_found += 1

        entity_recovery_rate = (
            round((entities_found / max(1, total_entities)) * 100.0, 2)
            if total_entities > 0 else 100.0
        )

        # Composite ground-truth restoration score (weighted: F1 50%, Char Sim 30%, Entities 20%)
        composite_accuracy = (
            (f1_metrics["f1"] * 0.50) +
            (char_sim * 0.30) +
            (entity_recovery_rate * 0.20)
        )

        return {
            "token_precision": f1_metrics["precision"],
            "token_recall": f1_metrics["recall"],
            "token_f1": f1_metrics["f1"],
            "character_similarity": char_sim,
            "entity_recovery_rate": entity_recovery_rate,
            "composite_accuracy": round(composite_accuracy, 2),
            "independent_readability_cli": cli_grade,
            "passed_oracle": composite_accuracy >= 80.0,
        }
