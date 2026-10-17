"""
Unifile by Soniscorett - Symbol, Zalgo & Noise Sanitizer
Cleans excessive combining diacritics (Zalgo), strips zero-width/bidi control characters,
resolves homoglyphs, and eliminates glitch artifacts.
"""

from __future__ import annotations
import re
import unicodedata
from typing import Tuple, List, Dict

# Zero-width, directional overrides, and invisible control codes
INVISIBLE_AND_CONTROL_RE = re.compile(
    r"[\u200B-\u200D\uFEFF\u2060\u00AD\u200E\u200F\u202A-\u202E\u2066-\u2069\x00-\x08\x0B\x0C\x0E-\x1F\x7F]"
)

# Combining marks regex (Zalgo corruption)
COMBINING_MARKS_RE = re.compile(
    r"[\u0300-\u036F\u0483-\u0489\u1DC0-\u1DFF\u20D0-\u20FF\uFE20-\uFE2F]"
)

# Severe glitch combining marks (strikethroughs, overlays, stacked glitches)
GLITCH_MARKS_RE = re.compile(
    r"[\u0334-\u0338\u033D-\u0362\u0483-\u0489\u1DC0-\u1DFF\u20D0-\u20FF\uFE20-\uFE2F]"
)

# Common homoglyph mappings (Cyrillic / Greek lookalikes in Latin context)
HOMOGLYPH_MAP: Dict[str, str] = {
    # Cyrillic small lookalikes
    "а": "a", "с": "c", "е": "e", "о": "o", "р": "p", "х": "x", "у": "y",
    "і": "i", "ј": "j", "ѕ": "s", "ԁ": "d", "ԛ": "q", "ԝ": "w",
    # Cyrillic capital lookalikes
    "А": "A", "В": "B", "С": "C", "Е": "E", "Н": "H", "І": "I", "Ј": "J",
    "К": "K", "М": "M", "О": "O", "Р": "P", "Ѕ": "S", "Т": "T", "Х": "X",
    # Greek lookalikes
    "α": "a", "ο": "o", "ν": "v", "ρ": "p", "Α": "A", "Β": "B", "Ε": "E",
    "Ζ": "Z", "Η": "H", "Ι": "I", "Κ": "K", "Μ": "M", "N": "N", "Ο": "O",
    "Ρ": "P", "Τ": "T", "Χ": "X",
}


class Sanitizer:
    """Removes Zalgo, invisible glyphs, homoglyph traps, and symbol noise."""

    @classmethod
    def sanitize(
        cls,
        text: str,
        preserve_accents: bool = True,
        resolve_homoglyphs: bool = True
    ) -> Tuple[str, List[str]]:
        """
        Sanitizes text by removing non-text noise and normalizing characters.
        Returns cleaned text and a log of applied sanitization steps.
        """
        if not text:
            return "", []

        actions: List[str] = []

        # 1. Strip invisible, zero-width, and bidi override characters
        invisible_count = len(INVISIBLE_AND_CONTROL_RE.findall(text))
        if invisible_count > 0:
            text = INVISIBLE_AND_CONTROL_RE.sub("", text)
            actions.append(f"Stripped {invisible_count} invisible / zero-width / bidi control characters.")

        # 2. De-Zalgo (Excessive & Glitch combining diacritics)
        zalgo_matches = len(COMBINING_MARKS_RE.findall(text))
        if zalgo_matches > 0:
            # First, strip combining marks attached to spaces or non-letters
            text = re.sub(r"(?<=\s)[\u0300-\u036F\u0483-\u0489\u1DC0-\u1DFF\u20D0-\u20FF]+", "", text)
            text = re.sub(r"[\u0300-\u036F\u0483-\u0489\u1DC0-\u1DFF\u20D0-\u20FF]+(?=\s)", "", text)

            # Strip strikethroughs, overlays, and extreme glitch marks
            text = GLITCH_MARKS_RE.sub("", text)

            # If zalgo marks are still present
            if zalgo_matches > 4:
                # Decompose and strip excessive combining marks
                decomposed = unicodedata.normalize("NFD", text)
                clean_decomposed = COMBINING_MARKS_RE.sub("", decomposed)
                text = unicodedata.normalize("NFC", clean_decomposed)
            else:
                text = unicodedata.normalize("NFC", text)

            actions.append(f"Eliminated Zalgo glitch artifacts ({zalgo_matches} combining marks removed).")

        # 3. Unicode normalization (NFKC normalizes fullwidth characters like Ｆｉｌｅ -> File)
        normalized = unicodedata.normalize("NFKC", text)
        if normalized != text:
            actions.append("Normalized fullwidth/compatibility Unicode forms (NFKC).")
            text = normalized

        # 4. Resolve homoglyphs (e.g. mixed Cyrillic/Greek in predominantly Latin text)
        if resolve_homoglyphs:
            latin_count = len(re.findall(r"[a-zA-Z]", text))
            cyrillic_or_greek = sum(1 for ch in text if ch in HOMOGLYPH_MAP)
            if latin_count > 10 and (cyrillic_or_greek / max(1, latin_count)) < 0.4 and cyrillic_or_greek > 0:
                chars = []
                replaced = 0
                for ch in text:
                    if ch in HOMOGLYPH_MAP:
                        chars.append(HOMOGLYPH_MAP[ch])
                        replaced += 1
                    else:
                        chars.append(ch)
                text = "".join(chars)
                actions.append(f"Resolved {replaced} deceptive Unicode homoglyph lookalikes into Latin equivalents.")

        # 5. Fix interleaved symbol noise: e.g. "a*n*d* *v*e*r*i*f*i*e*d" or "u*n*i*f*i*l*e"
        if "*" in text or "~" in text or "^" in text or "#" in text:
            before_inter = text
            text = re.sub(r"(?<=[a-zA-Z])[*~^#](?=[a-zA-Z]|\s|\.|$)", "", text)
            text = re.sub(r"(?<=\s|\^|\*|#)[*~^#](?=[a-zA-Z])", "", text)
            text = re.sub(r"([A-Za-z])[*~^|#](?=[A-Za-z][*~^|#][A-Za-z])", r"\1", text)
            if text != before_inter:
                actions.append("Cleaned interleaved symbol noise from words.")

        # 6. Collapse excessive punctuation/symbol stutters
        text = re.sub(r"([!?.,;:=#*~_-])\1{5,}", r"\1\1\1", text)

        # 7. Normalize whitespace runs
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip(), actions
