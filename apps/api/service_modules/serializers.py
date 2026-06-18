from __future__ import annotations

from ..models import CaseSnapshot, Child, Conversation, IgAccount, MessageEvent, RiskCase, User
from .privacy import sanitize_ai_output, sanitize_text
from .risk import normalize_stage, risk_level, signals_from_snapshot, snapshot_payload, stage_label
from .utils import parse_dt, safe_float, safe_int, to_iso, utcnow


def _child_related(bundle, child_id):
    accounts = bundle['accounts_by_child'].get(child_id, [])
    conversations = []
    for account in accounts:
        conversations.extend(bundle['conversations_by_account'].get(account.id, []))

    risk_cases = []
    events = []
    for conversation in conversations:
        risk_cases.extend(bundle['risk_cases_by_conversation'].get(conversation.id, []))
        events.extend(bundle['events_by_conversation'].get(conversation.id, []))

    return accounts, conversations, risk_cases, events


def serialize_user(user: User):
    return {
        'id': user.id,
        'email': user.email,
        'full_name': user.full_name,
        'created_at': to_iso(user.created_at),
    }


def serialize_account(account: IgAccount):
    return {
        'id': account.id,
        'child_id': account.child_id,
        'ig_user_id': account.ig_user_id,
        'ig_username': account.ig_username,
        'access_token': account.access_token,
        'token_expires_at': to_iso(account.token_expires_at),
        'webhook_enabled': bool(account.webhook_enabled),
        'status': account.status,
        'created_at': to_iso(account.created_at),
    }


def serialize_message_event(event: MessageEvent):
    return {
        'id': event.id,
        'conversation_id': event.conversation_id,
        'mid': event.mid,
        'sent_at': to_iso(event.sent_at),
        'direction': event.direction,
        'text_hash': event.text_hash,
        'features': event.features or {},
        'created_at': to_iso(event.created_at),
    }


def serialize_snapshot(snapshot: CaseSnapshot):
    payload = sanitize_ai_output(snapshot_payload(snapshot))
    return {
        'id': snapshot.id,
        'risk_case_id': snapshot.risk_case_id,
        'snapshot_json': payload,
        'encrypted': bool(snapshot.encrypted),
        'created_at': to_iso(snapshot.created_at),
        'signals': signals_from_snapshot(payload),
    }


def _conversation_summary(conversation: Conversation, bundle):
    related_cases = bundle['risk_cases_by_conversation'].get(conversation.id, [])
    stage_max = max((normalize_stage(case.stage) for case in related_cases), default=0)
    confidence_max = max((safe_float(case.confidence, 0.0) for case in related_cases), default=0.0)
    latest_case = related_cases[0] if related_cases else None
    latest_snapshot = None
    if latest_case:
        latest_rows = bundle['snapshots_by_case'].get(latest_case.id, [])
        latest_snapshot = snapshot_payload(latest_rows[-1]) if latest_rows else None
    return stage_max, confidence_max, latest_case, latest_snapshot


def serialize_conversation(conversation: Conversation, bundle):
    child = bundle['child_by_account'].get(conversation.ig_account_id)
    account = bundle['account_by_id'].get(conversation.ig_account_id)
    stage_max, confidence_max, latest_case, latest_snapshot = _conversation_summary(conversation, bundle)
    rolling_summary = sanitize_ai_output({'rolling_summary': conversation.rolling_summary or {}}).get('rolling_summary', {})
    peer_username = str(rolling_summary.get('peer_username') or '').strip().lstrip('@') or None
    return {
        'id': conversation.id,
        'ig_account_id': conversation.ig_account_id,
        'peer_id': conversation.peer_id,
        'peer_username': peer_username,
        'conversation_ext_id': conversation.conversation_ext_id,
        'created_at': to_iso(conversation.created_at),
        'last_message_at': to_iso(conversation.last_message_at),
        'last_preprocessed_at': to_iso(conversation.last_preprocessed_at),
        'pending_count': safe_int(conversation.pending_count, 0),
        'pending_since': to_iso(conversation.pending_since),
        'status': conversation.status,
        'child_id': child.id if child else None,
        'child_name': child.display_name if child else None,
        'account_username': account.ig_username if account else None,
        'account_ig_user_id': account.ig_user_id if account else None,
        'messages_count': len(bundle['events_by_conversation'].get(conversation.id, [])),
        'risk_cases_count': len(bundle['risk_cases_by_conversation'].get(conversation.id, [])),
        'max_stage': stage_max,
        'max_stage_label': stage_label(stage_max),
        'risk_level': risk_level(stage_max, confidence_max),
        'signals': signals_from_snapshot(latest_snapshot),
        'rolling_summary': rolling_summary,
        'latest_reason_safe': sanitize_text(latest_case.reason_safe, drop_child_disclosure=True) if latest_case else None,
    }


