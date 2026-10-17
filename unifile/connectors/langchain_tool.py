"""
Unifile by Soniscorett - LangChain & LlamaIndex Agent Connector
Provides drop-in tool wrappers for popular Python agentic frameworks.
"""

from __future__ import annotations
from typing import Optional, Type, Any, Dict
from pydantic import BaseModel, Field

from ..core.pipeline import UnifileEngine


class UnifileInputSchema(BaseModel):
    file_path: str = Field(description="Path to the file to inspect and translate (strictly read-only).")
    preferred_language: Optional[str] = Field(default="en", description="Target language code (e.g. 'en', 'es', 'fr', 'de').")
    max_length: Optional[int] = Field(default=32000, description="Maximum characters to extract.")


class UnifileTool:
    """
    LangChain compatible tool wrapper for Unifile by Soniscorett.
    Usage:
        from unifile.connectors.langchain_tool import UnifileTool
        tool = UnifileTool(preferred_language="en")
        content = tool.run("/path/to/corrupted.pdf")
    """

    name: str = "unifile_read_file"
    description: str = (
        "Universal read-only file translator and restoration tool for AI models by Soniscorett. "
        "Safely reads any file type (PDF, Word, Excel, PowerPoint, CSV, JSON, Code, Archives, etc.) "
        "and removes mojibake, encryption, zalgo, and truncation, translating into the user's preferred "
        "language with guaranteed >= 80% readability."
    )
    args_schema: Type[BaseModel] = UnifileInputSchema

    def __init__(self, preferred_language: str = "en", max_length: int = 32000):
        self.preferred_language = preferred_language
        self.max_length = max_length

    def run(self, file_path: str, preferred_language: Optional[str] = None, max_length: Optional[int] = None) -> str:
        lang = preferred_language or self.preferred_language
        limit = max_length or self.max_length
        result = UnifileEngine.process_file(file_path, preferred_language=lang, max_length=limit)
        return result.cleaned_text

    async def _arun(self, file_path: str, **kwargs) -> str:
        return self.run(file_path, **kwargs)

    def to_langchain_tool(self) -> Any:
        """Dynamically instantiates langchain_core.tools.Tool if installed."""
        try:
            from langchain_core.tools import Tool
            return Tool(
                name=self.name,
                func=self.run,
                description=self.description,
                args_schema=self.args_schema,
            )
        except ImportError:
            # Fallback wrapper
            return self
