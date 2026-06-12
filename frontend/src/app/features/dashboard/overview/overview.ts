import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../../core/services/api';

@Component({
  selector: 'app-dashboard-overview',
  templateUrl: './overview.html',
  styleUrls: ['./overview.css'],
  standalone: true,
  imports: [CommonModule],
})
export class OverviewComponent implements OnInit {
  stats: any = {};
  loading = true;

  constructor(private apiService: ApiService) {}

  ngOnInit(): void {
    this.apiService.getRiskCases().subscribe({
      next: (data) => {
        this.stats = {
          total_cases: data.length,
          critical: data.filter((c: any) => c.stage === 4).length,
          high: data.filter((c: any) => c.stage === 3).length,
        };
        this.loading = false;
      },
      error: (err) => {
        console.error('Error fetching stats:', err);
        this.loading = false;
      },
    });
  }
}