def serialize_conversation_detail(conversation: Conversation, bundle):
    item = serialize_conversation(conversation, bundle)
    related_cases = bundle['risk_cases_by_conversation'].get(conversation.id, [])
    related_cases_sorted = sorted(related_cases, key=lambda case: parse_dt(case.opened_at) or utcnow(), reverse=True)
    trend = 'stable'
    if len(related_cases_sorted) >= 2:
        first_stage = normalize_stage(related_cases_sorted[-1].stage)
        last_stage = normalize_stage(related_cases_sorted[0].stage)
        if last_stage > first_stage:
            trend = 'up'
        elif last_stage < first_stage:
            trend = 'down'
    item.update({
        'summary': item.get('rolling_summary') or {},
        'trend': trend,
        'risk_cases_count': len(related_cases_sorted),
    })
    return item


def serialize_child_card(child: Child, bundle):
    accounts, conversations, risk_cases, events = _child_related(bundle, child.id)
    stage_max = max((normalize_stage(case.stage) for case in risk_cases), default=0)
    confidence_max = max((safe_float(case.confidence, 0.0) for case in risk_cases), default=0.0)
    last_activity_candidates = [
        parse_dt(conversation.last_message_at) for conversation in conversations if conversation.last_message_at
    ] + [
        parse_dt(case.opened_at) for case in risk_cases if case.opened_at
    ] + [
        parse_dt(event.sent_at) for event in events if event.sent_at
    ]
    last_activity = max((ts for ts in last_activity_candidates if ts), default=None)
    latest_case = risk_cases[0] if risk_cases else None
    latest_snapshot = None
    if latest_case:
        snapshot_rows = bundle['snapshots_by_case'].get(latest_case.id, [])
        latest_snapshot = snapshot_payload(snapshot_rows[-1]) if snapshot_rows else None

    return {
        'id': child.id,
        'display_name': child.display_name,
        'created_at': to_iso(child.created_at),
        'ig_username': accounts[0].ig_username if accounts else None,
        'ig_user_id': accounts[0].ig_user_id if accounts else None,
        'status': accounts[0].status if accounts else None,
        'accounts_count': len(accounts),
        'conversations_count': len(conversations),
        'risk_cases_count': len(risk_cases),
        'open_risk_cases_count': sum(1 for case in risk_cases if case.status == 'open'),
        'max_risk_stage': stage_max,
        'max_risk_label': stage_label(stage_max),
        'risk_level': risk_level(stage_max, confidence_max),
        'last_activity_at': to_iso(last_activity),
        'latest_signals': signals_from_snapshot(latest_snapshot),
        'latest_reason_safe': sanitize_text(latest_case.reason_safe, drop_child_disclosure=True) if latest_case else None,
    }


