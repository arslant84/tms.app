import { Component, OnInit, ElementRef, ViewChild } from '@angular/core';
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
  @ViewChild('fileInput') fileInput!: ElementRef<HTMLInputElement>;

  currentUser: User | null = null;
  profileForm!: FormGroup;
  passwordForm!: FormGroup;
  loading = false;
  submitting = false;
  showPasswordModal = false;
  isEditing = false;

  previewImage: string | null = null;
  selectedFile: File | null = null;

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
      gender: [''],
      profile_photo: [null]
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
        this.previewImage = user.profile_photo || null;
        this.profileForm.patchValue({
          name: user.name,
          phone: user.phone,
          gender: user.gender,
          profile_photo: user.profile_photo
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

  toggleEdit(): void {
    if (this.isEditing) {
      this.handleCancel();
    } else {
      this.isEditing = true;
    }
  }

  handleCancel(): void {
    this.isEditing = false;
    this.previewImage = this.currentUser?.profile_photo || null;
    this.selectedFile = null;
    if (this.fileInput) {
      this.fileInput.nativeElement.value = '';
    }
    this.profileForm.patchValue({
      name: this.currentUser?.name,
      phone: this.currentUser?.phone,
      gender: this.currentUser?.gender,
      profile_photo: this.currentUser?.profile_photo
    });
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];

    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      this.toastService.error('Please select an image file');
      input.value = '';
      return;
    }

    // Validate file size (max 2MB)
    if (file.size > 2 * 1024 * 1024) {
      this.toastService.error('Image size must be less than 2MB');
      input.value = '';
      return;
    }

    this.selectedFile = file;

    // Preview the image
    const reader = new FileReader();
    reader.onload = (e: ProgressEvent<FileReader>) => {
      this.previewImage = e.target?.result as string;
      this.profileForm.patchValue({ profile_photo: this.previewImage });
    };
    reader.readAsDataURL(file);
  }

  triggerFileInput(): void {
    this.fileInput.nativeElement.click();
  }

  removePhoto(): void {
    this.previewImage = null;
    this.selectedFile = null;
    this.profileForm.patchValue({ profile_photo: null });
    if (this.fileInput) {
      this.fileInput.nativeElement.value = '';
    }
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

    // Debug: Log the data being sent
    console.log('Sending profile update:', formData);

    this.userService.updateUser(this.currentUser.id, formData).subscribe({
      next: (response) => {
        console.log('Profile updated successfully:', response);
        this.toastService.success('Profile updated successfully');
        this.isEditing = false;
        this.loadCurrentUser();
        this.submitting = false;
      },
      error: (error) => {
        console.error('Error updating profile:', error);
        console.error('Error details:', error.error);
        this.toastService.error(error.error?.detail || JSON.stringify(error.error) || 'Failed to update profile');
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

    const oldPassword = this.passwordForm.get('old_password')?.value;
    const passwordData = {
      old_password: oldPassword,
      new_password: newPassword
    };

    this.userService.changePassword(passwordData).subscribe({
      next: (response) => {
        this.toastService.success(response.message || 'Password changed successfully');
        this.closePasswordModal();
        this.submitting = false;
        this.passwordForm.reset();
      },
      error: (err) => {
        const errorMsg = err.error?.error || err.error?.detail || err.error?.old_password?.[0] || 'Failed to change password';
        this.toastService.error(errorMsg);
        this.submitting = false;
      }
    });
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
    if (!this.currentUser?.name) return 'U';
    const names = this.currentUser.name.split(' ');
    return names.map(n => n[0]).join('').toUpperCase();
  }

  getStatusBadgeClass(): string {
    return this.currentUser?.is_active ? 'bg-success' : 'bg-secondary';
  }

  getStatusText(): string {
    return this.currentUser?.is_active ? 'Active' : 'Inactive';
  }
}
