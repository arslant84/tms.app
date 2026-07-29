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

interface BookingDetails {
  vehicleType: string;
  vehicleNumber: string;
  driverName: string;
  driverContact?: string;
  pickupTime?: string;
  dropoffTime?: string;
  actualRoute?: string;
  bookingReference?: string;
  additionalNotes?: string;
}

@Component({
  selector: 'app-transport-processing',
  standalone: true,
  imports: [CommonModule, FormsModule, DepartmentNamePipe, LoadingSpinnerComponent],
  templateUrl: './transport-processing.component.html',
  styleUrl: './transport-processing.component.scss'
})
export class TransportProcessingComponent implements OnInit {
  activeTab: 'approved' | 'processing' | 'completed' = 'approved';

  // Transport Requests by status
  approvedRequests: TransportRequest[] = [];
  processingRequests: TransportRequest[] = [];
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
    vehicleType: '',
    vehicleNumber: '',
    driverName: '',
    driverContact: '',
    pickupTime: '',
    dropoffTime: '',
    actualRoute: '',
    bookingReference: '',
    additionalNotes: ''
  };

  constructor(
    private transportService: TransportService,
    private toastService: ToastService,
    private confirmationService: ConfirmationService,
    private router: Router,
    public dateUtils: DateUtilsService,
    private statusUtils: StatusUtilsService
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

    // Fetch all requests and filter on client side for better reliability
    this.transportService.getAllRequests({ page_size: 1000 }).subscribe({
      next: (response: any) => {
        const allRequests = response.results || response || [];

        // Filter approved requests - those approved by HOD and ready for transport admin
        this.approvedRequests = allRequests.filter((req: TransportRequest) => {
          const status = req.status || '';
          const statusLower = status.toLowerCase();
          const hasVehicleAssignment = req.vehicle_assignments && req.vehicle_assignments.length > 0;

          // Include requests that are approved, not completed/rejected, and don't have a vehicle assigned yet
          const isApproved = (
            statusLower.includes('approved') &&
            !statusLower.includes('processing') &&
            !statusLower.includes('completed') &&
            !statusLower.includes('rejected') &&
            !hasVehicleAssignment  // Not yet processed
          );
          return isApproved;
        });

        // Filter processing requests - those with vehicle assignments (being processed)
        this.processingRequests = allRequests.filter((req: TransportRequest) => {
          const status = req.status || '';
          const statusLower = status.toLowerCase();
          const hasVehicleAssignment = req.vehicle_assignments && req.vehicle_assignments.length > 0;

          // Exclude completed requests from processing tab
          const isCompleted = statusLower === 'completed';

          // Show in processing if:
          // 1. Status includes "processing", OR
          // 2. Request has vehicle assignment (vehicle assigned = being processed)
          // BUT NOT if status is "Completed"
          const isProcessing = !isCompleted && (statusLower.includes('processing') || hasVehicleAssignment);
          return isProcessing;
        });

        // Filter completed requests
        this.completedRequests = allRequests.filter((req: TransportRequest) => {
          const status = req.status || '';
          const statusLower = status.toLowerCase();
          return statusLower === 'completed';
        });

        this.isLoading = false;
      },
      error: (err) => {
        console.error('Failed to fetch transport requests:', err);
        this.error = 'Failed to load transport requests';
        this.isLoading = false;
      }
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
   * Handle completing transport processing with booking details
   * Assigns vehicle details and saves booking details to request
   */
  handleCompleteProcessing(): void {
    if (!this.selectedRequest) return;

    // Validate required fields
    if (!this.bookingForm.vehicleType || !this.bookingForm.vehicleNumber || !this.bookingForm.driverName) {
      this.toastService.error('Please fill in vehicle type, vehicle number, and driver name');
      return;
    }

    this.isLoading = true;

    // Prepare booking details to save to transport request
    const bookingDetails = {
      vehicle_type: this.bookingForm.vehicleType,
      vehicle_number: this.bookingForm.vehicleNumber,
      driver_name: this.bookingForm.driverName,
      driver_contact: this.bookingForm.driverContact || '',
      pickup_time: this.bookingForm.pickupTime || '',
      dropoff_time: this.bookingForm.dropoffTime || '',
      actual_route: this.bookingForm.actualRoute || '',
      booking_reference: this.bookingForm.bookingReference || '',
      additional_notes: this.bookingForm.additionalNotes || ''
    };

    // Prepare vehicle assignment data (for VehicleAssignment model)
    const vehicleData = {
      vehicle_type: this.bookingForm.vehicleType,
      vehicle_number: this.bookingForm.vehicleNumber,
      driver_name: this.bookingForm.driverName,
      driver_contact: this.bookingForm.driverContact || '',
      driver_license: '', // Optional
      vehicle_capacity: 4, // Default capacity
      status: 'Assigned' // Initial status
    };

    // First, assign vehicle (creates VehicleAssignment entry)
    this.transportService.assignVehicle(this.selectedRequest.id, vehicleData).subscribe({
      next: () => {
        // Then, update transport request with booking details
        this.transportService.updateRequest(this.selectedRequest!.id, {
          booking_details: bookingDetails
        }).subscribe({
          next: () => {
            this.toastService.success(`Vehicle assigned and booking details saved! Request moved to processing.`);
            this.showCompletingDialog = false;
            this.selectedRequest = null;
            this.resetBookingForm();

            // Refresh to show the request in the Processing tab
            setTimeout(() => {
              this.fetchTransportRequests();
              this.isLoading = false;
            }, 500);
          },
          error: (err) => {
            console.error('❌ Failed to save booking details:', err);
            this.toastService.error('Vehicle assigned but failed to save booking details: ' + (err.error?.message || err.message));
            this.isLoading = false;
            this.fetchTransportRequests(); // Still refresh to show vehicle assignment
          }
        });
      },
      error: (err) => {
        console.error('❌ Failed to assign vehicle:', err);
        this.toastService.error('Failed to assign vehicle: ' + (err.error?.message || err.message));
        this.isLoading = false;
      }
    });
  }

  /**
   * Reset booking form
   */
  resetBookingForm(): void {
    this.bookingForm = {
      vehicleType: '',
      vehicleNumber: '',
      driverName: '',
      driverContact: '',
      pickupTime: '',
      dropoffTime: '',
      actualRoute: '',
      bookingReference: '',
      additionalNotes: ''
    };
  }

  /**
   * Format transport details for display
   */
  formatTransportDetails(request: TransportRequest): string {
    if (!request.transportDetails || request.transportDetails.length === 0) {
      return 'No details available';
    }

    return request.transportDetails.map(detail =>
      `${detail.from || 'N/A'} → ${detail.to || 'N/A'} (${detail.departureTime || 'N/A'}, ${detail.numberOfPassengers || 0} pax)`
    ).join('; ');
  }

  /**
   * Get status badge class - delegates to StatusUtilsService so the same
   * status renders the same color everywhere in the app.
   */
  getStatusColor(status: string): string {
    return this.statusUtils.getStatusBadgeClass(status);
  }

  /**
   * Switch active tab
   */
  switchTab(tab: 'approved' | 'processing' | 'completed'): void {
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
      case 'COMPANY_VEHICLE': return 'badge-blue';
      case 'HIRED_VEHICLE': return 'badge-green';
      case 'RENTAL': return 'badge-amber';
      default: return 'badge-gray';
    }
  }

  /**
   * Complete transport request
   * Updates status to "Completed"
   */
  completeTransport(transport: any): void {
    this.confirmationService.confirm({
      title: 'Complete Request',
      message: `Mark transport request ${transport.request_number || transport.id} as completed?`,
      confirmText: 'Complete',
      type: 'success'
    }).subscribe(confirmed => {
      if (!confirmed) return;
      this.executeCompleteTransport(transport);
    });
  }

  private executeCompleteTransport(transport: any): void {
    this.isProcessing = true;

    // Use the proper workflow action to complete the request
    this.transportService.completeRequest(transport.id).subscribe({
      next: () => {
        this.toastService.success(`Request ${transport.request_number || transport.id} marked as completed`);
        this.fetchTransportRequests();
        this.isProcessing = false;
      },
      error: (err) => {
        this.toastService.error('Failed to complete request: ' + (err.error?.message || err.message));
        this.isProcessing = false;
      }
    });
  }
}
