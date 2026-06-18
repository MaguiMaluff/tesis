from __future__ import annotations

import json

from .privacy import sanitize_list
from .utils import safe_float, safe_int


def normalize_stage(value):
    stage = safe_int(value, 0)
    return max(0, min(stage, 4))


def stage_label(stage):
    labels = {
        0: 'Sin señales',
        1: 'Enganche',
        2: 'Confianza',
        3: 'Sexualización',
        4: 'Explotación',
    }
    return labels.get(normalize_stage(stage), 'Sin señales')


def risk_level(stage, confidence=None):
    stage = normalize_stage(stage)
    confidence = safe_float(confidence, 0.0)
    if stage >= 4 or confidence >= 0.9:
        return 'critical'
    if stage >= 3 or confidence >= 0.7:
        return 'high'
    if stage >= 2 or confidence >= 0.45:
        return 'medium'
    return 'low'


def snapshot_payload(snapshot_row):
    snapshot_json = snapshot_row.snapshot_json if hasattr(snapshot_row, 'snapshot_json') else snapshot_row.get('snapshot_json')
    if isinstance(snapshot_json, str):
        try:
            snapshot_json = json.loads(snapshot_json)
        except Exception:
            snapshot_json = {'raw': snapshot_json}
    if not isinstance(snapshot_json, dict):
        snapshot_json = {}
    return snapshot_json


def signals_from_snapshot(snapshot):
    if not isinstance(snapshot, dict):
        return []
    assessment = snapshot.get('assessment') or {}
    rolling_summary = snapshot.get('rolling_summary') or {}
    signals = []
    for source in (assessment.get('signals') or [], rolling_summary.get('signals_observed') or []):
        if isinstance(source, list):
            for item in source:
                signal = str(item).strip()
                if signal and signal not in signals:
                    signals.append(signal)
    return sanitize_list(signals, max_items=8)
