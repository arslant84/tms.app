import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { VisaService, VisaApplication } from '../../../visa/services/visa.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmationService } from '../../../../core/services/confirmation.service';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { StatusUtilsService } from '../../../../core/utils/status-utils.service';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';
import { HttpErrorHandlerService } from '../../../../core/utils/http-error-handler.service';

interface PendingVisa {
  id: number;
  request_number: string;
  requestorName: string;
  department: string;
  staffId: string;
  destination: string;
  visaType: string;
  travelPurpose: string;
  tripStartDate: string;
  tripEndDate: string;
  status: string;
  submittedDate: string;
  passportNumber: string;
}

interface CompletedVisa {
  id: number;
  request_number: string;
  requestorName: string;
  staffId: string;
  department: string;
  destination: string;
  visaType: string;
  status: string;
  completedDate: string;
  notes?: string;
  processing_details?: any;
}

@Component({
  selector: 'app-visa-processing',
  standalone: true,
  imports: [CommonModule, FormsModule, LoadingSpinnerComponent],
  templateUrl: './visa-processing.component.html',
  styleUrl: './visa-processing.component.scss'
})
export class VisaProcessingComponent implements OnInit {
  activeTab: 'pending' | 'processing' | 'completed' = 'pending';

  // Pending Visas
  pendingVisas: PendingVisa[] = [];
  isLoadingPending = false;
  errorPending: string | null = null;

  // Completed Visas
  completedVisas: CompletedVisa[] = [];
  isLoadingCompleted = false;

  // Selected Application for processing
  selectedApplication: PendingVisa | null = null;
  isProcessing = false;
  showProcessingDialog = false;

  // Processing form fields
  processingNotes = '';
  visaNumber = '';
  visaIssueDate = '';
  visaExpiryDate = '';

  constructor(
    private visaService: VisaService,
    private toastService: ToastService,
    private confirmationService: ConfirmationService,
    private router: Router,
    public dateUtils: DateUtilsService,
    private statusUtils: StatusUtilsService,
    private errorHandler: HttpErrorHandlerService
  ) {}

  ngOnInit(): void {
    this.loadAll();
  }

  private loadAll(): void {
    this.isLoadingPending = true;
    this.isLoadingCompleted = true;
    this.errorPending = null;

    this.visaService.getAllApplications({ adminView: true, page_size: 1000 }).subscribe({
      next: (response: any) => {
        const all = response.results || response;

        this.pendingVisas = all
          .filter((app: any) => app.status === 'Approved')
          .map((app: any) => ({
            id: app.id,
            request_number: app.request_number || `VIS-${app.id}`,
            requestorName: app.requestor_name || 'N/A',
            department: app.department || 'N/A',
            staffId: app.staff_id || 'N/A',
            destination: app.destination || 'N/A',
            visaType: app.visa_type || 'N/A',
            travelPurpose: app.travel_purpose || 'N/A',
            tripStartDate: app.trip_start_date || 'N/A',
            tripEndDate: app.trip_end_date || 'N/A',
            status: app.status,
            submittedDate: app.submitted_date || app.created_at,
            passportNumber: app.passport_number || 'N/A'
          }));

        this.completedVisas = all
          .filter((app: any) => app.status === 'Completed')
          .map((app: any) => ({
            id: app.id,
            request_number: app.request_number || `VIS-${app.id}`,
            requestorName: app.requestor_name || 'N/A',
            destination: app.destination || 'N/A',
            visaType: app.visa_type || 'N/A',
            status: app.status,
            completedDate: app.processing_completed_at || app.updated_at,
            notes: app.additional_comments,
            staffId: app.staff_id || 'N/A',
            department: app.department || 'N/A',
            processing_details: app.processing_details
          }));

        this.isLoadingPending = false;
        this.isLoadingCompleted = false;
      },
      error: () => {
        this.errorPending = 'Failed to load visa applications. Please try again.';
        this.pendingVisas = [];
        this.completedVisas = [];
        this.isLoadingPending = false;
        this.isLoadingCompleted = false;
      }
    });
  }

  /**
   * Select visa application for processing
   */
  selectApplication(application: PendingVisa): void {
    this.selectedApplication = application;
    this.resetFormFields();
  }

  /**
   * Reset form fields
   */
  resetFormFields(): void {
    this.processingNotes = '';
    this.visaNumber = '';
    this.visaIssueDate = '';
    this.visaExpiryDate = '';
  }

  /**
   * Mark visa as processing started
   */
  startProcessing(): void {
    if (!this.selectedApplication) {
      this.toastService.error('No application selected');
      return;
    }

    this.isProcessing = true;

    this.visaService.updateApplication(this.selectedApplication.id, {
      status: 'Processing',
      processing_started_at: new Date().toISOString()
    }).subscribe({
      next: () => {
        this.toastService.success(`Processing started for ${this.selectedApplication!.requestorName}`);
        this.loadAll();
        this.selectedApplication = null;
        this.resetFormFields();
        this.isProcessing = false;
      },
      error: (err) => {
        this.toastService.error(this.errorHandler.getErrorMessage(err, 'Failed to start processing'));
        this.isProcessing = false;
      }
    });
  }

  /**
   * Complete visa processing
   */
  completeProcessing(): void {
    if (!this.selectedApplication) {
      this.toastService.error('No application selected');
      return;
    }

    this.confirmationService.confirm({
      title: 'Complete Processing',
      message: `Mark visa application ${this.selectedApplication.request_number} as completed?`,
      confirmText: 'Complete',
      type: 'success'
    }).subscribe(confirmed => {
      if (!confirmed) return;
      this.executeCompleteProcessing();
    });
  }