def serialize_child_detail(child: Child, bundle):
    accounts, conversations, risk_cases, events = _child_related(bundle, child.id)
    conversations = sorted(conversations, key=lambda item: parse_dt(item.last_message_at or item.created_at) or utcnow(), reverse=True)
    risk_cases = sorted(risk_cases, key=lambda item: parse_dt(item.opened_at) or utcnow(), reverse=True)
    events = sorted(events, key=lambda item: parse_dt(item.sent_at) or utcnow(), reverse=True)

    conversations_payload = [serialize_conversation(conversation, bundle) for conversation in conversations]
    risk_cases_payload = [serialize_risk_case(risk_case, bundle) for risk_case in risk_cases]
    accounts_payload = [serialize_account(account) for account in accounts]

    timeline = []
    for conversation in conversations:
        timeline.append({
            'type': 'conversation',
            'id': conversation.id,
            'at': to_iso(conversation.last_message_at or conversation.created_at),
            'title': f'Conversación {conversation.peer_id}',
            'detail': f'Estado {conversation.status}',
            'severity': risk_level(0),
            'conversation_id': conversation.id,
        })
    for risk_case in risk_cases:
        timeline.append({
            'type': 'risk_case',
            'id': risk_case.id,
            'at': to_iso(risk_case.opened_at),
            'title': f'Caso etapa {risk_case.stage}',
            'detail': sanitize_text(risk_case.reason_safe, drop_child_disclosure=True) or 'Caso detectado por IA',
            'severity': risk_level(risk_case.stage, risk_case.confidence),
            'conversation_id': risk_case.conversation_id,
            'risk_case_id': risk_case.id,
        })
    for event in events:
        timeline.append({
            'type': 'message',
            'id': event.id,
            'at': to_iso(event.sent_at),
            'title': f'Mensaje {event.direction}',
            'detail': event.mid or 'Evento de mensaje',
            'severity': 'low',
            'conversation_id': event.conversation_id,
        })
    timeline = [item for item in timeline if item.get('at')]
    timeline.sort(key=lambda item: parse_dt(item.get('at')) or utcnow(), reverse=True)

    stage_max = max((normalize_stage(case.stage) for case in risk_cases), default=0)
    confidence_max = max((safe_float(case.confidence, 0.0) for case in risk_cases), default=0.0)
    trend = 'stable'
    if len(risk_cases) >= 2:
        first_stage = normalize_stage(risk_cases[-1].stage)
        last_stage = normalize_stage(risk_cases[0].stage)
        if last_stage > first_stage:
            trend = 'up'
        elif last_stage < first_stage:
            trend = 'down'

    latest_case = risk_cases[0] if risk_cases else None
    latest_snapshot = None
    if latest_case:
        latest_rows = bundle['snapshots_by_case'].get(latest_case.id, [])
        latest_snapshot = snapshot_payload(latest_rows[-1]) if latest_rows else None

    return {
        'id': child.id,
        'display_name': child.display_name,
        'created_at': to_iso(child.created_at),
        'ig_username': accounts[0].ig_username if accounts else None,
        'ig_user_id': accounts[0].ig_user_id if accounts else None,
        'status': accounts[0].status if accounts else None,
        'accounts': accounts_payload,
        'conversations': conversations_payload,
        'risk_cases': risk_cases_payload,
        'timeline': timeline,
        'metrics': {
            'monitored_accounts': len(accounts),
            'conversations_count': len(conversations),
            'risk_cases_count': len(risk_cases),
            'open_cases': sum(1 for case in risk_cases if case.status == 'open'),
            'max_risk_stage': stage_max,
            'risk_level': risk_level(stage_max, confidence_max),
            'trend': trend,
        },
        'signals': signals_from_snapshot(latest_snapshot),
        'max_stage': stage_max,
        'max_stage_label': stage_label(stage_max),
        'risk_level': risk_level(stage_max, confidence_max),
        'trend': trend,
        'last_activity_at': to_iso(timeline[0]['at']) if timeline else None,
        'accounts_count': len(accounts),
        'conversations_count': len(conversations),
        'risk_cases_count': len(risk_cases),
        'open_risk_cases_count': sum(1 for case in risk_cases if case.status == 'open'),
        'max_risk_stage': stage_max,
        'latest_signals': signals_from_snapshot(latest_snapshot),
        'latest_reason_safe': sanitize_text(latest_case.reason_safe, drop_child_disclosure=True) if latest_case else None,
    }


