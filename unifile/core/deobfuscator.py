"""
Unifile by Soniscorett - Deobfuscation & Decryption Reversal Engine
Detects and reverses Base64, Hex dumps, Binary streams, URL encoding, ROT/Caesar ciphers,
single-byte XOR obfuscation, Morse code, and Leetspeak.
"""

from __future__ import annotations
import base64
import binascii
import re
import urllib.parse
from typing import Tuple, List, Optional, Dict
from .readability import VOCABULARY_CORPUS

# English letter frequency distribution (percentages)
ENG_FREQ: Dict[str, float] = {
    'e': 12.02, 't': 9.10, 'a': 8.12, 'o': 7.68, 'i': 7.31, 'n': 6.95,
    's': 6.28, 'r': 6.02, 'h': 5.92, 'd': 4.32, 'l': 3.98, 'u': 2.88,
    'c': 2.71, 'm': 2.61, 'f': 2.30, 'y': 2.11, 'w': 2.09, 'g': 2.03,
    'p': 1.82, 'b': 1.49, 'v': 1.11, 'k': 0.69, 'x': 0.17, 'q': 0.11,
    'j': 0.10, 'z': 0.07, ' ': 15.0
}

MORSE_DICT: Dict[str, str] = {
    '.-': 'A', '-...': 'B', '-.-.': 'C', '-..': 'D', '.': 'E',
    '..-.': 'F', '--.': 'G', '....': 'H', '..': 'I', '.---': 'J',
    '-.-': 'K', '.-..': 'L', '--': 'M', '-.': 'N', '---': 'O',
    '.--.': 'P', '--.-': 'Q', '.-.': 'R', '...': 'S', '-': 'T',
    '..-': 'U', '...-': 'V', '.--': 'W', '-..-': 'X', '-.--': 'Y',
    '--..': 'Z', '-----': '0', '.----': '1', '..---': '2', '...--': '3',
    '....-': '4', '.....': '5', '-....': '6', '--...': '7', '---..': '8',
    '----.': '9', '.-.-.-': '.', '--..--': ',', '..--..': '?', '-..-.': '/',
    '-....-': '-', '-.--.': '(', '-.--.-': ')'
}


