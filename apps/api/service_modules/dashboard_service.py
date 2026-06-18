from __future__ import annotations

from .bundles import load_user_bundle
from .privacy import sanitize_text
from .risk import normalize_stage, stage_label
from .utils import parse_dt, safe_float, to_iso, utcnow


def dashboard_summary_for_user(user_id: str):
    bundle = load_user_bundle(user_id)
    children = bundle['children']
    conversations = bundle['conversations']
    risk_cases = bundle['risk_cases']
    events = bundle['events']

    stage_counts = {stage: 0 for stage in range(5)}
    for risk_case in risk_cases:
        stage_counts[normalize_stage(risk_case.stage)] += 1

    ordered_risk_cases = sorted(risk_cases, key=lambda item: parse_dt(item.opened_at) or utcnow(), reverse=True)
    recent_events = []
    for event in sorted(events, key=lambda item: parse_dt(item.sent_at) or utcnow(), reverse=True)[:12]:
        recent_events.append({
            'type': 'message',
            'at': to_iso(event.sent_at),
            'title': f'Mensaje {event.direction}',
            'detail': event.mid or 'Nuevo evento',
            'conversation_id': event.conversation_id,
        })
    for risk_case in ordered_risk_cases[:8]:
        recent_events.append({
            'type': 'risk_case',
            'at': to_iso(risk_case.opened_at),
            'title': f'Caso etapa {risk_case.stage}',
            'detail': sanitize_text(risk_case.reason_safe, drop_child_disclosure=True) or 'Clasificación IA',
            'conversation_id': risk_case.conversation_id,
            'risk_case_id': risk_case.id,
        })
    recent_events = [event for event in recent_events if event.get('at')]
    recent_events.sort(key=lambda item: parse_dt(item.get('at')) or utcnow(), reverse=True)

    return {
        'totals': {
            'profiles': len(children),
            'accounts': len(bundle['accounts']),
            'conversations': len(conversations),
            'risk_cases': len(risk_cases),
            'open_risk_cases': sum(1 for case in risk_cases if case.status == 'open'),
        },
        'cases_by_stage': [
            {'stage': stage, 'label': stage_label(stage), 'count': stage_counts[stage]}
            for stage in range(5)
        ],
        'risk_trend': [
            {
                'at': to_iso(risk_case.opened_at),
                'stage': normalize_stage(risk_case.stage),
                'confidence': safe_float(risk_case.confidence, 0.0),
                'conversation_id': risk_case.conversation_id,
            }
            for risk_case in ordered_risk_cases[:12]
        ],
        'latest_events': recent_events[:20],
        'profiles': [
            {
                'id': child.id,
                'display_name': child.display_name,
                'created_at': to_iso(child.created_at),
            }
            for child in children
        ],
    }


def get_general_stats_for_user(user_id: str):
    bundle = load_user_bundle(user_id)
    return {
        'active_monitored_accounts': len(bundle['accounts']),
        'open_risk_cases': sum(1 for case in bundle['risk_cases'] if case.status == 'open'),
        'system_health': 'ok',
    }
