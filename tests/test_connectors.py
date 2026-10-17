"""
Integration Tests for Unifile AI Connectors (MCP, OpenAI, LangChain, REST API, CLI).
"""

import json
import subprocess
import sys
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from unifile.server import app
from unifile.connectors.mcp_server import MCPServer
from unifile.connectors.openai_tools import UNIFILE_TOOL_SCHEMAS, execute_unifile_tool
from unifile.connectors.langchain_tool import UnifileTool

SAMPLES_DIR = Path(__file__).parent.parent / "samples"
client = TestClient(app)


def test_mcp_server_protocol():
    """Validates MCP 1.0 JSON-RPC Handshake, Tool Listing, and Execution."""
    # 1. Initialize
    init_req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    init_res = MCPServer.handle_request(init_req)
    assert init_res["result"]["serverInfo"]["name"] == "unifile-by-soniscorett"
    assert "tools" in init_res["result"]["capabilities"]

    # 2. Tools List
    list_req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    list_res = MCPServer.handle_request(list_req)
    tool_names = [t["name"] for t in list_res["result"]["tools"]]
    assert "unifile_read_file" in tool_names
    assert "unifile_clean_text" in tool_names

    # 3. Tool Call
    call_req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "unifile_clean_text",
            "arguments": {
                "raw_text": "L'Ã©quipe a validÃ© le contrat.",
                "preferred_language": "en"
            }
        }
    }
    call_res = MCPServer.handle_request(call_req)
    assert call_res["result"]["isError"] is False
    content_text = call_res["result"]["content"][0]["text"]
    data = json.loads(content_text)
    assert data["readability_score"] >= 80.0
    assert data["threshold_met"] is True


def test_openai_tools_schema_and_execution():
    """Validates OpenAI/Anthropic tool schemas and execution handler."""
    assert len(UNIFILE_TOOL_SCHEMAS) >= 3
    for s in UNIFILE_TOOL_SCHEMAS:
        assert s["type"] == "function"
        assert "name" in s["function"]
        assert "parameters" in s["function"]

    # Execute tool
    res = execute_unifile_tool("unifile_clean_text", {
        "raw_text": "data:text/plain;base64,VGhpcyBpcyBhIHRlc3QgbWVzc2FnZS4=",
        "preferred_language": "en"
    })
    assert res["threshold_met"] is True
    assert "test message" in res["cleaned_text"].lower()


def test_langchain_tool():
    """Validates LangChain tool connector."""
    tool = UnifileTool(preferred_language="en")
    assert tool.name == "unifile_read_file"
    sample_path = str(SAMPLES_DIR / "mojibake_latin1_sample.txt")
    output = tool.run(sample_path)
    assert len(output) > 20
    assert "Ã©" not in output  # Mojibake stripped


def test_rest_api_health_and_formats():
    """Validates FastAPI REST endpoints."""
    # Health
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["service"] == "Unifile by Soniscorett"
    assert r.json()["read_only"] is True

    # Formats
    r2 = client.get("/api/v1/formats")
    assert r2.status_code == 200
    assert ".pdf" in r2.json()["documents"]
    assert ".xlsx" in r2.json()["spreadsheets"]


def test_rest_api_translate_and_corrupt():
    """Validates /api/v1/translate and /api/v1/corrupt_demo endpoints."""
    # Corrupt demo
    r_corr = client.post("/api/v1/corrupt_demo", json={
        "text": "Hello world from Soniscorett",
        "distortion_type": "mojibake"
    })
    assert r_corr.status_code == 200
    corrupted = r_corr.json()["corrupted_text"]

    # Translate clean
    r_trans = client.post("/api/v1/translate", json={
        "text": corrupted,
        "preferred_language": "en"
    })
    assert r_trans.status_code == 200
    res_data = r_trans.json()
    assert res_data["readability_score"] >= 80.0
    assert res_data["threshold_met"] is True


def test_cli_execution():
    """Tests CLI command execution via subprocess using active Python interpreter."""
    sample_file = SAMPLES_DIR / "zalgo_symbol_corrupted.txt"
    cmd = [sys.executable, "-m", "unifile.cli", str(sample_file), "--lang", "en", "--json"]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(SAMPLES_DIR.parent))
    assert proc.returncode == 0
    cli_out = json.loads(proc.stdout)
    assert cli_out["readability_score"] >= 80.0
    assert cli_out["threshold_met"] is True
