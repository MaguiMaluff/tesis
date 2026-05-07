from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import requests


@dataclass(frozen=True)
class AIConfig:
    base_url: str          # e.g. https://ai.cloud.um.edu.ar/api/v1
    api_key: str
    model: str             # e.g. gpt-oss-20b
    temperature: float = 0.0
    max_tokens: int = 900
    timeout_seconds: int = 90


def load_ai_config_from_env() -> AIConfig:
    base_url = os.getenv("AI_BASE_URL", "").rstrip("/")
    api_key = os.getenv("AI_API_KEY", "")
    model = os.getenv("AI_MODEL", "gpt-oss-20b")
    temperature = float(os.getenv("AI_TEMPERATURE", "0"))
    max_tokens = int(os.getenv("AI_MAX_TOKENS", "900"))

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
    }

    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=cfg.timeout_seconds)
    if r.status_code >= 400:
        raise RuntimeError(f"AI HTTP {r.status_code}: {r.text[:500]}")

    return r.json()


def extract_json_content(openai_resp: dict[str, Any]) -> dict[str, Any]:
    """
    Expects the assistant to return JSON in message.content.
    """
    try:
        content = openai_resp["choices"][0]["message"]["content"]
    except Exception as e:
        raise RuntimeError(f"Unexpected AI response shape: {e}; resp={openai_resp!r}")

    try:
        return json.loads(content)
    except Exception as e:
        # Provide some context to debug malformed JSON
        preview = (content or "")[:500]
        raise RuntimeError(f"AI did not return valid JSON: {e}. content preview={preview!r}")