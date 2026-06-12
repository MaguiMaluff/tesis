import { Component, OnInit } from '@angular/core';
import { ApiService } from '../../../core/services/api';

@Component({
  selector: 'app-conversations-list',
  templateUrl: './list.html',
  styleUrls: ['./list.css'],
})
export class ListComponent implements OnInit {
  conversations: any[] = [];
  loading = true;

  constructor(private apiService: ApiService) {}

  ngOnInit(): void {
    this.apiService.getConversations().subscribe({
      next: (data) => {
        this.conversations = data;
        this.loading = false;
      },
      error: (err) => {
        console.error('Error fetching conversations:', err);
        this.loading = false;
      },
    });
  }
}