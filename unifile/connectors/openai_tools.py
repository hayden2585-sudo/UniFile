"""
Unifile by Soniscorett - OpenAI, Anthropic & Gemini Connector Definitions
Provides universal JSON schemas and execution handlers for LLM tool calling.
"""

from __future__ import annotations
from typing import Dict, Any, List
from ..core.pipeline import UnifileEngine

# OpenAI / Anthropic / Gemini Compatible Function Calling Schemas
UNIFILE_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "unifile_read_file",
            "description": "Universal READ-ONLY file extractor and translator for AI models by Soniscorett. Reads ANY file type (PDF, Word, Excel, PowerPoint, CSV, HTML, JSON, Code, Archives, Images, Raw Binaries) and automatically detects and fixes mojibake, encryption/base64/hex, zalgo/symbol corruption, and truncation, translating into the user's preferred language with at least 80% guaranteed readability.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the local file to read (strictly read-only)."
                    },
                    "preferred_language": {
                        "type": "string",
                        "description": "Target language code (e.g. 'en', 'es', 'fr', 'de', 'it', 'pt', 'ja', 'zh'). Defaults to 'en'.",
                        "default": "en"
                    },
                    "max_length": {
                        "type": "integer",
                        "description": "Maximum character count to return to fit within model context window.",
                        "default": 32000
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "unifile_clean_text",
            "description": "Cleans, deobfuscates, de-zalgos, un-garbles, and translates raw text or log strings into the user's preferred language (>= 80% readability).",
            "parameters": {
                "type": "object",
                "properties": {
                    "raw_text": {
                        "type": "string",
                        "description": "Distorted, encrypted, truncated, or garbled text stream."
                    },
                    "preferred_language": {
                        "type": "string",
                        "description": "Target language code (e.g. 'en', 'es', 'fr', 'de'). Defaults to 'en'.",
                        "default": "en"
                    }
                },
                "required": ["raw_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "unifile_inspect_diagnostics",
            "description": "Evaluates corruption level, mojibake count, encoding errors, and readability score of a file without altering it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to inspect."
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "unifile_retrieve_chat_share",
            "description": "Retrieves inaccessible, shared, or exported conversation threads from ChatGPT, Claude, Perplexity, Gemini, etc. Heals corrupted, truncated, or garbled turns, translates into target language, and synchronizes context across AI models.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Share URL (e.g. chatgpt.com/share/..., claude.ai/share/..., perplexity.ai/search/...) or raw HTML/JSON conversation dump."
                    },
                    "preferred_language": {
                        "type": "string",
                        "description": "Target language for all message turns (default: 'en').",
                        "default": "en"
                    },
                    "target_model": {
                        "type": "string",
                        "description": "Target AI model to format synchronization context for ('claude', 'openai', 'gemini', 'perplexity').",
                        "default": "claude"
                    }
                },
                "required": ["source"]
            }
        }
    }
]


def execute_unifile_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Executes a Unifile tool call from an AI model and returns JSON response."""
    try:
        if tool_name == "unifile_read_file":
            path = arguments.get("file_path")
            lang = arguments.get("preferred_language", "en")
            max_len = arguments.get("max_length", 32000)
            res = UnifileEngine.process_file(path_or_bytes=path, preferred_language=lang, max_length=max_len)
            return res.to_dict()

        elif tool_name == "unifile_clean_text":
            raw = arguments.get("raw_text", "")
            lang = arguments.get("preferred_language", "en")
            res = UnifileEngine.process_text(raw_text=raw, preferred_language=lang)
            return res.to_dict()

        elif tool_name == "unifile_inspect_diagnostics":
            path = arguments.get("file_path")
            res = UnifileEngine.process_file(path_or_bytes=path, preferred_language="en")
            return {
                "file_path": path,
                "readability_score": res.initial_report.score,
                "diagnostics": res.initial_report.diagnostics,
                "metrics": res.initial_report.metrics,
                "detected_language": res.initial_report.detected_language,
                "transformations_needed": res.transformations,
            }

        elif tool_name == "unifile_retrieve_chat_share":
            from ..core.ai_context_bridge import AIContextBridge
            src = arguments.get("source", "")
            lang = arguments.get("preferred_language", "en")
            target = arguments.get("target_model", "claude")
            return AIContextBridge.retrieve(source=src, preferred_language=lang, target_model=target)

        else:
            return {"error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        return {"error": f"Execution failed: {str(e)}"}
