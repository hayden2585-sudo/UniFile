"""
Unifile by Soniscorett - REST API Routes & Endpoints
Provides high-performance endpoints for web clients, AI connectors, and test harnesses.
"""

from __future__ import annotations
import base64
import random
import time
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, UploadFile, File, Form, Body, HTTPException, Request
from pydantic import BaseModel

from ..core.pipeline import UnifileEngine
from ..connectors.mcp_server import MCPServer
from ..core.translator import LANGUAGE_NAMES

router = APIRouter(prefix="/api/v1", tags=["Unifile"])

_START_TIME = time.time()


class TextTranslateRequest(BaseModel):
    text: str
    preferred_language: str = "en"
    filename: Optional[str] = "input.txt"
    max_length: Optional[int] = None


class CorruptionRequest(BaseModel):
    text: str
    distortion_type: str  # "zalgo", "mojibake", "base64", "rot13", "truncate_json", "leetspeak", "all_chaos"


class ContextRetrieveRequest(BaseModel):
    source: str
    preferred_language: Optional[str] = "en"
    target_model: Optional[str] = "claude"


@router.get("/context/platforms")
async def context_platforms():
    """Lists supported AI conversation share & sync platforms."""
    return {
        "platforms": [
            {
                "id": "chatgpt",
                "name": "ChatGPT / OpenAI",
                "share_url_patterns": ["chatgpt.com/share/*", "chat.openai.com/share/*"],
                "export_formats": ["conversations.json", "__NEXT_DATA__ JSON", "DOM HTML"],
            },
            {
                "id": "claude",
                "name": "Claude / Anthropic",
                "share_url_patterns": ["claude.ai/share/*"],
                "export_formats": ["Claude JSON export", "Share HTML DOM"],
            },
            {
                "id": "perplexity",
                "name": "Perplexity AI",
                "share_url_patterns": ["perplexity.ai/search/*", "perplexity.ai/page/*"],
                "export_formats": ["Perplexity Search Hydration JSON", "Markdown with Citations"],
            },
            {
                "id": "gemini",
                "name": "Google Gemini",
                "share_url_patterns": ["gemini.google.com/share/*"],
                "export_formats": ["Google Share DOM", "JSON State"],
            }
        ]
    }


