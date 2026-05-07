from __future__ import annotations

import json
from typing import Any


SYSTEM_PROMPT = """\
Sos un asistente especializado en detección temprana de grooming y violencia digital.
Respondé ÚNICAMENTE con JSON válido.

Políticas de salida:
- Si assessment.risk_stage es 0 o 1: NO incluyas citas textuales (evidence.quoted_messages debe ser []).
- Si assessment.risk_stage es 2, 3 o 4: podés incluir hasta 3 citas textuales cortas (máx 25 palabras cada una) en evidence.quoted_messages, evitando datos personales.
- Nunca incluyas nombres completos, teléfonos, direcciones, usuarios, links, ni datos identificatorios.
- No des consejos para cometer delitos ni para evadir detección.
"""

OUTPUT_SCHEMA_EXACT = {
    "assessment": {
        "risk_stage": 0,
        "risk_level": "low",           # low|medium|high|critical
        "confidence": 0.0,             # 0..1
        "signals": [],                 # list[str]
        "recommended_action": "none",  # none|monitor|notify_parent|urgent_notify
    },
    "evidence": {
        "evidence_safe": [],           # list[str] no quotes
        "quoted_messages": [],         # list[str] only if stage>=2 (policy above)
    },
    "explanation": {
        "short_reason_safe": "",       # brief, no quotes
        "analyst_notes": "",           # can be longer; no PII; quotes only if stage>=2 (but prefer in quoted_messages)
    },
    "rolling_summary": {
        "version": 1,
        "current_stage_max": 0,
        "trend": "stable",             # stable|up|down
        "signals_observed": [],        # list[str]
        "key_points_safe": [],         # list[str]
        "risk_history": [],            # list[{"window_end":..., "risk_stage":..., ...}]
    },
}


def build_user_prompt(
    rolling_summary_prev: dict | None,
    window_messages: list[dict],
    window_start: str,
    window_end: str,
) -> str:
    """
    rolling_summary_prev: JSON object from DB (jsonb) or None
    window_messages: [{"ts","direction","text","ig_id","context"}...]
    """
    rs = rolling_summary_prev if isinstance(rolling_summary_prev, dict) else None

    return f"""\
Analizá una ventana de mensajes de una conversación y un rolling_summary previo estructurado.

ETAPAS (Grooming Argentina):
1 Enganche (luring)
2 Confianza y fidelización
3 Sexualización y manipulación emocional
4 Violencia sexual y explotación

Objetivos:
A) Clasificar el riesgo de ESTA ventana (stage 0-4).
B) Actualizar rolling_summary (estructurado, acumulativo y sin PII).
C) Escribir una explicación en lenguaje natural (analyst_notes) justificando la clasificación.

REGLAS:
- No incluir PII (nombres completos, teléfonos, direcciones, usuarios, links).
- Si risk_stage <= 1: quoted_messages debe ser [].
- Si risk_stage >= 2: quoted_messages puede incluir hasta 3 citas cortas.

Contexto:
- window_start: {window_start}
- window_end: {window_end}

rolling_summary_prev (JSON o null):
{json.dumps(rs, ensure_ascii=False)}

window_messages (JSON cronológico):
{json.dumps(window_messages, ensure_ascii=False)}

Devolvé exactamente un JSON con este esquema (mismas claves):
{json.dumps(OUTPUT_SCHEMA_EXACT, ensure_ascii=False)}
"""