def serialize_risk_case(risk_case: RiskCase, bundle):
    conversation = bundle['conversation_by_id'].get(risk_case.conversation_id)
    child = bundle['child_by_account'].get(conversation.ig_account_id) if conversation else None
    latest_rows = bundle['snapshots_by_case'].get(risk_case.id, [])
    latest_snapshot = snapshot_payload(latest_rows[-1]) if latest_rows else {}
    stage = normalize_stage(risk_case.stage)
    confidence = safe_float(risk_case.confidence, 0.0)
    return {
        **serialize_risk_case_base(risk_case),
        'stage': stage,
        'stage_label': stage_label(stage),
        'risk_level': risk_level(stage, confidence),
        'child_id': child.id if child else None,
        'peer_id': conversation.peer_id if conversation else None,
        'peer_username': (conversation.rolling_summary or {}).get('peer_username') if conversation and isinstance(conversation.rolling_summary, dict) else None,
        'account_username': conversation.ig_account.ig_username if conversation and conversation.ig_account else None,
        'signals': signals_from_snapshot(latest_snapshot),
    }


def serialize_risk_case_base(risk_case: RiskCase):
    return {
        'id': risk_case.id,
        'conversation_id': risk_case.conversation_id,
        'opened_at': to_iso(risk_case.opened_at),
        'status': risk_case.status,
        'confidence': safe_float(risk_case.confidence, 0.0),
        'reason_safe': sanitize_text(risk_case.reason_safe, drop_child_disclosure=True),
        'evidence_window_start': to_iso(risk_case.evidence_window_start),
        'evidence_window_end': to_iso(risk_case.evidence_window_end),
    }


def serialize_risk_case_detail(risk_case: RiskCase, bundle):
    conversation = bundle['conversation_by_id'].get(risk_case.conversation_id)
    child = bundle['child_by_account'].get(conversation.ig_account_id) if conversation and conversation.ig_account_id else None
    snapshots = bundle['snapshots_by_case'].get(risk_case.id, [])
    snapshots_payload = [serialize_snapshot(snapshot) for snapshot in snapshots]
    snapshots_payload = sorted(snapshots_payload, key=lambda item: parse_dt(item['created_at']) or utcnow())
    evolution = [
        {
            'at': snapshot['created_at'],
            'stage': normalize_stage((snapshot['snapshot_json'] or {}).get('assessment', {}).get('risk_stage')),
            'confidence': safe_float((snapshot['snapshot_json'] or {}).get('assessment', {}).get('confidence'), 0.0),
            'signals': snapshot.get('signals', []),
        }
        for snapshot in snapshots_payload
    ]
    latest_snapshot = snapshots_payload[-1]['snapshot_json'] if snapshots_payload else {}
    explanation = (latest_snapshot.get('explanation') or {}) if isinstance(latest_snapshot, dict) else {}
    stage = normalize_stage(risk_case.stage)
    return {
        **serialize_risk_case_base(risk_case),
        'stage': stage,
        'stage_label': stage_label(stage),
        'risk_level': risk_level(stage, risk_case.confidence),
        'signals': signals_from_snapshot(latest_snapshot),
        'snapshots': snapshots_payload,
        'evolution': evolution,
        'explanation': explanation,
        'conversation': {
            'id': conversation.id if conversation else None,
            'peer_id': conversation.peer_id if conversation else None,
            'peer_username': (conversation.rolling_summary or {}).get('peer_username') if conversation and isinstance(conversation.rolling_summary, dict) else None,
            'account_username': conversation.ig_account.ig_username if conversation and conversation.ig_account else None,
            'child_id': child.id if child else None,
            'child_name': child.display_name if child else None,
            'last_message_at': to_iso(conversation.last_message_at) if conversation else None,
            'status': conversation.status if conversation else None,
        },
    }
