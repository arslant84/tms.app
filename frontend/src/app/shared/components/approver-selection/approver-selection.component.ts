import { Component, Input, Output, EventEmitter, OnInit, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  WorkflowService,
  WorkflowStepWithApprovers,
  EligibleApprover,
  ApproverSelection
} from '../../../core/services/workflow.service';
import { LoadingSpinnerComponent } from '../loading-spinner/loading-spinner.component';

/**
 * Interface for skipped steps selection.
 * Maps step_order to skip reason (optional).
 */
export interface SkippedStepsSelection {
  [stepOrder: number]: string | null;  // step_order -> skip_reason (null means no reason provided)
}

@Component({
  selector: 'app-approver-selection',
  standalone: true,
  imports: [CommonModule, FormsModule, LoadingSpinnerComponent],
  templateUrl: './approver-selection.component.html',
  styleUrls: ['./approver-selection.component.scss']
})
export class ApproverSelectionComponent implements OnInit, OnChanges {
  @Input() entityType: string = '';
  @Input() required: boolean = false;
  @Input() showTitle: boolean = true;
  @Input() initialSelections: ApproverSelection = {};
  /**
   * Optional requester user ID. Use this in edit mode to ensure approvers are
   * filtered by the original requester's department, not the current viewer's department.
   */
  @Input() requesterId?: number;
  /**
   * Optional staff ID. Used as fallback when requesterId is not available
   * (for modules like accommodation that store staff_id instead of user FK).
   */
  @Input() staffId?: string;
  /**
   * Initial skipped steps to pre-populate (for edit mode).
   */
  @Input() initialSkippedSteps: SkippedStepsSelection = {};
  /**
   * Whether to show the skip option for skippable steps.
   * Default: true
   */
  @Input() allowSkip: boolean = true;
  @Output() selectionChange = new EventEmitter<ApproverSelection>();
  @Output() validityChange = new EventEmitter<boolean>();
  @Output() skippedStepsChange = new EventEmitter<SkippedStepsSelection>();

  steps: WorkflowStepWithApprovers[] = [];
  selections: ApproverSelection = {};
  skippedSteps: SkippedStepsSelection = {};
  isLoading = false;
  error: string | null = null;
  searchTerms: { [stepOrder: number]: string } = {};
  private initialSelectionsApplied = false;

  constructor(private workflowService: WorkflowService) {}

  ngOnInit(): void {
    this.loadEligibleApprovers();
  }

  ngOnChanges(changes: SimpleChanges): void {
    // Reload approvers if entityType, requesterId, or staffId changes
    if ((changes['entityType'] && !changes['entityType'].firstChange) ||
        (changes['requesterId'] && !changes['requesterId'].firstChange) ||
        (changes['staffId'] && !changes['staffId'].firstChange)) {
      this.initialSelectionsApplied = false;
      this.loadEligibleApprovers();
    }

    // Apply initial selections if they change after steps are loaded
    if (changes['initialSelections'] && this.steps.length > 0) {
      this.applyInitialSelections();
    }
  }

  loadEligibleApprovers(): void {
    if (!this.entityType) return;

    this.isLoading = true;
    this.error = null;
    this.selections = {};
    this.skippedSteps = {};
    this.searchTerms = {};

    // Build options for the service call
    const options: { requesterId?: number; staffId?: string } = {};
    if (this.requesterId) {
      options.requesterId = this.requesterId;
    }
    if (this.staffId) {
      options.staffId = this.staffId;
    }

    this.workflowService.getEligibleApprovers(this.entityType, Object.keys(options).length > 0 ? options : undefined).subscribe({
      next: (response) => {
        if (response && response.steps) {
          this.steps = response.steps;

          // First, apply initial selections if provided
          this.applyInitialSelections();

          // Apply initial skipped steps
          this.applyInitialSkippedSteps();

          // Then, for steps without initial selection or skip, pre-select if only one approver
          this.steps.forEach(step => {
            const isSkipped = this.skippedSteps[step.step_order] !== undefined;
            if (!isSkipped && this.selections[step.step_order] === undefined && step.eligible_approvers.length === 1) {
              this.selections[step.step_order] = step.eligible_approvers[0].id;
            }
          });

          this.emitSelection();
          this.emitSkippedSteps();
          this.emitValidity();
        } else {
          // Response was null or had no steps - workflow not found
          this.steps = [];
        }
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Error loading eligible approvers:', err);
        this.error = 'Failed to load approvers. Please try again.';
        this.isLoading = false;
        this.emitValidity();
      }
    });
  }

  /**
   * Apply initial selections to the component.
   * Only applies selections for approvers that are eligible for the step.
   */
  private applyInitialSelections(): void {
    if (!this.initialSelections || Object.keys(this.initialSelections).length === 0) {
      return;
    }

    // Apply initial selections, but only if the approver is in the eligible list
    for (const [stepOrderStr, userId] of Object.entries(this.initialSelections)) {
      const stepOrder = parseInt(stepOrderStr, 10);
      const step = this.steps.find(s => s.step_order === stepOrder);

      if (step) {
        // Check if the user is in the eligible approvers list
        // Use Number() conversion to handle potential type mismatches
        const userIdNum = Number(userId);
        const isEligible = step.eligible_approvers.some(a => Number(a.id) === userIdNum);
        if (isEligible) {
          this.selections[stepOrder] = userIdNum;
        }
      }
    }

    this.initialSelectionsApplied = true;
  }

