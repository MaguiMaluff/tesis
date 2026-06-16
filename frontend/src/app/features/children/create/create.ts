import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators
} from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { ApiService } from '../../../core/services/api';

@Component({
  selector: 'app-child-create',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  templateUrl: './create.html',
  styleUrls: ['./create.css'],
})
export class CreateChildComponent implements OnInit {
  loading = false;
  errorMessage = '';
  successMessage = '';

  childForm!: FormGroup;

  constructor(
    private formBuilder: FormBuilder,
    private apiService: ApiService,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.childForm = this.formBuilder.group({
      display_name: ['', [Validators.required, Validators.minLength(2)]],
      ig_user_id: ['', [Validators.required, Validators.minLength(3)]],
      access_token: ['', [Validators.required, Validators.minLength(6)]],
    });
  }

  submit(): void {
    if (this.childForm.invalid || this.loading) {
      this.childForm.markAllAsTouched();
      return;
    }

    const payload = {
      display_name: String(
        this.childForm.value.display_name || ''
      ).trim(),

      ig_user_id: String(
        this.childForm.value.ig_user_id || ''
      ).trim(),

      access_token: String(
        this.childForm.value.access_token || ''
      ).trim(),
    };

    this.loading = true;
    this.errorMessage = '';
    this.successMessage = '';

    this.apiService.createChild(payload).subscribe({
      next: () => {
        this.successMessage =
          'Hijo creado correctamente. Redirigiendo al dashboard...';

        this.loading = false;
        this.cdr.detectChanges();

        window.setTimeout(() => {
          void this.router.navigate(['/dashboard']);
        }, 1200);
      },
      error: (error) => {
        console.error('Create child failed:', error);

        this.errorMessage =
          'No se pudo crear el hijo. Revisa los datos e intenta nuevamente.';

        this.loading = false;
        this.cdr.detectChanges();
      },
    });
  }

  get displayNameInvalid(): boolean {
    const control = this.childForm.get('display_name');
    return !!(control?.touched && control.invalid);
  }

  get igUserIdInvalid(): boolean {
    const control = this.childForm.get('ig_user_id');
    return !!(control?.touched && control.invalid);
  }

  get accessTokenInvalid(): boolean {
    const control = this.childForm.get('access_token');
    return !!(control?.touched && control.invalid);
  }
}