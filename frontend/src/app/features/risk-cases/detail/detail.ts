import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { ApiService } from '../../../core/services/api';

@Component({
  selector: 'app-risk-cases-detail',
  templateUrl: './detail.html',
  styleUrls: ['./detail.css'],
})
export class DetailComponent implements OnInit {
  riskCase: any;
  loading = true;

  constructor(
    private route: ActivatedRoute,
    private apiService: ApiService
  ) {}

  ngOnInit(): void {
    this.route.params.subscribe((params) => {
      const id = params['id'];
      this.apiService.getRiskCase(id).subscribe({
        next: (data) => {
          this.riskCase = data;
          this.loading = false;
        },
        error: (err) => {
          console.error('Error fetching risk case:', err);
          this.loading = false;
        },
      });
    });
  }
}