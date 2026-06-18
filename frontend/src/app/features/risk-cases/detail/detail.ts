import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, ActivatedRoute } from '@angular/router';
import { forkJoin, of, Subscription, switchMap } from 'rxjs';
import { ApiService, ConversationItem, RiskCaseDetail, RiskCaseSnapshot } from '../../../core/services/api';
import { ChangeDetectorRef } from '@angular/core';
import {
  riskLevelLabel as formatRiskLevel,
  statusLabel as formatStatus,
} from '../../../shared/presentation-labels';

@Component({
  selector: 'app-risk-cases-detail',
  templateUrl: './detail.html',
  styleUrls: ['./detail.css'],
  standalone: true,
  imports: [CommonModule, RouterModule],
})
export class DetailComponent implements OnInit {
  riskCase: RiskCaseDetail | null = null;
  conversation: ConversationItem | null = null;
  snapshots: RiskCaseSnapshot[] = [];
  loading = true;
  errorMessage = '';

  private subscription?: Subscription;

  constructor(
    private route: ActivatedRoute,
    private apiService: ApiService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.subscription = this.route.paramMap
      .pipe(
        switchMap((params) => this.apiService.getRiskCase(params.get('id') || '')),
        switchMap((riskCase) =>
          forkJoin({
            riskCase: of(riskCase),
            conversation: this.apiService.getConversation(riskCase.conversation_id),
          }),
        ),
      )
      .subscribe({
        next: ({ riskCase, conversation }) => {
          this.riskCase = riskCase;
          this.conversation = conversation;
          this.snapshots = [...(riskCase.snapshots || [])].sort(
            (left, right) => new Date(left.created_at).getTime() - new Date(right.created_at).getTime()
          );
          this.loading = false;
          this.cdr.detectChanges();

        },
        error: (error) => {
          console.error('Error fetching risk case:', error);
          this.errorMessage = 'No se pudo cargar el detalle del caso de riesgo.';
          this.loading = false;
          this.cdr.detectChanges();
        },
      });
  }

  ngOnDestroy(): void {
    this.subscription?.unsubscribe();
  }

  goBack(): void {
    window.history.back();
  }

  get contactLabel(): string {
    const username = this.conversation?.peer_username || this.riskCase?.peer_username || this.riskCase?.conversation?.peer_username;
    return username ? `@${username}` : this.conversation?.peer_id || this.riskCase?.peer_id || this.riskCase?.conversation?.peer_id || 'Contacto externo';
  }

  get monitoredAccountLabel(): string {
    const username = this.conversation?.account_username || this.riskCase?.account_username || this.riskCase?.conversation?.account_username;
    return username ? `@${username}` : 'Cuenta monitoreada';
  }

  get latestSnapshot(): RiskCaseSnapshot | null {
    return this.snapshots.length ? this.snapshots[this.snapshots.length - 1] : null;
  }

  get latestAnalysis(): Record<string, any> {
    return (this.latestSnapshot?.snapshot_json as Record<string, any>) || {};
  }

  get signals(): string[] {
    const latest = (this.latestSnapshot?.snapshot_json as Record<string, any>) || {};
    const assessmentSignals = this.asTextArray(this.readPath(latest, 'assessment', 'signals'));
    const rollingSignals = this.asTextArray(this.readPath(latest, 'rolling_summary', 'signals_observed'));
    const snapshotSignals = this.snapshots.flatMap((snapshot) => snapshot.signals || []);
    return [...new Set([...assessmentSignals, ...rollingSignals, ...snapshotSignals])].slice(0, 10);
  }

  get explanation(): string {
    return this.resolveReason(this.latestAnalysis) || this.safeText(this.riskCase?.reason_safe) || this.reasonFallback;
  }

  get analysisSummary(): string {
    const latest = this.latestAnalysis;
    const candidates = [
      this.readPath(latest, 'summary'),
      this.readPath(latest, 'analysis_summary'),
      this.readPath(latest, 'explanation', 'summary'),
      this.readPath(latest, 'explanation', 'classification_summary'),
      this.readPath(latest, 'rolling_summary', 'summary_safe'),
      this.readPath(latest, 'rolling_summary', 'summary'),
      this.readPath(latest, 'rolling_summary', 'brief'),
    ];
    return this.firstText(candidates) || this.explanation;
  }

