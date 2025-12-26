import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, FormsModule } from '@angular/forms';
import { UserService, User, Role } from '../../services/user.service';
import { ToastService } from '../../../../core/services/toast.service';

@Component({
  selector: 'app-user-admin',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, FormsModule],
  templateUrl: './user-admin.component.html',
  styleUrls: ['./user-admin.component.scss']
})
export class UserAdminComponent implements OnInit, OnDestroy {
  users: User[] = [];
  roles: Role[] = [];
  loading = false;
  showModal = false;
  isEditMode = false;
  selectedUserId: number | null = null;
  userForm!: FormGroup;
  submitting = false;

  // Filters
  searchTerm = '';
  filterRole: string | null = null;  // UUID
  filterDepartment = '';
  filterStatus: boolean | null = null;
  currentPage = 1;
  pageSize = 20;
  totalCount = 0;

  // Dropdown options
  departments = ['IT', 'HR', 'Finance', 'Operations', 'Sales', 'Marketing', 'Admin'];
  genders = [
    { value: 'Male', label: 'Male' },
    { value: 'Female', label: 'Female' },
    { value: 'Other', label: 'Other' }
  ];

  constructor(
    private fb: FormBuilder,
    private userService: UserService,
    private toastService: ToastService
  ) {}

  ngOnInit(): void {
    this.initializeForm();
    this.loadUsers();
    this.loadRoles();
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
        console.log('Roles API response:', response);
        console.log('Response type:', typeof response);
        console.log('Is array:', Array.isArray(response));

        // Handle both array response and paginated response
        if (Array.isArray(response)) {
          this.roles = response;
          console.log('Set roles from array:', this.roles);
        } else if (response && typeof response === 'object' && 'results' in response) {
          this.roles = Array.isArray(response.results) ? response.results : [];
          console.log('Set roles from paginated response:', this.roles);
        } else {
          console.warn('Unexpected roles response format:', response);
          this.roles = [];
        }

        console.log('Final roles value:', this.roles);
        console.log('Final roles is array:', Array.isArray(this.roles));
      },
      error: (error) => {
        console.error('Error loading roles:', error);
        this.roles = [];
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
    this.userForm.get('password')?.setValidators([Validators.required, Validators.minLength(8)]);
    this.userForm.get('password_confirm')?.setValidators([Validators.required]);
    this.showModal = true;
    // Lock body scroll
    document.body.classList.add('modal-open');
  }

  openEditModal(user: User): void {
    this.isEditMode = true;
    this.selectedUserId = user.id;
    this.userForm.patchValue({
      email: user.email,
      name: user.name,
      role: user.role?.id,
      department: user.department,
      is_admin: user.is_admin,
      is_active: user.is_active,
      staff_id: user.staff_id,
      phone: user.phone,
      gender: user.gender
    });
    this.userForm.get('password')?.clearValidators();
    this.userForm.get('password_confirm')?.clearValidators();
    this.showModal = true;
    // Lock body scroll
    document.body.classList.add('modal-open');
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

  deleteUser(user: User): void {
    if (!confirm(`Are you sure you want to delete user "${user.name}"?`)) return;

    this.userService.deleteUser(user.id).subscribe({
      next: () => {
        this.toastService.success('User deleted successfully');
        this.loadUsers();
      },
      error: (error) => {
        console.error('Error deleting user:', error);
        this.toastService.error('Failed to delete user');
      }
    });
  }

  toggleUserStatus(user: User): void {
    const action = user.is_active ? 'deactivate' : 'activate';
    if (!confirm(`Are you sure you want to ${action} user "${user.name}"?`)) return;

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
    }
    return '';
  }
}
