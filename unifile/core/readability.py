"""
Unifile by Soniscorett - Readability & Quality Scoring Engine
Evaluates text clarity, lexical coherence, encoding integrity, and verifies
whether text satisfies the >= 80% readability threshold in the user's target language.
"""

from __future__ import annotations
import math
import re
import unicodedata
from typing import Dict, Any, List, Set, Tuple

# Common high-frequency words for major languages to establish lexical coherence
VOCABULARY_CORPUS: Dict[str, Set[str]] = {
    "en": {
        "the", "be", "to", "of", "and", "a", "in", "that", "have", "i", "it", "for", "not",
        "on", "with", "he", "as", "you", "do", "at", "this", "but", "his", "by", "from",
        "they", "we", "say", "her", "she", "or", "an", "will", "my", "one", "all", "would",
        "there", "their", "what", "so", "up", "out", "if", "about", "who", "get", "which",
        "go", "me", "when", "make", "can", "like", "time", "no", "just", "him", "know",
        "take", "people", "into", "year", "your", "good", "some", "could", "them", "see",
        "other", "than", "then", "now", "look", "only", "come", "its", "over", "think",
        "also", "back", "after", "use", "two", "how", "our", "work", "first", "well",
        "way", "even", "new", "want", "because", "any", "these", "give", "day", "most",
        "file", "data", "system", "text", "user", "model", "document", "function", "read",
        "code", "report", "error", "clean", "name", "value", "status", "server", "process",
        "translation", "connector", "result", "version", "universal", "content", "format"
    },
    "es": {
        "de", "la", "que", "el", "en", "y", "a", "los", "del", "se", "las", "por", "un",
        "para", "con", "no", "una", "su", "al", "lo", "como", "mas", "pero", "sus", "le",
        "ya", "o", "este", "si", "porque", "esta", "entre", "cuando", "muy", "sin", "sobre",
        "ser", "tiene", "tambien", "me", "hasta", "hay", "donde", "quien", "desde", "todo",
        "nos", "durante", "todos", "uno", "les", "ni", "contra", "otros", "ese", "eso",
        "ante", "ellos", "e", "esto", "mi", "antes", "algunos", "que", "unos", "yo", "otro",
        "archivo", "datos", "sistema", "texto", "usuario", "modelo", "documento", "informe",
        "limpio", "estado", "servidor", "proceso", "traduccion", "conector", "resultado"
    },
    "fr": {
        "de", "la", "le", "et", "les", "des", "en", "un", "du", "une", "est", "pour", "que",
        "dans", "qui", "ce", "il", "sur", "pas", "plus", "au", "avec", "ne", "se", "par",
        "son", "sur", "sa", "aux", "ou", "comme", "mais", "ses", "tout", "nous", "sa",
        "leur", "bien", "y", "sans", "meme", "fait", "leur", "faire", "peut", "ces", "ont",
        "fichier", "donnees", "systeme", "texte", "utilisateur", "modele", "document",
        "rapport", "propre", "etat", "serveur", "processus", "traduction", "connecteur"
    },
    "de": {
        "der", "die", "und", "in", "den", "von", "zu", "das", "mit", "sich", "des", "auf",
        "fur", "ist", "im", "dem", "nicht", "ein", "eine", "als", "auch", "es", "an", "werden",
        "aus", "er", "hat", "dass", "sie", "nach", "wird", "bei", "einer", "um", "am", "sind",
        "noch", "wie", "einem", "uber", "einen", "so", "sie", "zum", "war", "haben", "nur",
        "datei", "daten", "system", "text", "benutzer", "modell", "dokument", "bericht",
        "status", "server", "prozess", "ubersetzung", "anschluss", "ergebnis", "sauber"
    },
    "it": {
        "di", "e", "il", "la", "che", "in", "un", "per", "non", "del", "dei", "con", "le",
        "si", "della", "delle", "al", "dalla", "da", "piu", "ha", "questo", "suo", "come",
        "ma", "ed", "o", "sono", "anche", "nel", "questa", "gli", "sua", "era", "ai", "ci",
        "file", "dati", "sistema", "testo", "utente", "modello", "documento", "rapporto",
        "stato", "server", "processo", "traduzione", "connettore", "risultato"
    },
    "pt": {
        "de", "a", "o", "que", "e", "do", "da", "em", "um", "para", "com", "nao", "uma",
        "os", "no", "se", "na", "por", "mais", "as", "dos", "como", "mas", "foi", "ao",
        "ele", "das", "tem", "sua", "seu", "suas", "seus", "muito", "quando", "mesmo",
        "arquivo", "dados", "sistema", "texto", "usuario", "modelo", "documento", "relatorio",
        "estado", "servidor", "processo", "traducao", "conector", "resultado"
    }
}

