import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { ApiService, RiskCaseItem } from '../../../core/services/api';
import { ChangeDetectorRef } from '@angular/core';
import {
  riskLevelLabel as formatRiskLevel,
  statusLabel as formatStatus,
} from '../../../shared/presentation-labels';

@Component({
  selector: 'app-risk-cases-list',
  templateUrl: './list.html',
  styleUrls: ['./list.css'],
  standalone: true,
  imports: [CommonModule, RouterModule],
})
export class ListComponent implements OnInit {
  riskCases: RiskCaseItem[] = [];
  loading = true;
  searchTerm = '';
  selectedStage = 'all';
  selectedSeverity = 'all';
  selectedStatus = 'all';
  sortOrder: 'recent' | 'oldest' = 'recent';
  errorMessage = '';

  constructor(private apiService: ApiService, private cdr: ChangeDetectorRef) {}

  ngOnInit(): void {
    this.apiService.getRiskCases().subscribe({
      next: (data) => {
        this.riskCases = data;
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: (error) => {
        console.error('Error fetching risk cases:', error);
        this.errorMessage = 'No se pudo cargar la lista de casos de riesgo.';
        this.loading = false;
        this.cdr.detectChanges();
      },
    });
  }

  get filteredRiskCases(): RiskCaseItem[] {
    const query = this.searchTerm.trim().toLowerCase();
    return [...this.riskCases]
      .filter((riskCase) => {
        if (this.selectedStage !== 'all' && String(riskCase.stage) !== this.selectedStage) {
          return false;
        }
        if (this.selectedSeverity !== 'all' && riskCase.risk_level !== this.selectedSeverity) {
          return false;
        }
        if (this.selectedStatus !== 'all' && riskCase.status !== this.selectedStatus) {
          return false;
        }
        if (!query) {
          return true;
        }
        return [riskCase.reason_safe, riskCase.stage_label, riskCase.peer_username, riskCase.peer_id, riskCase.status]
          .filter(Boolean)
          .some((value) => String(value).toLowerCase().includes(query));
      })
      .sort((left, right) => {
        const leftTime = new Date(left.opened_at || 0).getTime() || 0;
        const rightTime = new Date(right.opened_at || 0).getTime() || 0;
        return this.sortOrder === 'recent' ? rightTime - leftTime : leftTime - rightTime;
      });
  }

  setSortOrder(order: 'recent' | 'oldest'): void {
    this.sortOrder = order;
  }

  trackById(_: number, item: RiskCaseItem): string {
    return item.id;
  }

  contactLabel(riskCase: RiskCaseItem): string {
    return riskCase.peer_username ? `@${riskCase.peer_username}` : riskCase.peer_id || 'Contacto externo';
  }

  riskLevelLabel(level?: string | null): string {
    return formatRiskLevel(level);
  }

  statusLabel(status?: string | null): string {
    return formatStatus(status);
  }

  goBack(): void {
    window.history.back();
  }
}
