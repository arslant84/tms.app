import { Component, Input, Output, EventEmitter, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subject, takeUntil } from 'rxjs';
import { WorkflowStepExecution } from '../../../core/models/workflow.models';
import { WorkflowService } from '../../../core/services/workflow.service';
import { ConfirmationService } from '../../../core/services/confirmation.service';
import { ToastService } from '../../../core/services/toast.service';
import { LoadingSpinnerComponent } from '../loading-spinner/loading-spinner.component';
import { HttpErrorHandlerService } from '../../../core/utils/http-error-handler.service';

@Component({
  selector: 'app-approval-actions',
  standalone: true,
  imports: [CommonModule, FormsModule, LoadingSpinnerComponent],
  templateUrl: './approval-actions.component.html',
  styleUrls: ['./approval-actions.component.scss']
})
export class ApprovalActionsComponent implements OnInit, OnDestroy {
  @Input() stepExecution!: WorkflowStepExecution;
  @Input() compact: boolean = false;

  @Output() approved = new EventEmitter<void>();
  @Output() rejected = new EventEmitter<void>();
  @Output() delegated = new EventEmitter<void>();
  @Output() skipped = new EventEmitter<void>();

  // UI state
  processing: boolean = false;
  showCommentDialog: boolean = false;
  showDelegationDialog: boolean = false;

  // Form data
  comments: string = '';
  delegationUserId: string = '';
  delegationReason: string = '';

  // Action type for comment dialog
  currentAction: 'approve' | 'reject' | 'skip' | null = null;

  private destroy$ = new Subject<void>();

  constructor(
    public workflowService: WorkflowService,
    private confirmationService: ConfirmationService,
    private toastService: ToastService,
    private errorHandler: HttpErrorHandlerService
  ) {}

  ngOnInit(): void {
    if (!this.stepExecution) {
      console.error('ApprovalActionsComponent: stepExecution is required');
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  get canAction(): boolean {
    return this.stepExecution?.can_action === true &&
           this.stepExecution?.status === 'pending' &&
           !this.processing;
  }

  get canSkip(): boolean {
    return this.stepExecution?.workflow_step_detail?.can_skip === true;
  }

  get requiresComments(): boolean {
    return this.stepExecution?.workflow_step_detail?.requires_comments === true;
  }

  // ==================== Approve Action ====================

  onApprove(): void {
    if (!this.canAction) return;

    if (this.requiresComments) {
      // Show comment dialog
      this.currentAction = 'approve';
      this.comments = '';
      this.showCommentDialog = true;
    } else {
      // Show confirmation
      this.confirmationService.confirm({
        title: 'Confirm Approval',
        message: 'Are you sure you want to approve this step?',
        confirmText: 'Approve',
        cancelText: 'Cancel',
        type: 'success'
      })
        .pipe(takeUntil(this.destroy$))
        .subscribe(confirmed => {
          if (confirmed) {
            this.approveStep();
          }
        });
    }
  }

  private approveStep(comments?: string): void {
    this.processing = true;

    this.workflowService.approveStep(this.stepExecution.id, comments)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.processing = false;
          this.showCommentDialog = false;
          this.toastService.success('Step approved successfully');
          this.approved.emit();
        },
        error: (err) => {
          this.processing = false;
          this.toastService.error(this.errorHandler.getErrorMessage(err, 'Failed to approve step'));
          console.error('Error approving step:', err);
        }
      });
  }

  // ==================== Reject Action ====================

  onReject(): void {
    if (!this.canAction) return;

    // Show comment dialog (required for reject)
    this.currentAction = 'reject';
    this.comments = '';
    this.showCommentDialog = true;
  }

  private rejectStep(comments: string): void {
    this.processing = true;

    this.workflowService.rejectStep(this.stepExecution.id, comments)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.processing = false;
          this.showCommentDialog = false;
          this.toastService.success('Step rejected successfully');
          this.rejected.emit();
        },
        error: (err) => {
          this.processing = false;
          this.toastService.error(this.errorHandler.getErrorMessage(err, 'Failed to reject step'));
          console.error('Error rejecting step:', err);
        }
      });
  }

  // ==================== Skip Action ====================

  onSkip(): void {
    if (!this.canAction || !this.canSkip) return;

    this.confirmationService.confirm({
      title: 'Confirm Skip',
      message: 'Are you sure you want to skip this step? This action cannot be undone.',
      confirmText: 'Skip',
      cancelText: 'Cancel',
      type: 'warning'
    })
      .pipe(takeUntil(this.destroy$))
      .subscribe(confirmed => {
        if (confirmed) {
          this.skipStep();
        }
      });
  }

  private skipStep(comments?: string): void {
    this.processing = true;

    this.workflowService.skipStep(this.stepExecution.id, comments)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.processing = false;
          this.toastService.success('Step skipped successfully');
          this.skipped.emit();
        },
        error: (err) => {
          this.processing = false;
          this.toastService.error(this.errorHandler.getErrorMessage(err, 'Failed to skip step'));
          console.error('Error skipping step:', err);
        }
      });
  }

  // ==================== Delegate Action ====================

  onDelegate(): void {
    if (!this.canAction) return;

    // Show delegation dialog
    this.delegationUserId = '';
    this.delegationReason = '';
    this.showDelegationDialog = true;
  }

  private delegateStep(): void {
    if (!this.delegationUserId) {
      this.toastService.warning('Please select a user to delegate to');
      return;
    }

    this.processing = true;

    this.workflowService.delegateStep(
      this.stepExecution.id,
      this.delegationUserId,
      this.delegationReason
    )
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.processing = false;
          this.showDelegationDialog = false;
          this.toastService.success('Step delegated successfully');
          this.delegated.emit();
        },
        error: (err) => {
          this.processing = false;
          this.toastService.error(this.errorHandler.getErrorMessage(err, 'Failed to delegate step'));
          console.error('Error delegating step:', err);
        }
      });
  }

  // ==================== Dialog Actions ====================

  onCommentDialogSubmit(): void {
    if (this.currentAction === 'reject' && !this.comments.trim()) {
      this.toastService.warning('Comments are required when rejecting');
      return;
    }

    if (this.currentAction === 'approve') {
      this.approveStep(this.comments);
    } else if (this.currentAction === 'reject') {
      this.rejectStep(this.comments);
    } else if (this.currentAction === 'skip') {
      this.skipStep(this.comments);
    }
  }

  onCommentDialogCancel(): void {
    this.showCommentDialog = false;
    this.currentAction = null;
    this.comments = '';
  }

  onDelegationDialogSubmit(): void {
    this.delegateStep();
  }

  onDelegationDialogCancel(): void {
    this.showDelegationDialog = false;
    this.delegationUserId = '';
    this.delegationReason = '';
  }

  // ==================== Helper Methods ====================

  getActionButtonClass(action: string): string {
    const classes: { [key: string]: string } = {
      'approve': 'btn-success',
      'reject': 'btn-danger',
      'skip': 'btn-secondary',
      'delegate': 'btn-info'
    };
    return classes[action] || 'btn-primary';
  }

  getDialogTitle(): string {
    if (this.currentAction === 'approve') return 'Approve with Comments';
    if (this.currentAction === 'reject') return 'Reject with Comments';
    if (this.currentAction === 'skip') return 'Skip with Comments';
    return 'Add Comments';
  }

  isCommentsRequired(): boolean {
    return this.currentAction === 'reject';
  }
}