# Known mojibake pattern indicators
MOJIBAKE_PATTERNS = [
    re.compile(r"Ã[¡¢£¤¥¦§¨©ª«¬®¯°±²³´µ¶·¸¹º»¼½¾¿ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß]"),
    re.compile(r"â[€™œžŸ¡¢£¤¥¦§¨©ª«¬®¯°±²³´µ¶·¸¹º»¼½¾¿]"),
    re.compile(r"Â[¡¢£¤¥¦§¨©ª«¬®¯°±²³´µ¶·¸¹º»¼½¾¿]"),
    re.compile(r"\ufffd"),  # Unicode replacement char 
    re.compile(r"\\x[0-9a-fA-F]{2}"),
    re.compile(r"\\u[0-9a-fA-F]{4}"),
    re.compile(r"&[a-zA-Z]{2,8};|&#[0-9]{2,5};|&#x[0-9a-fA-F]{2,5};"),
    re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]"),  # Non-printable control characters
]

# Zalgo combining mark pattern
ZALGO_PATTERN = re.compile(r"[\u0300-\u036f\u0483-\u0489\u1dc0-\u1dff\u20d0-\u20ff\ufe20-\ufe2f]")


class ReadabilityReport:
    """Holds detailed readability analytics."""

    def __init__(
        self,
        score: float,
        passed: bool,
        metrics: Dict[str, float],
        diagnostics: List[str],
        detected_language: str,
        target_language: str,
        token_count: int,
        cleaned_length: int,
    ):
        self.score = round(score, 2)
        self.passed = passed
        self.metrics = {k: round(v, 2) for k, v in metrics.items()}
        self.diagnostics = diagnostics
        self.detected_language = detected_language
        self.target_language = target_language
        self.token_count = token_count
        self.cleaned_length = cleaned_length

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "passed": self.passed,
            "minimum_required": 80.0,
            "grade": self._grade(),
            "metrics": self.metrics,
            "diagnostics": self.diagnostics,
            "detected_language": self.detected_language,
            "target_language": self.target_language,
            "token_count": self.token_count,
            "character_count": self.cleaned_length,
        }

    def _grade(self) -> str:
        if self.score >= 95:
            return "Pristine (A+)"
        elif self.score >= 90:
            return "Excellent (A)"
        elif self.score >= 85:
            return "Very Good (B+)"
        elif self.score >= 80:
            return "Readable (B - Threshold Met)"
        elif self.score >= 60:
            return "Partial Degraded (C)"
        elif self.score >= 40:
            return "Distorted / Low Coherence (D)"
        else:
            return "Severe Corruption / Unreadable (F)"


