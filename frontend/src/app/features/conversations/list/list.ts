import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { ApiService, ConversationItem } from '../../../core/services/api';
import { ChangeDetectorRef } from '@angular/core';
import { statusLabel as formatStatus } from '../../../shared/presentation-labels';

@Component({
  selector: 'app-conversations-list',
  templateUrl: './list.html',
  styleUrls: ['./list.css'],
  standalone: true,
  imports: [CommonModule, RouterModule],
})
export class ListComponent implements OnInit {
  conversations: ConversationItem[] = [];
  loading = true;
  searchTerm = '';
  sortOrder: 'recent' | 'oldest' = 'recent';
  errorMessage = '';

  constructor(
    private apiService: ApiService,
    private cdr: ChangeDetectorRef

  ) {}

  ngOnInit(): void {
    this.apiService.getConversations().subscribe({
      next: (data) => {
        this.conversations = data;
        this.loading = false;
        this.cdr.detectChanges();

      },
      error: (error) => {
        console.error('Error fetching conversations:', error);
        this.errorMessage = 'No se pudo cargar la lista de conversaciones.';
        this.loading = false;
        this.cdr.detectChanges();

      },
    });
  }

  get visibleConversations(): ConversationItem[] {
    const query = this.searchTerm.trim().toLowerCase();
    return [...this.conversations]
      .filter((conversation) => {
        if (!query) {
          return true;
        }
        return [conversation.peer_username, conversation.peer_id, conversation.child_name, conversation.status, conversation.max_stage_label]
          .filter(Boolean)
          .some((value) => String(value).toLowerCase().includes(query));
      })
      .sort((left, right) => {
        const leftTime = new Date(left.last_message_at || left.created_at || 0).getTime() || 0;
        const rightTime = new Date(right.last_message_at || right.created_at || 0).getTime() || 0;
        return this.sortOrder === 'recent' ? rightTime - leftTime : leftTime - rightTime;
      });
  }

  setSortOrder(order: 'recent' | 'oldest'): void {
    this.sortOrder = order;
  }

  trackById(_: number, item: ConversationItem): string {
    return item.id;
  }

  conversationTitle(conversation: ConversationItem): string {
    return conversation.peer_username ? `@${conversation.peer_username}` : conversation.peer_id;
  }

  statusLabel(status?: string | null): string {
    return formatStatus(status);
  }

  goBack(): void {
    window.history.back();
  }
}
