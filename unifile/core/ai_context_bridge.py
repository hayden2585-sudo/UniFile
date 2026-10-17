"""
Unifile by Soniscorett - AI Conversation Bridge & Cross-Model Context Synchronizer
Retrieves inaccessible, shared, or exported conversation threads from ChatGPT, Claude,
Perplexity, Gemini, etc., repairs corruption/truncation, and synchronizes context across models.
"""

from __future__ import annotations
import json
import re
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple, Union
import httpx
from bs4 import BeautifulSoup

from .pipeline import UnifileEngine, UnifileResult
from .syntax_healer import SyntaxHealer
from .readability import assess_readability
from .network_guard import NetworkGuard, SecurityValidationError


class UniversalMessage:
    """Represents a normalized conversational turn across any AI model."""

    def __init__(
        self,
        role: str,
        content: str,
        original_content: Optional[str] = None,
        model: Optional[str] = None,
        timestamp: Optional[str] = None,
        citations: Optional[List[Dict[str, str]]] = None,
    ):
        self.role = role.lower()  # "user", "assistant", "system", "tool"
        self.content = content
        self.original_content = original_content or content
        self.model = model
        self.timestamp = timestamp
        self.citations = citations or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "original_content": self.original_content,
            "model": self.model,
            "timestamp": self.timestamp,
            "citations": self.citations,
        }


class UniversalConversation:
    """A multi-turn conversation extracted from any AI platform."""

    def __init__(
        self,
        title: str,
        platform: str,
        messages: List[UniversalMessage],
        share_url: Optional[str] = None,
        readability_score: float = 100.0,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.title = title
        self.platform = platform
        self.messages = messages
        self.share_url = share_url
        self.readability_score = readability_score
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "platform": self.platform,
            "share_url": self.share_url,
            "readability_score": round(self.readability_score, 2),
            "turn_count": len(self.messages),
            "messages": [m.to_dict() for m in self.messages],
            "metadata": self.metadata,
        }


