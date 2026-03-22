import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, FormsModule, AbstractControl, ValidationErrors } from '@angular/forms';
import { UserService, User, Role } from '../../services/user.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmationService } from '../../../../core/services/confirmation.service';
import { DepartmentService } from '../../../../core/services/department.service';
import { DepartmentListItem } from '../../../../core/models/user.model';
import { ModalService } from '../../../../core/services/modal.service';
import { ConfirmDeleteModalComponent } from '../../../../core/components/confirm-delete-modal/confirm-delete-modal.component';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';
import { PASSWORD_MIN_LENGTH } from '../../../../core/constants';

@Component({
  selector: 'app-user-admin',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, FormsModule, LoadingSpinnerComponent],
  templateUrl: './user-admin.component.html',
  styleUrls: ['./user-admin.component.scss']
})
export class UserAdminComponent implements OnInit, OnDestroy {
  users: User[] = [];
  roles: Role[] = [];
  departments: DepartmentListItem[] = [];
  loading = false;
  showModal = false;
  isEditMode = false;
  selectedUserId: number | null = null;
  userForm!: FormGroup;
  submitting = false;
  passwordMinLength = PASSWORD_MIN_LENGTH;

  // Delete confirmation
  private userToDelete: User | null = null;

  // Filters
  searchTerm = '';
  filterRole: string | null = null;  // UUID
  filterDepartment = '';
  filterStatus: boolean | null = null;
  currentPage = 1;
  pageSize = 20;
  totalCount = 0;

  // Dropdown options
  genders = [
    { value: 'Male', label: 'Male' },
    { value: 'Female', label: 'Female' },
    { value: 'Other', label: 'Other' }
  ];

  // Password visibility toggles
  showPassword = false;
  showConfirmPassword = false;

  constructor(
    private fb: FormBuilder,
    private userService: UserService,
    private toastService: ToastService,
    private confirmationService: ConfirmationService,
    private departmentService: DepartmentService,
    private modalService: ModalService
  ) {}

  ngOnInit(): void {
    this.initializeForm();
    this.loadUsers();
    this.loadRoles();
    this.loadDepartments();
  }

