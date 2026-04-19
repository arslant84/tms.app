import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TmsApp_Core_Services_RolesService, TmsApp_Roles_RoleWithPermissions } from '../../../../core/services/roles.service';
import { ToastService } from '../../../../core/services/toast.service';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../../environments/environment';
import { WorkflowStepNotificationConfig } from '../../../../core/models/workflow.models';
import { StepNotificationConfigComponent } from '../step-notification-config/step-notification-config.component';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';

interface WorkflowStepConfig {
  order: number;
  roleId: string;
  roleName?: string;
  escalationHours: number;
  slaHours: number;
  notification_configs?: WorkflowStepNotificationConfig[];
}

interface ModuleWorkflowConfig {
  module: string;
  moduleName: string;
  steps: WorkflowStepConfig[];
}

@Component({
  selector: 'app-enhanced-workflow-config',
  standalone: true,
  imports: [CommonModule, FormsModule, StepNotificationConfigComponent, LoadingSpinnerComponent],
  templateUrl: './enhanced-workflow-config.component.html',
  styleUrls: ['./enhanced-workflow-config.component.scss']
})
export class EnhancedWorkflowConfigComponent implements OnInit {
  // Available modules
  modules = [
    { value: 'travelrequest', label: 'Travel Service Request (TSR)' },
    { value: 'transportrequest', label: 'Transport Request' },
    { value: 'visaapplication', label: 'Visa Application' },
    { value: 'accommodation', label: 'Accommodation Request' },
    { value: 'combinedrequest', label: 'Combined Request (TSR + Transport + Accommodation + Visa)' }
  ];

  // Available roles
  availableRoles: TmsApp_Roles_RoleWithPermissions[] = [];

  // Current configuration
  selectedModule = '';
  numberOfSteps = 3;
  workflowName = '';
  workflowDescription = '';
  steps: WorkflowStepConfig[] = [];

  // State management
  isLoading = false;
  isSaving = false;
  existingWorkflows: any[] = [];
  editingWorkflowId: string | null = null;
  showStepsConfiguration = false;
  workflowToDelete: { id: string; name: string } | null = null;

  constructor(
    private rolesService: TmsApp_Core_Services_RolesService,
    private toast: ToastService,
    private http: HttpClient
  ) {}

  // Get available modules (excluding those with existing workflows)
  get availableModules() {
    if (this.editingWorkflowId) {
      // When editing, allow the current module to be shown
      return this.modules;
    }

    // Filter out modules that already have workflows
    const occupiedModules = this.existingWorkflows.map(w => w.entity_type);
    return this.modules.filter(m => !occupiedModules.includes(m.value));
  }

  ngOnInit(): void {
    this.loadRoles();
    this.loadExistingWorkflows();
    this.initializeSteps();
  }

  loadRoles(): void {
    this.rolesService.getRoles().subscribe({
      next: (roles) => {
        this.availableRoles = roles;
      },
      error: () => this.toast.error('Failed to load roles')
    });
  }

  loadExistingWorkflows(): void {
    this.isLoading = true;
    this.http.get<any>(`${environment.apiUrl}/workflows/templates/`).subscribe({
      next: (response) => {
        // Handle paginated response
        this.existingWorkflows = response.results || response;
        this.isLoading = false;
      },
      error: () => {
        this.toast.error('Failed to load existing workflows');
        this.isLoading = false;
      }
    });
  }

  onModuleChange(): void {
    const module = this.modules.find(m => m.value === this.selectedModule);
    if (module) {
      this.workflowName = `${module.label} Approval Workflow`;
      this.workflowDescription = `Multi-step approval workflow for ${module.label}`;
      this.showStepsConfiguration = true; // Show steps configuration when module is selected
    } else {
      this.showStepsConfiguration = false;
    }
  }

  onStepsCountChange(): void {
    // Clamp between 1 and 10
    if (this.numberOfSteps < 1) this.numberOfSteps = 1;
    if (this.numberOfSteps > 10) this.numberOfSteps = 10;

    this.initializeSteps();

    // Show steps configuration if we have a selected module
    if (this.selectedModule) {
      this.showStepsConfiguration = true;
    }
  }

  initializeSteps(): void {
    this.steps = [];
    for (let i = 1; i <= this.numberOfSteps; i++) {
      this.steps.push({
        order: i,
        roleId: '',
        escalationHours: 48,
        slaHours: 72
      });
    }
  }

  getRoleNameById(roleId: string): string {
    const role = this.availableRoles.find(r => r.id === roleId);
    return role ? role.name : 'Select Role';
  }

  validateForm(): boolean {
    if (!this.selectedModule) {
      this.toast.error('Please select a module');
      return false;
    }

    if (!this.workflowName.trim()) {
      this.toast.error('Please enter a workflow name');
      return false;
    }

    if (this.steps.length === 0) {
      this.toast.error('Please configure at least one approval step');
      return false;
    }

    for (let i = 0; i < this.steps.length; i++) {
      if (!this.steps[i].roleId) {
        this.toast.error(`Please select a role for Step ${i + 1}`);
        return false;
      }
    }

    return true;
  }

