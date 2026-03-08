import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Router } from '@angular/router';
import { TmsApp_Core_Services_RolesService, TmsApp_Roles_RoleWithPermissions, TmsApp_Roles_Permission } from '../../../../core/services/roles.service';
import { RoleFormComponent } from '../role-form/role-form.component';
import { ToastService } from '../../../../core/services/toast.service';
import { RbacService } from '../../../../core/services/rbac.service';
import { Permission } from '../../../../core/models/permission.models';
import { ModalService } from '../../../../core/services/modal.service';
import { ConfirmDeleteModalComponent } from '../../../../core/components/confirm-delete-modal/confirm-delete-modal.component';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';

@Component({
  selector: 'tmsapp-admin-systemsettings-role-management',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, LoadingSpinnerComponent],
  templateUrl: './role-management.component.html',
  styleUrls: ['./role-management.component.scss']
})
export class TmsApp_Admin_SystemSettings_RoleManagementComponent implements OnInit, OnDestroy {
  isLoading = true;
  isSaving = false;
  roles: TmsApp_Roles_RoleWithPermissions[] = [];
  permissions: TmsApp_Roles_Permission[] = [];

  private roleToDelete: TmsApp_Roles_RoleWithPermissions | null = null;

  constructor(
    private rolesService: TmsApp_Core_Services_RolesService,
    private toast: ToastService,
    private rbacService: RbacService,
    private router: Router,
    private modalService: ModalService
  ) {}

  ngOnInit(): void {
    // Check if user has permission to manage roles
    if (!this.hasManageRolesPermission) {
      this.toast.error('You do not have permission to manage roles. This feature requires system administrator access.');
      this.isLoading = false;
      // Redirect to dashboard after showing error
      setTimeout(() => {
        this.router.navigate(['/dashboard']);
      }, 2000);
      return;
    }

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
    this.modalService.open(RoleFormComponent, { permissions: this.permissions });
    this.modalService.afterClosed.subscribe(result => {
      if (result) {
        this.loadData();
      }
    });
  }

  openEdit(role: TmsApp_Roles_RoleWithPermissions): void {
    this.modalService.open(RoleFormComponent, { 
      editId: role.id, 
      role: role, 
      permissions: this.permissions 
    });
    this.modalService.afterClosed.subscribe(result => {
      if (result) {
        this.loadData();
      }
    });
  }


  confirmDelete(role: TmsApp_Roles_RoleWithPermissions): void {
    this.roleToDelete = role;

    this.modalService.open(ConfirmDeleteModalComponent, {
      title: 'Confirm Delete',
      message: 'Are you sure you want to delete this role?',
      warningMessage: `This action cannot be undone. Role "${role.name}" will be permanently removed. Ensure no users are currently assigned this role before deleting.`,
      confirmButtonText: 'Delete Role'
    });

    // Get reference to the modal component
    const modalRef = (this.modalService as any).componentRef;
    if (modalRef) {
      // Subscribe to confirm event
      modalRef.instance.confirm.subscribe(() => {
        this.executeDelete();
      });
    }
  }

  executeDelete(): void {
    if (!this.roleToDelete) return;

    // Update the modal's isDeleting state
    const modalRef = (this.modalService as any).componentRef;
    if (modalRef) {
      modalRef.instance.isDeleting = true;
    }

    this.rolesService.deleteRole(this.roleToDelete.id).subscribe({
      next: () => {
        this.toast.success('Role deleted successfully');
        this.modalService.close();
        this.roleToDelete = null;
        this.loadData();
      },
      error: (err) => {
        this.toast.error('Failed to delete role');
        console.error(err);
        if (modalRef) {
          modalRef.instance.isDeleting = false;
        }
      }
    });
  }

  ngOnDestroy(): void {
    // Component cleanup
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
