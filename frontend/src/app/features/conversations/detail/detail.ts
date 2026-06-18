import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { forkJoin, Subscription, switchMap } from 'rxjs';
import { ApiService, ConversationItem, RiskCaseItem } from '../../../core/services/api';
import {
  riskLevelLabel as formatRiskLevel,
  statusLabel as formatStatus,
  trendLabel as formatTrend,
} from '../../../shared/presentation-labels';

@Component({
  selector: 'app-conversations-detail',
  templateUrl: './detail.html',
  styleUrls: ['./detail.css'],
  standalone: true,
  imports: [CommonModule, RouterModule],
})
export class DetailComponent implements OnInit, OnDestroy {
  conversation: ConversationItem | null = null;
  riskCases: RiskCaseItem[] = [];
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
        switchMap((params) => {
          const id = params.get('id') || '';

          return forkJoin({
            conversation: this.apiService.getConversation(id),
            riskCases: this.apiService.getRiskCases(),
          });
        })
      )
      .subscribe({
        next: ({ conversation, riskCases }) => {
          this.conversation = conversation;
          this.riskCases = riskCases.filter(
            (riskCase) => riskCase.conversation_id === conversation.id
          );
          this.loading = false;
          this.cdr.detectChanges();
        },
        error: (error) => {
          console.error('Error fetching conversation:', error);
          this.errorMessage = 'No se pudo cargar el detalle de la conversación.';
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

  get monitoredAccountLabel(): string {
    return this.conversation?.account_username ? `@${this.conversation.account_username}` : 'Cuenta monitoreada';
  }

  get peerLabel(): string {
    return this.conversation?.peer_username ? `@${this.conversation.peer_username}` : this.conversation?.peer_id || 'Contacto externo';
  }

  get summary(): Record<string, unknown> {
    return (this.conversation?.rolling_summary as Record<string, unknown>) || {};
  }

  get currentStageMax(): number | string {
    return (this.summary['current_stage_max'] as number | undefined) ?? 'No disponible';
  }

  get trendLabel(): string {
    return formatTrend(this.summary['trend'] as string);
  }

  get statusLabel(): string {
    return formatStatus(this.conversation?.status);
  }

  get riskLevelLabel(): string {
    return formatRiskLevel(this.riskLevel);
  }

  get keyPoints(): string[] {
    return (this.summary['key_points_safe'] as string[]) || [];
  }

  get signals(): string[] {
    const summarySignals = (this.summary['signals_observed'] as string[]) || [];
    const riskCaseSignals = this.riskCases.flatMap((riskCase) => riskCase.signals || []);
    return [...new Set([...summarySignals, ...riskCaseSignals])].slice(0, 8);
  }

  get maxStage(): number {
    return Math.max(...this.riskCases.map((riskCase) => riskCase.stage), 0);
  }

  get riskLevel(): string {
    const maxConfidence = Math.max(
      ...this.riskCases.map((riskCase) => Number(riskCase.confidence || 0)),
      0
    );

    if (this.maxStage >= 4 || maxConfidence >= 0.9) {
      return 'critical';
    }

    if (this.maxStage >= 3 || maxConfidence >= 0.7) {
      return 'high';
    }

    if (this.maxStage >= 2 || maxConfidence >= 0.45) {
      return 'medium';
    }

    return 'low';
  }

  riskCaseLevelLabel(riskCase: RiskCaseItem): string {
    return formatRiskLevel(riskCase.risk_level);
  }

  trackById(_: number, item: { id: string }): string {
    return item.id;
  }

  trackByString(_: number, value: string): string {
    return value;
  }
}
