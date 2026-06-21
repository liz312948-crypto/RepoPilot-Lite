from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class OptionalLLMSummarizer:
    """Small stdlib-only OpenAI-compatible chat client with safe fallback behavior."""

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def summarize(
        self,
        repo_name: str,
        question: str,
        files: list[str],
        readme: str | None,
        search_matches: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        if not self.is_configured:
            return None

        payload = {
            "model": self.model,
            "temperature": 0.2,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You summarize repositories for a lightweight coding-agent backend. "
                        "Return only compact JSON with repo_summary, key_files, "
                        "modification_plan, risk_notes, and suggestions."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "repo_name": repo_name,
                            "question": question,
                            "files": files[:80],
                            "readme_excerpt": (readme or "")[:2000],
                            "search_matches": search_matches[:20],
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        }

        request = Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=20) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError):
            return None

        try:
            content = raw["choices"][0]["message"]["content"]
            parsed = json.loads(_strip_json_fence(content))
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            return None

        if not isinstance(parsed, dict):
            return None
        parsed["llm_used"] = True
        return parsed


def _strip_json_fence(content: str) -> str:
    text = content.strip()
    if text.startswith("```json"):
        text = text.removeprefix("```json").strip()
    elif text.startswith("```"):
        text = text.removeprefix("```").strip()
    if text.endswith("```"):
        text = text.removesuffix("```").strip()
    return text