  saveWorkflow(): void {
    if (!this.validateForm()) {
      return;
    }

    this.isSaving = true;

    // Prepare workflow data
    const workflowData = {
      name: this.workflowName,
      description: this.workflowDescription,
      entity_type: this.selectedModule,
      is_active: true,
      allow_parallel_steps: false,
      auto_approve_on_condition: false,
      steps: this.steps.map(step => ({
        step_order: step.order,
        step_name: `Step ${step.order}: ${this.getRoleNameById(step.roleId)} Approval`,
        step_description: `Approval by ${this.getRoleNameById(step.roleId)}`,
        approver_role: step.roleId,
        is_required: true,
        can_skip: false,
        requires_comments: false,
        sla_hours: step.slaHours,
        escalation_hours: step.escalationHours,
        notification_configs: step.notification_configs || []
      }))
    };

    const request = this.editingWorkflowId
      ? this.http.put(`${environment.apiUrl}/workflows/templates/${this.editingWorkflowId}/`, workflowData)
      : this.http.post(`${environment.apiUrl}/workflows/templates/`, workflowData);

    request.subscribe({
      next: () => {
        this.toast.success(this.editingWorkflowId ? 'Workflow updated successfully' : 'Workflow created successfully');
        this.resetForm();
        this.loadExistingWorkflows();
      },
      error: (error) => {
        console.error('Error saving workflow:', error);
        this.toast.error('Failed to save workflow');
        this.isSaving = false;
      },
      complete: () => this.isSaving = false
    });
  }

  editWorkflow(workflow: any): void {
    // Fetch full workflow details with steps
    this.http.get<any>(`${environment.apiUrl}/workflows/templates/${workflow.id}/`).subscribe({
      next: (fullWorkflow) => {
        this.editingWorkflowId = fullWorkflow.id;
        this.selectedModule = fullWorkflow.entity_type;
        this.workflowName = fullWorkflow.name;
        this.workflowDescription = fullWorkflow.description || '';
        this.numberOfSteps = fullWorkflow.steps?.length || 3;

        this.steps = (fullWorkflow.steps || []).map((step: any) => ({
          order: step.step_order,
          roleId: step.approver_role || '',
          escalationHours: step.escalation_hours || 48,
          slaHours: step.sla_hours || 72,
          notification_configs: step.notification_configs || []
        }));

        // Show steps configuration when editing
        this.showStepsConfiguration = true;

        // Scroll to form
        window.scrollTo({ top: 0, behavior: 'smooth' });
      },
      error: () => {
        this.toast.error('Failed to load workflow details');
      }
    });
  }

  deleteWorkflow(workflow: any): void {
    // Show confirmation by setting the workflow to delete
    this.workflowToDelete = {
      id: workflow.id,
      name: workflow.name
    };
  }

  confirmDelete(): void {
    if (!this.workflowToDelete) return;

    this.http.delete(`${environment.apiUrl}/workflows/templates/${this.workflowToDelete.id}/`).subscribe({
      next: () => {
        this.toast.success('Workflow deleted successfully');
        this.workflowToDelete = null;
        this.loadExistingWorkflows();
      },
      error: () => {
        this.toast.error('Failed to delete workflow');
        this.workflowToDelete = null;
      }
    });
  }

  cancelDelete(): void {
    this.workflowToDelete = null;
  }

  toggleWorkflowStatus(workflow: any): void {
    // First fetch the full workflow details
    this.http.get<any>(`${environment.apiUrl}/workflows/templates/${workflow.id}/`).subscribe({
      next: (fullWorkflow) => {
        const updatedData = {
          name: fullWorkflow.name,
          description: fullWorkflow.description,
          entity_type: fullWorkflow.entity_type,
          is_active: !fullWorkflow.is_active,
          allow_parallel_steps: fullWorkflow.allow_parallel_steps,
          auto_approve_on_condition: fullWorkflow.auto_approve_on_condition,
          steps: fullWorkflow.steps.map((step: any) => ({
            step_order: step.step_order,
            step_name: step.step_name,
            step_description: step.step_description,
            approver_role: step.approver_role,
            is_required: step.is_required,
            can_skip: step.can_skip,
            requires_comments: step.requires_comments,
            sla_hours: step.sla_hours,
            escalation_hours: step.escalation_hours
          }))
        };

        this.http.put(`${environment.apiUrl}/workflows/templates/${workflow.id}/`, updatedData).subscribe({
          next: () => {
            this.toast.success(`Workflow ${workflow.is_active ? 'deactivated' : 'activated'} successfully`);
            this.loadExistingWorkflows();
          },
          error: () => this.toast.error('Failed to update workflow status')
        });
      },
      error: () => this.toast.error('Failed to load workflow details')
    });
  }

  resetForm(): void {
    this.selectedModule = '';
    this.numberOfSteps = 3;
    this.workflowName = '';
    this.workflowDescription = '';
    this.editingWorkflowId = null;
    this.showStepsConfiguration = false; // Hide steps configuration when resetting
    this.initializeSteps();
  }

  getModuleName(entityType: string): string {
    const module = this.modules.find(m => m.value === entityType);
    return module ? module.label : entityType;
  }
}
