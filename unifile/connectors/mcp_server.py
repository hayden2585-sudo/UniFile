"""
Unifile by Soniscorett - Model Context Protocol (MCP) 1.0 Compliant Server
Enables Claude Desktop, Cursor, Windsurf, and custom LLM agents to seamlessly
invoke Unifile as a standard MCP tool via stdio or HTTP JSON-RPC.
"""

from __future__ import annotations
import json
import sys
from typing import Dict, Any, List, Optional
from .openai_tools import UNIFILE_TOOL_SCHEMAS, execute_unifile_tool
from ..core.unicode_env import configure_unicode_output

# Ensure UTF-8 stdio streams on Windows and all platforms
configure_unicode_output()

MCP_VERSION = "2024-11-05"


class MCPServer:
    """Standard Model Context Protocol (MCP) JSON-RPC 2.0 Server."""

    @classmethod
    def get_tool_definitions(cls) -> List[Dict[str, Any]]:
        """Converts OpenAPI/OpenAI style schema to MCP tool format."""
        mcp_tools = []
        for s in UNIFILE_TOOL_SCHEMAS:
            fn = s["function"]
            mcp_tools.append({
                "name": fn["name"],
                "description": fn["description"],
                "inputSchema": fn["parameters"]
            })
        return mcp_tools

    @classmethod
    def handle_request(cls, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Processes a single JSON-RPC 2.0 request."""
        req_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        # 1. Initialize Handshake
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": MCP_VERSION,
                    "capabilities": {
                        "tools": {
                            "listChanged": False
                        },
                        "resources": {},
                        "prompts": {}
                    },
                    "serverInfo": {
                        "name": "unifile-by-soniscorett",
                        "version": "2.4.0",
                        "vendor": "Soniscorett"
                    }
                }
            }

        # 2. Notifications (e.g. initialized)
        elif method == "notifications/initialized" or method == "initialized":
            return None

        # 3. Ping
        elif method == "ping":
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}

        # 4. Tools list
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": cls.get_tool_definitions()
                }
            }

        # 5. Tool call
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            result = execute_unifile_tool(tool_name, tool_args)
            
            # Format according to MCP tool response spec
            text_payload = json.dumps(result, indent=2, ensure_ascii=False)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": text_payload
                        }
                    ],
                    "isError": "error" in result
                }
            }

        # 6. Prompts list
        elif method == "prompts/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "prompts": [
                        {
                            "name": "analyze_corrupted_file",
                            "description": "Reads and restores a distorted, encrypted, or truncated file into readable format (>=80% readable) using Soniscorett Unifile.",
                            "arguments": [
                                {
                                    "name": "path",
                                    "description": "File path to process",
                                    "required": True
                                },
                                {
                                    "name": "language",
                                    "description": "Target language (default: en)",
                                    "required": False
                                }
                            ]
                        }
                    ]
                }
            }

        # Fallback Method Not Found
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Method '{method}' not found."
                }
            }

    @classmethod
    def run_stdio(cls):
        """Standard IO event loop for MCP CLI integration."""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
                response = cls.handle_request(request)
                if response is not None:
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
            except Exception as e:
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {str(e)}"}
                }
                sys.stdout.write(json.dumps(err_resp) + "\n")
                sys.stdout.flush()


if __name__ == "__main__":
    MCPServer.run_stdio()
