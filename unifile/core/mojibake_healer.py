"""
Unifile by Soniscorett - Mojibake & Encoding Distortion Healer
Detects and repairs double-encoded UTF-8, Latin-1/CP1252 misinterpretations,
unescapes HTML/hex/unicode entities, and reconstructs damaged characters.
"""

from __future__ import annotations
import html
import re
from typing import Tuple, List, Optional
import ftfy

from .readability import MOJIBAKE_PATTERNS


class MojibakeHealer:
    """Heuristic repair engine for scrambled encodings and character distortions."""

    CANDIDATE_ENCODINGS = [
        ("latin-1", "utf-8"),
        ("cp1252", "utf-8"),
        ("iso-8859-1", "utf-8"),
        ("utf-8", "latin-1"),
        ("cp1251", "utf-8"),
        ("shift_jis", "utf-8"),
    ]

    @classmethod
    def count_mojibake_signals(cls, text: str) -> int:
        """Counts mojibake indicator pattern matches in text."""
        total = 0
        for pat in MOJIBAKE_PATTERNS:
            total += len(pat.findall(text))
        return total

    @classmethod
    def heal(cls, text: str) -> Tuple[str, List[str]]:
        """
        Applies multi-pass Mojibake recovery.
        Returns the restored text and an audit trail of applied fixes.
        """
        if not text:
            return "", []

        actions: List[str] = []
        original_signals = cls.count_mojibake_signals(text)

        # 1. Unescape HTML entities (e.g. &amp;, &#8217;, &quot;, &lt;)
        if "&" in text:
            unescaped = html.unescape(text)
            if unescaped != text:
                actions.append("Unescaped HTML entities and numerical character references.")
                text = unescaped

        # 2. Unescape Python/C style string escapes if found literally (e.g. \u00e9, \x20, \n)
        if "\\u" in text or "\\x" in text:
            def replace_unicode(match: re.Match) -> str:
                try:
                    return chr(int(match.group(1), 16))
                except Exception:
                    return match.group(0)

            before_esc = text
            text = re.sub(r"\\u([0-9a-fA-F]{4})", replace_unicode, text)
            text = re.sub(r"\\x([0-9a-fA-F]{2})", replace_unicode, text)
            if text != before_esc:
                actions.append("Decoded raw escaped hex and Unicode sequences (\\uXXXX / \\xXX).")

        # 3. Apply ftfy (Fixes Text For You) - Handles double-UTF8, mojibake, surrogate pairs
        ftfy_fixed = ftfy.fix_text(text, normalization="NFKC")
        if ftfy_fixed != text:
            ftfy_signals = cls.count_mojibake_signals(ftfy_fixed)
            if ftfy_signals <= cls.count_mojibake_signals(text):
                text = ftfy_fixed
                actions.append("Repaired multi-byte UTF-8 / mojibake distortions via ftfy heuristics.")

        # 4. Heuristic candidate re-encoding loop (for stubborn multi-hop encoding mismatches)
        current_signals = cls.count_mojibake_signals(text)
        if current_signals > 0:
            best_candidate = text
            best_signals = current_signals
            best_enc_pair = None

            for enc_from, enc_to in cls.CANDIDATE_ENCODINGS:
                try:
                    # Attempt to re-encode bytes as if it was originally read with wrong encoding
                    raw_bytes = text.encode(enc_from, errors="ignore")
                    redecoded = raw_bytes.decode(enc_to, errors="ignore")
                    re_signals = cls.count_mojibake_signals(redecoded)
                    
                    # Ensure candidate isn't destroyed (has reasonable length)
                    if len(redecoded) >= len(text) * 0.7 and re_signals < best_signals:
                        best_candidate = redecoded
                        best_signals = re_signals
                        best_enc_pair = (enc_from, enc_to)
                except Exception:
                    continue

            if best_enc_pair and best_candidate != text:
                text = best_candidate
                actions.append(f"Re-aligned encoding mismatch from {best_enc_pair[0]} to {best_enc_pair[1]} (reduced artifacts by {current_signals - best_signals}).")

        # 5. Clean orphan replacement characters (\ufffd) or fallback to common punctuation
        if "\ufffd" in text:
            # Often replacement chars in text represent apostrophes, quotes, or dashes
            text = re.sub(r"(\w)\ufffd(\w)", r"\1'\2", text)  # e.g. dont -> don't
            text = re.sub(r"\ufffd+", " - ", text)             # e.g. word  word -> word - word
            actions.append("Reconstructed orphan Unicode replacement characters (U+FFFD).")

        final_signals = cls.count_mojibake_signals(text)
        if original_signals > 0 and final_signals == 0:
            actions.append("All character encoding distortions successfully cleared.")

        return text, actions