class Deobfuscator:
    """Decodes obfuscated, encoded, or lightweight-encrypted text."""

    @classmethod
    def english_score(cls, text: str) -> float:
        """Calculates rough English letter frequency score (higher is better)."""
        if not text:
            return 0.0
        text_lower = text.lower()
        total_chars = len(text_lower)
        score = 0.0
        alpha_count = 0

        for ch in text_lower:
            if ch in ENG_FREQ:
                score += ENG_FREQ[ch]
                alpha_count += 1
            elif ch.isprintable():
                score += 1.0
            else:
                score -= 10.0

        if total_chars == 0 or (alpha_count / total_chars) < 0.6:
            return 0.0

        return score / total_chars

    @classmethod
    def decode_url(cls, text: str) -> Tuple[str, Optional[str]]:
        """Reverts URL/percent-encoded text."""
        if "%20" in text or "%3A" in text or "%2F" in text or re.search(r"%[0-9A-Fa-f]{2}", text):
            try:
                unquoted = urllib.parse.unquote(text)
                if unquoted != text:
                    return unquoted, "Reverted URL/percent-encoding."
            except Exception:
                pass
        return text, None

    @classmethod
    def decode_base64_full(cls, text: str) -> Tuple[str, Optional[str]]:
        """Attempts to decode text if entire string (or prefix) is Base64."""
        cleaned = text.strip()
        # Handle data URI: e.g. data:text/plain;base64,...
        if cleaned.startswith("data:") and ";base64," in cleaned:
            cleaned = cleaned.split(";base64,")[1].strip()

        # Check if valid base64 character set
        if len(cleaned) >= 16 and re.fullmatch(r"[A-Za-z0-9+/= \r\n]+", cleaned):
            no_spaces = re.sub(r"\s+", "", cleaned)
            if len(no_spaces) % 4 == 0:
                try:
                    decoded_bytes = base64.b64decode(no_spaces, validate=True)
                    decoded_str = decoded_bytes.decode("utf-8", errors="replace")
                    printable_ratio = sum(1 for c in decoded_str if c.isprintable() or c in "\n\r\t") / max(1, len(decoded_str))
                    if printable_ratio > 0.85 and len(decoded_str.strip()) > 3:
                        return decoded_str, f"Decoded Base64 payload ({len(no_spaces)} chars -> {len(decoded_str)} chars)."
                except Exception:
                    pass
        return text, None

    @classmethod
    def decode_base64_embedded(cls, text: str) -> Tuple[str, List[str]]:
        """Finds and replaces embedded Base64 blocks inside text."""
        actions: List[str] = []

        # 1. Match data URIs: data:text/plain;base64,...
        pattern_data_uri = r"data:[a-zA-Z0-9/+-]+;base64,([A-Za-z0-9+/=]+)"
        def repl_uri(m: re.Match) -> str:
            payload = m.group(1).strip()
            try:
                dec = base64.b64decode(payload).decode("utf-8", errors="replace")
                if sum(1 for c in dec if c.isprintable() or c in "\n\r\t") / max(1, len(dec)) > 0.8:
                    actions.append(f"Decoded Base64 Data URI block ({len(payload)} chars).")
                    return dec
            except Exception:
                pass
            return m.group(0)

        text = re.sub(pattern_data_uri, repl_uri, text)

        # 2. Match raw embedded base64 blocks (24+ characters)
        pattern_raw_b64 = r"(?<![A-Za-z0-9+/])([A-Za-z0-9+/]{24,}={0,2})(?![A-Za-z0-9+/])"
        def repl_raw(match: re.Match) -> str:
            raw = match.group(1).strip()
            if len(raw) % 4 != 0:
                return match.group(0)
            try:
                dec = base64.b64decode(raw, validate=True)
                s = dec.decode("utf-8", errors="strict")
                if sum(1 for c in s if c.isprintable() or c in "\n\r\t") / max(1, len(s)) > 0.85:
                    actions.append(f"Decoded embedded Base64 block ({len(raw)} chars).")
                    return s
            except Exception:
                pass
            return match.group(0)

        text = re.sub(pattern_raw_b64, repl_raw, text)
        return text, actions

    @classmethod
    def decode_hex(cls, text: str) -> Tuple[str, Optional[str]]:
        """Decodes raw hex dumps, e.g. '48656c6c6f' or '48 65 6c 6c 6f' or '\\x48\\x65...'"""
        cleaned = text.strip()
        # Case 1: \x48\x65...
        if "\\x" in cleaned:
            hex_chars = re.findall(r"\\x([0-9a-fA-F]{2})", cleaned)
            if len(hex_chars) >= 4:
                try:
                    byte_data = bytes.fromhex("".join(hex_chars))
                    decoded = byte_data.decode("utf-8", errors="replace")
                    if sum(1 for c in decoded if c.isprintable() or c in "\n\r\t") / max(1, len(decoded)) > 0.8:
                        return decoded, f"Decoded {len(hex_chars)} bytes of \\x escaped hex data."
                except Exception:
                    pass

        # Case 2: Space/comma separated hex: "48 65 6c 6c 6f" or "0x48, 0x65"
        tokens = re.split(r"[\s,]+", cleaned)
        if len(tokens) >= 5 and all(re.fullmatch(r"(?:0x)?[0-9a-fA-F]{2}", t) for t in tokens):
            try:
                hex_str = "".join(t.replace("0x", "") for t in tokens)
                byte_data = bytes.fromhex(hex_str)
                decoded = byte_data.decode("utf-8", errors="replace")
                if sum(1 for c in decoded if c.isprintable() or c in "\n\r\t") / max(1, len(decoded)) > 0.8:
                    return decoded, f"Decoded {len(tokens)} space-separated hex bytes."
            except Exception:
                pass

        # Case 3: Embedded space/comma separated hex sequences inside larger text
        pattern_embedded_hex = r"(?:(?:\b(?:0x)?[0-9a-fA-F]{2}[\s,]+){4,}(?:0x)?[0-9a-fA-F]{2}\b)"
        embedded_hits = 0
        def repl_hex(m: re.Match) -> str:
            nonlocal embedded_hits
            raw = m.group(0)
            toks = re.split(r"[\s,]+", raw.strip())
            try:
                b = bytes.fromhex("".join(t.replace("0x", "") for t in toks))
                s = b.decode("utf-8", errors="replace")
                if sum(1 for c in s if c.isprintable() or c in "\n\r\t") / max(1, len(s)) > 0.8:
                    embedded_hits += 1
                    return s
            except Exception:
                pass
            return raw

        new_text = re.sub(pattern_embedded_hex, repl_hex, text)
        if embedded_hits > 0:
            return new_text, f"Decoded {embedded_hits} embedded hexadecimal dumps into plaintext."

        # Case 4: Continuous raw hex stream: "48656c6c6f20..."
        if len(cleaned) >= 16 and len(cleaned) % 2 == 0 and re.fullmatch(r"[0-9a-fA-F]+", cleaned):
            try:
                byte_data = bytes.fromhex(cleaned)
                decoded = byte_data.decode("utf-8", errors="replace")
                if sum(1 for c in decoded if c.isprintable() or c in "\n\r\t") / max(1, len(decoded)) > 0.85:
                    return decoded, f"Decoded continuous hex dump ({len(cleaned)} hex digits)."
            except Exception:
                pass

        return text, None

    @classmethod
    def decode_binary_string(cls, text: str) -> Tuple[str, Optional[str]]:
        """Decodes 8-bit binary strings: '01001000 01100101 01101100'"""
        tokens = text.strip().split()
        if len(tokens) >= 4 and all(re.fullmatch(r"[01]{8}", t) for t in tokens):
            try:
                chars = [chr(int(t, 2)) for t in tokens]
                decoded = "".join(chars)
                if sum(1 for c in decoded if c.isprintable() or c in "\n\r\t") / max(1, len(decoded)) > 0.8:
                    return decoded, f"Decoded {len(tokens)} 8-bit binary bytes."
            except Exception:
                pass
        return text, None

    @classmethod
    def decode_morse(cls, text: str) -> Tuple[str, Optional[str]]:
        """Decodes Morse code if input consists of dots, dashes, spaces, slashes."""
        cleaned = text.strip()
        tokens = cleaned.split()
        if len(tokens) >= 3 and all(re.fullmatch(r"[.\-/]+", t) for t in tokens):
            out_words: List[str] = []
            cur_word: List[str] = []
            for t in tokens:
                if t == "/":
                    if cur_word:
                        out_words.append("".join(cur_word))
                        cur_word = []
                elif t in MORSE_DICT:
                    cur_word.append(MORSE_DICT[t])
                else:
                    return text, None
            if cur_word:
                out_words.append("".join(cur_word))
            decoded = " ".join(out_words)
            if len(decoded) > 2:
                return decoded, f"Decoded Morse code message ({len(tokens)} symbols)."
        return text, None

    @classmethod
    def decode_caesar_or_rot(cls, text: str) -> Tuple[str, Optional[str]]:
        """
        Solves Caesar ciphers and ROT13 via dictionary matching and frequency analysis.
        """
        if len(text.strip()) < 15:
            return text, None

        vocab = VOCABULARY_CORPUS["en"]
        base_words = re.findall(r"\b[a-z]{2,}\b", text.lower())
        base_matches = sum(1 for w in base_words if w in vocab)
        base_score = cls.english_score(text)

        best_score = base_score
        best_matches = base_matches
        best_shift = 0
        best_text = text

        for shift in range(1, 26):
            shifted_chars = []
            for ch in text:
                if 'a' <= ch <= 'z':
                    shifted_chars.append(chr((ord(ch) - ord('a') - shift) % 26 + ord('a')))
                elif 'A' <= ch <= 'Z':
                    shifted_chars.append(chr((ord(ch) - ord('A') - shift) % 26 + ord('A')))
                else:
                    shifted_chars.append(ch)
            cand = "".join(shifted_chars)
            cand_words = re.findall(r"\b[a-z]{2,}\b", cand.lower())
            cand_matches = sum(1 for w in cand_words if w in vocab)
            cand_score = cls.english_score(cand)

            # Check if this shift makes much more linguistic sense
            if (cand_matches > best_matches and cand_score >= 6.0) or (cand_score > best_score and cand_score >= 7.0):
                best_matches = cand_matches
                best_score = cand_score
                best_shift = shift
                best_text = cand

        if best_shift > 0:
            cipher_name = "ROT-13" if best_shift == 13 else f"Caesar Cipher (shift={best_shift})"
            return best_text, f"Solved and decrypted {cipher_name} ({best_matches} dictionary matches, score: {best_score:.2f})."

        return text, None

    @classmethod
    def decode_single_byte_xor(cls, raw_bytes: bytes) -> Tuple[Optional[str], Optional[str]]:
        """Tests all 256 keys to break single-byte XOR obfuscation."""
        if len(raw_bytes) < 16:
            return None, None

        best_score = 0.0
        best_key = -1
        best_str = None

        for key in range(1, 256):
            dec = bytes([b ^ key for b in raw_bytes])
            try:
                s = dec.decode("ascii")
                score = cls.english_score(s)
                if score > best_score and score >= 7.0:
                    best_score = score
                    best_key = key
                    best_str = s
            except Exception:
                continue

        if best_key != -1 and best_str:
            return best_str, f"Cracked single-byte XOR obfuscation (key=0x{best_key:02X}, score={best_score:.2f})."

        return None, None

    @classmethod
    def revert_leetspeak(cls, text: str) -> Tuple[str, Optional[str]]:
        """Normalizes common 1337/leetspeak substitutions when detected."""
        leet_signals = len(re.findall(r"\b[A-Za-z0-9]*[013457][A-Za-z0-9]*\b", text))
        total_words = len(text.split())

        if total_words >= 5 and (leet_signals / total_words) > 0.35:
            subs = {
                '0': 'o', '1': 'i', '3': 'e', '4': 'a',
                '5': 's', '7': 't', '8': 'b'
            }
            res = []
            for ch in text:
                res.append(subs.get(ch, ch))
            restored = "".join(res)
            return restored, f"Reverted Leetspeak obfuscation ({leet_signals} obfuscated tokens restored)."
        return text, None

    @classmethod
    def deobfuscate(cls, text: str) -> Tuple[str, List[str]]:
        """
        Runs complete de-obfuscation pipeline.
        Returns decoded text and log of de-obfuscation actions.
        """
        actions: List[str] = []
        if not text:
            return "", actions

        # 1. URL decoding
        text, act = cls.decode_url(text)
        if act:
            actions.append(act)

        # 2. Binary string decoding
        text, act = cls.decode_binary_string(text)
        if act:
            actions.append(act)

        # 3. Morse code decoding
        text, act = cls.decode_morse(text)
        if act:
            actions.append(act)

        # 4. Embedded Base64 decoding (checks Data URIs and raw tokens)
        text, emb_acts = cls.decode_base64_embedded(text)
        actions.extend(emb_acts)

        # 5. Full Base64 decoding
        text, act = cls.decode_base64_full(text)
        if act:
            actions.append(act)

        # 6. Full Hex decoding
        text, act = cls.decode_hex(text)
        if act:
            actions.append(act)

        # 7. Caesar / ROT cipher breaking
        text, act = cls.decode_caesar_or_rot(text)
        if act:
            actions.append(act)

        # 8. Single byte XOR check
        try:
            raw_b = text.encode("latin-1")
            xor_str, act = cls.decode_single_byte_xor(raw_b)
            if xor_str and act:
                text = xor_str
                actions.append(act)
        except Exception:
            pass

        # 9. Leetspeak reversal
        text, act = cls.revert_leetspeak(text)
        if act:
            actions.append(act)

        return text, actions