class AIContextBridge:
    """Retrieves and synchronizes conversation contexts across AI ecosystems."""

    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    @classmethod
    def retrieve(
        cls,
        source: str,
        preferred_language: str = "en",
        target_model: str = "claude"
    ) -> Dict[str, Any]:
        """
        Retrieves conversation from a URL (ChatGPT/Claude/Perplexity share),
        or raw HTML/JSON string/export file, normalizes it, ungarbles text,
        and generates synchronized cross-model context representations.
        """
        # Step 1: Ingest raw content (URL or direct payload)
        raw_text, platform, url = cls._ingest_source(source)

        # Step 2: Parse conversation tree into Universal Messages
        conversation = cls._parse_conversation(raw_text, platform, share_url=url)

        # Step 3: Run Unifile multi-pass distortion healer & translator on all turns
        total_initial_score = 0.0
        total_final_score = 0.0
        healed_messages: List[UniversalMessage] = []

        for msg in conversation.messages:
            res: UnifileResult = UnifileEngine.process_text(
                raw_text=msg.content,
                preferred_language=preferred_language,
                metadata={"role": msg.role, "platform": conversation.platform}
            )
            total_initial_score += res.initial_report.score
            total_final_score += res.final_report.score

            healed_messages.append(
                UniversalMessage(
                    role=msg.role,
                    content=res.cleaned_text,
                    original_content=msg.content,
                    model=msg.model,
                    timestamp=msg.timestamp,
                    citations=msg.citations,
                )
            )

        turn_count = max(1, len(healed_messages))
        avg_initial = round(total_initial_score / turn_count, 2)
        avg_final = round(total_final_score / turn_count, 2)

        conversation.messages = healed_messages
        conversation.readability_score = avg_final

        # Step 4: Synchronize Context Across Models
        sync_payloads = cls.synchronize_context(conversation, target_model=target_model)

        return {
            "success": True,
            "title": conversation.title,
            "platform": conversation.platform,
            "share_url": conversation.share_url,
            "turn_count": len(conversation.messages),
            "initial_readability_score": avg_initial,
            "readability_score": avg_final,
            "threshold_met": avg_final >= 80.0,
            "preferred_language": preferred_language,
            "conversation": conversation.to_dict(),
            "synchronized_context": sync_payloads,
        }

    @classmethod
    def _ingest_source(cls, source: str) -> Tuple[str, str, Optional[str]]:
        """Determines platform and retrieves HTML/JSON payload from URL or direct text."""
        source_clean = source.strip()
        url: Optional[str] = None
        platform = "generic"

        if source_clean.startswith("http://") or source_clean.startswith("https://"):
            url = source_clean
            # Platform detection by URL
            if "chatgpt.com" in url or "chat.openai.com" in url:
                platform = "chatgpt"
            elif "claude.ai" in url:
                platform = "claude"
            elif "perplexity.ai" in url:
                platform = "perplexity"
            elif "gemini.google.com" in url:
                platform = "gemini"

            # Secure fetch using NetworkGuard with SSRF defense and redirect validation
            try:
                raw_text, final_url = NetworkGuard.safe_fetch(
                    url=url,
                    user_agent=cls.USER_AGENT,
                    enforce_domain_allowlist=True,
                )
                url = final_url
            except SecurityValidationError as sve:
                raise ValueError(f"Security Policy Rejection (SSRF Defense): {str(sve)}")
            except Exception as e:
                # If network fetch fails (e.g. offline sandbox or remote host down), return informative offline indicator
                raw_text = f"<!-- Offline Snapshot of {url} -->\n<div class='error'>Remote URL fetch unavailable: {str(e)}</div>"
        else:
            raw_text = source_clean
            # Detect platform from payload structure
            if '"linear_conversation"' in raw_text or '"sharedConversationId"' in raw_text or "chatgpt" in raw_text.lower():
                platform = "chatgpt"
            elif '"chat_messages"' in raw_text or "claude" in raw_text.lower():
                platform = "claude"
            elif '"webResults"' in raw_text or "perplexity" in raw_text.lower():
                platform = "perplexity"
            elif "gemini" in raw_text.lower():
                platform = "gemini"

        return raw_text, platform, url

    @classmethod
    def _parse_conversation(cls, raw: str, platform: str, share_url: Optional[str] = None) -> UniversalConversation:
        """Extracts messages from Next.js hydration scripts, JSON exports, or DOM nodes."""
        messages: List[UniversalMessage] = []
        title = "AI Conversation Thread"

        # Strategy 1: Check for embedded __NEXT_DATA__ JSON script tag (used by ChatGPT & Perplexity)
        next_data_match = re.search(r'<script[^>]*id=\\?["\']__NEXT_DATA__\\?["\'][^>]*>(.*?)</script>', raw, flags=re.DOTALL)
        if next_data_match:
            try:
                parsed_json = json.loads(next_data_match.group(1))
                extracted = cls._extract_from_next_data(parsed_json, platform)
                if extracted:
                    return extracted
            except Exception:
                pass

        # Strategy 2: Direct JSON payload (e.g. conversations.json export or API payload)
        if (raw.startswith("{") and raw.endswith("}")) or (raw.startswith("[") and raw.endswith("]")):
            try:
                data = json.loads(raw)
                extracted = cls._extract_from_json_export(data, platform)
                if extracted:
                    return extracted
            except Exception:
                pass

        # Strategy 3: HTML DOM extraction (fallback for server-rendered or archived share pages)
        soup = BeautifulSoup(raw, "html.parser")
        
        # Check page title
        title_tag = soup.find("title")
        if title_tag and title_tag.text.strip():
            title = title_tag.text.strip().replace(" - ChatGPT", "").replace(" - Claude", "").replace(" | Perplexity", "")

        # A. ChatGPT HTML DOM
        chatgpt_nodes = soup.find_all(attrs={"data-message-author-role": True})
        if chatgpt_nodes:
            for node in chatgpt_nodes:
                role = node.get("data-message-author-role", "assistant")
                txt = node.get_text(separator="\n", strip=True)
                if txt:
                    messages.append(UniversalMessage(role=role, content=txt, model="gpt-4o"))
            if messages:
                return UniversalConversation(title=title, platform="chatgpt", messages=messages, share_url=share_url)

        # B. Claude HTML DOM
        claude_user = soup.find_all(class_=re.compile(r"user-message|font-user", re.I))
        claude_assistant = soup.find_all(class_=re.compile(r"claude-message|font-claude", re.I))
        if claude_user or claude_assistant:
            for node in soup.find_all(class_=re.compile(r"message-row|conversation-turn", re.I)):
                is_user = bool(node.find(class_=re.compile(r"user", re.I)))
                txt = node.get_text(separator="\n", strip=True)
                if txt:
                    messages.append(UniversalMessage(role="user" if is_user else "assistant", content=txt, model="claude-3-5-sonnet"))
            if messages:
                return UniversalConversation(title=title, platform="claude", messages=messages, share_url=share_url)

        # Strategy 4: Fallback Text / Transcript RegEx Scanner
        # Matches patterns like "User:", "Human:", "Assistant:", "ChatGPT:", "Claude:", "Perplexity:"
        turn_pattern = re.compile(r"(?:\n|^)(User|Human|Assistant|ChatGPT|Claude|Perplexity|Gemini):\s*", re.IGNORECASE)
        splits = turn_pattern.split(raw)

        if len(splits) >= 3:
            # Pattern matched alternating [prefix, speaker, content, speaker, content...]
            for i in range(1, len(splits), 2):
                speaker = splits[i].strip().lower()
                content = splits[i+1].strip() if (i+1) < len(splits) else ""
                role = "user" if speaker in ("user", "human") else "assistant"
                if content:
                    messages.append(UniversalMessage(role=role, content=content, model=speaker))

            if messages:
                return UniversalConversation(title=title, platform=platform, messages=messages, share_url=share_url)

        # Catch-all: Single turn containing the whole salvaged document
        clean_raw = soup.get_text(separator="\n", strip=True) if "<" in raw else raw
        messages.append(UniversalMessage(role="assistant", content=clean_raw or raw, model="universal-salvage"))

        return UniversalConversation(title=title, platform=platform, messages=messages, share_url=share_url)

    @classmethod
    def _extract_from_next_data(cls, data: Dict[str, Any], platform: str) -> Optional[UniversalConversation]:
        """Navigates Next.js pageProps for ChatGPT or Perplexity conversation trees."""
        page_props = data.get("props", {}).get("pageProps", {})

        # ChatGPT Share Format
        if "serverResponse" in page_props or "sharedConversationId" in page_props:
            srv = page_props.get("serverResponse", {}).get("data", {})
            title = srv.get("title") or page_props.get("title") or "ChatGPT Shared Conversation"
            mapping = srv.get("mapping", {})
            linear = srv.get("linear_conversation", [])

            messages: List[UniversalMessage] = []

            # If linear_conversation array exists
            if linear:
                for item in linear:
                    role = item.get("message", {}).get("author", {}).get("role", "user")
                    parts = item.get("message", {}).get("content", {}).get("parts", [])
                    content = "\n".join(str(p) for p in parts if isinstance(p, str))
                    model = item.get("message", {}).get("metadata", {}).get("model_slug")
                    if content.strip():
                        messages.append(UniversalMessage(role=role, content=content, model=model))

            # Otherwise walk mapping graph
            elif mapping:
                for node_id, node in mapping.items():
                    msg = node.get("message")
                    if msg and msg.get("author") and msg.get("content"):
                        role = msg["author"].get("role")
                        if role in ("user", "assistant"):
                            parts = msg["content"].get("parts", [])
                            content = "\n".join(str(p) for p in parts if isinstance(p, str))
                            model = msg.get("metadata", {}).get("model_slug")
                            if content.strip():
                                messages.append(UniversalMessage(role=role, content=content, model=model))

            if messages:
                return UniversalConversation(title=title, platform="chatgpt", messages=messages)

        # Perplexity Share / Search Format
        if "query" in page_props or "webResults" in page_props or "entry" in page_props:
            title = page_props.get("query") or "Perplexity Research Thread"
            messages: List[UniversalMessage] = []
            
            # User query
            if "query" in page_props:
                messages.append(UniversalMessage(role="user", content=page_props["query"]))

            # Extract synthesis and sources
            answer = page_props.get("answer") or page_props.get("entry", {}).get("text") or ""
            web_results = page_props.get("webResults", []) or []
            citations = [
                {"title": r.get("name") or r.get("title", ""), "name": r.get("name") or r.get("title", ""), "url": r.get("url", "")}
                for r in web_results if isinstance(r, dict)
            ]

            if answer:
                messages.append(UniversalMessage(role="assistant", content=answer, model="sonar-pro", citations=citations))

            if messages:
                return UniversalConversation(title=title, platform="perplexity", messages=messages)

        return None

    @classmethod
    def _extract_from_json_export(cls, data: Union[Dict, List], platform: str) -> Optional[UniversalConversation]:
        """Parses exported conversation dumps from ChatGPT, Claude, or Perplexity."""
        messages: List[UniversalMessage] = []

        # Case 1: ChatGPT data export conversations.json (list of conversations)
        if isinstance(data, list) and data and "mapping" in data[0]:
            conv0 = data[0]
            title = conv0.get("title", "ChatGPT Conversation Export")
            for node_id, node in conv0.get("mapping", {}).items():
                msg = node.get("message")
                if msg and msg.get("author") and msg.get("content"):
                    role = msg["author"].get("role")
                    if role in ("user", "assistant"):
                        parts = msg["content"].get("parts", [])
                        text = "\n".join(str(p) for p in parts if isinstance(p, str))
                        if text.strip():
                            messages.append(UniversalMessage(role=role, content=text))
            if messages:
                return UniversalConversation(title=title, platform="chatgpt", messages=messages)

        # Case 2: Claude conversation export format: {"name": "...", "chat_messages": [...]}
        if isinstance(data, dict) and "chat_messages" in data:
            title = data.get("name", "Claude Conversation Export")
            for msg in data.get("chat_messages", []):
                sender = msg.get("sender", "human")
                role = "user" if sender == "human" else "assistant"
                text = msg.get("text", "")
                if text.strip():
                    messages.append(UniversalMessage(role=role, content=text, model="claude-3-5-sonnet"))
            if messages:
                return UniversalConversation(title=title, platform="claude", messages=messages)

        # Case 3: List of generic OpenAI messages: [{"role": "user", "content": "..."}, ...]
        if isinstance(data, list) and data and "role" in data[0] and "content" in data[0]:
            for item in data:
                messages.append(UniversalMessage(role=item.get("role", "user"), content=item.get("content", "")))
            return UniversalConversation(title="Synchronized Model Messages", platform=platform, messages=messages)

        return None

    @classmethod
    def synchronize_context(cls, conv: UniversalConversation, target_model: str = "claude") -> Dict[str, Any]:
        """
        Translates and maps universal conversation turns into model-specific injection formats.
        Enables seamless cross-model continuation.
        """
        target = target_model.lower()

        # 1. Claude XML Context Handover Format
        claude_xml_parts = [
            f'<context_handover platform="{conv.platform.upper()}" title="{conv.title}">',
            f'  <metadata readability_score="{conv.readability_score}%" turns="{len(conv.messages)}" />',
            '  <conversation_history>'
        ]
        for m in conv.messages:
            claude_xml_parts.append(f'    <turn role="{m.role}">\n{m.content}\n    </turn>')
        claude_xml_parts.append('  </conversation_history>\n</context_handover>')
        claude_prompt = "\n".join(claude_xml_parts)

        # 2. OpenAI / ChatGPT Messages Payload Format
        openai_messages = [
            {
                "role": "system",
                "content": (
                    f"You are continuing a conversation previously held on {conv.platform.upper()} (Title: '{conv.title}'). "
                    f"Readability is verified at {conv.readability_score}%. Seamlessly preserve this shared context."
                )
            }
        ]
        for m in conv.messages:
            openai_messages.append({"role": m.role if m.role in ("user", "assistant", "system") else "user", "content": m.content})

        # 3. Gemini Contents Payload Format
        gemini_contents = []
        for m in conv.messages:
            gemini_role = "user" if m.role == "user" else "model"
            gemini_contents.append({"role": gemini_role, "parts": [{"text": m.content}]})

        # 4. Perplexity Context Query Bundle
        last_turn = conv.messages[-1].content if conv.messages else ""
        perplexity_query = f"[Context from {conv.platform.upper()}: {conv.title}]\n{last_turn}"

        # 5. Clean Markdown Transcript
        md_lines = [
            f"# {conv.title}",
            f"> **Source Platform:** {conv.platform.upper()} | **Readability:** {conv.readability_score}% | **Turns:** {len(conv.messages)}",
            "",
            "---",
            ""
        ]
        for m in conv.messages:
            speaker_badge = "👤 **User**" if m.role == "user" else f"🤖 **Assistant ({m.model or conv.platform.upper()})**"
            md_lines.append(f"{speaker_badge}:\n\n{m.content}\n\n---")

        markdown_transcript = "\n".join(md_lines)

        return {
            "claude_xml_prompt": claude_prompt,
            "openai_messages": openai_messages,
            "gemini_contents": gemini_contents,
            "perplexity_query": perplexity_query,
            "markdown_transcript": markdown_transcript,
            "preferred_target": target,
        }
