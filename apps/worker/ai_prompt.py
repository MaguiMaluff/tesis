from __future__ import annotations

import json


SYSTEM_PROMPT = """\
Sos un asistente especializado en detección temprana de grooming y violencia digital.
Respondé ÚNICAMENTE con JSON válido (sin markdown, sin texto extra).

Políticas de salida:
- Si assessment.risk_stage es 0 o 1: NO incluyas citas textuales (evidence.quoted_messages debe ser []).
- Si assessment.risk_stage es 2, 3 o 4: podés incluir hasta 3 citas textuales cortas (máx 25 palabras cada una) en evidence.quoted_messages, evitando datos personales.
- Nunca incluyas nombres completos, teléfonos, direcciones, usuarios, links, ni datos identificatorios.
- No incluyas edades exactas; usá categorías (p. ej. "menor de edad", "adulto", "diferencia de edad").
- Escribí short_reason_safe y analyst_notes en español.
"""


def build_user_prompt(
    rolling_summary_prev: dict | None,
    window_messages: list[dict],
    window_start: str,
    window_end: str,
) -> str:
    rs = rolling_summary_prev if isinstance(rolling_summary_prev, dict) else None

    return f"""\
Analizá una ventana de mensajes de una conversación y un rolling_summary previo estructurado.

ETAPAS (Grooming Argentina):
0 Sin señales
1 Enganche (luring)
2 Confianza y fidelización
3 Sexualización y manipulación emocional
4 Explotación / coacción / amenazas

REGLAS:
- No incluir PII (nombres completos, teléfonos, direcciones, usuarios, links).
- No incluyas edades exactas; usá categorías (p. ej. "menor de edad", "adulto").
- Si risk_stage <= 1: evidence.quoted_messages debe ser [].
- Si risk_stage >= 2: evidence.quoted_messages puede incluir hasta 3 citas cortas (máx 25 palabras cada una).
- Siempre agregá una entrada a rolling_summary.risk_history con window_end, risk_stage, risk_level, confidence y signals.
- Devolvé SOLO JSON.

Contexto:
- window_start: {window_start}
- window_end: {window_end}

rolling_summary_prev (JSON o null):
{json.dumps(rs, ensure_ascii=False)}

window_messages (JSON cronológico):
{json.dumps(window_messages, ensure_ascii=False)}

FORMATO DE SALIDA (obligatorio):
Devolvé SOLO JSON con estas claves de primer nivel:
- assessment
- evidence
- explanation
- rolling_summary

assessment debe incluir: risk_stage (0-4), risk_level (low|medium|high|critical), confidence (0..1), signals (list[str]), recommended_action (none|monitor|notify_parent|urgent_notify)
evidence debe incluir: evidence_safe (list[str]), quoted_messages (list[str])
explanation debe incluir: short_reason_safe (str), analyst_notes (str)
rolling_summary debe incluir: version (int), current_stage_max (int), trend (stable|up|down), signals_observed (list[str]), key_points_safe (list[str]), risk_history (list[object])
risk_history item: window_end (str ISO), risk_stage (int), risk_level (str), confidence (float), signals (list[str])
"""