import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { ApiService } from '../../../core/services/api';

@Component({
  selector: 'app-risk-cases-list',
  templateUrl: './list.html',
  styleUrls: ['./list.css'],
  standalone: true,
  imports: [CommonModule, RouterModule],
})
export class ListComponent implements OnInit {
  riskCases: any[] = [];
  loading = true;

  constructor(private apiService: ApiService) {}

  ngOnInit(): void {
    this.apiService.getRiskCases().subscribe({
      next: (data) => {
        this.riskCases = data;
        this.loading = false;
      },
      error: (err) => {
        console.error('Error fetching risk cases:', err);
        this.loading = false;
      },
    });
  }
}