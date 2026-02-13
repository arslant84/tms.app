import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { FormUtilsService } from '../../../../core/utils/form-utils.service';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { StatusUtilsService } from '../../../../core/utils/status-utils.service';

export interface ApprovalStep {
  role: string;
  name: string;
  status: 'Current' | 'Pending' | 'Approved' | 'Rejected' | 'Not Started' | 'Cancelled';
  date?: Date | string;
  comments?: string;
}

export interface ApprovalSubmissionData {
  additionalComments: string;
}

@Component({
  selector: 'app-approval-submission',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './approval-submission.component.html',
  styleUrls: ['./approval-submission.component.scss']
})
export class ApprovalSubmissionComponent implements OnInit {
  @Input() travelType: 'Domestic' | 'Overseas' | 'Home Leave' | 'External Parties' | null = null;
  @Input() requestorData: any = null;
  @Input() travelDetails: any = null;
  @Input() initialData: Partial<ApprovalSubmissionData> = {};
  @Input() approvalWorkflow: ApprovalStep[] = [];

  @Output() formSubmit = new EventEmitter<ApprovalSubmissionData>();
  @Output() backClick = new EventEmitter<void>();

  approvalForm!: FormGroup;
  isInternationalTravel: boolean = false;

  constructor(
    private fb: FormBuilder,
    private formUtils: FormUtilsService,
    public dateUtils: DateUtilsService,
    public statusUtils: StatusUtilsService
  ) {}

  ngOnInit(): void {
    // Determine if international travel
    this.isInternationalTravel =
      this.travelType === 'Overseas' || this.travelType === 'Home Leave';

    this.initForm();
    this.initializeApprovalWorkflow();
  }

  private initForm(): void {
    this.approvalForm = this.fb.group({
      additionalComments: [this.initialData.additionalComments || '']
    });
  }

  private initializeApprovalWorkflow(): void {
    // If no workflow provided, create initial workflow
    if (!this.approvalWorkflow || this.approvalWorkflow.length === 0) {
      const requestorName = this.requestorData?.fullName || 'Requestor';
      this.approvalWorkflow = [
        { role: 'Requestor', name: requestorName, status: 'Current', date: new Date() },
        { role: 'Department Focal', name: 'Pending Department Focal', status: 'Pending' },
        { role: 'Line Manager', name: 'Pending Line Manager', status: 'Pending' },
        { role: 'HOD', name: 'Pending HOD', status: 'Pending' }
      ];
    }
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


  onSubmit(): void {
    if (this.approvalForm.valid) {
      this.formSubmit.emit(this.approvalForm.value);
    } else {
      this.formUtils.markFormGroupTouched(this.approvalForm);
    }
  }

  onBack(): void {
    this.backClick.emit();
  }

  // Public methods for wizard integration
  getFormData(): ApprovalSubmissionData {
    return this.approvalForm.value;
  }

  isValid(): boolean {
    return this.approvalForm.valid;
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
