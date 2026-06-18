import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface DashboardTotals {
  profiles: number;
  accounts: number;
  conversations: number;
  risk_cases: number;
  open_risk_cases: number;
}

export interface DashboardStageBucket {
  stage: number;
  label: string;
  count: number;
}

export interface DashboardEvent {
  type: 'message' | 'risk_case' | 'conversation';
  at: string;
  title: string;
  detail: string;
  conversation_id?: string;
  risk_case_id?: string;
}

export interface DashboardSummary {
  totals: DashboardTotals;
  cases_by_stage: DashboardStageBucket[];
  risk_trend: Array<{
    at: string;
    stage: number;
    confidence: number;
    conversation_id?: string;
  }>;
  latest_events: DashboardEvent[];
  profiles: Array<{
    id: string;
    display_name: string;
    created_at?: string;
  }>;
}

export interface ChildCard {
  id: string;
  display_name: string;
  created_at?: string;
  ig_username?: string | null;
  ig_user_id?: string | null;
  status?: string | null;
  accounts_count: number;
  conversations_count: number;
  risk_cases_count: number;
  open_risk_cases_count: number;
  max_risk_stage: number;
  max_risk_label: string;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  last_activity_at?: string;
  latest_signals: string[];
  latest_reason_safe?: string;
}

export interface ChildAccount {
  id: string;
  child_id: string;
  ig_user_id: string;
  ig_username: string;
  access_token?: string | null;
  token_expires_at?: string | null;
  webhook_enabled: boolean;
  status: string;
  created_at?: string;
}

export interface ChildDetail extends ChildCard {
  ig_user_id?: string | null;
  status?: string;
  accounts: ChildAccount[];
  conversations: Array<ConversationItem>;
  risk_cases: Array<RiskCaseItem>;
  timeline: TimelineEntry[];
  metrics: {
    monitored_accounts: number;
    conversations_count: number;
    risk_cases_count: number;
    open_cases: number;
    max_risk_stage: number;
    risk_level: 'low' | 'medium' | 'high' | 'critical';
    trend: 'stable' | 'up' | 'down';
  };
  signals: string[];
  trend: 'stable' | 'up' | 'down';
}

export interface TimelineEntry {
  type: 'conversation' | 'risk_case' | 'message';
  id: string;
  at: string;
  title: string;
  detail: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  conversation_id?: string;
  risk_case_id?: string;
}

export interface ConversationItem {
  id: string;
  ig_account_id?: string;
  peer_id: string;
  peer_username?: string | null;
  account_username?: string | null;
  account_ig_user_id?: string | null;
  conversation_ext_id?: string | null;
  created_at?: string;
  last_message_at?: string | null;
  last_preprocessed_at?: string | null;
  pending_count?: number;
  pending_since?: string | null;
  status?: string;
  child_id?: string | null;
  child_name?: string | null;
  messages_count?: number;
  risk_cases_count?: number;
  max_stage?: number;
  max_stage_label?: string;
  risk_level?: 'low' | 'medium' | 'high' | 'critical';
  signals?: string[];
  rolling_summary?: Record<string, unknown>;
}

export interface ConversationEvent {
  id: string;
  conversation_id: string;
  mid: string;
  sent_at: string;
  direction: 'inbound' | 'outbound';
  text_hash?: string | null;
  features?: Record<string, unknown>;
  created_at?: string;
}

export interface RiskCaseItem {
  id: string;
  conversation_id: string;
  opened_at: string;
  status: 'open' | 'closed';
  stage: number;
  confidence?: number | null;
  reason_safe?: string | null;
  evidence_window_start?: string | null;
  evidence_window_end?: string | null;
  risk_level?: 'low' | 'medium' | 'high' | 'critical';
  stage_label?: string;
  child_id?: string | null;
  peer_id?: string | null;
  peer_username?: string | null;
  account_username?: string | null;
  signals?: string[];
}

export interface RiskCaseSnapshot {
  id: string;
  risk_case_id: string;
  snapshot_json: Record<string, unknown>;
  encrypted: boolean;
  created_at: string;
  signals?: string[];
}

export interface RiskCaseDetail extends RiskCaseItem {
  snapshots: RiskCaseSnapshot[];
  evolution?: Array<{
    at: string;
    stage: number;
    confidence: number;
    signals: string[];
  }>;
  explanation?: Record<string, unknown>;
  conversation?: {
    id: string;
    peer_id: string;
    peer_username?: string | null;
    account_username?: string | null;
    child_id?: string | null;
    child_name?: string | null;
    last_message_at?: string | null;
    status?: string;
  } | null;
}

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  private apiUrl = environment.apiUrl.replace(/\/$/, '');

  constructor(private http: HttpClient) {}

  getDashboardSummary(): Observable<DashboardSummary> {
    return this.http.get<DashboardSummary>(`${this.apiUrl}/dashboard/summary`);
  }

  getChildren(): Observable<ChildCard[]> {
    return this.http.get<ChildCard[]>(`${this.apiUrl}/children`);
  }

  createChild(payload: {
    display_name: string;
    ig_user_id: string;
    ig_username: string;
    access_token: string;
  }): Observable<ChildDetail> {
    return this.http.post<ChildDetail>(`${this.apiUrl}/children`, payload);
  }

  getChild(id: string): Observable<ChildDetail> {
    return this.http.get<ChildDetail>(`${this.apiUrl}/children/${id}`);
  }

  getConversations(params?: { search?: string; order?: 'recent' | 'oldest' }): Observable<ConversationItem[]> {
    let httpParams = new HttpParams();
    if (params?.search) {
      httpParams = httpParams.set('search', params.search);
    }
    if (params?.order) {
      httpParams = httpParams.set('order', params.order);
    }
    return this.http.get<ConversationItem[]>(`${this.apiUrl}/conversations`, { params: httpParams });
  }

  getConversation(id: string): Observable<ConversationItem> {
    return this.http.get<ConversationItem>(`${this.apiUrl}/conversations/${id}`);
  }

  getConversationEvents(id: string): Observable<ConversationEvent[]> {
    return this.http.get<ConversationEvent[]>(`${this.apiUrl}/conversations/${id}/events`);
  }

  getRiskCases(params?: {
    search?: string;
    stage?: string | number;
    severity?: string;
    status?: string;
    order?: 'recent' | 'oldest';
  }): Observable<RiskCaseItem[]> {
    let httpParams = new HttpParams();
    if (params?.search) {
      httpParams = httpParams.set('search', params.search);
    }
    if (params?.stage !== undefined && params.stage !== null) {
      httpParams = httpParams.set('stage', String(params.stage));
    }
    if (params?.severity) {
      httpParams = httpParams.set('severity', params.severity);
    }
    if (params?.status) {
      httpParams = httpParams.set('status', params.status);
    }
    if (params?.order) {
      httpParams = httpParams.set('order', params.order);
    }
    return this.http.get<RiskCaseItem[]>(`${this.apiUrl}/risk-cases`, { params: httpParams });
  }

  getRiskCase(id: string): Observable<RiskCaseDetail> {
    return this.http.get<RiskCaseDetail>(`${this.apiUrl}/risk-cases/${id}`);
  }
}
