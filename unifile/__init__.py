"""
Unifile by Soniscorett
Universal Read-Only File Translator & Corruption Healer Connector for AI Models.
"""

from .core.unicode_env import configure_unicode_output, safe_print

# Ensure UTF-8 output streams across Windows and all platforms immediately upon import
configure_unicode_output()

from .core.pipeline import UnifileEngine, UnifileResult
from .core.parser import UniversalParser
from .core.readability import assess_readability, ReadabilityReport
from .core.translator import UniversalTranslator
from .core.ai_context_bridge import AIContextBridge, UniversalConversation, UniversalMessage
from .connectors.mcp_server import MCPServer
from .connectors.openai_tools import UNIFILE_TOOL_SCHEMAS, execute_unifile_tool

__version__ = "2.4.0"
__author__ = "Soniscorett"
__all__ = [
    "UnifileEngine",
    "UnifileResult",
    "UniversalParser",
    "assess_readability",
    "ReadabilityReport",
    "UniversalTranslator",
    "AIContextBridge",
    "UniversalConversation",
    "UniversalMessage",
    "MCPServer",
    "UNIFILE_TOOL_SCHEMAS",
    "execute_unifile_tool",
    "read",
    "clean",
    "sync_chat",
]


def read(path: str, lang: str = "en", max_length: int = 32000) -> str:
    """Convenience function: Read any file into clean readable text in target language."""
    res = UnifileEngine.process_file(path, preferred_language=lang, max_length=max_length)
    return res.cleaned_text


def clean(text: str, lang: str = "en") -> str:
    """Convenience function: Clean, deobfuscate, and translate raw text."""
    res = UnifileEngine.process_text(text, preferred_language=lang)
    return res.cleaned_text


def sync_chat(source: str, lang: str = "en", target_model: str = "claude") -> dict:
    """Convenience function: Retrieve shared ChatGPT/Claude/Perplexity chat & sync context across models."""
    return AIContextBridge.retrieve(source=source, preferred_language=lang, target_model=target_model)
