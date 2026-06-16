import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, ActivatedRoute } from '@angular/router';
import { forkJoin, of, Subscription, switchMap } from 'rxjs';
import { ApiService, ConversationItem, RiskCaseDetail, RiskCaseSnapshot } from '../../../core/services/api';
import { ChangeDetectorRef } from '@angular/core';

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
          this.snapshots = [...(riskCase.snapshots || [])].sort((left, right) => new Date(left.created_at).getTime() - new Date(right.created_at).getTime());
          this.loading = false;
          this.cdr.detectChanges();

        },
        error: (error) => {
          console.error('Error fetching risk case:', error);
          this.errorMessage = 'No se pudo cargar el detalle del risk case.';
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

  get latestSnapshot(): RiskCaseSnapshot | null {
    return this.snapshots.length ? this.snapshots[this.snapshots.length - 1] : null;
  }

  get signals(): string[] {
    const latest = this.latestSnapshot?.snapshot_json || {};
    const assessmentSignals = (latest as any)?.assessment?.signals || [];
    const rollingSignals = (latest as any)?.rolling_summary?.signals_observed || [];
    const snapshotSignals = this.snapshots.flatMap((snapshot) => snapshot.signals || []);
    return [...new Set([...assessmentSignals, ...rollingSignals, ...snapshotSignals])].slice(0, 10);
  }

  get explanation(): string {
    const latest = this.latestSnapshot?.snapshot_json || {};
    return (latest as any)?.explanation?.short_reason_safe || this.riskCase?.reason_safe || 'No explanation available.';
  }

  get stageEvolution(): Array<{ at: string; stage: number; confidence: number }> {
    return this.snapshots.map((snapshot) => ({
      at: snapshot.created_at,
      stage: Number((snapshot.snapshot_json as any)?.assessment?.risk_stage || 0),
      confidence: Number((snapshot.snapshot_json as any)?.assessment?.confidence || 0),
    }));
  }

  snapshotStage(snapshot: RiskCaseSnapshot): number {
    return Number((snapshot.snapshot_json as any)?.assessment?.risk_stage || 0);
  }

  snapshotConfidence(snapshot: RiskCaseSnapshot): number {
    return Number((snapshot.snapshot_json as any)?.assessment?.confidence || 0);
  }

  snapshotReason(snapshot: RiskCaseSnapshot): string {
    return (snapshot.snapshot_json as any)?.explanation?.short_reason_safe || this.riskCase?.reason_safe || 'No reason available';
  }

  trackById(_: number, item: { id: string }): string {
    return item.id;
  }

  trackByStagePoint(_: number, point: { at: string; stage: number; confidence: number }): string {
    return `${point.at}-${point.stage}-${point.confidence}`;
  }
}