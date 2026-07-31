import { Component, EventEmitter, Input, OnInit, Output, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { FormUtilsService } from '../../../../core/utils/form-utils.service';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { StatusUtilsService } from '../../../../core/utils/status-utils.service';
import { WorkflowService, ApproverSelection } from '../../../../core/services/workflow.service';
import { WorkflowTemplate, WorkflowStep } from '../../../../core/models/workflow.models';
import { ApproverSelectionComponent, SkippedStepsSelection } from '../../../../shared/components/approver-selection/approver-selection.component';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';

export interface ApprovalStep {
  role: string;
  name: string;
  status: 'Current' | 'Pending' | 'Approved' | 'Rejected' | 'Not Started' | 'Cancelled';
  date?: Date | string;
  comments?: string;
}

export interface ApprovalSubmissionData {
  additionalComments: string;
  selected_approvers?: ApproverSelection;
  skipped_steps?: SkippedStepsSelection;
}

@Component({
  selector: 'app-approval-submission',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, ApproverSelectionComponent, LoadingSpinnerComponent],
  templateUrl: './approval-submission.component.html',
  styleUrls: ['./approval-submission.component.scss']
})
export class ApprovalSubmissionComponent implements OnInit {
  @ViewChild(ApproverSelectionComponent) approverSelectionComponent?: ApproverSelectionComponent;

  @Input() travelType: 'Domestic' | 'Overseas' | 'Home Leave' | 'External Parties' | null = null;
  @Input() requestorData: any = null;
  @Input() travelDetails: any = null;
  @Input() initialData: Partial<ApprovalSubmissionData> = {};
  @Input() approvalWorkflow: ApprovalStep[] = [];
  @Input() entityType: string = 'travelrequest';
  @Input() enableApproverSelection: boolean = true;
  /**
   * Staff ID of the original requestor. Used for department-based approver filtering
   * in edit mode to ensure approvers are filtered by the original requester's department.
   */
  @Input() requesterStaffId?: string;

  @Output() formSubmit = new EventEmitter<ApprovalSubmissionData>();
  @Output() backClick = new EventEmitter<void>();

  approvalForm!: FormGroup;
  isInternationalTravel: boolean = false;
  isLoadingWorkflow: boolean = false;
  selectedApprovers: ApproverSelection = {};
  skippedSteps: SkippedStepsSelection = {};
  approverSelectionValid: boolean = true;

  constructor(
    private fb: FormBuilder,
    private formUtils: FormUtilsService,
    public dateUtils: DateUtilsService,
    public statusUtils: StatusUtilsService,
    private workflowService: WorkflowService
  ) {}

  ngOnInit(): void {
    // Determine if international travel
    this.isInternationalTravel =
      this.travelType === 'Overseas' || this.travelType === 'Home Leave';

    // Initialize selectedApprovers from initialData if available (edit mode)
    if (this.initialData?.selected_approvers) {
      this.selectedApprovers = this.initialData.selected_approvers;
    }

    // Initialize skippedSteps from initialData if available (edit mode)
    if (this.initialData?.skipped_steps) {
      this.skippedSteps = this.initialData.skipped_steps;
    }

    this.initForm();
    this.initializeApprovalWorkflow();
  }

  private initForm(): void {
    this.approvalForm = this.fb.group({
      additionalComments: [this.initialData.additionalComments || '']
    });
  }

  /**
   * Maps travelType to its per-travel-type workflow entity_type. Must stay in
   * sync with TravelRequest.WORKFLOW_ENTITY_TYPE_MAP (backend/trf/models.py) -
   * see docs/TSR_SUBMODULE_WORKFLOW_ROADMAP.md.
   */
  private resolveWorkflowEntityType(): string {
    const map: Record<string, string> = {
      'Domestic': 'travelrequest_domestic',
      'Overseas': 'travelrequest_overseas',
      'Home Leave': 'travelrequest_homeleave',
      'External Parties': 'travelrequest_external'
    };
    return (this.travelType && map[this.travelType]) || 'travelrequest';
  }

