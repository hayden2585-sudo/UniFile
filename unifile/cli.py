"""
Unifile by Soniscorett - Command Line Interface (CLI)
Provides intuitive terminal commands to parse, heal, translate, or serve files.
"""

from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path

from .core.pipeline import UnifileEngine
from .connectors.mcp_server import MCPServer
from .core.unicode_env import configure_unicode_output, safe_print

# Ensure UTF-8 console output is active on Windows and legacy terminals
configure_unicode_output()


def run_cli():
    parser = argparse.ArgumentParser(
        prog="unifile",
        description="Unifile by Soniscorett - Universal Read-Only File Translator Connector for AI Models.",
        epilog="Guarantees >= 80% readable text in user's preferred language from any corrupted/encrypted/truncated source."
    )
    parser.add_argument("input", nargs="?", help="Path to input file, or omit to read from stdin.")
    parser.add_argument("-l", "--lang", default="en", help="Target preferred language (default: 'en').")
    parser.add_argument("-o", "--output", help="Output file path (default: prints to stdout).")
    parser.add_argument("-m", "--mcp", action="store_true", help="Launch Model Context Protocol (MCP) stdio server.")
    parser.add_argument("-s", "--server", action="store_true", help="Launch Unifile Web Dashboard & API server.")
    parser.add_argument("-p", "--port", type=int, default=8000, help="Port for web server (default: 8000).")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1; use 0.0.0.0 only when intentionally exposing the service).")
    parser.add_argument("--json", action="store_true", help="Output complete JSON metadata and diagnostics.")
    parser.add_argument("--inspect", action="store_true", help="Inspect file health without full translation.")
    parser.add_argument("--chat", action="store_true", help="Retrieve and synchronize a shared conversation link or export (ChatGPT, Claude, Perplexity).")
    parser.add_argument("--target-model", default="claude", help="Target model for context synchronization ('claude', 'openai', 'gemini', 'perplexity').")

    args = parser.parse_args()

    # MCP Server Mode
    if args.mcp:
        MCPServer.run_stdio()
        return

    # Web Server Mode
    if args.server:
        import uvicorn
        from .server import app
        host = os.environ.get("UNIFILE_HOST", args.host)
        port = int(os.environ.get("UNIFILE_PORT", args.port))
        safe_print(f"⚡ Starting Unifile by Soniscorett Web Dashboard on http://{host}:{port}")
        uvicorn.run(app, host=host, port=port)
        return

    # Chat Bridge Mode
    if args.chat:
        from .core.ai_context_bridge import AIContextBridge
        src = args.input
        if not src and not sys.stdin.isatty():
            src = sys.stdin.read()
        if not src:
            print("Error: Must provide a shared conversation URL or file/stdin to retrieve.", file=sys.stderr)
            sys.exit(1)
        res = AIContextBridge.retrieve(source=src, preferred_language=args.lang, target_model=args.target_model)
        if args.json:
            safe_print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            safe_print(f"=== Unifile AI Context Bridge: {res['platform'].upper()} -> {args.target_model.upper()} ===")
            safe_print(f"Title: {res['title']} | Turns: {res['turn_count']} | Readability: {res['readability_score']}%")
            safe_print(f"{'=' * 40}\n")
            safe_print(res["synchronized_context"]["markdown_transcript"])
        return

    # Processing File / Stdin
    raw_text: str = ""
    file_path: Path | None = None

    if args.input:
        file_path = Path(args.input)
        if not file_path.exists():
            safe_print(f"Error: File not found: {args.input}", file=sys.stderr)
            sys.exit(1)
    else:
        # Check stdin
        if not sys.stdin.isatty():
            raw_text = sys.stdin.read()
        else:
            parser.print_help()
            sys.exit(0)

    # Execute Engine
    if file_path:
        result = UnifileEngine.process_file(file_path, preferred_language=args.lang)
    else:
        result = UnifileEngine.process_text(raw_text, preferred_language=args.lang)

    res_dict = result.to_dict()

    if args.inspect:
        safe_print(json.dumps({
            "initial_score": res_dict["initial_score"],
            "final_score": res_dict["readability_score"],
            "grade": res_dict["grade"],
            "threshold_met": res_dict["threshold_met"],
            "detected_language": res_dict["detected_language"],
            "diagnostics": res_dict["diagnostics"],
            "transformations": res_dict["transformations_applied"],
        }, indent=2))
        return

    if args.json:
        output_str = json.dumps(res_dict, indent=2, ensure_ascii=False)
    else:
        # Text output with header summary
        status_sym = "✅" if res_dict["threshold_met"] else "⚠️"
        header = (
            f"=== Unifile by Soniscorett ===\n"
            f"{status_sym} Readability: {res_dict['readability_score']}% (Initial: {res_dict['initial_score']}%) | Grade: {res_dict['grade']}\n"
            f"🌐 Target Language: {res_dict['preferred_language_name']} | Source: {res_dict['detected_language'].upper()}\n"
            f"🛠️ Transformations: {len(res_dict['transformations_applied'])} applied\n"
            f"{'=' * 30}\n\n"
        )
        output_str = header + res_dict["cleaned_text"]

    if args.output:
        with open(args.output, "w", encoding="utf-8", errors="replace") as f:
            f.write(output_str)
        safe_print(f"Cleaned output saved to {args.output}")
    else:
        safe_print(output_str)


if __name__ == "__main__":
    run_cli()
