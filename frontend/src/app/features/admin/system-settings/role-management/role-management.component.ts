import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { TmsApp_Core_Services_RolesService, TmsApp_Roles_RoleWithPermissions, TmsApp_Roles_Permission, TmsApp_Roles_RoleFormValues } from '../../../../core/services/roles.service';
import { ToastService } from '../../../../core/services/toast.service';

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

  constructor(
    private rolesService: TmsApp_Core_Services_RolesService,
    private toast: ToastService
  ) {}

  ngOnInit(): void {
    this.loadData();
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
      })
      .catch(() => {
        this.toast.error('Failed to load roles or permissions');
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
    this.isSaving = true;
    const op = this.editId
      ? this.rolesService.updateRole(this.editId, this.form)
      : this.rolesService.createRole(this.form);

    op.subscribe({
      next: () => {
        this.toast.success(this.editId ? 'Role updated' : 'Role created');
        this.showForm = false;
        this.editId = null;
        this.loadData();
      },
      error: (err) => {
        this.submitError = 'Failed to save role';
        console.error(err);
      },
      complete: () => {
        this.isSaving = false;
      }
    });
  }

  deleteRole(role: TmsApp_Roles_RoleWithPermissions): void {
    if (!confirm('Delete this role')) return;
    this.rolesService.deleteRole(role.id).subscribe({
      next: () => {
        this.toast.success('Role deleted');
        this.loadData();
      },
      error: () => this.toast.error('Failed to delete role')
    });
  }
}
