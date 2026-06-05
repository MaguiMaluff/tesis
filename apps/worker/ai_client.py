from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import requests


@dataclass(frozen=True)
class AIConfig:
    base_url: str          
    api_key: str
    model: str             
    temperature: float = 0.0
    max_tokens: int = 1500
    timeout_seconds: int = 90


def load_ai_config_from_env() -> AIConfig:
    base_url = os.getenv("AI_BASE_URL", "").rstrip("/")
    api_key = os.getenv("AI_API_KEY", "")
    model = os.getenv("AI_MODEL", "gpt-oss-20b")
    temperature = float(os.getenv("AI_TEMPERATURE", "0"))
    max_tokens = int(os.getenv("AI_MAX_TOKENS", "1500"))
    timeout_seconds = int(os.getenv("AI_TIMEOUT_SECONDS", "90"))

    missing = []
    for k, v in [("AI_BASE_URL", base_url), ("AI_API_KEY", api_key), ("AI_MODEL", model)]:
        if not v:
            missing.append(k)
    if missing:
        raise RuntimeError(f"Missing required AI env vars: {', '.join(missing)}")

    return AIConfig(
        base_url=base_url,
        api_key=api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout_seconds=timeout_seconds,
    )


def chat_completions(cfg: AIConfig, messages: list[dict[str, str]]) -> dict[str, Any]:
    """
    Calls OpenAI-compatible /chat/completions and returns parsed JSON response.
    """
    url = f"{cfg.base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": cfg.model,
        "messages": messages,
        "temperature": cfg.temperature,
        "max_tokens": cfg.max_tokens,
        "tools": [],
        "tool_choice": "none",
    }

    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=cfg.timeout_seconds)
    if r.status_code >= 400:
        raise RuntimeError(f"AI HTTP {r.status_code}: {r.text[:500]}")

    return r.json()


def _extract_first_balanced_json_object(s: str) -> str:
    """
    Returns the first balanced {...} JSON object found in s.
    If none found, returns s.

    This avoids greedy-regex failures when the backend returns extra text
    or when there are braces inside strings.
    """
    start = s.find("{")
    if start == -1:
        return s

    depth = 0
    in_str = False
    escape = False

    for i in range(start, len(s)):
        ch = s[i]

        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue

        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]

    # Truncated/unbalanced: return from first '{' so caller can decide what to do
    return s[start:]


def extract_json_content(openai_resp: dict[str, Any]) -> dict[str, Any]:
    """
    Extracts and parses JSON from OpenAI-compatible response.

    OpenWebUI/Ollama-like backends may return output in:
      - choices[0].message.content
      - OR choices[0].message.reasoning (with content empty)
    We handle both. Also uses balanced-brace extraction for robustness.
    """
    try:
        choice0 = (openai_resp.get("choices") or [{}])[0]
        msg = choice0.get("message") or {}

        content = (msg.get("content") or "").strip()
        if not content:
            content = (msg.get("reasoning") or "").strip()

        if not content:
            raise RuntimeError(
                "AI returned empty content and reasoning. "
                f"choice0_keys={list(choice0.keys())} "
                f"message_keys={list(msg.keys())} "
                f"finish_reason={choice0.get('finish_reason')!r}"
            )

        json_str = _extract_first_balanced_json_object(content).strip()
        return json.loads(json_str)

    except Exception as e:
        preview = str(openai_resp)[:1200]
        raise RuntimeError(f"AI did not return valid JSON: {e}. resp_preview={preview}")