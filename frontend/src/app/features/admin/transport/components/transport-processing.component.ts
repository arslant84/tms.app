import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { TransportService, TransportRequest } from '../../../transport/services/transport.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmationService } from '../../../../core/services/confirmation.service';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { StatusUtilsService } from '../../../../core/utils/status-utils.service';
import { DepartmentNamePipe } from '../../../../core/pipes/department-name.pipe';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';
import { HttpErrorHandlerService } from '../../../../core/utils/http-error-handler.service';

interface BookingDetails {
  vehicleNumber: string;
  driverName: string;
  driverContact?: string;
  pickupTime?: string;
  additionalNotes?: string;
}

@Component({
  selector: 'app-transport-processing',
  standalone: true,
  imports: [CommonModule, FormsModule, DepartmentNamePipe, LoadingSpinnerComponent],
  templateUrl: './transport-processing.component.html',
  styleUrl: './transport-processing.component.scss',
})
export class TransportProcessingComponent implements OnInit {
  activeTab: 'pending' | 'completed' = 'pending';

  // Transport Requests by status. There is no separate "Processing" stage
  // any more - filling in booking details completes the request in one
  // action (see handleCompleteProcessing), so a request is either still
  // waiting to be processed or already Completed. pendingRequests also
  // covers older requests that already have a vehicle assigned from before
  // this change, so they remain reachable to finish off.
  pendingRequests: TransportRequest[] = [];
  completedRequests: TransportRequest[] = [];

  // Loading states
  isLoading = false;
  isProcessing = false;
  error: string | null = null;

  // Selected Request for dialogs
  selectedRequest: TransportRequest | null = null;
  showProcessingDialog = false;
  showCompletingDialog = false;
  showDetailsDialog = false;

  // Booking form state
  bookingForm: BookingDetails = {
    vehicleNumber: '',
    driverName: '',
    driverContact: '',
    pickupTime: '',
    additionalNotes: '',
  };

  constructor(
    private transportService: TransportService,
    private toastService: ToastService,
    private confirmationService: ConfirmationService,
    private router: Router,
    public dateUtils: DateUtilsService,
    private statusUtils: StatusUtilsService,
    private errorHandler: HttpErrorHandlerService
  ) {}

  ngOnInit(): void {
    this.fetchTransportRequests();
  }

  /**
   * Fetch all transport requests by status
   */
  fetchTransportRequests(): void {
    this.isLoading = true;
    this.error = null;

    // Fetch all requests and filter on client side for better reliability.
    // adminView: true is required so the backend returns every user's
    // requests instead of scoping to just the signed-in admin's own ones
    // (see TransportRequestViewSet.get_queryset's admin_view param) - without
    // it, this page silently only showed the admin's own approved requests.
    this.transportService.getAllRequests({ page_size: 1000, adminView: true }).subscribe({
      next: (response: { results?: TransportRequest[] } | TransportRequest[]) => {
        const allRequests = (Array.isArray(response) ? response : response.results) || [];

        // Anything approved and not yet completed - including older requests
        // that already have a vehicle assigned from before completing was
        // folded into the same action (see hasVehicleAssignment()).
        this.pendingRequests = allRequests.filter((req: TransportRequest) => {
          const statusLower = (req.status || '').toLowerCase();
          return (
            (statusLower.includes('approved') || statusLower.includes('processing')) &&
            !statusLower.includes('completed') &&
            !statusLower.includes('rejected')
          );
        });

        // Filter completed requests
        this.completedRequests = allRequests.filter((req: TransportRequest) => {
          const status = req.status || '';
          const statusLower = status.toLowerCase();
          return statusLower === 'completed';
        });

        this.isLoading = false;
      },
      error: err => {
        console.error('Failed to fetch transport requests:', err);
        this.error = 'Failed to load transport requests';
        this.isLoading = false;
      },
    });
  }

  /**
   * Handle starting transport processing
   * Opens the booking form to assign vehicle details
   */
  handleStartProcessing(): void {
    // Close the confirmation dialog and open the booking form
    this.showProcessingDialog = false;
    this.showCompletingDialog = true;
    // selectedRequest is already set from openProcessingDialog
  }

