import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, AbstractControl, ValidationErrors } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { Subject, takeUntil } from 'rxjs';

import { AuthService } from '../../../../core/services/auth.service';
import { DepartmentService } from '../../../../core/services/department.service';
import { ToastService } from '../../../../core/services/toast.service';
import { HttpErrorHandlerService } from '../../../../core/utils/http-error-handler.service';
import { DepartmentListItem } from '../../../../core/models/user.model';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.scss']
})
export class RegisterComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();

  registerForm!: FormGroup;
  departments: DepartmentListItem[] = [];
  isLoading = false;
  showPassword = false;
  showConfirmPassword = false;
  selectedFileName = '';
  profilePhotoPreview: string | null = null;

  genderOptions = [
    { value: 'Male', label: 'Male' },
    { value: 'Female', label: 'Female' },
    { value: 'Other', label: 'Other' }
  ];

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private departmentService: DepartmentService,
    private toastService: ToastService,
    private errorHandler: HttpErrorHandlerService,
    private router: Router
  ) {
    this.initializeForm();
  }

  ngOnInit(): void {
    this.loadDepartments();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private initializeForm(): void {
    this.registerForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      name: ['', [Validators.required, Validators.minLength(2)]],
      staff_id: [''],
      phone: [''],
      department: ['', Validators.required],
      gender: [''],
      password: ['', [Validators.required, Validators.minLength(8), this.passwordStrengthValidator]],
      password_confirm: ['', Validators.required],
      profile_photo: ['']
    }, {
      validators: this.passwordMatchValidator
    });
  }

  private loadDepartments(): void {
    this.departmentService.getActiveDepartments()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response: DepartmentListItem[]) => {
          this.departments = response;
        },
        error: (err: any) => {
          const message = this.errorHandler.getErrorMessage(err);
          this.toastService.error('Failed to load departments: ' + message);
        }
      });
  }

  /**
   * Custom validator for password strength
   * Requires: uppercase, lowercase, number, min 8 chars
   * Note: Backend has additional validation (common passwords, similarity to user attributes)
   */
  private passwordStrengthValidator(control: AbstractControl): ValidationErrors | null {
    const value = control.value;
    if (!value) return null;

    const hasUpperCase = /[A-Z]/.test(value);
    const hasLowerCase = /[a-z]/.test(value);
    const hasNumber = /[0-9]/.test(value);
    const isLongEnough = value.length >= 8;
    const hasSpecialChar = /[^a-zA-Z0-9]/.test(value);

    // Check for common weak patterns
    const commonPatterns = [
      /^password/i,
      /^123456/,
      /^qwerty/i,
      /^abc123/i,
      /^letmein/i
    ];
    const isCommonPattern = commonPatterns.some(pattern => pattern.test(value));

    const passwordValid = hasUpperCase && hasLowerCase && hasNumber && isLongEnough && !isCommonPattern;

    if (!passwordValid) {
      return {
        passwordStrength: {
          hasUpperCase,
          hasLowerCase,
          hasNumber,
          isLongEnough,
          hasSpecialChar,
          isCommonPattern
        }
      };
    }

    return null;
  }

  /**
   * Validator to check if password and password_confirm match
   */
  private passwordMatchValidator(group: AbstractControl): ValidationErrors | null {
    const password = group.get('password')?.value;
    const confirmPassword = group.get('password_confirm')?.value;

    if (password && confirmPassword && password !== confirmPassword) {
      group.get('password_confirm')?.setErrors({ passwordMismatch: true });
      return { passwordMismatch: true };
    }

    // Clear error if passwords match
    const confirmControl = group.get('password_confirm');
    if (confirmControl?.hasError('passwordMismatch')) {
      confirmControl.setErrors(null);
    }

    return null;
  }

  /**
   * Get password strength level (0-4)
   */
  getPasswordStrength(): number {
    const password = this.registerForm.get('password')?.value || '';
    let strength = 0;

    if (password.length >= 8) strength++;
    if (/[a-z]/.test(password)) strength++;
    if (/[A-Z]/.test(password)) strength++;
    if (/[0-9]/.test(password)) strength++;
    if (/[^a-zA-Z0-9]/.test(password)) strength++;

    return Math.min(strength, 4);
  }

  /**
   * Get password strength label
   */
  getPasswordStrengthLabel(): string {
    const strength = this.getPasswordStrength();
    const labels = ['', 'Weak', 'Fair', 'Good', 'Strong'];
    return labels[strength] || '';
  }

  /**
   * Get password strength CSS class
   */
  getPasswordStrengthClass(): string {
    const strength = this.getPasswordStrength();
    if (strength <= 1) return 'strength-weak';
    if (strength === 2) return 'strength-fair';
    if (strength === 3) return 'strength-good';
    return 'strength-strong';
  }

  /**
   * Toggle password visibility
   */
  togglePasswordVisibility(): void {
    this.showPassword = !this.showPassword;
  }

  /**
   * Toggle confirm password visibility
   */
  toggleConfirmPasswordVisibility(): void {
    this.showConfirmPassword = !this.showConfirmPassword;
  }

  /**
   * Handle profile photo file selection
   */
  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (!input.files || input.files.length === 0) return;

    const file = input.files[0];
    this.selectedFileName = file.name;

    // Validate file size (5MB max)
    const maxSize = 5 * 1024 * 1024; // 5MB
    if (file.size > maxSize) {
      this.toastService.error('File size must be less than 5MB');
      this.clearFileSelection();
      return;
    }

    // Validate file type
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif'];
    if (!allowedTypes.includes(file.type)) {
      this.toastService.error('Only JPEG, PNG, and GIF images are allowed');
      this.clearFileSelection();
      return;
    }

    // Convert to base64
    const reader = new FileReader();
    reader.onload = (e: ProgressEvent<FileReader>) => {
      const base64 = e.target?.result as string;
      this.profilePhotoPreview = base64;
      this.registerForm.patchValue({ profile_photo: base64 });
    };
    reader.readAsDataURL(file);
  }

  /**
   * Clear file selection
   */
  clearFileSelection(): void {
    this.selectedFileName = '';
    this.profilePhotoPreview = null;
    this.registerForm.patchValue({ profile_photo: '' });
  }

  /**
   * Check if field has error and is touched
   */
  hasError(fieldName: string, errorType?: string): boolean {
    const field = this.registerForm.get(fieldName);
    if (!field) return false;

    if (errorType) {
      return field.hasError(errorType) && (field.dirty || field.touched);
    }
    return field.invalid && (field.dirty || field.touched);
  }

  /**
   * Get error message for field
   */
  getErrorMessage(fieldName: string): string {
    const field = this.registerForm.get(fieldName);
    if (!field || !field.errors) return '';

    if (field.hasError('required')) return `${this.getFieldLabel(fieldName)} is required`;
    if (field.hasError('email')) return 'Please enter a valid email address';
    if (field.hasError('minlength')) {
      const minLength = field.errors['minlength'].requiredLength;
      return `Must be at least ${minLength} characters`;
    }
    if (field.hasError('passwordMismatch')) return 'Passwords do not match';
    if (field.hasError('passwordStrength')) {
      const errors = field.errors['passwordStrength'];
      if (errors.isCommonPattern) return 'Password is too common. Please choose a stronger password';
      if (!errors.hasUpperCase) return 'Password must contain at least one uppercase letter';
      if (!errors.hasLowerCase) return 'Password must contain at least one lowercase letter';
      if (!errors.hasNumber) return 'Password must contain at least one number';
      if (!errors.isLongEnough) return 'Password must be at least 8 characters';
      return 'Password must contain uppercase, lowercase, and number';
    }

    return 'Invalid value';
  }

  private getFieldLabel(fieldName: string): string {
    const labels: { [key: string]: string } = {
      email: 'Email',
      name: 'Full Name',
      staff_id: 'Staff ID',
      phone: 'Phone',
      department: 'Department',
      gender: 'Gender',
      password: 'Password',
      password_confirm: 'Confirm Password'
    };
    return labels[fieldName] || fieldName;
  }

  /**
   * Handle form submission
   */
  onSubmit(): void {
    if (this.registerForm.invalid) {
      Object.keys(this.registerForm.controls).forEach(key => {
        this.registerForm.get(key)?.markAsTouched();
      });
      this.toastService.error('Please fill in all required fields correctly');
      return;
    }

    this.isLoading = true;
    const formData = this.registerForm.value;

    // Debug logging
    console.log('=== REGISTRATION FORM SUBMISSION ===');
    console.log('Form valid:', this.registerForm.valid);
    console.log('Form data:', {
      email: formData.email,
      name: formData.name,
      staff_id: formData.staff_id || '(empty)',
      phone: formData.phone || '(empty)',
      department: formData.department,
      gender: formData.gender || '(empty)',
      password: '[REDACTED]',
      password_confirm: '[REDACTED]',
      profile_photo: formData.profile_photo ? '[BASE64_DATA]' : null
    });
    console.log('Available departments:', this.departments);
    console.log('Selected department value:', formData.department);
    console.log('====================================');

    this.authService.register(formData)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response: any) => {
          this.isLoading = false;

          if (response.success) {
            this.toastService.success(response.message || 'Registration successful!');

            // Redirect to login after 2 seconds
            setTimeout(() => {
              this.router.navigate(['/auth/login'], {
                queryParams: { registered: 'true' }
              });
            }, 2000);
          } else {
            this.toastService.error(response.message || 'Registration failed');
          }
        },
        error: (err: any) => {
          this.isLoading = false;

          // Debug logging
          console.error('Registration error:', err);
          console.error('Error response:', err.error);
          console.error('Error status:', err.status);
          console.error('Full error object:', JSON.stringify(err.error, null, 2));

          // Handle rate limiting (403/429)
          if (err.status === 403 || err.status === 429) {
            this.toastService.error('Too many registration attempts. Please try again later.');
            return;
          }

          const message = this.errorHandler.getErrorMessage(err);

          // Apply field errors if available
          const fieldErrors = this.errorHandler.getFieldErrors(err);
          if (Object.keys(fieldErrors).length > 0) {
            console.log('Field errors detected:');
            Object.entries(fieldErrors).forEach(([field, error]) => {
              console.log(`  - ${field}: ${error}`);
            });

            Object.keys(fieldErrors).forEach(field => {
              const control = this.registerForm.get(field);
              if (control) {
                control.setErrors({ serverError: fieldErrors[field] });
                control.markAsTouched();
              }
            });

            // Show specific field errors to user
            this.toastService.error('Registration failed. Please check the form for errors.');
          } else {
            this.toastService.error(message);
          }
        }
      });
  }
}
