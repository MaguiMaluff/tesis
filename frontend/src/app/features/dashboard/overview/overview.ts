import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { forkJoin } from 'rxjs';
import { ApiService } from '../../../core/services/api';
import { ChangeDetectorRef } from '@angular/core';

@Component({
  selector: 'app-dashboard-overview',
  templateUrl: './overview.html',
  styleUrls: ['./overview.css'],
  standalone: true,
  imports: [CommonModule, RouterModule],
})
export class OverviewComponent implements OnInit {
  summary: any = null;
  children: any[] = [];
  loading = true;
  errorMessage = '';

  constructor(private apiService: ApiService, private cdr: ChangeDetectorRef) {}

  ngOnInit(): void {
    forkJoin({
      summary: this.apiService.getDashboardSummary(),
      children: this.apiService.getChildren(),
    }).subscribe({
      next: ({ summary, children }) => {
        this.summary = summary;
        this.children = [...children].sort((left, right) => {
          const leftRank = this.riskRank(left.risk_level);
          const rightRank = this.riskRank(right.risk_level);
          if (leftRank !== rightRank) {
            return rightRank - leftRank;
          }
          return (new Date(right.last_activity_at || 0).getTime() || 0) - (new Date(left.last_activity_at || 0).getTime() || 0);
        });
        this.loading = false;
        this.cdr.detectChanges();

      },
      error: (error) => {
        console.error('Error fetching dashboard data:', error);
        this.errorMessage = 'No se pudo cargar el tablero desde la API.';
        this.loading = false;
        this.cdr.detectChanges();

      },
    });
  }

  riskRank(level: string): number {
    return {
      low: 1,
      medium: 2,
      high: 3,
      critical: 4,
    }[level || 'low'] ?? 1;
  }

  maxStageCount(): number {
    return Math.max(...(this.summary?.cases_by_stage?.map((item: any) => item.count) || [1]), 1);
  }

  trackById(_: number, item: { id: string }): string {
    return item.id;
  }

  trackBySignal(_: number, signal: string): string {
    return signal;
  }
}