import { Component, Input, OnInit, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  WorkflowInstance,
  WorkflowStep,
  WorkflowStepExecution,
} from '../../../core/models/workflow.models';
import { WorkflowService } from '../../../core/services/workflow.service';
import { DateUtilsService } from '../../../core/utils/date-utils.service';
import { LoadingSpinnerComponent } from '../loading-spinner/loading-spinner.component';

export interface StepperItem {
  order: number;
  name: string;
  /** 'upcoming' means the template defines this step but it hasn't started
   *  yet - it has no step_execution row (WorkflowEngine creates those
   *  lazily), so there's nothing else to show for it but its name. */
  status: 'approved' | 'rejected' | 'skipped' | 'pending' | 'delegated' | 'upcoming';
  isCurrent: boolean;
  execution?: WorkflowStepExecution;
}

@Component({
  selector: 'app-workflow-status',
  standalone: true,
  imports: [CommonModule, LoadingSpinnerComponent],
  templateUrl: './workflow-status.component.html',
  styleUrls: ['./workflow-status.component.scss'],
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
      next: workflow => {
        this.workflow = workflow;
        this.loading = false;
      },
      error: err => {
        this.error = 'Failed to load workflow status';
        this.loading = false;
        console.error('Error loading workflow:', err);
      },
    });
  }

  isCurrentStep(step: WorkflowStepExecution): boolean {
    if (!this.workflow || !step.workflow_step_detail) return false;
    return (
      step.workflow_step_detail.step_order === this.workflow.current_step_order &&
      step.status === 'pending'
    );
  }

  getStatusClass(): string {
    if (!this.workflow) return '';
    return this.workflowService.getStatusClass(this.workflow.status);
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

  /**
   * The template's real, configured step count - not sortedSteps.length,
   * which only counts steps reached so far (WorkflowEngine creates step
   * executions lazily, one at a time, so a workflow still on step 1 of a
   * 3-step template only has 1 step_execution row and would wrongly show
   * "Step 1 of 1").
   */
  get totalStepCount(): number {
    return this.workflow?.workflow_template_detail?.step_count || this.sortedSteps.length;
  }

  /**
   * Merges the template's full, ordered step list (all of them, including
   * ones not started yet) with this instance's step_executions (which only
   * exist for steps actually reached so far) into one array the stepper can
   * render end-to-end. Falls back to sortedSteps alone when the template's
   * step list isn't available (e.g. an older cached response).
   */
  get stepperItems(): StepperItem[] {
    const templateSteps = this.workflow?.workflow_template_detail?.steps;
    if (!templateSteps?.length) {
      return this.sortedSteps.map(execution => ({
        order: execution.workflow_step_detail?.step_order || 0,
        name: execution.workflow_step_detail?.step_name || 'Step',
        status: execution.status,
        isCurrent: this.isCurrentStep(execution),
        execution,
      }));
    }

    const sortedTemplateSteps = [...templateSteps].sort((a, b) => a.step_order - b.step_order);
    return sortedTemplateSteps.map(templateStep => this.toStepperItem(templateStep));
  }

  private toStepperItem(templateStep: WorkflowStep): StepperItem {
    const execution = this.sortedSteps.find(
      e => e.workflow_step === templateStep.id || e.workflow_step_detail?.id === templateStep.id
    );
    return {
      order: templateStep.step_order,
      name: templateStep.step_name,
      status: execution?.status || 'upcoming',
      isCurrent: !!execution && this.isCurrentStep(execution),
      execution,
    };
  }

  /**
   * Circles sit centered within their own 1/N-wide slice of the row, so the
   * track (drawn center-to-center) is inset by half a slice on each side.
   */
  get stepperTrackInsetPercent(): number {
    const n = this.stepperItems.length;
    return n > 0 ? 50 / n : 0;
  }

  /**
   * Width of the colored "progress" segment of the track, as a percentage
   * of the full row - from the first circle's center up to the center of
   * the furthest step reached (last approved/rejected/skipped/current one).
   */
  get stepperProgressWidthPercent(): number {
    const n = this.stepperItems.length;
    if (n <= 1) return 0;
    const inset = this.stepperTrackInsetPercent;
    const trackSpan = 100 - 2 * inset;
    return (this.stepperFurthestIndex / (n - 1)) * trackSpan;
  }

  private get stepperFurthestIndex(): number {
    let furthest = 0;
    this.stepperItems.forEach((item, index) => {
      if (item.status !== 'upcoming') {
        furthest = index;
      }
    });
    return furthest;
  }

  getStepperClass(item: StepperItem): string {
    if (item.status === 'approved') return 'stepper-completed';
    if (item.status === 'rejected') return 'stepper-rejected';
    if (item.status === 'skipped') return 'stepper-skipped';
    if (item.isCurrent) return 'stepper-current';
    if (item.status === 'upcoming') return 'stepper-upcoming';
    return 'stepper-pending';
  }

  getStepperCaption(item: StepperItem): string {
    const execution = item.execution;
    if (item.status === 'upcoming') {
      return 'Upcoming';
    }
    if (item.status === 'approved' || item.status === 'rejected' || item.status === 'skipped') {
      const actor = execution ? this.formatUserName(execution) : '';
      const date = execution?.action_date ? this.dateUtils.formatDate(execution.action_date) : '';
      const statusLabel = item.status.charAt(0).toUpperCase() + item.status.slice(1);
      return actor && date ? `${statusLabel} (${actor}, ${date})` : statusLabel;
    }
    if (item.isCurrent) {
      return 'Awaiting Review';
    }
    return 'Pending';
  }
}
