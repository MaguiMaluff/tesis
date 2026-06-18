from __future__ import annotations

import copy
import re
from typing import Any


_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_PHONE_RE = re.compile(r"\+?\d[\d\s().-]{6,}\d")
_HANDLE_RE = re.compile(r"(?<!\w)@[A-Za-z0-9._]{2,}")
_EXACT_AGE_RE = re.compile(r"\b\d{1,2}\s*(?:años|ano|año|yrs?|years?)\b", re.IGNORECASE)
_AGE_CONTEXT_RE = re.compile(r"\b(?:edad|menor|adulto|adolescente)\D{0,20}\b\d{1,2}\b", re.IGNORECASE)
_LONG_NUMBER_RE = re.compile(r"\b\d{6,}\b")
_MULTI_SPACE_RE = re.compile(r"\s+")

_CHILD_SUBJECT_RE = re.compile(r"\b(?:menor|niñ[oa]|adolescente|chic[oa]|hij[oa])\b", re.IGNORECASE)
_CHILD_DISCLOSURE_RE = re.compile(
    r"\b(?:indica|dice|menciona|cuenta|informa|comparte|revela|responde|declara|"
    r"tiene|vive|usa|no usa|entrega|da|env[ií]a)\b",
    re.IGNORECASE,
)
_ACTION_RE = re.compile(
    r"\b(?:solicita|pide|pregunta|intenta|presiona|propone|busca|insiste|requiere|"
    r"contacto|encuentro|secreto|foto|imagen|edad|whatsapp|wpp)\b",
    re.IGNORECASE,
)
_ACTION_VERB_RE = re.compile(
    r"\b(?:solicita|pide|pregunta|intenta|presiona|propone|busca|insiste|requiere)\b",
    re.IGNORECASE,
)


def _clean_spaces(value: str) -> str:
    return _MULTI_SPACE_RE.sub(" ", value).strip(" .;:-")


def _redact_private_data(value: str) -> str:
    value = _EMAIL_RE.sub("[email omitido]", value)
    value = _URL_RE.sub("[link omitido]", value)
    value = _PHONE_RE.sub("[telefono omitido]", value)
    value = _HANDLE_RE.sub("[usuario omitido]", value)
    value = _EXACT_AGE_RE.sub("[edad exacta omitida]", value)
    value = _AGE_CONTEXT_RE.sub("[edad exacta omitida]", value)
    value = _LONG_NUMBER_RE.sub("[identificador omitido]", value)
    return _clean_spaces(value)


def _is_child_disclosure(value: str) -> bool:
    return bool(_CHILD_SUBJECT_RE.search(value) and _CHILD_DISCLOSURE_RE.search(value))


def _remove_child_disclosure_sentences(value: str) -> str:
    parts = re.split(r"(?<=[.!?])\s+|;\s+", value)
    kept = [part for part in parts if part and not _is_child_disclosure(part)]
    return _clean_spaces(" ".join(kept))


def sanitize_text(value: Any, *, drop_child_disclosure: bool = False) -> str:
    text = _redact_private_data(str(value or ""))
    if drop_child_disclosure and _is_child_disclosure(text):
        return _remove_child_disclosure_sentences(text)
    return text


def sanitize_list(values: Any, *, max_items: int, drop_child_disclosure: bool = True) -> list[str]:
    if not isinstance(values, list):
        return []

    sanitized: list[str] = []
    for item in values:
        text = sanitize_text(item, drop_child_disclosure=drop_child_disclosure)
        if "[edad exacta omitida]" in text and not _ACTION_VERB_RE.search(text):
            continue
        if text and text not in sanitized:
            sanitized.append(text)
        if len(sanitized) >= max_items:
            break
    return sanitized


def _sanitize_recursive(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sanitize_recursive(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_recursive(item) for item in value]
    if isinstance(value, str):
        return sanitize_text(value)
    return value


def sanitize_ai_output(ai_json: dict[str, Any]) -> dict[str, Any]:
    sanitized = _sanitize_recursive(copy.deepcopy(ai_json if isinstance(ai_json, dict) else {}))

    assessment = sanitized.setdefault("assessment", {})
    if isinstance(assessment, dict):
        assessment["signals"] = sanitize_list(assessment.get("signals"), max_items=8)

    evidence = sanitized.setdefault("evidence", {})
    if isinstance(evidence, dict):
        evidence["quoted_messages"] = []

    explanation = sanitized.setdefault("explanation", {})
    if isinstance(explanation, dict):
        explanation["short_reason_safe"] = sanitize_text(
            explanation.get("short_reason_safe"),
            drop_child_disclosure=True,
        )[:280]

    rolling = sanitized.setdefault("rolling_summary", {})
    if isinstance(rolling, dict):
        rolling["signals_observed"] = sanitize_list(rolling.get("signals_observed"), max_items=10)
        rolling["key_points_safe"] = sanitize_list(rolling.get("key_points_safe"), max_items=5)

        risk_history = rolling.get("risk_history")
        if isinstance(risk_history, list):
            for item in risk_history:
                if isinstance(item, dict):
                    item["signals"] = sanitize_list(item.get("signals"), max_items=8)

    return sanitized
