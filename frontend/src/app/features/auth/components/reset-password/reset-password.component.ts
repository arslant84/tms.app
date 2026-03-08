import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, ActivatedRoute, RouterModule } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../../environments/environment';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';

@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, LoadingSpinnerComponent],
  templateUrl: './reset-password.component.html',
  styleUrls: ['./reset-password.component.scss']
})
export class ResetPasswordComponent implements OnInit {
  token = '';
  newPassword = '';
  newPasswordConfirm = '';
  error = '';
  success = '';
  loading = false;
  invalidToken = false;

  constructor(
    private http: HttpClient,
    private router: Router,
    private route: ActivatedRoute
  ) {}

  ngOnInit(): void {
    // Get token from URL query parameter
    this.route.queryParams.subscribe(params => {
      this.token = params['token'] || '';
      if (!this.token) {
        this.invalidToken = true;
        this.error = 'Invalid or missing reset token';
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

    if (this.newPassword.length < 8) {
      this.error = 'Password must be at least 8 characters';
      return;
    }

    this.loading = true;
    const url = `${environment.apiUrl}/password/reset/confirm/`;

    this.http.post(url, {
      token: this.token,
      new_password: this.newPassword,
      new_password_confirm: this.newPasswordConfirm
    }).subscribe({
      next: (response: any) => {
        this.loading = false;
        this.success = response.message || 'Password reset successfully. You can now log in with your new password.';

        // Redirect to login after 3 seconds
        setTimeout(() => {
          this.router.navigate(['/auth/login']);
        }, 3000);
      },
      error: (err) => {
        this.loading = false;
        this.error = err.error?.message || err.error?.error || 'Invalid or expired reset token';
        this.invalidToken = true;
      }
    });
  }
}
