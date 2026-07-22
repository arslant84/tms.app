import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, ActivatedRoute, RouterModule } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { Observable, map, take } from 'rxjs';
import { environment } from '../../../../../environments/environment';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';
import { AppSettingsService } from '../../../../core/services/app-settings.service';
import { PASSWORD_MIN_LENGTH } from '../../../../core/constants';

@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, LoadingSpinnerComponent],
  templateUrl: './reset-password.component.html',
  styleUrls: ['./reset-password.component.scss'],
})
export class ResetPasswordComponent implements OnInit {
  token = '';
  newPassword = '';
  newPasswordConfirm = '';
  error = '';
  success = '';
  loading = false;
  invalidToken = false;
  applicationName$: Observable<string>;
  passwordMinLength = PASSWORD_MIN_LENGTH;

  constructor(
    private http: HttpClient,
    private router: Router,
    private route: ActivatedRoute,
    private appSettingsService: AppSettingsService
  ) {
    this.applicationName$ = this.appSettingsService.settings$.pipe(
      map(settings => settings.application_name || 'TMS')
    );
  }

  ngOnInit(): void {
    this.route.fragment.pipe(take(1)).subscribe(fragment => {
      const params = new URLSearchParams(fragment || '');
      this.token = params.get('token') || '';
      if (!this.token) {
        this.invalidToken = true;
        this.error = 'Invalid or missing reset token';
      } else {
        // Strip fragment from URL immediately — token held in memory only, submitted via POST body.
        this.router.navigate([], {
          relativeTo: this.route,
          fragment: undefined,
          replaceUrl: true,
        });
      }
    });
  }

  onSubmit(): void {
    this.error = '';
    this.success = '';

    if (!this.newPassword || !this.newPasswordConfirm) {
      this.error = 'All fields are required';
      return;
    }

    if (this.newPassword !== this.newPasswordConfirm) {
      this.error = 'Passwords do not match';
      return;
    }

    if (this.newPassword.length < PASSWORD_MIN_LENGTH) {
      this.error = `Password must be at least ${PASSWORD_MIN_LENGTH} characters`;
      return;
    }

    this.loading = true;
    const url = `${environment.apiUrl}/password/reset/confirm/`;

    this.http
      .post(url, {
        token: this.token,
        new_password: this.newPassword,
        new_password_confirm: this.newPasswordConfirm,
      })
      .subscribe({
        next: (response: { message?: string }) => {
          this.loading = false;
          this.success =
            response.message ||
            'Password reset successfully. You can now log in with your new password.';

          // Redirect to login after 3 seconds
          setTimeout(() => {
            this.router.navigate(['/auth/login']);
          }, 3000);
        },
        error: err => {
          this.loading = false;
          this.error = err.error?.message || err.error?.error || 'Invalid or expired reset token';
          this.invalidToken = true;
        },
      });
  }
}
