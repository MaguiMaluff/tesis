from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from flask import current_app

from .database import db
from .models import CaseSnapshot, Child, Conversation, IgAccount, MessageEvent, RiskCase, User


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_uuid() -> str:
    return str(uuid4())


def parse_dt(value):
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        raw = str(value).strip()
        if raw.endswith('Z'):
            raw = raw[:-1] + '+00:00'
        try:
            parsed = datetime.fromisoformat(raw)
        except Exception:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def to_iso(value):
    parsed = parse_dt(value)
    return parsed.isoformat().replace('+00:00', 'Z') if parsed else None


def safe_int(value, default=0):
    try:
        return default if value is None else int(value)
    except Exception:
        return default


def safe_float(value, default=0.0):
    try:
        return default if value is None else float(value)
    except Exception:
        return default


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
    return signals[:8]


def issue_token(user: User) -> str:
    payload = {
        'sub': user.id,
        'email': user.email,
        'full_name': user.full_name,
        'iat': utcnow(),
        'exp': utcnow() + timedelta(hours=current_app.config['JWT_EXPIRATION_HOURS']),
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')


def load_user_bundle(user_id: str):
    children = Child.query.filter_by(parent_id=user_id).order_by(Child.created_at.asc()).all()
    child_ids = [child.id for child in children]

    accounts = IgAccount.query.filter(IgAccount.child_id.in_(child_ids)).order_by(IgAccount.created_at.asc()).all() if child_ids else []
    account_ids = [account.id for account in accounts]

    conversations = (
        Conversation.query.filter(Conversation.ig_account_id.in_(account_ids)).order_by(Conversation.created_at.asc()).all()
        if account_ids
        else []
    )
    conversation_ids = [conversation.id for conversation in conversations]

    risk_cases = (
        RiskCase.query.filter(RiskCase.conversation_id.in_(conversation_ids)).order_by(RiskCase.opened_at.desc()).all()
        if conversation_ids
        else []
    )
    risk_case_ids = [risk_case.id for risk_case in risk_cases]

    snapshots = (
        CaseSnapshot.query.filter(CaseSnapshot.risk_case_id.in_(risk_case_ids)).order_by(CaseSnapshot.created_at.asc()).all()
        if risk_case_ids
        else []
    )
    events = (
        MessageEvent.query.filter(MessageEvent.conversation_id.in_(conversation_ids)).order_by(MessageEvent.sent_at.asc()).all()
        if conversation_ids
        else []
    )

    child_by_id = {child.id: child for child in children}
    account_by_id = {account.id: account for account in accounts}
    conversation_by_id = {conversation.id: conversation for conversation in conversations}

    accounts_by_child = defaultdict(list)
    for account in accounts:
        accounts_by_child[account.child_id].append(account)

    conversations_by_account = defaultdict(list)
    for conversation in conversations:
        conversations_by_account[conversation.ig_account_id].append(conversation)

    risk_cases_by_conversation = defaultdict(list)
    for risk_case in risk_cases:
        risk_cases_by_conversation[risk_case.conversation_id].append(risk_case)

    snapshots_by_case = defaultdict(list)
    for snapshot in snapshots:
        snapshots_by_case[snapshot.risk_case_id].append(snapshot)

    events_by_conversation = defaultdict(list)
    for event in events:
        events_by_conversation[event.conversation_id].append(event)

    child_by_account = {}
    for account in accounts:
        child_by_account[account.id] = child_by_id.get(account.child_id)

    return {
        'children': children,
        'accounts': accounts,
        'conversations': conversations,
        'risk_cases': risk_cases,
        'snapshots': snapshots,
        'events': events,
        'child_by_id': child_by_id,
        'account_by_id': account_by_id,
        'conversation_by_id': conversation_by_id,
        'accounts_by_child': accounts_by_child,
        'conversations_by_account': conversations_by_account,
        'risk_cases_by_conversation': risk_cases_by_conversation,
        'snapshots_by_case': snapshots_by_case,
        'events_by_conversation': events_by_conversation,
        'child_by_account': child_by_account,
    }


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
    payload = snapshot_payload(snapshot)
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
    stage_max, confidence_max, latest_case, latest_snapshot = _conversation_summary(conversation, bundle)
    return {
        'id': conversation.id,
        'ig_account_id': conversation.ig_account_id,
        'peer_id': conversation.peer_id,
        'conversation_ext_id': conversation.conversation_ext_id,
        'created_at': to_iso(conversation.created_at),
        'last_message_at': to_iso(conversation.last_message_at),
        'last_preprocessed_at': to_iso(conversation.last_preprocessed_at),
        'pending_count': safe_int(conversation.pending_count, 0),
        'pending_since': to_iso(conversation.pending_since),
        'status': conversation.status,
        'child_id': child.id if child else None,
        'child_name': child.display_name if child else None,
        'messages_count': len(bundle['events_by_conversation'].get(conversation.id, [])),
        'risk_cases_count': len(bundle['risk_cases_by_conversation'].get(conversation.id, [])),
        'max_stage': stage_max,
        'max_stage_label': stage_label(stage_max),
        'risk_level': risk_level(stage_max, confidence_max),
        'signals': signals_from_snapshot(latest_snapshot),
        'rolling_summary': conversation.rolling_summary or {},
        'latest_reason_safe': latest_case.reason_safe if latest_case else None,
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
        'summary': conversation.rolling_summary or {},
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
        'accounts_count': len(accounts),
        'conversations_count': len(conversations),
        'risk_cases_count': len(risk_cases),
        'open_risk_cases_count': sum(1 for case in risk_cases if case.status == 'open'),
        'max_risk_stage': stage_max,
        'max_risk_label': stage_label(stage_max),
        'risk_level': risk_level(stage_max, confidence_max),
        'last_activity_at': to_iso(last_activity),
        'latest_signals': signals_from_snapshot(latest_snapshot),
        'latest_reason_safe': latest_case.reason_safe if latest_case else None,
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
            'detail': risk_case.reason_safe or 'Caso detectado por IA',
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
        'latest_reason_safe': latest_case.reason_safe if latest_case else None,
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
        'signals': signals_from_snapshot(latest_snapshot),
    }


def serialize_risk_case_base(risk_case: RiskCase):
    return {
        'id': risk_case.id,
        'conversation_id': risk_case.conversation_id,
        'opened_at': to_iso(risk_case.opened_at),
        'status': risk_case.status,
        'confidence': safe_float(risk_case.confidence, 0.0),
        'reason_safe': risk_case.reason_safe,
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
            'child_id': child.id if child else None,
            'child_name': child.display_name if child else None,
            'last_message_at': to_iso(conversation.last_message_at) if conversation else None,
            'status': conversation.status if conversation else None,
        },
    }


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
            'detail': risk_case.reason_safe or 'Clasificación IA',
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
