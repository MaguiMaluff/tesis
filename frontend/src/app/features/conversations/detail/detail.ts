import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, ActivatedRoute } from '@angular/router';
import { ApiService } from '../../../core/services/api';

@Component({
  selector: 'app-conversations-detail',
  templateUrl: './detail.html',
  styleUrls: ['./detail.css'],
  standalone: true,
  imports: [CommonModule, RouterModule],
})
export class DetailComponent implements OnInit {
  conversation: any;
  loading = true;

  constructor(
    private route: ActivatedRoute,
    private apiService: ApiService
  ) {}

  ngOnInit(): void {
    this.route.params.subscribe((params) => {
      const id = params['id'];
      this.apiService.getConversation(id).subscribe({
        next: (data) => {
          this.conversation = data;
          this.loading = false;
        },
        error: (err) => {
          console.error('Error fetching conversation:', err);
          this.loading = false;
        },
      });
    });
  }

  goBack(): void {
    window.history.back();
  }
}