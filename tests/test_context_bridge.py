"""
Tests for AI Conversation Retrieval and Cross-Model Context Synchronization.
Validates extraction from ChatGPT, Claude, Perplexity, Gemini, and healing corruptions.
"""

import json
import pytest
from fastapi.testclient import TestClient

from unifile.core.ai_context_bridge import AIContextBridge, UniversalConversation, UniversalMessage
from unifile.server import app

client = TestClient(app)

# Realistic ChatGPT Next.js hydration payload sample with corrupted/garbled content
CHATGPT_NEXT_DATA_SAMPLE = """<!DOCTYPE html>
<html>
<head><title>Quantum Telemetry Analysis - ChatGPT</title></head>
<body>
<div id="__next">
  <script id="__NEXT_DATA__" type="application/json">
  {
    "props": {
      "pageProps": {
        "sharedConversationId": "share-98741-alpha",
        "serverResponse": {
          "data": {
            "title": "Quantum Telemetry Analysis",
            "linear_conversation": [
              {
                "message": {
                  "id": "msg-1",
                  "author": {"role": "user"},
                  "content": {"parts": ["Please inspect the l'Ã©quipe telemetry logs and confirm if all neural parameters are valid."]},
                  "metadata": {"model_slug": "gpt-4o"}
                }
              },
              {
                "message": {
                  "id": "msg-2",
                  "author": {"role": "assistant"},
                  "content": {"parts": ["T\u200bh\u200be̷ ̵s̴y̵s̴t̵e̵m̴ operational metrics have been fully decrypted.\\nAll 128 nodes report optimal coherence."]},
                  "metadata": {"model_slug": "gpt-4o"}
                }
              }
            ]
          }
        }
      }
    }
  }
  </script>
</div>
</body>
</html>"""

# Realistic Claude conversation export sample
CLAUDE_EXPORT_SAMPLE = json.dumps({
    "uuid": "claude-thread-789",
    "name": "Distributed Memory Architecture",
    "chat_messages": [
        {
            "sender": "human",
            "text": "How do we bridge context between Claude and OpenAI models without losing token state?"
        },
        {
            "sender": "assistant",
            "text": "Soniscorett Unifile establishes a universal normalized message schema that translates context into model-native structures, guaranteeing at least eighty percent readability across all platforms."
        }
    ]
})

# Realistic Perplexity search payload sample with web citations
PERPLEXITY_SEARCH_SAMPLE = """<!DOCTYPE html>
<html>
<head><title>Universal AI File Connector Standards | Perplexity</title></head>
<body>
<script id="__NEXT_DATA__" type="application/json">
{
  "props": {
    "pageProps": {
      "query": "What are the latest open standards for universal AI file connectors?",
      "answer": "Universal file connectors like Unifile by Soniscorett allow read-only ingestion across 30+ formats while repairing Mojibake and Zalgo [1]. They bridge context across LLM ecosystems [2].",
      "webResults": [
        {"name": "Soniscorett Labs", "url": "https://soniscorett.ai/unifile"},
        {"name": "Model Context Protocol", "url": "https://modelcontextprotocol.io"}
      ]
    }
  }
}
</script>
</body>
</html>"""


def test_retrieve_chatgpt_share_and_heal():
    """Tests extracting ChatGPT conversation, healing mojibake & zalgo, and verifying >=80% readability."""
    res = AIContextBridge.retrieve(
        source=CHATGPT_NEXT_DATA_SAMPLE,
        preferred_language="en",
        target_model="claude"
    )

    assert res["success"] is True
    assert res["platform"] == "chatgpt"
    assert res["title"] == "Quantum Telemetry Analysis"
    assert res["turn_count"] == 2
    assert res["readability_score"] >= 80.0
    assert res["threshold_met"] is True

    # Check ungarbling in user message: 'l'Ã©quipe' -> 'l'équipe'
    user_turn = res["conversation"]["messages"][0]
    assert user_turn["role"] == "user"
    assert "équipe" in user_turn["content"] or "team" in user_turn["content"].lower()

    # Check zalgo cleaning in assistant message
    asst_turn = res["conversation"]["messages"][1]
    assert asst_turn["role"] == "assistant"
    assert "system" in asst_turn["content"].lower()

    # Verify cross-model synchronized context outputs
    sync = res["synchronized_context"]
    assert "<context_handover" in sync["claude_xml_prompt"]
    assert len(sync["openai_messages"]) >= 3  # system + 2 turns
    assert sync["openai_messages"][0]["role"] == "system"
    assert "# Quantum Telemetry Analysis" in sync["markdown_transcript"]


def test_retrieve_claude_export_and_sync_to_openai():
    """Tests importing Claude conversation export and syncing into OpenAI / ChatGPT format."""
    res = AIContextBridge.retrieve(
        source=CLAUDE_EXPORT_SAMPLE,
        preferred_language="en",
        target_model="openai"
    )

    assert res["success"] is True
    assert res["platform"] == "claude"
    assert res["turn_count"] == 2
    assert res["readability_score"] >= 80.0

    # Verify OpenAI format payload
    openai_msgs = res["synchronized_context"]["openai_messages"]
    assert openai_msgs[0]["role"] == "system"
    assert "CLAUDE" in openai_msgs[0]["content"]
    assert openai_msgs[1]["role"] == "user"
    assert openai_msgs[2]["role"] == "assistant"


def test_retrieve_perplexity_with_citations():
    """Tests extracting Perplexity search synthesis and citations."""
    res = AIContextBridge.retrieve(
        source=PERPLEXITY_SEARCH_SAMPLE,
        preferred_language="en",
        target_model="claude"
    )

    assert res["success"] is True
    assert res["platform"] == "perplexity"
    assert res["turn_count"] == 2

    # Check assistant turn citations
    asst_turn = res["conversation"]["messages"][1]
    assert len(asst_turn["citations"]) >= 2
    assert asst_turn["citations"][0]["name"] == "Soniscorett Labs" or "Soniscorett" in asst_turn["citations"][0].get("title", "")


def test_rest_api_context_retrieve():
    """Validates FastAPI /api/v1/context/retrieve endpoint."""
    resp = client.post("/api/v1/context/retrieve", json={
        "source": CLAUDE_EXPORT_SAMPLE,
        "preferred_language": "es",  # Translate to Spanish
        "target_model": "claude"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["readability_score"] >= 80.0
    assert data["preferred_language"] == "es"
    assert "<context_handover" in data["synchronized_context"]["claude_xml_prompt"]


def test_rest_api_context_platforms():
    """Validates /api/v1/context/platforms metadata endpoint."""
    resp = client.get("/api/v1/context/platforms")
    assert resp.status_code == 200
    platforms = [p["id"] for p in resp.json()["platforms"]]
    assert "chatgpt" in platforms
    assert "claude" in platforms
    assert "perplexity" in platforms
    assert "gemini" in platforms