@router.post("/context/retrieve")
async def retrieve_context_endpoint(req: ContextRetrieveRequest):
    """
    Retrieves inaccessible, shared, or exported conversation threads
    from ChatGPT, Claude, Perplexity, Gemini, etc.
    Heals corruption and synchronizes context across models.
    """
    from ..core.ai_context_bridge import AIContextBridge
    try:
        result = AIContextBridge.retrieve(
            source=req.source,
            preferred_language=req.preferred_language or "en",
            target_model=req.target_model or "claude"
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to retrieve conversation: {str(e)}")



@router.get("/health")
async def health():
    """Health check and system capabilities."""
    return {
        "status": "healthy",
        "service": "Unifile by Soniscorett",
        "version": "2.4.0",
        "read_only": True,
        "uptime_seconds": round(time.time() - _START_TIME, 2),
        "supported_languages": LANGUAGE_NAMES,
        "modules": [
            "universal_parser",
            "mojibake_healer",
            "zalgo_symbol_sanitizer",
            "deobfuscator_and_ciphers",
            "syntax_truncation_healer",
            "universal_translator",
            "readability_guarantee_engine",
            "mcp_protocol_server",
        ]
    }


@router.get("/formats")
async def list_formats():
    """Lists all universally supported file types."""
    return {
        "documents": [".pdf", ".docx", ".doc", ".rtf", ".odt"],
        "spreadsheets": [".xlsx", ".xls", ".csv", ".tsv"],
        "presentations": [".pptx", ".ppt"],
        "data_and_markup": [".json", ".jsonl", ".xml", ".html", ".htm", ".yaml", ".yml", ".toml"],
        "code_and_scripts": [".py", ".js", ".ts", ".jsx", ".tsx", ".sql", ".sh", ".bash", ".c", ".cpp", ".rs", ".go", ".java", ".php", ".rb"],
        "text_and_docs": [".txt", ".md", ".markdown", ".rst", ".log", ".env", ".ini", ".conf"],
        "archives": [".zip", ".tar", ".gz", ".tgz"],
        "media_metadata": [".svg", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"],
        "binary_streams": [".bin", ".dat", ".raw", ".dump", "unknown_hexdump"]
    }


@router.post("/translate")
async def translate_endpoint(
    request: Request,
    file: Optional[UploadFile] = File(None),
    preferred_language: Optional[str] = Form(None),
    max_length: Optional[int] = Form(None),
):
    """
    Universal File/Text Translator endpoint.
    Accepts multipart file upload OR application/json body.
    """
    content_type = request.headers.get("content-type", "")

    # Handle multipart file upload
    if file:
        file_bytes = await file.read()
        target_lang = preferred_language or "en"
        res = UnifileEngine.process_file(
            path_or_bytes=file_bytes,
            filename=file.filename,
            preferred_language=target_lang,
            max_length=int(max_length) if max_length else None,
        )
        return res.to_dict()

    # Handle JSON payload
    if "application/json" in content_type:
        try:
            body = await request.json()
            raw_text = body.get("text", "")
            target_lang = body.get("preferred_language", "en")
            filename = body.get("filename", "input.txt")
            limit = body.get("max_length")

            res = UnifileEngine.process_text(
                raw_text=raw_text,
                preferred_language=target_lang,
                metadata={"source_type": "json_post", "filename": filename, "read_only": True},
                max_length=int(limit) if limit else None,
            )
            return res.to_dict()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON request: {str(e)}")

    raise HTTPException(status_code=400, detail="Must provide either a file upload or JSON payload.")


@router.post("/inspect")
async def inspect_endpoint(
    request: Request,
    file: Optional[UploadFile] = File(None),
):
    """Inspects text/file for health metrics and corruption diagnostics without altering it."""
    if file:
        file_bytes = await file.read()
        res = UnifileEngine.process_file(file_bytes, filename=file.filename, preferred_language="en")
    else:
        body = await request.json()
        raw_text = body.get("text", "")
        res = UnifileEngine.process_text(raw_text, preferred_language="en")

    return {
        "readability_score": res.initial_report.score,
        "passed_threshold": res.initial_report.passed,
        "diagnostics": res.initial_report.diagnostics,
        "metrics": res.initial_report.metrics,
        "detected_language": res.initial_report.detected_language,
        "transformations_needed": res.transformations,
        "metadata": res.metadata,
    }


@router.post("/mcp")
async def mcp_rpc(request: Request):
    """Model Context Protocol (MCP) JSON-RPC 2.0 endpoint."""
    body = await request.json()
    resp = MCPServer.handle_request(body)
    return resp or {}


@router.post("/corrupt_demo")
async def corrupt_demo(req: CorruptionRequest):
    """
    Intentionally corrupts text with specific distortion patterns
    to demonstrate Unifile's recovery power in the live playground.
    """
    t = req.text
    dtype = req.distortion_type

    if dtype == "zalgo":
        # Add excessive combining marks
        combining = ["\u0300", "\u0301", "\u0302", "\u0303", "\u0304", "\u0305", "\u0334", "\u0337", "\u0338"]
        corrupted = "".join(ch + "".join(random.choices(combining, k=3)) if ch.isalpha() else ch for ch in t)
        return {"corrupted_text": corrupted, "type": "Zalgo Combining Glitch", "hint": "Excessive Unicode diacritics"}

    elif dtype == "mojibake":
        # Encode as UTF-8 then decode as Latin-1 or CP1252
        try:
            b = t.encode("utf-8")
            corrupted = b.decode("latin-1")
            return {"corrupted_text": corrupted, "type": "Mojibake Encoding Distortion", "hint": "UTF-8 read as Latin-1"}
        except Exception:
            return {"corrupted_text": t.replace("e", "Ã©").replace("'", "â€™"), "type": "Synthetic Mojibake"}

    elif dtype == "base64":
        encoded = base64.b64encode(t.encode("utf-8")).decode("ascii")
        return {"corrupted_text": f"data:text/plain;base64,{encoded}", "type": "Base64 Encrypted Payload", "hint": "Base64 Data URI"}

    elif dtype == "rot13":
        # Shift 13 letters
        shifted = []
        for ch in t:
            if 'a' <= ch <= 'z':
                shifted.append(chr((ord(ch) - ord('a') + 13) % 26 + ord('a')))
            elif 'A' <= ch <= 'Z':
                shifted.append(chr((ord(ch) - ord('A') + 13) % 26 + ord('A')))
            else:
                shifted.append(ch)
        return {"corrupted_text": "".join(shifted), "type": "ROT-13 Cipher Stream", "hint": "Caesar shift key 13"}

    elif dtype == "truncate_json":
        sample_json = '{\n  "connector": "Soniscorett Unifile",\n  "status": "active",\n  "system_logs": [\n    {"event": "file_read", "severity": "info", "payload": "' + t.replace('"', '\\"')[:80] + '", "active_trans'
        return {"corrupted_text": sample_json, "type": "Truncated Incomplete JSON", "hint": "Severed brackets, open quotes, cut mid-stream"}

    elif dtype == "leetspeak":
        subs = {'e': '3', 'E': '3', 'a': '4', 'A': '4', 'o': '0', 'O': '0', 'i': '1', 'I': '1', 's': '5', 't': '7'}
        corrupted = "".join(subs.get(ch, ch) for ch in t)
        return {"corrupted_text": corrupted, "type": "1337 / Leetspeak Obfuscation", "hint": "Numeric substitutions"}

    elif dtype == "all_chaos":
        # Combined: mojibake + zalgo + zero-width + symbol noise
        combining = ["\u0301", "\u0334", "\u0308"]
        step1 = t.replace("e", "Ã©").replace("a", "Ã¡").replace("'", "â€™")
        step2 = "".join(ch + "\u200B" if i % 4 == 0 else ch for i, ch in enumerate(step1))
        step3 = "".join(ch + random.choice(combining) if ch.isalpha() and random.random() < 0.4 else ch for ch in step2)
        step4 = " " + " *#~ ".join(step3.split()[:15]) + " ... [TRUNCATED STREAM]"
        return {"corrupted_text": step4, "type": "Maximum Entropy Chaos", "hint": "Mojibake + Zalgo + Zero-width + Noise + Truncation"}

    return {"corrupted_text": t, "type": "None"}