  get reasonItems(): string[] {
    const latest = this.latestAnalysis;
    const candidates = [
      this.readPath(latest, 'explanation', 'reasons'),
      this.readPath(latest, 'explanation', 'key_reasons'),
      this.readPath(latest, 'explanation', 'risk_factors'),
      this.readPath(latest, 'assessment', 'reasons'),
      this.readPath(latest, 'assessment', 'risk_factors'),
      this.readPath(latest, 'rolling_summary', 'key_points_safe'),
      this.readPath(latest, 'rolling_summary', 'key_points'),
    ];
    const values = candidates.flatMap((value) => this.asTextArray(value));

    const safeReason = this.safeText(this.riskCase?.reason_safe);
    if (safeReason) {
      values.unshift(safeReason);
    }

    const uniqueReasons = [...new Set(values)].filter(Boolean).slice(0, 6);
    return uniqueReasons.length ? uniqueReasons : this.signals.slice(0, 6);
  }

  get statusLabel(): string {
    return formatStatus(this.riskCase?.status);
  }

  get riskLevelLabel(): string {
    return formatRiskLevel(this.riskCase?.risk_level);
  }

  get stageEvolution(): Array<{ at: string; stage: number; confidence: number }> {
    return this.snapshots.map((snapshot) => ({
      at: snapshot.created_at,
      stage: Number(this.readPath(snapshot.snapshot_json as Record<string, any>, 'assessment', 'risk_stage') || 0),
      confidence: Number(this.readPath(snapshot.snapshot_json as Record<string, any>, 'assessment', 'confidence') || 0),
    }));
  }

  snapshotStage(snapshot: RiskCaseSnapshot): number {
    return Number(this.readPath(snapshot.snapshot_json as Record<string, any>, 'assessment', 'risk_stage') || 0);
  }

  snapshotConfidence(snapshot: RiskCaseSnapshot): number {
    return Number(this.readPath(snapshot.snapshot_json as Record<string, any>, 'assessment', 'confidence') || 0);
  }

  snapshotReason(snapshot: RiskCaseSnapshot): string {
    return this.resolveReason(snapshot.snapshot_json as Record<string, any>) || this.safeText(this.riskCase?.reason_safe) || this.reasonFallback;
  }

  private get reasonFallback(): string {
    return this.signals.length
      ? 'El caso fue abierto por señales de riesgo detectadas en la conversación.'
      : 'El análisis no incluye una explicación textual disponible.';
  }

  private resolveReason(source: Record<string, any>): string {
    return this.firstText([
      this.readPath(source, 'explanation', 'short_reason_safe'),
      this.readPath(source, 'explanation', 'short_reason'),
      this.readPath(source, 'explanation', 'reason_safe'),
      this.readPath(source, 'explanation', 'reason'),
      this.readPath(source, 'explanation', 'rationale'),
      this.readPath(source, 'assessment', 'reason'),
      this.readPath(source, 'assessment', 'rationale'),
      this.readPath(source, 'reason_safe'),
      this.readPath(source, 'reason'),
    ]);
  }

  private readPath(source: Record<string, any> | null | undefined, ...keys: string[]): unknown {
    let current: unknown = source;

    for (const key of keys) {
      if (!current || typeof current !== 'object') {
        return undefined;
      }

      current = (current as Record<string, unknown>)[key];
    }

    return current;
  }

  private firstText(values: unknown[]): string {
    for (const value of values) {
      if (typeof value === 'string' && value.trim() && !this.isDisallowedReason(value)) {
        return value.trim();
      }
    }

    return '';
  }

  private safeText(value?: string | null): string {
    return value && !this.isDisallowedReason(value) ? value : '';
  }

  private asTextArray(value: unknown): string[] {
    if (Array.isArray(value)) {
      return value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0 && !this.isDisallowedReason(item));
    }

    if (typeof value === 'string' && value.trim() && !this.isDisallowedReason(value)) {
      return [value.trim()];
    }

    return [];
  }

  private isDisallowedReason(value: string): boolean {
    return /\b(menor|niñ[oa]|nene|nena|hij[oa]|adolescente)\b/i.test(value);
  }

  trackById(_: number, item: { id: string }): string {
    return item.id;
  }

  trackByStagePoint(_: number, point: { at: string; stage: number; confidence: number }): string {
    return `${point.at}-${point.stage}-${point.confidence}`;
  }
}