  /**
   * Apply initial skipped steps to the component.
   * Only applies skips for steps that have can_skip=true.
   */
  private applyInitialSkippedSteps(): void {
    if (!this.initialSkippedSteps || Object.keys(this.initialSkippedSteps).length === 0) {
      return;
    }

    for (const [stepOrderStr, reason] of Object.entries(this.initialSkippedSteps)) {
      const stepOrder = parseInt(stepOrderStr, 10);
      const step = this.steps.find(s => s.step_order === stepOrder);

      if (step && step.can_skip) {
        this.skippedSteps[stepOrder] = reason;
        // Remove any approver selection for skipped step
        delete this.selections[stepOrder];
      }
    }
  }

  /**
   * Toggle skip status for a workflow step.
   * Only works for steps with can_skip=true.
   */
  onSkipToggle(stepOrder: number, skip: boolean, reason?: string): void {
    const step = this.steps.find(s => s.step_order === stepOrder);
    if (!step || !step.can_skip) return;

    if (skip) {
      this.skippedSteps[stepOrder] = reason || null;
      // Remove approver selection when skipping
      delete this.selections[stepOrder];
    } else {
      delete this.skippedSteps[stepOrder];
      // Auto-select approver if only one available
      if (step.eligible_approvers.length === 1) {
        this.selections[stepOrder] = step.eligible_approvers[0].id;
      }
    }

    this.emitSelection();
    this.emitSkippedSteps();
    this.emitValidity();
  }

  /**
   * Check if a step is currently marked as skipped.
   */
  isStepSkipped(stepOrder: number): boolean {
    return this.skippedSteps[stepOrder] !== undefined;
  }

  /**
   * Check if a step can be skipped.
   * Always allow skipping when no eligible approvers exist — the user must
   * be able to proceed even if no one matches the department filter.
   */
  canSkipStep(step: WorkflowStepWithApprovers): boolean {
    if (!this.allowSkip) return false;
    return step.can_skip || step.eligible_approvers.length === 0;
  }

  onApproverSelect(stepOrder: number, userId: number | null): void {
    if (userId) {
      this.selections[stepOrder] = userId;
    } else {
      delete this.selections[stepOrder];
    }
    this.emitSelection();
    this.emitValidity();
  }

  filterApprovers(step: WorkflowStepWithApprovers): EligibleApprover[] {
    const searchTerm = (this.searchTerms[step.step_order] || '').toLowerCase().trim();
    if (!searchTerm) return step.eligible_approvers;

    return step.eligible_approvers.filter(approver =>
      approver.full_name.toLowerCase().includes(searchTerm) ||
      approver.email.toLowerCase().includes(searchTerm) ||
      (approver.department && approver.department.toLowerCase().includes(searchTerm)) ||
      (approver.role && approver.role.toLowerCase().includes(searchTerm))
    );
  }

  isValid(): boolean {
    if (!this.required) return true;
    if (this.steps.length === 0) return true;

    return this.steps
      .filter(s => s.is_required)
      .every(s => {
        // Step is valid if it has an approver selected OR if it's skipped
        const hasApprover = this.selections[s.step_order] !== undefined;
        const isSkipped = this.skippedSteps[s.step_order] !== undefined;
        return hasApprover || isSkipped;
      });
  }

  private emitSelection(): void {
    this.selectionChange.emit({ ...this.selections });
  }

  private emitSkippedSteps(): void {
    this.skippedStepsChange.emit({ ...this.skippedSteps });
  }

  private emitValidity(): void {
    this.validityChange.emit(this.isValid());
  }

  getSelectedApprover(step: WorkflowStepWithApprovers): EligibleApprover | undefined {
    const userId = this.selections[step.step_order];
    return step.eligible_approvers.find(a => a.id === userId);
  }

  hasNoApprovers(step: WorkflowStepWithApprovers): boolean {
    return step.eligible_approvers.length === 0;
  }

  getSelections(): ApproverSelection {
    return { ...this.selections };
  }

  getSkippedSteps(): SkippedStepsSelection {
    return { ...this.skippedSteps };
  }

  clearSelections(): void {
    this.selections = {};
    this.skippedSteps = {};
    this.emitSelection();
    this.emitSkippedSteps();
    this.emitValidity();
  }

  /**
   * Programmatically set selections from outside the component.
   * Useful when loading existing data in edit mode.
   */
  setSelections(selections: ApproverSelection): void {
    if (!selections) return;

    // Apply only if steps are loaded
    if (this.steps.length > 0) {
      for (const [stepOrderStr, userId] of Object.entries(selections)) {
        const stepOrder = parseInt(stepOrderStr, 10);
        const step = this.steps.find(s => s.step_order === stepOrder);

        if (step) {
          const isEligible = step.eligible_approvers.some(a => a.id === userId);
          if (isEligible) {
            // Clear skip if selecting an approver
            delete this.skippedSteps[stepOrder];
            this.selections[stepOrder] = userId;
          }
        }
      }
      this.emitSelection();
      this.emitSkippedSteps();
      this.emitValidity();
    } else {
      // Steps not loaded yet, store as initial selections
      this.initialSelections = selections;
    }
  }

  /**
   * Programmatically set skipped steps from outside the component.
   * Useful when loading existing data in edit mode.
   */
  setSkippedSteps(skippedSteps: SkippedStepsSelection): void {
    if (!skippedSteps) return;

    // Apply only if steps are loaded
    if (this.steps.length > 0) {
      for (const [stepOrderStr, reason] of Object.entries(skippedSteps)) {
        const stepOrder = parseInt(stepOrderStr, 10);
        const step = this.steps.find(s => s.step_order === stepOrder);

        if (step && step.can_skip) {
          this.skippedSteps[stepOrder] = reason;
          // Clear approver selection if skipping
          delete this.selections[stepOrder];
        }
      }
      this.emitSelection();
      this.emitSkippedSteps();
      this.emitValidity();
    } else {
      // Steps not loaded yet, store as initial skipped steps
      this.initialSkippedSteps = skippedSteps;
    }
  }
}
