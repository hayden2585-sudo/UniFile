"""
Tests for Windows and Legacy Terminal Unicode Output Stabilization.
Verifies that no UnicodeEncodeError is raised even on restricted cp1252 or ASCII output streams.
"""

import io
import sys
import pytest
from unifile.core.unicode_env import configure_unicode_output, safe_print


class MockRestrictedStream:
    """Simulates a legacy Windows console stream with restricted encoding (e.g. cp1252/ascii)."""

    def __init__(self, encoding="cp1252"):
        self._encoding = encoding
        self.buffer_data = []

    @property
    def encoding(self):
        return self._encoding

    def write(self, s):
        # Emulate standard Windows terminal encode check
        s.encode(self._encoding)
        self.buffer_data.append(s)
        return len(s)

    def flush(self):
        pass

    def getvalue(self):
        return "".join(self.buffer_data)


def test_safe_print_on_restricted_cp1252_stream():
    """Verifies that safe_print prevents UnicodeEncodeError on cp1252 stream."""
    stream = MockRestrictedStream(encoding="cp1252")
    # Emojis like ✅ or Japanese glyphs like 日本語 are not representable in cp1252
    problematic_text = "Status: ✅ Processed successfully | 翻訳: 日本語 | Readability: 96%"
    
    # Standard print would raise UnicodeEncodeError:
    with pytest.raises(UnicodeEncodeError):
        stream.write(problematic_text)

    # safe_print handles it gracefully:
    safe_print(problematic_text, file=stream)
    content = stream.getvalue()
    assert len(content) > 0
    assert "Processed successfully" in content


def test_safe_print_on_ascii_stream():
    """Verifies safe_print on strict 7-bit ASCII stream."""
    stream = MockRestrictedStream(encoding="ascii")
    unicode_text = "Héllò Wörld — Soniscorett Unifile 🚀"
    
    with pytest.raises(UnicodeEncodeError):
        stream.write(unicode_text)

    safe_print(unicode_text, file=stream)
    assert "Soniscorett Unifile" in stream.getvalue()


def test_configure_unicode_output_callable():
    """Verifies configure_unicode_output executes cleanly on current environment."""
    configure_unicode_output()
    assert sys.stdout is not None
    assert sys.stderr is not None