  private executeCompleteProcessing(): void {
    if (!this.selectedApplication) return;
    this.isProcessing = true;

    const completionData: any = {};

    if (this.processingNotes.trim()) {
      completionData.additional_comments = this.processingNotes;
    }

    // Add visa details if provided
    if (this.visaNumber || this.visaIssueDate || this.visaExpiryDate) {
      completionData.processing_details = {
        visa_number: this.visaNumber,
        visa_issue_date: this.visaIssueDate,
        visa_expiry_date: this.visaExpiryDate,
        completed_by_admin: true,
        completed_at: new Date().toISOString()
      };
    }

    this.visaService.completeApplication(this.selectedApplication.id, completionData).subscribe({
      next: (response) => {
        this.toastService.success(`Visa application for ${this.selectedApplication!.requestorName} marked as completed`);

        // Clear selected application first
        const appName = this.selectedApplication!.requestorName;
        this.selectedApplication = null;
        this.resetFormFields();

        this.loadAll();

        this.isProcessing = false;
      },
      error: (err) => {
        this.toastService.error(this.errorHandler.getErrorMessage(err, 'Failed to complete processing'));
        this.isProcessing = false;
      }
    });
  }

  /**
   * Reject visa application (Unable to process)
   */
  rejectApplication(): void {
    if (!this.selectedApplication) {
      this.toastService.error('No application selected');
      return;
    }

    const reason = prompt('Please provide a reason for rejecting this visa application:');
    if (!reason || !reason.trim()) {
      return;
    }

    this.isProcessing = true;

    this.visaService.rejectApplication(this.selectedApplication.id, reason).subscribe({
      next: () => {
        this.toastService.success(`Visa application ${this.selectedApplication!.request_number} rejected`);
        this.loadAll();
        this.selectedApplication = null;
        this.resetFormFields();
        this.isProcessing = false;
      },
      error: (err) => {
        this.toastService.error(this.errorHandler.getErrorMessage(err, 'Failed to reject application'));
        this.isProcessing = false;
      }
    });
  }

  /**
   * Switch tab
   */
  switchTab(tab: 'pending' | 'processing' | 'completed'): void {
    this.activeTab = tab;
  }

  /**
   * Open processing dialog
   */
  openProcessingDialog(application: PendingVisa): void {
    this.selectedApplication = application;
    this.resetFormFields();
    this.showProcessingDialog = true;
    document.body.classList.add('modal-open');
  }

  /**
   * Close processing dialog
   */
  closeProcessingDialog(): void {
    this.showProcessingDialog = false;
    this.selectedApplication = null;
    this.resetFormFields();
    document.body.classList.remove('modal-open');
  }

  /**
   * Complete processing from dialog
   */
  completeProcessingFromDialog(): void {
    if (!this.selectedApplication) {
      this.toastService.error('No application selected');
      return;
    }

    this.confirmationService.confirm({
      title: 'Complete Processing',
      message: `Mark visa application ${this.selectedApplication.request_number} as completed?`,
      confirmText: 'Complete',
      type: 'success'
    }).subscribe(confirmed => {
      if (!confirmed) return;
      this.executeCompleteProcessingFromDialog();
    });
  }

  private executeCompleteProcessingFromDialog(): void {
    if (!this.selectedApplication) return;
    this.isProcessing = true;

    const completionData: any = {};

    if (this.processingNotes.trim()) {
      completionData.additional_comments = this.processingNotes;
    }

    // Add processing details (visa information only)
    if (this.visaNumber || this.visaIssueDate || this.visaExpiryDate || this.processingNotes) {
      completionData.processing_details = {
        visa_number: this.visaNumber,
        visa_valid_from: this.visaIssueDate,
        visa_valid_to: this.visaExpiryDate,
        processing_notes: this.processingNotes,
        completed_by_admin: true,
        completed_at: new Date().toISOString()
      };
    }

    this.visaService.completeApplication(this.selectedApplication.id, completionData).subscribe({
      next: (response) => {
        this.toastService.success(`Visa application for ${this.selectedApplication!.requestorName} marked as completed`);

        this.closeProcessingDialog();
        this.loadAll();

        this.isProcessing = false;
      },
      error: (err) => {
        this.toastService.error(this.errorHandler.getErrorMessage(err, 'Failed to complete processing'));
        this.isProcessing = false;
      }
    });
  }

  /**
   * View application details
   */
  viewApplication(applicationId: number): void {
    this.router.navigate(['/visa', applicationId]);
  }

  /**
   * Navigate back to overview
   */
  goToOverview(): void {
    this.router.navigate(['/admin/visa']);
  }

  /**
   * Get status badge class - delegates to StatusUtilsService so the same
   * status renders the same color everywhere in the app.
   */
  getStatusClass(status: string): string {
    return this.statusUtils.getStatusBadgeClass(status);
  }

  /**
   * Get destination badge class
   */
  getDestinationBadgeClass(destination: string): string {
    const hash = destination?.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0) || 0;
    const colors = ['badge-blue', 'badge-green', 'badge-amber', 'badge-purple'];
    return colors[hash % colors.length];
  }

  /**
   * Get visa type badge class
   */
  getVisaTypeBadgeClass(visaType: string): string {
    const typeLower = visaType?.toLowerCase() || '';
    if (typeLower === 'business' || typeLower === 'work') return 'badge-blue';
    if (typeLower === 'diplomatic' || typeLower === 'official') return 'badge-amber';
    if (typeLower === 'student') return 'badge-purple';
    if (typeLower === 'tourist' || typeLower === 'transit') return 'badge-green';
    return 'badge-gray';
  }

  /**
   * Retry loading pending visas
   */
  retryPending(): void {
    this.loadAll();
  }
}
