import { Component, OnInit, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TmsApp_Core_Services_RolesService, TmsApp_Roles_Permission, TmsApp_Roles_RoleFormValues, TmsApp_Roles_RoleWithPermissions } from '../../../../core/services/roles.service';
import { ToastService } from '../../../../core/services/toast.service';

@Component({
  selector: 'app-role-form',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './role-form.component.html',
  styleUrls: ['./role-form.component.scss']
})
export class RoleFormComponent implements OnInit {
  @Input() editId: string | null = null;
  @Input() role: TmsApp_Roles_RoleWithPermissions | null = null;
  @Input() permissions: TmsApp_Roles_Permission[] = [];
  @Output() close = new EventEmitter<boolean>();

  isSaving = false;
  form: TmsApp_Roles_RoleFormValues = { name: '', description: '', permissionIds: [] };
  submitError = '';

  constructor(
    private rolesService: TmsApp_Core_Services_RolesService,
    private toast: ToastService
  ) {}

  ngOnInit(): void {
    if (this.role) {
      this.form = {
        name: this.role.name,
        description: this.role.description || '',
        permissionIds: this.role.permissionIds || []
      };
    }
  }

  togglePermission(id: string): void {
    const list = new Set(this.form.permissionIds || []);
    if (list.has(id)) {
      list.delete(id);
    } else {
      list.add(id);
    }
    this.form.permissionIds = Array.from(list);
  }

  cancelForm(): void {
    this.close.emit(false);
  }

  submitForm(): void {
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

    const operation = this.editId
      ? this.rolesService.updateRole(this.editId, this.form)
      : this.rolesService.createRole(this.form);

    operation.subscribe({
      next: () => {
        this.toast.success(this.editId ? 'Role updated successfully' : 'Role created successfully');
        this.isSaving = false;
        this.close.emit(true); // Emit true on success to signal a reload
      },
      error: (err) => {
        this.isSaving = false;
        if (err.error?.message) {
          this.submitError = err.error.message;
        } else {
          this.submitError = `Failed to save role: ${err.statusText || 'Unknown error'}`;
        }
        this.toast.error(this.submitError);
      }
    });
  }
}
