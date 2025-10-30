import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { ExpenseClaimsService } from '../../services/expense-claims.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmationService } from '../../../../core/services/confirmation.service';
import { WorkflowService } from '../../../../core/services/workflow.service';
import { WorkflowStatusComponent } from '../../../../shared/components/workflow-status/workflow-status.component';
import { ApprovalActionsComponent } from '../../../../shared/components/approval-actions/approval-actions.component';
import { WorkflowInstance, WorkflowStepExecution } from '../../../../core/models/workflow.models';
import {
  ExpenseClaim,
  ExpenseItem,
  ForeignExchangeRate,
  toFrontendFormat
} from '../../models/expense-claim.model';

@Component({
  selector: 'app-expense-detail',
  standalone: true,
  imports: [CommonModule, WorkflowStatusComponent, ApprovalActionsComponent],
  templateUrl: './expense-detail.component.html',
  styleUrls: ['./expense-detail.component.scss']
})
export class ExpenseDetailComponent implements OnInit {
  claim: ExpenseClaim | null = null;
  loading: boolean = true;
  error: string = '';
  claimId!: number;

  // Calculated totals
  totalMileage = 0;
  totalTransport = 0;
  totalHotel = 0;
  totalOutstation = 0;
  totalMisc = 0;
  totalOther = 0;

  // Workflow properties
  workflow: WorkflowInstance | null = null;
  workflowLoading: boolean = false;
  currentStepExecution: WorkflowStepExecution | null = null;

