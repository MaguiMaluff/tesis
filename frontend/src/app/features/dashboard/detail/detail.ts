import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { Subscription, switchMap } from 'rxjs';
import { ApiService, ChildDetail } from '../../../core/services/api';
import { statusLabel as formatStatus } from '../../../shared/presentation-labels';

@Component({
  selector: 'app-dashboard-detail',
  templateUrl: './detail.html',
  styleUrls: ['./detail.css'],
  standalone: true,
  imports: [CommonModule, RouterModule],
})
export class DetailComponent implements OnInit, OnDestroy {
  child: ChildDetail | null = null;
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
      .pipe(switchMap((params) => this.apiService.getChild(params.get('id') || '')))
      .subscribe({
        next: (child) => {
          this.child = child;
          this.loading = false;
          this.cdr.detectChanges();
        },
        error: (error) => {
          console.error('Error fetching child detail:', error);
          this.errorMessage = 'No se pudo cargar el perfil monitoreado.';
          this.loading = false;
          this.cdr.detectChanges();
        },
      });
  }

  ngOnDestroy(): void {
    this.subscription?.unsubscribe();
  }

  back(): void {
    window.history.back();
  }

  get statusLabel(): string {
    return formatStatus(this.child?.status || this.primaryAccount?.status);
  }

  get primaryAccount(): any {
    return this.child?.accounts?.[0] || null;
  }

  get igUserId(): string {
    return String(this.child?.ig_user_id || this.primaryAccount?.ig_user_id || 'No disponible');
  }

  get igUsername(): string {
    const username = this.child?.ig_username || this.primaryAccount?.ig_username;
    return username ? `@${username}` : 'No disponible';
  }

  trackById(_: number, item: { id: string }): string {
    return item.id;
  }

  trackBySignal(_: number, signal: string): string {
    return signal;
  }
}
