import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import {
  AbstractControl,
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators
} from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../../core/services/auth';

@Component({
  selector: 'app-signup',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  templateUrl: './signup.html',
  styleUrls: ['./signup.css'],
})
export class SignupComponent implements OnInit {
  loading = false;
  successMessage = '';
  errorMessage = '';

  signupForm!: FormGroup;

  constructor(
    private formBuilder: FormBuilder,
    private authService: AuthService,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.signupForm = this.formBuilder.group(
      {
        full_name: ['', [Validators.required, Validators.minLength(3)]],
        email: ['', [Validators.required, Validators.email]],
        password: ['', [Validators.required, Validators.minLength(6)]],
        confirm_password: ['', [Validators.required, Validators.minLength(6)]],
      },
      { validators: this.passwordsMatchValidator }
    );
  }

  submit(): void {
    if (this.signupForm.invalid || this.loading) {
      this.signupForm.markAllAsTouched();
      return;
    }

    const full_name = String(this.signupForm.value.full_name || '').trim();
    const email = String(this.signupForm.value.email || '').trim();
    const password = String(this.signupForm.value.password || '');

    this.loading = true;
    this.errorMessage = '';
    this.successMessage = '';

    this.authService.signup(full_name, email, password).subscribe({
      next: () => {
        this.successMessage =
          'Usuario creado correctamente. Redirigiendo al login...';

        this.loading = false;
        this.cdr.detectChanges();

        window.setTimeout(() => {
          void this.router.navigate(['/login']);
        }, 1200);
      },
      error: (error) => {
        console.error('Signup failed:', error);

        this.errorMessage =
          'No se pudo crear la cuenta. Verifica los datos e inténtalo nuevamente.';

        this.loading = false;
        this.cdr.detectChanges();
      },
    });
  }

  get fullNameInvalid(): boolean {
    const control = this.signupForm.get('full_name');
    return !!(control?.touched && control.invalid);
  }

  get emailInvalid(): boolean {
    const control = this.signupForm.get('email');
    return !!(control?.touched && control.invalid);
  }

  get passwordInvalid(): boolean {
    const control = this.signupForm.get('password');
    return !!(control?.touched && control.invalid);
  }

  get confirmPasswordInvalid(): boolean {
    const control = this.signupForm.get('confirm_password');

    return !!(
      control?.touched &&
      (control.invalid || this.signupForm.hasError('passwordMismatch'))
    );
  }

  private passwordsMatchValidator(group: AbstractControl) {
    const password = group.get('password')?.value;
    const confirmPassword = group.get('confirm_password')?.value;

    return password === confirmPassword
      ? null
      : { passwordMismatch: true };
  }
}