  /**
   * Handle completing transport processing with booking details.
   * Assigns vehicle details, saves booking details, and immediately marks
   * the request Completed in one action - there is no separate "Processing"
   * step to action afterwards. (The Processing tab/status still exists for
   * any older requests that only had a vehicle assigned before this
   * simplification, but nothing new lands there.)
   */
  handleCompleteProcessing(): void {
    if (!this.selectedRequest) return;

    // Validate required fields
    if (!this.bookingForm.vehicleNumber || !this.bookingForm.driverName) {
      this.toastService.error('Please fill in vehicle number and driver name');
      return;
    }

    this.isLoading = true;

    // Prepare booking details to save to transport request
    const bookingDetails = {
      vehicle_number: this.bookingForm.vehicleNumber,
      driver_name: this.bookingForm.driverName,
      driver_contact: this.bookingForm.driverContact || '',
      pickup_time: this.bookingForm.pickupTime || '',
      additional_notes: this.bookingForm.additionalNotes || '',
    };

    // Prepare vehicle assignment data (for VehicleAssignment model)
    const vehicleData = {
      vehicle_number: this.bookingForm.vehicleNumber,
      driver_name: this.bookingForm.driverName,
      driver_contact: this.bookingForm.driverContact || '',
      driver_license: '', // Optional
      vehicle_capacity: 4, // Default capacity
      status: 'Assigned', // Initial status
    };

    const requestId = this.selectedRequest.id;

    // First, assign vehicle (creates VehicleAssignment entry)
    this.transportService.assignVehicle(requestId, vehicleData).subscribe({
      next: () => {
        // Then, save booking details on the request itself
        this.transportService
          .updateRequest(requestId, { booking_details: bookingDetails })
          .subscribe({
            next: () => {
              // Finally, mark the request Completed - complete() requires a
              // vehicle_assignment to exist, which the step above just created.
              this.transportService.completeRequest(requestId).subscribe({
                next: () => {
                  this.toastService.success('Transport request completed successfully!');
                  this.finishCompleteProcessing();
                },
                error: err => {
                  console.error('❌ Failed to mark request as completed:', err);
                  this.toastService.error(
                    this.errorHandler.getErrorMessage(
                      err,
                      'Booking details saved but failed to mark request as completed'
                    )
                  );
                  this.finishCompleteProcessing();
                },
              });
            },
            error: err => {
              console.error('❌ Failed to save booking details:', err);
              this.toastService.error(
                this.errorHandler.getErrorMessage(
                  err,
                  'Vehicle assigned but failed to save booking details'
                )
              );
              this.finishCompleteProcessing();
            },
          });
      },
      error: err => {
        console.error('❌ Failed to assign vehicle:', err);
        this.toastService.error(this.errorHandler.getErrorMessage(err, 'Failed to assign vehicle'));
        this.isLoading = false;
      },
    });
  }

  /** Shared cleanup for handleCompleteProcessing's terminal (success or partial-failure) paths. */
  private finishCompleteProcessing(): void {
    this.showCompletingDialog = false;
    this.selectedRequest = null;
    this.resetBookingForm();

    setTimeout(() => {
      this.fetchTransportRequests();
      this.isLoading = false;
    }, 500);
  }

  /**
   * Reset booking form
   */
  resetBookingForm(): void {
    this.bookingForm = {
      vehicleNumber: '',
      driverName: '',
      driverContact: '',
      pickupTime: '',
      additionalNotes: '',
    };
  }

  /**
   * Format transport details for display
   */
  formatTransportDetails(request: TransportRequest): string {
    if (!request.transportDetails || request.transportDetails.length === 0) {
      return 'No details available';
    }

    return request.transportDetails
      .map(
        detail =>
          `${detail.from || 'N/A'} → ${detail.to || 'N/A'} (${detail.departureTime || 'N/A'}, ${detail.numberOfPassengers || 0} pax)`
      )
      .join('; ');
  }

  /**
   * Get status badge class - delegates to StatusUtilsService so the same
   * status renders the same color everywhere in the app.
   */
  getStatusColor(status: string): string {
    return this.statusUtils.getStatusBadgeClass(status);
  }

  /**
   * True for older requests that already had a vehicle assigned before
   * completing was folded into the same action as processing - these can
   * be finished directly via completeTransport() instead of reopening the
   * booking form.
   */
  hasVehicleAssignment(request: TransportRequest): boolean {
    return !!(request.vehicle_assignments && request.vehicle_assignments.length > 0);
  }

  /**
   * Switch active tab
   */
  switchTab(tab: 'pending' | 'completed'): void {
    this.activeTab = tab;
  }

  /**
   * Open dialogs
   */
  openProcessingDialog(request: TransportRequest): void {
    this.selectedRequest = request;
    this.showProcessingDialog = true;
  }

  openCompletingDialog(request: TransportRequest): void {
    this.selectedRequest = request;
    this.showCompletingDialog = true;
  }

  openDetailsDialog(request: TransportRequest): void {
    this.selectedRequest = request;
    this.showDetailsDialog = true;
  }

  /**
   * Close dialogs
   */
  closeDialogs(): void {
    this.showProcessingDialog = false;
    this.showCompletingDialog = false;
    this.showDetailsDialog = false;
    this.selectedRequest = null;
  }

  /**
   * Navigate back to transport admin
   */
  goBack(): void {
    this.router.navigate(['/admin/transport']);
  }

  /**
   * View request details
   */
  viewRequest(requestId: number | string): void {
    this.router.navigate(['/transport', requestId]);
  }

  /**
   * Get vehicle type badge class
   */
  getVehicleTypeBadgeClass(type: string): string {
    switch (type) {
      case 'COMPANY_VEHICLE':
        return 'badge-blue';
      case 'HIRED_VEHICLE':
        return 'badge-green';
      case 'RENTAL':
        return 'badge-amber';
      default:
        return 'badge-gray';
    }
  }

  /**
   * Complete transport request
   * Updates status to "Completed"
   */
  completeTransport(transport: TransportRequest): void {
    this.confirmationService
      .confirm({
        title: 'Complete Request',
        message: `Mark transport request ${transport.request_number || transport.id} as completed?`,
        confirmText: 'Complete',
        type: 'success',
      })
      .subscribe(confirmed => {
        if (!confirmed) return;
        this.executeCompleteTransport(transport);
      });
  }

  private executeCompleteTransport(transport: TransportRequest): void {
    this.isProcessing = true;

    // Use the proper workflow action to complete the request
    this.transportService.completeRequest(transport.id).subscribe({
      next: () => {
        this.toastService.success(
          `Request ${transport.request_number || transport.id} marked as completed`
        );
        this.fetchTransportRequests();
        this.isProcessing = false;
      },
      error: err => {
        this.toastService.error(
          this.errorHandler.getErrorMessage(err, 'Failed to complete request')
        );
        this.isProcessing = false;
      },
    });
  }
}
