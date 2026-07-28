/* eslint-disable @typescript-eslint/no-explicit-any -- pre-existing loose typing against raw API responses, unrelated to this change */
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import {
  TmsApp_Core_Services_WorkflowsService,
  TmsApp_Workflows_WorkflowModuleWithSteps,
  TmsApp_Workflows_WorkflowStepFormValues,
  TmsApp_Workflows_WorkflowStep,
} from '../../../../core/services/workflows.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmationService } from '../../../../core/services/confirmation.service';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';

@Component({
  selector: 'tmsapp-admin-systemsettings-workflow-configuration',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, LoadingSpinnerComponent],
  templateUrl: './workflow-configuration.component.html',
  styleUrls: ['./workflow-configuration.component.scss'],
})
export class TmsApp_Admin_SystemSettings_WorkflowConfigurationComponent implements OnInit {
  isLoading = true;
  isSaving = false;
  modules: TmsApp_Workflows_WorkflowModuleWithSteps[] = [];

  showForm = false;
  currentModuleId: string | null = null;
  editStepId: string | null = null;
  form: TmsApp_Workflows_WorkflowStepFormValues = {
    name: '',
    approverRoleId: '',
    order: null,
  };

  constructor(
    private workflowsService: TmsApp_Core_Services_WorkflowsService,
    private toast: ToastService,
    private confirmationService: ConfirmationService
  ) {}

  ngOnInit(): void {
    this.loadModules();
  }

  private unwrapModules(resp: any): TmsApp_Workflows_WorkflowModuleWithSteps[] {
    if (resp && Array.isArray(resp)) return resp;
    if (resp && Array.isArray(resp.data)) return resp.data;
    return [];
  }

  loadModules(): void {
    this.isLoading = true;
    this.workflowsService.getModulesWithSteps().subscribe({
      next: resp => {
        this.modules = this.unwrapModules(resp);
      },
      error: () => this.toast.error('Failed to load workflows'),
      complete: () => (this.isLoading = false),
    });
  }

  openCreate(moduleId: string): void {
    this.showForm = true;
    this.currentModuleId = moduleId;
    this.editStepId = null;
    this.form = { name: '', approverRoleId: '', order: null };
  }

  openEdit(moduleId: string, step: TmsApp_Workflows_WorkflowStep): void {
    this.showForm = true;
    this.currentModuleId = moduleId;
    this.editStepId = step.id;
    this.form = {
      name: step.name,
      approverRoleId: step.approverRoleId || '',
      order: step.order || null,
    };
  }

  cancelForm(): void {
    this.showForm = false;
    this.currentModuleId = null;
    this.editStepId = null;
  }

  submitForm(): void {
    if (!this.currentModuleId) return;
    this.isSaving = true;

    const op = this.editStepId
      ? this.workflowsService.updateStep(this.editStepId, this.form)
      : this.workflowsService.createStep(this.currentModuleId, this.form);

    op.subscribe({
      next: () => {
        this.toast.success(this.editStepId ? 'Workflow step updated' : 'Workflow step created');
        this.showForm = false;
        this.currentModuleId = null;
        this.editStepId = null;
        this.loadModules();
      },
      error: () => this.toast.error('Failed to save workflow step'),
      complete: () => (this.isSaving = false),
    });
  }

  deleteStep(step: TmsApp_Workflows_WorkflowStep): void {
    this.confirmationService.confirmDelete('this workflow step').subscribe(confirmed => {
      if (!confirmed) return;
      this.workflowsService.deleteStep(step.id).subscribe({
        next: () => {
          this.toast.success('Workflow step deleted');
          this.loadModules();
        },
        error: () => this.toast.error('Failed to delete workflow step'),
      });
    });
  }
}
