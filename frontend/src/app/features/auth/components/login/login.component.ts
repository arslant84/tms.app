import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router, ActivatedRoute, RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../../../core/services/auth.service';
import { AppSettingsService } from '../../../../core/services/app-settings.service';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';
import { Observable, map } from 'rxjs';
import { environment } from '../../../../../environments/environment';

const SSO_ERROR_MESSAGES: Record<string, string> = {
  not_configured: 'Sign in with Microsoft is not set up yet.',
  unavailable: 'Sign in with Microsoft is temporarily unavailable. Please try again shortly.',
  session_expired: 'Your sign-in session expired. Please try again.',
  auth_failed: 'Microsoft sign-in failed. Please try again.',
  no_email: 'Your Microsoft account did not provide an email address.',
  no_account: 'No TMS account matches your Microsoft email address. Contact your administrator.',
  inactive_account: 'Your TMS account is inactive. Contact your administrator.',
};

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule, LoadingSpinnerComponent],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss',
})
export class LoginComponent implements OnInit {
  loginForm!: FormGroup;
  isSubmitting = false;
  errorMessage = '';
  showPassword = false;
  applicationName$: Observable<string>;

  constructor(
    private formBuilder: FormBuilder,
    private authService: AuthService,
    private router: Router,
    private route: ActivatedRoute,
    private appSettingsService: AppSettingsService
  ) {
    this.applicationName$ = this.appSettingsService.settings$.pipe(
      map(settings => settings.application_name || 'TMS')
    );
  }

  ngOnInit(): void {
    this.loginForm = this.formBuilder.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]],
    });

    const ssoError = this.route.snapshot.queryParams['sso_error'];
    if (ssoError) {
      this.errorMessage =
        SSO_ERROR_MESSAGES[ssoError] || 'Microsoft sign-in failed. Please try again.';
    }
  }

  signInWithMicrosoft(): void {
    window.location.href = `${environment.apiUrl}/oidc/azure/login/`;
  }

  togglePasswordVisibility(): void {
    this.showPassword = !this.showPassword;
  }

  onSubmit(): void {
    // Mark all form controls as touched to trigger validation messages
    if (this.loginForm.invalid) {
      Object.keys(this.loginForm.controls).forEach(key => {
        const control = this.loginForm.get(key);
        control?.markAsTouched();
      });
      return;
    }

    this.isSubmitting = true;
    this.errorMessage = '';

    const { email, password } = this.loginForm.value;

    this.authService.login(email, password).subscribe({
      next: result => {
        if (result.type === 'mfa_required') {
          this.router.navigate(['/auth/mfa-verify']);
        } else if (result.type === 'mfa_setup_required') {
          this.router.navigate(['/auth/mfa-setup']);
        } else {
          const returnUrl = this.route.snapshot.queryParams['returnUrl'] || '/dashboard';
          this.router.navigate([returnUrl]);
        }
      },
      error: error => {
        this.isSubmitting = false;
        this.errorMessage = error.message || 'Login failed. Please check your credentials.';
      },
    });
  }
}
