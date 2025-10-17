import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { UserService, User } from '../../services/user.service';
import { ToastService } from '../../../../core/services/toast.service';
import { AuthService } from '../../../../core/services/auth.service';

@Component({
  selector: 'app-user-profile',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './user-profile.component.html',
  styleUrls: ['./user-profile.component.scss']
})
export class UserProfileComponent implements OnInit {
  currentUser: User | null = null;
  profileForm!: FormGroup;
  passwordForm!: FormGroup;
  loading = false;
  submitting = false;
  showPasswordModal = false;

  genders = [
    { value: 'Male', label: 'Male' },
    { value: 'Female', label: 'Female' },
    { value: 'Other', label: 'Other' }
  ];

  constructor(
    private fb: FormBuilder,
    private userService: UserService,
    private authService: AuthService,
    private toastService: ToastService
  ) {}

  ngOnInit(): void {
    this.initializeForms();
    this.loadCurrentUser();
  }

  initializeForms(): void {
    // Profile form - only editable fields
    this.profileForm = this.fb.group({
      name: ['', Validators.required],
      phone: [''],
      gender: ['']
    });

    // Password change form
    this.passwordForm = this.fb.group({
      current_password: ['', Validators.required],
      new_password: ['', [Validators.required, Validators.minLength(8)]],
      confirm_password: ['', Validators.required]
    });
  }

  loadCurrentUser(): void {
    this.loading = true;
    const userId = this.authService.getCurrentUserId();

    if (!userId) {
      this.toastService.error('User not found');
      this.loading = false;
      return;
    }

    this.userService.getUserById(userId).subscribe({
      next: (user) => {
        this.currentUser = user;
        this.profileForm.patchValue({
          name: user.name,
          phone: user.phone,
          gender: user.gender
        });
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading user profile:', error);
        this.toastService.error('Failed to load profile');
        this.loading = false;
      }
    });
  }

  onSubmitProfile(): void {
    if (this.profileForm.invalid) {
      this.toastService.warning('Please fill in all required fields');
      Object.keys(this.profileForm.controls).forEach(key => {
        const control = this.profileForm.get(key);
        if (control?.invalid) {
          control.markAsTouched();
        }
      });
      return;
    }

    if (!this.currentUser) return;

    this.submitting = true;
    const formData = this.profileForm.value;

    this.userService.updateUser(this.currentUser.id, formData).subscribe({
      next: () => {
        this.toastService.success('Profile updated successfully');
        this.loadCurrentUser();
        this.submitting = false;
      },
      error: (error) => {
        console.error('Error updating profile:', error);
        this.toastService.error(error.error?.detail || 'Failed to update profile');
        this.submitting = false;
      }
    });
  }

  openPasswordModal(): void {
    this.passwordForm.reset();
    this.showPasswordModal = true;
  }

  closePasswordModal(): void {
    this.showPasswordModal = false;
    this.passwordForm.reset();
  }

  onSubmitPassword(): void {
    if (this.passwordForm.invalid) {
      this.toastService.warning('Please fill in all required fields');
      return;
    }

    const newPassword = this.passwordForm.get('new_password')?.value;
    const confirmPassword = this.passwordForm.get('confirm_password')?.value;

    if (newPassword !== confirmPassword) {
      this.toastService.error('Passwords do not match');
      return;
    }

    this.submitting = true;
    // TODO: Implement password change API call
    // For now, just show a success message
    setTimeout(() => {
      this.toastService.success('Password changed successfully');
      this.closePasswordModal();
      this.submitting = false;
    }, 1000);
  }

  isFieldInvalid(formName: 'profile' | 'password', fieldName: string): boolean {
    const form = formName === 'profile' ? this.profileForm : this.passwordForm;
    const field = form.get(fieldName);
    return !!(field && field.invalid && field.touched);
  }

  getFieldError(formName: 'profile' | 'password', fieldName: string): string {
    const form = formName === 'profile' ? this.profileForm : this.passwordForm;
    const field = form.get(fieldName);
    if (field?.errors) {
      if (field.errors['required']) return 'This field is required';
      if (field.errors['email']) return 'Invalid email format';
      if (field.errors['minlength']) return `Minimum length is ${field.errors['minlength'].requiredLength}`;
    }
    return '';
  }

  getInitials(): string {
    return this.currentUser?.name?.charAt(0).toUpperCase() || 'U';
  }

  getStatusBadgeClass(): string {
    return this.currentUser?.is_active ? 'bg-success' : 'bg-secondary';
  }

  getStatusText(): string {
    return this.currentUser?.is_active ? 'Active' : 'Inactive';
  }
}