  // Status-based visibility constants
  private readonly EDITABLE_STATUSES = ['Pending Department Focal', 'Pending Verification', 'Draft', 'DRAFT', 'Rejected', 'REJECTED', 'SUBMITTED', 'Submitted'];
  private readonly CANCELLABLE_STATUSES = ['Pending Department Focal', 'Pending Verification', 'Pending Line Manager', 'Pending HOD', 'SUBMITTED', 'Submitted', 'UNDER_REVIEW', 'Under Review'];
  private readonly DELETABLE_STATUSES = ['Draft', 'DRAFT', 'Rejected', 'REJECTED'];

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private expenseService: ExpenseClaimsService,
    private toastService: ToastService,
    private confirmationService: ConfirmationService,
    public workflowService: WorkflowService
  ) {}

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      this.claimId = +params['id'];
      if (this.claimId) {
        this.loadClaimDetails();
        this.loadWorkflow();
      }
    });
  }

  loadClaimDetails(): void {
    this.loading = true;
    this.error = '';

    this.expenseService.getClaimById(this.claimId).subscribe({
      next: (data: any) => {
        console.log('📊 Raw backend data:', data);
        console.log('📊 Has additional_data:', !!data.additional_data);
        if (data.additional_data) {
          console.log('📊 Additional data keys:', Object.keys(data.additional_data));
        }

        // Convert backend format to frontend format
        this.claim = toFrontendFormat(data);
        console.log('📊 Converted claim:', this.claim);
        console.log('📊 Header Details:', this.claim.headerDetails);

        this.calculateTotals();
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load claim details: ' + (err.error?.message || err.message || 'Unknown error');
        this.loading = false;
        console.error('Error loading claim:', err);
      }
    });
  }

  calculateTotals(): void {
    if (!this.claim) return;

    const items = this.claim.expenseItems;
    this.totalMileage = items.reduce((sum, item) => sum + (Number(item.officialMileageKM) || 0), 0);
    this.totalTransport = items.reduce((sum, item) => sum + (Number(item.transport) || 0), 0);
    this.totalHotel = items.reduce((sum, item) => sum + (Number(item.hotelAccommodationAllowance) || 0), 0);
    this.totalOutstation = items.reduce((sum, item) => sum + (Number(item.outStationAllowanceMeal) || 0), 0);
    this.totalMisc = items.reduce((sum, item) => sum + (Number(item.miscellaneousAllowance10Percent) || 0), 0);
    this.totalOther = items.reduce((sum, item) => sum + (Number(item.otherExpenses) || 0), 0);
  }

  canEdit(): boolean {
    return this.EDITABLE_STATUSES.includes(this.claim?.status || '');
  }

  canCancel(): boolean {
    return this.CANCELLABLE_STATUSES.includes(this.claim?.status || '');
  }

  canDelete(): boolean {
    return this.DELETABLE_STATUSES.includes(this.claim?.status || '');
  }

  getStatusClass(): string {
    const status = this.claim?.status?.toLowerCase() || '';
    if (status.includes('approved') || status.includes('processed')) return 'badge-success';
    if (status.includes('rejected')) return 'badge-danger';
    if (status.includes('pending') || status.includes('verification')) return 'badge-warning';
    if (status.includes('draft')) return 'badge-secondary';
    if (status.includes('cancelled')) return 'badge-secondary';
    return 'badge-info';
  }

  goBack(): void {
    this.router.navigate(['/expenses']);
  }

  onEdit(): void {
    this.router.navigate(['/expenses/edit', this.claimId]);
  }

  onCancel(): void {
    this.confirmationService.confirmDestructive('Cancel', 'this claim').subscribe(confirmed => {
      if (confirmed) {
        this.expenseService.cancelClaim(this.claimId).subscribe({
          next: () => {
            this.toastService.success('Claim cancelled successfully');
            this.router.navigate(['/expenses']);
          },
          error: (err) => {
            this.toastService.error('Failed to cancel claim: ' + (err.error?.message || err.message));
            console.error('Error cancelling claim:', err);
          }
        });
      }
    });
  }

  onDelete(): void {
    this.confirmationService.confirmDelete('this claim').subscribe(confirmed => {
      if (confirmed) {
        this.expenseService.deleteClaim(this.claimId).subscribe({
          next: () => {
            this.toastService.success('Claim deleted successfully');
            this.router.navigate(['/expenses']);
          },
          error: (err) => {
            this.toastService.error('Failed to delete claim: ' + (err.error?.message || err.message));
            console.error('Error deleting claim:', err);
          }
        });
      }
    });
  }

  onPrint(): void {
    window.print();
  }

  // Helper methods for formatting
  formatNumber(value: any, decimals: number = 2): string {
    if (value === null || value === undefined || value === '') return '';
    const num = Number(value);
    return isNaN(num) ? '' : num.toLocaleString(undefined, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    });
  }

  formatCurrency(amount: number | string | null | undefined): string {
    if (!amount && amount !== 0) return '$0.00';
    const num = Number(amount);
    return isNaN(num) ? '$0.00' : new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(num);
  }

  formatDate(dateValue: Date | string | null | undefined): string {
    if (!dateValue) return 'N/A';
    const date = typeof dateValue === 'string' ? new Date(dateValue) : dateValue;
    if (isNaN(date.getTime())) return 'Invalid Date';
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  }

  formatMonthYear(dateValue: Date | string | null | undefined): string {
    if (!dateValue) return 'N/A';
    const date = typeof dateValue === 'string' ? new Date(dateValue) : dateValue;
    if (isNaN(date.getTime())) return 'Invalid Date';
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long' });
  }

  formatTime(timeStr: string | null | undefined): string {
    if (!timeStr || !/^[0-2]\d:[0-5]\d$/.test(timeStr)) return 'N/A';
    const [hours, minutes] = timeStr.split(':');
    const date = new Date();
    date.setHours(parseInt(hours), parseInt(minutes));
    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
  }

  getTravelDetails(item: ExpenseItem): string {
    if (typeof item.claimOrTravelDetails === 'string') {
      return item.claimOrTravelDetails;
    }
    const details = item.claimOrTravelDetails;
    const parts = [];
    if (details.from) parts.push(`From: ${details.from}`);
    if (details.to) parts.push(`To: ${details.to}`);
    if (details.placeOfStay) parts.push(`Place: ${details.placeOfStay}`);
    return parts.join(', ') || 'N/A';
  }

  // ==================== Workflow Methods ====================

  loadWorkflow(): void {
    this.workflowLoading = true;

    this.workflowService.getInstances({
      entity_type: 'expenseclaim'
    }).subscribe({
      next: (response: any) => {
        // Handle both paginated response and array response
        const instances = Array.isArray(response) ? response : (response.results || []);

        const instance = instances.find((i: any) =>
          i.entity_info?.id === this.claimId
        );

        if (instance && instance.id) {
          this.workflowService.getInstance(instance.id).subscribe({
            next: (workflow) => {
              this.workflow = workflow;
              this.updateCurrentStepExecution();
              this.workflowLoading = false;
            },
            error: (err) => {
              console.error('Error loading workflow details:', err);
              this.workflowLoading = false;
            }
          });
        } else {
          this.workflowLoading = false;
        }
      },
      error: (err) => {
        console.error('Error loading workflow:', err);
        this.workflowLoading = false;
      }
    });
  }

  updateCurrentStepExecution(): void {
    if (!this.workflow?.step_executions) {
      this.currentStepExecution = null;
      return;
    }

    this.currentStepExecution = this.workflow.step_executions.find(
      step => step.status === 'pending' &&
              step.workflow_step_detail?.step_order === this.workflow?.current_step_order &&
              step.can_action === true
    ) || null;
  }

  onWorkflowApproved(): void {
    this.toastService.success('Approval successful');
    this.loadClaimDetails();
    this.loadWorkflow();
  }

  onWorkflowRejected(): void {
    this.toastService.success('Request rejected');
    this.loadClaimDetails();
    this.loadWorkflow();
  }

  onWorkflowDelegated(): void {
    this.toastService.success('Successfully delegated');
    this.loadWorkflow();
  }

  getWorkflowStatus(): string {
    if (!this.workflow) return '';

    const status = this.workflow.status;
    const currentStep = this.workflow.current_step_order;
    const totalSteps = this.workflow.step_executions?.length || 0;

    if (status === 'approved') return 'Approved';
    if (status === 'rejected') return 'Rejected';
    if (status === 'cancelled') return 'Cancelled';
    if (status === 'in_progress') return `Pending Approval (Step ${currentStep} of ${totalSteps})`;
    if (status === 'pending') return 'Pending Approval';

    return status.charAt(0).toUpperCase() + status.slice(1);
  }

  getWorkflowStatusClass(): string {
    if (!this.workflow) return 'badge-secondary';

    const status = this.workflow.status;
    if (status === 'approved') return 'badge-success';
    if (status === 'rejected') return 'badge-danger';
    if (status === 'cancelled') return 'badge-secondary';
    if (status === 'in_progress' || status === 'pending') return 'badge-warning';

    return 'badge-info';
  }
}
