import { Component, OnInit, OnDestroy } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';
import { Subject } from 'rxjs';
import { AuthService } from '../../../../core/services/auth.service';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';

@Component({
  selector: 'app-mfa-verify',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule, LoadingSpinnerComponent],
  templateUrl: './mfa-verify.component.html',
  styleUrl: './mfa-verify.component.scss'
})
export class MfaVerifyComponent implements OnInit, OnDestroy {
  otpForm!: FormGroup;
  isSubmitting = false;
  errorMessage = '';
  private challengeToken: string | null = null;
  private destroy$ = new Subject<void>();

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.challengeToken = this.authService.getChallengeToken();
    if (!this.challengeToken) {
      this.router.navigate(['/auth/login']);
      return;
    }
    this.otpForm = this.fb.group({
      otp: ['', [Validators.required, Validators.pattern('^[0-9]{6}$')]]
    });
  }

  onSubmit(): void {
    if (this.otpForm.invalid) {
      this.otpForm.markAllAsTouched();
      return;
    }
    this.isSubmitting = true;
    this.errorMessage = '';

    this.authService.verifyMfa(this.challengeToken!, this.otpForm.value.otp).subscribe({
      next: () => this.router.navigate(['/dashboard']),
      error: (err) => {
        this.isSubmitting = false;
        this.errorMessage = err.message;
        this.otpForm.reset();
      }
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  backToLogin(): void {
    this.router.navigate(['/auth/login']);
  }
}
