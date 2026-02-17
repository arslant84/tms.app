import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Router } from '@angular/router';
import { DepartmentService, DepartmentCreatePayload, DepartmentUpdatePayload } from '../../../../core/services/department.service';
import { ToastService } from '../../../../core/services/toast.service';
import { RbacService } from '../../../../core/services/rbac.service';
import { Permission } from '../../../../core/models/permission.models';
import { Department } from '../../../../core/models/user.model';

@Component({
  selector: 'app-department-management',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './department-management.component.html',
  styleUrls: ['./department-management.component.scss']
})
export class DepartmentManagementComponent implements OnInit, OnDestroy {
  isLoading = true;
  isSaving = false;
  departments: Department[] = [];

  // Form state
  showForm = false;
  editingDepartment: Department | null = null;
  formData: DepartmentCreatePayload = {
    name: '',
    code: '',
    description: '',
    is_active: true
  };

  // Delete confirmation
  showDeleteConfirm = false;
  departmentToDelete: Department | null = null;

  constructor(
    private departmentService: DepartmentService,
    private toast: ToastService,
    private rbacService: RbacService,
    private router: Router
  ) {}

  ngOnInit(): void {
    // Check if user has permission to manage users (departments are related to user management)
    if (!this.hasManageUsersPermission) {
      this.toast.error('You do not have permission to manage departments.');
      this.isLoading = false;
      setTimeout(() => {
        this.router.navigate(['/dashboard']);
      }, 2000);
      return;
    }

    this.loadDepartments();
  }

  get hasManageUsersPermission(): boolean {
    return this.rbacService.hasAnyPermission([
      Permission.MANAGE_USERS,
      Permission.SYSTEM_ADMIN
    ]);
  }

  loadDepartments(): void {
    this.isLoading = true;
    this.departmentService.getDepartments().subscribe({
      next: (departments) => {
        this.departments = departments;
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Error loading departments:', err);
        if (err.status === 401) {
          this.toast.error('Session expired. Please login again.');
          setTimeout(() => this.router.navigate(['/auth/login']), 1500);
        } else if (err.status === 403) {
          this.toast.error('Access Denied: You need administrator privileges.');
          setTimeout(() => this.router.navigate(['/dashboard']), 2000);
        } else {
          this.toast.error('Failed to load departments');
        }
        this.isLoading = false;
      }
    });
  }

  openCreate(): void {
    this.editingDepartment = null;
    this.formData = {
      name: '',
      code: '',
      description: '',
      is_active: true
    };
    this.showForm = true;
  }

  openEdit(department: Department): void {
    this.editingDepartment = department;
    this.formData = {
      name: department.name,
      code: department.code || '',
      description: department.description || '',
      is_active: department.is_active
    };
    this.showForm = true;
  }

  cancelForm(): void {
    this.showForm = false;
    this.editingDepartment = null;
    this.formData = {
      name: '',
      code: '',
      description: '',
      is_active: true
    };
  }

  saveForm(): void {
    if (!this.formData.name.trim()) {
      this.toast.error('Department name is required');
      return;
    }

    this.isSaving = true;

    if (this.editingDepartment) {
      // Update existing
      const updateData: DepartmentUpdatePayload = {
        name: this.formData.name.trim(),
        code: this.formData.code?.trim() || undefined,
        description: this.formData.description?.trim() || undefined,
        is_active: this.formData.is_active
      };

      this.departmentService.updateDepartment(this.editingDepartment.id, updateData).subscribe({
        next: () => {
          this.toast.success('Department updated successfully');
          this.cancelForm();
          this.loadDepartments();
        },
        error: (err) => {
          console.error('Error updating department:', err);
          if (err.error?.name) {
            this.toast.error(err.error.name[0] || 'A department with this name already exists');
          } else if (err.error?.code) {
            this.toast.error(err.error.code[0] || 'A department with this code already exists');
          } else {
            this.toast.error('Failed to update department');
          }
        },
        complete: () => {
          this.isSaving = false;
        }
      });
    } else {
      // Create new
      const createData: DepartmentCreatePayload = {
        name: this.formData.name.trim(),
        code: this.formData.code?.trim() || undefined,
        description: this.formData.description?.trim() || undefined,
        is_active: this.formData.is_active
      };

      this.departmentService.createDepartment(createData).subscribe({
        next: () => {
          this.toast.success('Department created successfully');
          this.cancelForm();
          this.loadDepartments();
        },
        error: (err) => {
          console.error('Error creating department:', err);
          if (err.error?.name) {
            this.toast.error(err.error.name[0] || 'A department with this name already exists');
          } else if (err.error?.code) {
            this.toast.error(err.error.code[0] || 'A department with this code already exists');
          } else {
            this.toast.error('Failed to create department');
          }
        },
        complete: () => {
          this.isSaving = false;
        }
      });
    }
  }

  confirmDelete(department: Department): void {
    this.departmentToDelete = department;
    this.showDeleteConfirm = true;
    document.body.classList.add('modal-open');
  }

  cancelDelete(): void {
    this.departmentToDelete = null;
    this.showDeleteConfirm = false;
    document.body.classList.remove('modal-open');
  }

  executeDelete(): void {
    if (!this.departmentToDelete) return;

    this.isSaving = true;
    this.departmentService.deleteDepartment(this.departmentToDelete.id).subscribe({
      next: () => {
        this.toast.success('Department deleted successfully');
        this.showDeleteConfirm = false;
        this.departmentToDelete = null;
        document.body.classList.remove('modal-open');
        this.loadDepartments();
      },
      error: (err) => {
        console.error('Error deleting department:', err);
        if (err.error?.message) {
          this.toast.error(err.error.message);
        } else {
          this.toast.error('Failed to delete department. It may have users assigned.');
        }
      },
      complete: () => {
        this.isSaving = false;
      }
    });
  }

  ngOnDestroy(): void {
    if (this.showDeleteConfirm) {
      document.body.classList.remove('modal-open');
    }
  }
}
