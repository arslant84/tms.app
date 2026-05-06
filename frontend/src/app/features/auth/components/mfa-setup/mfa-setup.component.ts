import { Component, OnInit, OnDestroy } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import QRCode from 'qrcode';
import { AuthService } from '../../../../core/services/auth.service';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';

@Component({
  selector: 'app-mfa-setup',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, LoadingSpinnerComponent],
  templateUrl: './mfa-setup.component.html',
  styleUrl: './mfa-setup.component.scss'
})
export class MfaSetupComponent implements OnInit, OnDestroy {
  confirmForm!: FormGroup;
  isLoading = true;
  isSubmitting = false;
  errorMessage = '';
  qrCodeDataUrl = '';
  secret = '';
  secretCopied = false;
  private destroy$ = new Subject<void>();

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.confirmForm = this.fb.group({
      otp: ['', [Validators.required, Validators.pattern('^[0-9]{6}$')]]
    });

    this.authService.setupMfa().pipe(takeUntil(this.destroy$)).subscribe({
      next: async (data) => {
        this.secret = data.secret;
        this.qrCodeDataUrl = await QRCode.toDataURL(data.qr_uri, {
          width: 220,
          margin: 2,
          color: { dark: '#1a1a2e', light: '#ffffff' }
        });
        this.isLoading = false;
      },
      error: (err) => {
        this.isLoading = false;
        this.errorMessage = err.message;
      }
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  copySecret(): void {
    navigator.clipboard.writeText(this.secret).then(() => {
      this.secretCopied = true;
      setTimeout(() => this.secretCopied = false, 2000);
    });
  }

  onConfirm(): void {
    if (this.confirmForm.invalid) {
      this.confirmForm.markAllAsTouched();
      return;
    }
    this.isSubmitting = true;
    this.errorMessage = '';

    this.authService.confirmMfa(this.confirmForm.value.otp).subscribe({
      next: () => this.router.navigate(['/dashboard']),
      error: (err) => {
        this.isSubmitting = false;
        this.errorMessage = err.message;
        this.confirmForm.reset();
      }
    });
  }
}
