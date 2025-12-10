import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Router } from '@angular/router';
import { TmsApp_Core_Services_RolesService, TmsApp_Roles_RoleWithPermissions, TmsApp_Roles_Permission, TmsApp_Roles_RoleFormValues } from '../../../../core/services/roles.service';
import { ToastService } from '../../../../core/services/toast.service';
import { RbacService } from '../../../../core/services/rbac.service';
import { Permission } from '../../../../core/models/permission.models';

@Component({
  selector: 'tmsapp-admin-systemsettings-role-management',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './role-management.component.html',
  styleUrls: ['./role-management.component.scss']
})
export class TmsApp_Admin_SystemSettings_RoleManagementComponent implements OnInit {
  isLoading = true;
  isSaving = false;
  roles: TmsApp_Roles_RoleWithPermissions[] = [];
  permissions: TmsApp_Roles_Permission[] = [];

  showForm = false;
  editId: string | null = null;
  form: TmsApp_Roles_RoleFormValues = { name: '', description: '', permissionIds: [] };
  submitError = '';

  showDeleteConfirm = false;
  roleToDelete: TmsApp_Roles_RoleWithPermissions | null = null;

  constructor(
    private rolesService: TmsApp_Core_Services_RolesService,
    private toast: ToastService,
    private rbacService: RbacService,
    private router: Router
  ) {}

  ngOnInit(): void {
    // Debug logging
    const currentUser = this.rbacService['authService'].getCurrentUser();
    console.log('=== Role Management Component Init ===');
    console.log('Current user:', currentUser);
    console.log('User role:', currentUser?.role);
    console.log('Role name:', typeof currentUser?.role === 'object' ? currentUser?.role?.name : currentUser?.role);
    console.log('User permissions:', currentUser?.permissions);
    console.log('Has manage_roles permission:', currentUser?.permissions?.includes('manage_roles'));
    console.log('Has system_admin permission:', currentUser?.permissions?.includes('system_admin'));
    console.log('Is admin:', currentUser?.is_admin);
    console.log('hasManageRolesPermission check result:', this.hasManageRolesPermission);

    // Check if user has permission to manage roles
    if (!this.hasManageRolesPermission) {
      console.error('❌ Permission check failed! Redirecting to dashboard...');
      this.toast.error('You do not have permission to manage roles. This feature requires system administrator access.');
      this.isLoading = false;
      // Redirect to dashboard after showing error
      setTimeout(() => {
        this.router.navigate(['/dashboard']);
      }, 2000);
      return;
    }

    console.log('✅ Permission check passed! Loading data...');
    this.loadData();
  }

  get hasManageRolesPermission(): boolean {
    return this.rbacService.hasAnyPermission([
      Permission.MANAGE_ROLES,
      Permission.SYSTEM_ADMIN
    ]);
  }

  loadData(): void {
    this.isLoading = true;
    Promise.all([
      this.rolesService.getRoles().toPromise(),
      this.rolesService.getPermissions().toPromise()
    ])
      .then(([roles, perms]) => {
        this.roles = roles || [];
        this.permissions = perms || [];
        console.log('Loaded roles:', this.roles);
        console.log('Loaded permissions:', this.permissions);

        if (this.permissions.length === 0) {
          this.toast.error('No permissions available in the system. Please contact your administrator.');
        }
      })
      .catch((err) => {
        console.error('Error loading roles/permissions:', err);

        if (err.status === 401) {
          this.toast.error('Session expired. Please login again.');
          setTimeout(() => this.router.navigate(['/auth/login']), 1500);
        } else if (err.status === 403) {
          this.toast.error('Access Denied: You need System Administrator privileges. Your account is not authorized to manage roles and permissions.');
          setTimeout(() => this.router.navigate(['/dashboard']), 2000);
        } else {
          this.toast.error(`Failed to load data: ${err.statusText || 'Unknown error'}. Please refresh the page or contact support.`);
        }
      })
      .finally(() => {
        this.isLoading = false;
      });
  }

  openCreate(): void {
    this.showForm = true;
    this.editId = null;
    this.form = { name: '', description: '', permissionIds: [] };
    this.submitError = '';
  }

  openEdit(role: TmsApp_Roles_RoleWithPermissions): void {
    this.showForm = true;
    this.editId = role.id;
    this.form = {
      name: role.name,
      description: role.description || '',
      permissionIds: role.permissionIds || []
    };
    this.submitError = '';
  }

  cancelForm(): void {
    this.showForm = false;
    this.editId = null;
    this.submitError = '';
  }

  togglePermission(id: string): void {
    const list = new Set(this.form.permissionIds || []);
    if (list.has(id)) list.delete(id); else list.add(id);
    this.form.permissionIds = Array.from(list);
  }

  submitForm(): void {
    // Validate form
    if (!this.form.name || !this.form.name.trim()) {
      this.submitError = 'Role name is required';
      return;
    }

    if (!this.form.permissionIds || this.form.permissionIds.length === 0) {
      this.submitError = 'At least one permission must be selected';
      return;
    }

    this.isSaving = true;
    this.submitError = '';

    console.log('Submitting role form:', this.form);

    const op = this.editId
      ? this.rolesService.updateRole(this.editId, this.form)
      : this.rolesService.createRole(this.form);

    op.subscribe({
      next: (response) => {
        console.log('Role saved successfully:', response);
        this.toast.success(this.editId ? 'Role updated successfully' : 'Role created successfully');
        this.showForm = false;
        this.editId = null;
        this.form = { name: '', description: '', permissionIds: [] };
        this.loadData();
      },
      error: (err) => {
        console.error('Error saving role:', err);

        if (err.status === 401) {
          this.submitError = 'Unauthorized. Please login again.';
        } else if (err.status === 403) {
          this.submitError = 'You do not have permission to perform this action. Admin access required.';
        } else if (err.status === 400) {
          this.submitError = err.error?.message || 'Invalid form data. Please check your input.';
        } else if (err.error && typeof err.error === 'string') {
          this.submitError = err.error;
        } else if (err.error && err.error.message) {
          this.submitError = err.error.message;
        } else {
          this.submitError = `Failed to save role: ${err.statusText || 'Unknown error'}`;
        }

        this.toast.error(this.submitError);
      },
      complete: () => {
        this.isSaving = false;
      }
    });
  }

  confirmDelete(role: TmsApp_Roles_RoleWithPermissions): void {
    this.roleToDelete = role;
    this.showDeleteConfirm = true;
  }

  cancelDelete(): void {
    this.roleToDelete = null;
    this.showDeleteConfirm = false;
  }

  executeDelete(): void {
    if (!this.roleToDelete) return;

    this.isSaving = true;
    this.rolesService.deleteRole(this.roleToDelete.id).subscribe({
      next: () => {
        this.toast.success('Role deleted successfully');
        this.showDeleteConfirm = false;
        this.roleToDelete = null;
        this.loadData();
      },
      error: (err) => {
        this.toast.error('Failed to delete role');
        console.error(err);
      },
      complete: () => {
        this.isSaving = false;
      }
    });
  }

  getPermissionNames(permissionIds: string[]): string {
    if (!permissionIds || permissionIds.length === 0) return 'None';

    const names = permissionIds
      .map(id => {
        const perm = this.permissions.find(p => p.id === id);
        return perm ? perm.name : id.substring(0, 8);
      })
      .slice(0, 3);

    const remaining = permissionIds.length - 3;
    return remaining > 0 ? `${names.join(', ')}, +${remaining} more` : names.join(', ');
  }
}