  private initializeApprovalWorkflow(): void {
    // If workflow already provided (e.g., from existing TRF), use it
    if (this.approvalWorkflow && this.approvalWorkflow.length > 0) {
      return;
    }

    // Fetch the active workflow template for this travel type, falling back
    // to the shared "travelrequest" template if no sub-type-specific one is
    // configured yet (see docs/TSR_SUBMODULE_WORKFLOW_ROADMAP.md).
    this.isLoadingWorkflow = true;
    this.workflowService.getTemplates({
      entity_type: this.resolveWorkflowEntityType(),
      fallback_entity_type: 'travelrequest',
      is_active: true
    }).subscribe({
      next: (templates: WorkflowTemplate[]) => {
        this.isLoadingWorkflow = false;
        if (templates && templates.length > 0) {
          const template = templates[0];
          // Convert workflow template steps to approval steps for display
          this.approvalWorkflow = this.convertTemplateToApprovalSteps(template);
        } else {
          // Fallback: No workflow template configured - show generic message
          this.approvalWorkflow = this.createFallbackWorkflow();
        }
      },
      error: (error) => {
        this.isLoadingWorkflow = false;
        console.error('Error fetching workflow template:', error);
        // Fallback on error
        this.approvalWorkflow = this.createFallbackWorkflow();
      }
    });
  }

  private convertTemplateToApprovalSteps(template: WorkflowTemplate): ApprovalStep[] {
    const requestorName = this.requestorData?.fullName || 'Requestor';
    const steps: ApprovalStep[] = [
      { role: 'Requestor', name: requestorName, status: 'Current', date: new Date() }
    ];

    // Add steps from workflow template
    if (template.steps && template.steps.length > 0) {
      // Sort steps by step_order
      const sortedSteps = [...template.steps].sort((a, b) => a.step_order - b.step_order);

      for (const step of sortedSteps) {
        steps.push({
          role: step.step_name,
          name: `Pending ${step.step_name}`,
          status: 'Pending'
        });
      }
    }

    return steps;
  }

  private createFallbackWorkflow(): ApprovalStep[] {
    const requestorName = this.requestorData?.fullName || 'Requestor';
    return [
      { role: 'Requestor', name: requestorName, status: 'Current', date: new Date() },
      { role: 'Approval', name: 'Pending Approval', status: 'Pending' }
    ];
  }

  getStatusBadgeClass(status: string): string {
    return this.statusUtils.getStatusBadgeClass(status);
  }

  getTravelTypeIcon(): string {
    const iconMap: { [key: string]: string } = {
      'Domestic': 'bi-building',
      'Overseas': 'bi-globe',
      'Home Leave': 'bi-house-door',
      'External Parties': 'bi-people'
    };
    return iconMap[this.travelType || ''] || 'bi-airplane';
  }


  onApproverSelectionChange(selection: ApproverSelection): void {
    this.selectedApprovers = selection;
  }

  onApproverValidityChange(isValid: boolean): void {
    this.approverSelectionValid = isValid;
  }

  onSkippedStepsChange(skippedSteps: SkippedStepsSelection): void {
    this.skippedSteps = skippedSteps;
  }

  onSubmit(): void {
    if (this.approvalForm.valid && this.approverSelectionValid) {
      const submissionData: ApprovalSubmissionData = {
        ...this.approvalForm.value,
        selected_approvers: this.selectedApprovers,
        skipped_steps: this.skippedSteps
      };
      this.formSubmit.emit(submissionData);
    } else {
      this.formUtils.markFormGroupTouched(this.approvalForm);
    }
  }

  onBack(): void {
    this.backClick.emit();
  }

  // Public methods for wizard integration
  getFormData(): ApprovalSubmissionData {
    return {
      ...this.approvalForm.value,
      selected_approvers: this.selectedApprovers,
      skipped_steps: this.skippedSteps
    };
  }

  isValid(): boolean {
    return this.approvalForm.valid && this.approverSelectionValid;
  }

  markAllAsTouched(): void {
    this.formUtils.markFormGroupTouched(this.approvalForm);
  }

  // Helper methods for displaying travel summary
  getItineraryCount(): number {
    return this.travelDetails?.itinerary?.length || 0;
  }

  getMealSelectionsCount(): number {
    return this.travelDetails?.mealProvisions?.dailySelections?.length || 0;
  }

  hasAccommodation(): boolean {
    return !!this.travelDetails?.accommodation;
  }

  getTransportCount(): number {
    return this.travelDetails?.companyTransportation?.length || 0;
  }
}
