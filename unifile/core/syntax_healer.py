"""
Unifile by Soniscorett - Truncation & Syntax Repair Engine
Heals cut-off files, truncated JSON/XML/HTML, unbalanced brackets,
and mid-sentence/hyphenated word breaks.
"""

from __future__ import annotations
import json
import re
from typing import Tuple, List, Optional


class SyntaxHealer:
    """Repairs truncated data structures and severed text streams."""

    @classmethod
    def heal_truncated_json(cls, text: str) -> Tuple[str, Optional[str]]:
        """
        Attempts to heal truncated JSON by closing open quotes, brackets, and braces.
        """
        s = text.strip()
        if not ((s.startswith("{") and not s.endswith("}")) or (s.startswith("[") and not s.endswith("]"))):
            # Check if it already parses
            try:
                json.loads(s)
                return text, None
            except Exception:
                pass

        if not (s.startswith("{") or s.startswith("[")):
            return text, None

        # Clean trailing incomplete tokens: e.g. trailing comma or partial key/value
        # If open quote exists, close it
        in_quote = False
        escaped = False
        bracket_stack: List[str] = []

        for ch in s:
            if escaped:
                escaped = False
                continue
            if ch == "\\":
                escaped = True
                continue
            if ch == '"':
                in_quote = not in_quote
                continue
            if not in_quote:
                if ch in "{[":
                    bracket_stack.append(ch)
                elif ch == "}" and bracket_stack and bracket_stack[-1] == "{":
                    bracket_stack.pop()
                elif ch == "]" and bracket_stack and bracket_stack[-1] == "[":
                    bracket_stack.pop()

        candidate = s
        if in_quote:
            candidate += '"'

        # Trim trailing colon or comma before closing brackets
        candidate = re.sub(r":\s*$", ': ""', candidate)
        candidate = re.sub(r",\s*$", "", candidate)

        # Close all remaining open brackets in reverse order
        for open_bracket in reversed(bracket_stack):
            if open_bracket == "{":
                candidate += "}"
            elif open_bracket == "[":
                candidate += "]"

        try:
            parsed = json.loads(candidate)
            formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
            return formatted, f"Healed truncated JSON structure (restored {len(bracket_stack)} unclosed container brackets)."
        except Exception:
            # Fallback regex trailing cleanup
            pass

        return text, None

    @classmethod
    def heal_truncated_xml_html(cls, text: str) -> Tuple[str, Optional[str]]:
        """Balances unclosed XML/HTML tags in truncated markup."""
        s = text.strip()
        if not ("<" in s and ">" in s):
            return text, None

        # Strip partial trailing opening tag at EOF: e.g. "<div>Hello<p cla" -> "<div>Hello"
        if re.search(r"<[^>]*$", s):
            s = re.sub(r"<[^>]*$", "", s)

        # Find opened and closed tags
        void_tags = {"br", "hr", "img", "input", "meta", "link", "col", "base"}
        open_tags: List[str] = []

        # Simple tag scanner
        tag_matches = re.finditer(r"<(/)?([a-zA-Z0-9]+)(?:\s+[^>]*)?>", s)
        for m in tag_matches:
            is_close = m.group(1) == "/"
            tag_name = m.group(2).lower()
            if tag_name in void_tags:
                continue
            if is_close:
                if open_tags and open_tags[-1] == tag_name:
                    open_tags.pop()
            else:
                # Check for self-closing XML: <tag ... />
                if not m.group(0).rstrip(">").endswith("/"):
                    open_tags.append(tag_name)

        if open_tags:
            closers = "".join(f"</{tag}>" for tag in reversed(open_tags))
            healed = s + closers
            return healed, f"Healed truncated HTML/XML markup (auto-closed {len(open_tags)} tags: {', '.join(open_tags)})."

        return text, None

    @classmethod
    def heal_hyphenated_linebreaks(cls, text: str) -> Tuple[str, Optional[str]]:
        """Fixes hyphenated word breaks across lines: 'interconne-\\nction' -> 'interconnection'."""
        pattern = r"([A-Za-z]{2,})-\s*\n\s*([A-Za-z]{2,})"
        matches = len(re.findall(pattern, text))
        if matches > 0:
            healed = re.sub(pattern, r"\1\2", text)
            return healed, f"Reconnected {matches} hyphenated word breaks severed across line wraps."
        return text, None

    @classmethod
    def heal_unbalanced_brackets(cls, text: str) -> Tuple[str, Optional[str]]:
        """Heals unbalanced parentheses, braces, or brackets in text or code."""
        pairs = {"(": ")", "[": "]", "{": "}"}
        stack: List[str] = []
        for ch in text:
            if ch in pairs:
                stack.append(pairs[ch])
            elif ch in pairs.values():
                if stack and stack[-1] == ch:
                    stack.pop()

        if stack:
            # Append missing closers
            addition = "".join(reversed(stack))
            return text + addition, f"Balanced {len(stack)} unclosed syntax brackets ({addition})."
        return text, None

    @classmethod
    def heal_truncation(cls, text: str) -> Tuple[str, List[str]]:
        """Coordinates full truncation repair pipeline."""
        actions: List[str] = []
        if not text:
            return "", actions

        # 1. Hyphenated wrap healing
        text, act = cls.heal_hyphenated_linebreaks(text)
        if act:
            actions.append(act)

        # 2. JSON healing
        text, act = cls.heal_truncated_json(text)
        if act:
            actions.append(act)

        # 3. HTML/XML healing
        text, act = cls.heal_truncated_xml_html(text)
        if act:
            actions.append(act)

        # 4. Bracket balancing
        text, act = cls.heal_unbalanced_brackets(text)
        if act:
            actions.append(act)

        return text, actions