  initializeForm(): void {
    this.userForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      name: ['', Validators.required],
      password: [''],
      password_confirm: [''],
      role: [null],
      department: [''],
      is_admin: [false],
      is_active: [true],
      staff_id: [''],
      phone: [''],
      gender: ['']
    }, {
      validators: this.passwordMatchValidator
    });
  }

  loadUsers(): void {
    this.loading = true;
    const filters = {
      search: this.searchTerm || undefined,
      role: this.filterRole || undefined,
      department: this.filterDepartment || undefined,
      is_active: this.filterStatus !== null ? this.filterStatus : undefined,
      page: this.currentPage,
      page_size: this.pageSize
    };

    this.userService.getAllUsers(filters).subscribe({
      next: (response) => {
        // Handle both paginated response and direct array response
        if (Array.isArray(response)) {
          this.users = response;
          this.totalCount = response.length;
        } else if (response && typeof response === 'object') {
          this.users = response.results || [];
          this.totalCount = response.count || 0;
        } else {
          this.users = [];
          this.totalCount = 0;
        }
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading users:', error);
        this.toastService.error('Failed to load users');
        this.users = [];
        this.loading = false;
      }
    });
  }

  loadRoles(): void {
    this.userService.getAllRoles().subscribe({
      next: (response) => {
        // Handle both array response and paginated response
        if (Array.isArray(response)) {
          this.roles = response;
        } else if (response && typeof response === 'object' && 'results' in response) {
          this.roles = Array.isArray(response.results) ? response.results : [];
        } else {
          this.roles = [];
        }
      },
      error: (error) => {
        console.error('Error loading roles:', error);
        this.roles = [];
      }
    });
  }

  loadDepartments(): void {
    this.departmentService.getActiveDepartments().subscribe({
      next: (departments) => {
        this.departments = departments;
      },
      error: (error) => {
        console.error('Error loading departments:', error);
        this.departments = [];
      }
    });
  }

  openCreateModal(): void {
    this.isEditMode = false;
    this.selectedUserId = null;
    this.userForm.reset({
      is_admin: false,
      is_active: true
    });
    this.userForm.get('password')?.setValidators([Validators.required, Validators.minLength(PASSWORD_MIN_LENGTH), this.passwordStrengthValidator]);
    this.userForm.get('password_confirm')?.setValidators([Validators.required]);
    this.userForm.get('password')?.updateValueAndValidity();
    this.userForm.get('password_confirm')?.updateValueAndValidity();
    this.showModal = true;
    // Lock body scroll
    document.body.classList.add('modal-open');
  }

  openEditModal(user: User): void {
    this.isEditMode = true;
    this.selectedUserId = user.id;

    // Extract department ID from department object or string
    const departmentId = this.extractDepartmentId(user.department);

    // Clear password validators for edit mode
    this.userForm.get('password')?.clearValidators();
    this.userForm.get('password_confirm')?.clearValidators();
    this.userForm.get('password')?.updateValueAndValidity();
    this.userForm.get('password_confirm')?.updateValueAndValidity();

    // Patch form values
    this.userForm.patchValue({
      email: user.email || '',
      name: user.name || '',
      role: user.role?.id || null,
      department: departmentId || '',
      is_admin: user.is_admin ?? false,
      is_active: user.is_active ?? true,
      staff_id: user.staff_id || '',
      phone: user.phone || '',
      gender: user.gender || ''
    });

    this.showModal = true;
    document.body.classList.add('modal-open');
  }

  private extractDepartmentId(department: any): string {
    if (!department) {
      return '';
    }
    if (typeof department === 'string') {
      return department;
    }
    if (typeof department === 'object' && department.id) {
      return department.id;
    }
    return '';
  }

  closeModal(): void {
    this.showModal = false;
    this.userForm.reset();
    // Unlock body scroll
    document.body.classList.remove('modal-open');
  }

  ngOnDestroy(): void {
    // Ensure modal is closed and scroll unlocked when component is destroyed
    if (this.showModal) {
      document.body.classList.remove('modal-open');
    }
  }

  onSubmit(): void {
    if (this.userForm.invalid) {
      this.toastService.warning('Please fill in all required fields');
      Object.keys(this.userForm.controls).forEach(key => {
        const control = this.userForm.get(key);
        if (control?.invalid) {
          control.markAsTouched();
        }
      });
      return;
    }

    // Validate password match for new users
    if (!this.isEditMode) {
      const password = this.userForm.get('password')?.value;
      const passwordConfirm = this.userForm.get('password_confirm')?.value;
      if (password !== passwordConfirm) {
        this.toastService.error('Passwords do not match');
        return;
      }
    }

    this.submitting = true;
    const formData = { ...this.userForm.value };

    // Remove password fields if editing and they're empty
    if (this.isEditMode) {
      if (!formData.password) {
        delete formData.password;
        delete formData.password_confirm;
      }
      // Transform role to role_id for UserAdminUpdateSerializer
      if (formData.role) {
        formData.role_id = formData.role;
        delete formData.role;
      }
    }

    const request = this.isEditMode && this.selectedUserId
      ? this.userService.updateUser(this.selectedUserId, formData)
      : this.userService.createUser(formData);

    request.subscribe({
      next: () => {
        const action = this.isEditMode ? 'updated' : 'created';
        this.toastService.success(`User ${action} successfully`);
        this.closeModal();
        this.loadUsers();
        this.submitting = false;
      },
      error: (error) => {
        console.error('Error saving user:', error);
        this.toastService.error(error.error?.detail || 'Failed to save user');
        this.submitting = false;
      }
    });
  }

  confirmDeleteUser(user: User): void {
    this.userToDelete = user;

    this.modalService.open(ConfirmDeleteModalComponent, {
      title: 'Confirm Delete User',
      message: `Are you sure you want to delete user "${user.name}"?`,
      warningMessage: `This action cannot be undone. User "${user.email}" will be permanently removed from the system.`,
      confirmButtonText: 'Delete User'
    });

    // Get reference to the modal component
    const modalRef = (this.modalService as any).componentRef;
    if (modalRef) {
      // Subscribe to confirm event
      modalRef.instance.confirm.subscribe(() => {
        this.executeDeleteUser();
      });
    }
  }

  private executeDeleteUser(): void {
    if (!this.userToDelete) return;

    // Update the modal's isDeleting state
    const modalRef = (this.modalService as any).componentRef;
    if (modalRef) {
      modalRef.instance.isDeleting = true;
    }

    this.userService.deleteUser(this.userToDelete.id).subscribe({
      next: () => {
        this.toastService.success('User deleted successfully');
        this.modalService.close();
        this.userToDelete = null;
        this.loadUsers();
      },
      error: (error) => {
        console.error('Error deleting user:', error);
        this.toastService.error('Failed to delete user');
        if (modalRef) {
          modalRef.instance.isDeleting = false;
        }
      }
    });
  }

  toggleUserStatus(user: User): void {
    const action = user.is_active ? 'deactivate' : 'activate';
    this.confirmationService.confirm({
      title: `${action.charAt(0).toUpperCase() + action.slice(1)} User`,
      message: `Are you sure you want to ${action} user "${user.name}"?`,
      confirmText: action.charAt(0).toUpperCase() + action.slice(1),
      type: user.is_active ? 'warning' : 'success'
    }).subscribe(confirmed => {
      if (!confirmed) return;
      this.executeToggleUserStatus(user, action);
    });
  }

  private executeToggleUserStatus(user: User, action: string): void {
    this.userService.updateUser(user.id, { is_active: !user.is_active }).subscribe({
      next: () => {
        this.toastService.success(`User ${action}d successfully`);
        this.loadUsers();
      },
      error: (error) => {
        console.error('Error updating user status:', error);
        this.toastService.error('Failed to update user status');
      }
    });
  }

  onSearch(): void {
    this.currentPage = 1;
    this.loadUsers();
  }

  onFilterChange(): void {
    this.currentPage = 1;
    this.loadUsers();
  }

  clearFilters(): void {
    this.searchTerm = '';
    this.filterRole = null;
    this.filterDepartment = '';
    this.filterStatus = null;
    this.currentPage = 1;
    this.loadUsers();
  }

  nextPage(): void {
    if (this.currentPage * this.pageSize < this.totalCount) {
      this.currentPage++;
      this.loadUsers();
    }
  }

  previousPage(): void {
    if (this.currentPage > 1) {
      this.currentPage--;
      this.loadUsers();
    }
  }

  getRoleName(user: User): string {
    return user.role?.name || 'No Role';
  }

  getDepartmentName(user: User): string {
    const dept = user.department;
    if (!dept) {
      return 'N/A';
    }
    if (typeof dept === 'string') {
      return dept;
    }
    if (typeof dept === 'object' && dept !== null && 'name' in dept) {
      return (dept as any).name || 'N/A';
    }
    return 'N/A';
  }

  getStatusBadgeClass(user: User): string {
    return user.is_active ? 'bg-success' : 'bg-secondary';
  }

  getStatusText(user: User): string {
    return user.is_active ? 'Active' : 'Inactive';
  }

  isFieldInvalid(fieldName: string): boolean {
    const field = this.userForm.get(fieldName);
    return !!(field && field.invalid && field.touched);
  }

  getFieldError(fieldName: string): string {
    const field = this.userForm.get(fieldName);
    if (field?.errors) {
      if (field.errors['required']) return 'This field is required';
      if (field.errors['email']) return 'Invalid email format';
      if (field.errors['minlength']) return `Minimum length is ${field.errors['minlength'].requiredLength}`;
      if (field.errors['passwordMismatch']) return 'Passwords do not match';
      if (field.errors['passwordStrength']) {
        const errors = field.errors['passwordStrength'];
        if (errors.isCommonPattern) return 'Password is too common. Please choose a stronger password';
        if (!errors.hasUpperCase) return 'Password must contain at least one uppercase letter';
        if (!errors.hasLowerCase) return 'Password must contain at least one lowercase letter';
        if (!errors.hasNumber) return 'Password must contain at least one number';
        if (!errors.isLongEnough) return `Password must be at least ${PASSWORD_MIN_LENGTH} characters`;
        return 'Password must contain uppercase, lowercase, and number';
      }
    }
    return '';
  }

  /**
   * Custom validator for password strength
   * Requires: uppercase, lowercase, number, min PASSWORD_MIN_LENGTH chars
   * Checks for common password patterns
   */
  private passwordStrengthValidator(control: AbstractControl): ValidationErrors | null {
    const value = control.value;
    if (!value) return null;

    const hasUpperCase = /[A-Z]/.test(value);
    const hasLowerCase = /[a-z]/.test(value);
    const hasNumber = /[0-9]/.test(value);
    const isLongEnough = value.length >= PASSWORD_MIN_LENGTH;
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

    // Skip validation if both are empty (edit mode)
    if (!password && !confirmPassword) {
      return null;
    }

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
    const password = this.userForm.get('password')?.value || '';
    let strength = 0;

    if (password.length >= PASSWORD_MIN_LENGTH) strength++;
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
}
