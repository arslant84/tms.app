import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../../environments/environment';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';

@Component({
  selector: 'app-forgot-password',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, LoadingSpinnerComponent],
  templateUrl: './forgot-password.component.html',
  styleUrls: ['./forgot-password.component.scss']
})
export class ForgotPasswordComponent {
  email = '';
  error = '';
  success = '';
  loading = false;

  constructor(
    private http: HttpClient,
    private router: Router
  ) {}

  onSubmit(): void {
    this.error = '';
    this.success = '';

    if (!this.email) {
      this.error = 'Email is required';
      return;
    }

    if (!this.isValidEmail(this.email)) {
      this.error = 'Please enter a valid email address';
      return;
    }

    this.loading = true;
    const url = `${environment.apiUrl}/password/reset/request/`;

    this.http.post(url, {
      email: this.email
    }).subscribe({
      next: (response: any) => {
        this.loading = false;
        this.success = response.message || 'If an account exists with this email, a password reset link has been sent.';
        this.email = '';
      },
      error: (err) => {
        this.loading = false;
        this.error = err.error?.message || err.error?.error || 'Failed to send password reset email';
      }
    });
  }

  private isValidEmail(email: string): boolean {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }
}
