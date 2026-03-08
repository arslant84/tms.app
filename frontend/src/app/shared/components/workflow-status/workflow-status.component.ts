import { Component, Input, OnInit, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { WorkflowInstance, WorkflowStepExecution } from '../../../core/models/workflow.models';
import { WorkflowService } from '../../../core/services/workflow.service';
import { DateUtilsService } from '../../../core/utils/date-utils.service';
import { LoadingSpinnerComponent } from '../../shared/components/loading-spinner/loading-spinner.component';

@Component({
  selector: 'app-workflow-status',
  standalone: true,
  imports: [CommonModule, LoadingSpinnerComponent],
  templateUrl: './workflow-status.component.html',
  styleUrls: ['./workflow-status.component.scss']
})
export class WorkflowStatusComponent implements OnInit, OnChanges {
  @Input() workflowInstanceId?: string;
  @Input() workflowInstance?: WorkflowInstance;
  @Input() compact: boolean = false; // Compact view for lists

  workflow: WorkflowInstance | null = null;
  loading: boolean = false;
  error: string = '';

  constructor(
    public workflowService: WorkflowService,
    public dateUtils: DateUtilsService
  ) {}

  ngOnInit(): void {
    if (this.workflowInstance) {
      this.workflow = this.workflowInstance;
    } else if (this.workflowInstanceId) {
      this.loadWorkflow();
    }
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['workflowInstanceId'] && !changes['workflowInstanceId'].firstChange) {
      if (this.workflowInstanceId) {
        this.loadWorkflow();
      }
    }
    if (changes['workflowInstance'] && !changes['workflowInstance'].firstChange) {
      this.workflow = this.workflowInstance || null;
    }
  }

  loadWorkflow(): void {
    if (!this.workflowInstanceId) return;

    this.loading = true;
    this.error = '';

    this.workflowService.getInstance(this.workflowInstanceId).subscribe({
      next: (workflow) => {
        this.workflow = workflow;
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load workflow status';
        this.loading = false;
        console.error('Error loading workflow:', err);
      }
    });
  }

  getStepClass(step: WorkflowStepExecution): string {
    if (step.status === 'approved') return 'step-completed';
    if (step.status === 'rejected') return 'step-rejected';
    if (step.status === 'skipped') return 'step-skipped';
    if (step.status === 'pending' && this.isCurrentStep(step)) return 'step-current';
    return 'step-pending';
  }

  getStepIcon(step: WorkflowStepExecution): string {
    if (step.status === 'approved') return '✓';
    if (step.status === 'rejected') return '✗';
    if (step.status === 'skipped') return '⊘';
    if (step.status === 'pending' && this.isCurrentStep(step)) return '⧗';
    return '○';
  }

  isCurrentStep(step: WorkflowStepExecution): boolean {
    if (!this.workflow || !step.workflow_step_detail) return false;
    return step.workflow_step_detail.step_order === this.workflow.current_step_order &&
           step.status === 'pending';
  }

  getStatusClass(): string {
    if (!this.workflow) return '';
    return this.workflowService.getStatusClass(this.workflow.status);
  }

  getStepStatusBadge(step: WorkflowStepExecution): string {
    return this.workflowService.getStepStatusClass(step.status);
  }

  formatUserName(step: WorkflowStepExecution): string {
    if (step.actioned_by_user) {
      return this.workflowService.formatUserName(step.actioned_by_user);
    }
    if (step.assigned_to_user) {
      return this.workflowService.formatUserName(step.assigned_to_user);
    }
    if (step.workflow_step_detail?.approver_role) {
      return step.workflow_step_detail.approver_role;
    }
    return 'Unassigned';
  }

  getDelegatedUserName(step: WorkflowStepExecution): string {
    if (step.delegations && step.delegations.length > 0) {
      const delegation = step.delegations[0];
      if (delegation.delegated_to_user) {
        return this.workflowService.formatUserName(delegation.delegated_to_user);
      }
    }
    return 'Unknown';
  }

  getTimeRemaining(step: WorkflowStepExecution): string {
    if (step.status !== 'pending') return '';
    return this.workflowService.getTimeRemaining(step.sla_due_date);
  }

  isOverdue(step: WorkflowStepExecution): boolean {
    return this.workflowService.isStepOverdue(step);
  }

  get progressPercentage(): number {
    return this.workflow?.progress_percentage || 0;
  }

  get sortedSteps(): WorkflowStepExecution[] {
    if (!this.workflow?.step_executions) return [];
    return [...this.workflow.step_executions].sort((a, b) => {
      const orderA = a.workflow_step_detail?.step_order || 0;
      const orderB = b.workflow_step_detail?.step_order || 0;
      return orderA - orderB;
    });
  }
}
