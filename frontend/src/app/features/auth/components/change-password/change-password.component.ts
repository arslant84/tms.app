import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { AuthService } from '../../../../core/services/auth.service';
import { environment } from '../../../../../environments/environment';

@Component({
  selector: 'app-change-password',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './change-password.component.html',
  styleUrls: ['./change-password.component.scss']
})
export class ChangePasswordComponent {
  oldPassword = '';
  newPassword = '';
  newPasswordConfirm = '';
  error = '';
  loading = false;

  constructor(
    private http: HttpClient,
    private router: Router,
    private authService: AuthService
  ) {}

  onSubmit(): void {
    this.error = '';

    if (!this.oldPassword || !this.newPassword || !this.newPasswordConfirm) {
      this.error = 'All fields are required';
      return;
    }

    if (this.newPassword !== this.newPasswordConfirm) {
      this.error = 'New passwords do not match';
      return;
    }

    if (this.newPassword.length < 8) {
      this.error = 'Password must be at least 8 characters';
      return;
    }

    this.loading = true;
    const url = `${environment.apiUrl}/password/change/`;

    this.http.post(url, {
      old_password: this.oldPassword,
      new_password: this.newPassword,
      new_password_confirm: this.newPasswordConfirm
    }, { withCredentials: true }).subscribe({
      next: () => {
        // Update user in auth service to clear password_change_required flag
        const currentUser = this.authService.getCurrentUser();
        if (currentUser) {
          currentUser.password_change_required = false;
        }
        this.router.navigate(['/dashboard']);
      },
      error: (err) => {
        this.loading = false;
        this.error = err.error?.error || 'Password change failed';
      }
    });
  }
}