def assess_readability(
    text: str,
    target_lang: str = "en",
    detected_lang: str = "en"
) -> ReadabilityReport:
    """
    Computes a comprehensive readability score (0.0% to 100.0%) for text,
    verifying if it satisfies >= 80% human & AI readability in target_lang.
    """
    target_lang = (target_lang or "en").lower().split("-")[0]
    detected_lang = (detected_lang or "en").lower().split("-")[0]

    if not text or not text.strip():
        return ReadabilityReport(
            score=0.0,
            passed=False,
            metrics={
                "lexical_coherence": 0.0,
                "encoding_integrity": 0.0,
                "symbol_noise_ratio": 0.0,
                "structural_flow": 0.0,
                "language_alignment": 0.0,
            },
            diagnostics=["Input text is empty or contains only whitespace."],
            detected_language=detected_lang,
            target_language=target_lang,
            token_count=0,
            cleaned_length=0,
        )

    clean_text = text.strip()
    total_chars = len(clean_text)

    # 1. Encoding Integrity & Mojibake Check
    mojibake_hits = 0
    for pat in MOJIBAKE_PATTERNS:
        mojibake_hits += len(pat.findall(clean_text))

    zalgo_hits = len(ZALGO_PATTERN.findall(clean_text))
    
    encoding_penalty = min(60.0, (mojibake_hits * 3.5) + (zalgo_hits * 1.5))
    encoding_score = max(0.0, 100.0 - encoding_penalty)

    # 2. Symbol Noise Ratio
    # Count alpha, numeric, normal punctuation, and whitespace
    normal_char_count = 0
    noise_char_count = 0

    for ch in clean_text:
        cat = unicodedata.category(ch)
        if cat.startswith("L") or cat.startswith("N"):  # Letter or Number
            normal_char_count += 1
        elif ch in " \t\r\n.,!?;:'\"-—()[]{}/@#$%&*+=<>_~`^|\\":
            normal_char_count += 1
        elif cat.startswith("P") or cat.startswith("Z"):  # Punctuation or Separator
            normal_char_count += 1
        else:
            noise_char_count += 1

    noise_ratio = noise_char_count / max(1, total_chars)
    symbol_score = max(0.0, 100.0 - (noise_ratio * 150.0))

    # 3. Tokenization and Lexical Coherence
    words = re.findall(r"\b[^\W\d_]+\b", clean_text.lower(), flags=re.UNICODE)
    token_count = len(words)

    if token_count == 0:
        lexical_score = 10.0
        avg_word_len = 0.0
    else:
        avg_word_len = sum(len(w) for w in words) / token_count
        vocab = VOCABULARY_CORPUS.get(target_lang, VOCABULARY_CORPUS["en"])
        
        # Check matching words or phonotactic plausibility
        recognized_words = sum(1 for w in words if w in vocab or len(w) <= 2)
        match_ratio = recognized_words / token_count

        # Even for specialized words not in mini-corpus, check if consonant/vowel ratio is natural
        vowels = set("aeiouyáéíóúàèìòùäëïöüãõâêîôû")
        phonetic_plausible = 0
        for w in words:
            if len(w) > 30:  # Suspiciously long gibberish token
                continue
            has_vowel = any(c in vowels for c in w)
            consonant_cluster = re.search(r"[bcdfghjklmnpqrstvwxyz]{6,}", w)
            if has_vowel and not consonant_cluster:
                phonetic_plausible += 1

        plausibility_ratio = phonetic_plausible / token_count
        lexical_score = min(100.0, (match_ratio * 60.0) + (plausibility_ratio * 40.0))

    # 4. Structural Flow & Syntactic Cadence
    # Penalize lack of spaces, excessive repeated characters, or unclosed wrappers
    structural_penalties = 0.0

    # Excessive repeated characters (e.g. "aaaaaaa" or "!!!!!????")
    repetition_hits = len(re.findall(r"(.)\1{4,}", clean_text))
    structural_penalties += min(25.0, repetition_hits * 5.0)

    # Word length realism: natural languages average 4-9 chars per word
    if avg_word_len > 15:
        structural_penalties += min(30.0, (avg_word_len - 15) * 4.0)
    elif avg_word_len < 2.0 and token_count > 5:
        structural_penalties += 15.0

    # Sentence boundary presence
    has_sentence_end = bool(re.search(r"[.!?\n]", clean_text))
    if not has_sentence_end and total_chars > 80:
        structural_penalties += 10.0

    structural_score = max(0.0, 100.0 - structural_penalties)

    # 5. Language Alignment
    if detected_lang == target_lang:
        lang_alignment_score = 100.0
    elif target_lang in ("en", "es", "fr", "de", "it", "pt") and detected_lang in ("en", "es", "fr", "de", "it", "pt"):
        # Related Latin-script language
        lang_alignment_score = 85.0
    else:
        lang_alignment_score = 75.0

    # Weighted Composite Score
    # Lexical Coherence: 35%, Encoding Integrity: 25%, Symbol Cleanliness: 20%, Structural Flow: 15%, Language: 5%
    composite_score = (
        (lexical_score * 0.35) +
        (encoding_score * 0.25) +
        (symbol_score * 0.20) +
        (structural_score * 0.15) +
        (lang_alignment_score * 0.05)
    )

    composite_score = max(0.0, min(100.0, composite_score))
    passed = composite_score >= 80.0

    # Build Diagnostics
    diagnostics = []
    if passed:
        diagnostics.append(f"Readability threshold satisfied ({composite_score:.1f}% >= 80.0%). Ready for AI model consumption.")
    else:
        diagnostics.append(f"Readability is below 80% threshold ({composite_score:.1f}%). Heuristic restoration required.")

    if mojibake_hits > 0:
        diagnostics.append(f"Detected {mojibake_hits} encoding artifacts/mojibake sequences.")
    else:
        diagnostics.append("Encoding integrity: Clean standard character encodings.")

    if zalgo_hits > 0:
        diagnostics.append(f"Detected {zalgo_hits} Zalgo/corrupted combining diacritic marks.")

    if noise_ratio > 0.08:
        diagnostics.append(f"Elevated symbol noise ratio ({noise_ratio * 100:.1f}% of characters).")

    if avg_word_len > 15:
        diagnostics.append(f"Abnormal average token length ({avg_word_len:.1f} chars/word), indicating unspaced or concatenated text.")

    diagnostics.append(f"Lexical coherence: {lexical_score:.1f}%, Target language: {target_lang.upper()}.")

    return ReadabilityReport(
        score=composite_score,
        passed=passed,
        metrics={
            "lexical_coherence": lexical_score,
            "encoding_integrity": encoding_score,
            "symbol_noise_ratio": symbol_score,
            "structural_flow": structural_score,
            "language_alignment": lang_alignment_score,
        },
        diagnostics=diagnostics,
        detected_language=detected_lang,
        target_language=target_lang,
        token_count=token_count,
        cleaned_length=total_chars,
    )
