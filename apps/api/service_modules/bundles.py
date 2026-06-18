from __future__ import annotations

from collections import defaultdict

from ..models import CaseSnapshot, Child, Conversation, IgAccount, MessageEvent, RiskCase


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
