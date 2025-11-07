import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { TransportService, TransportRequest, VehicleAssignment } from '../../transport/services/transport.service';
import { ToastService } from '../../../core/services/toast.service';

interface PendingTransport {
  id: number;
  request_number: string;
  requestorName: string;
  department: string;
  purpose: string;
  transportType: string;
  passengers: number;
  pickupLocation: string;
  dropoffLocation: string;
  scheduledDate: string;
  scheduledTime: string;
  status: string;
  requestedDate: string;
}

interface AssignedTransport {
  id: number;
  request_number: string;
  requestorName: string;
  vehicleNumber: string;
  vehicleType: string;
  driverName: string;
  driverContact: string;
  scheduledDate: string;
  status: string;
  assignmentDate: string;
}

@Component({
  selector: 'app-transport-processing',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './transport-processing.component.html',
  styleUrl: './transport-processing.component.scss'
})
export class TransportProcessingComponent implements OnInit {
  activeTab: 'pending' | 'assigned' = 'pending';

  // Pending Transport Requests
  pendingTransports: PendingTransport[] = [];
  isLoadingPending = false;
  errorPending: string | null = null;

  // Assigned Transport Requests
  assignedTransports: AssignedTransport[] = [];
  isLoadingAssigned = false;

  // Selected Request for processing
  selectedRequest: PendingTransport | null = null;
  isProcessing = false;

  // Vehicle assignment form fields
  vehicleData: VehicleAssignment = {
    vehicle_number: '',
    vehicle_type: 'COMPANY_VEHICLE',
    vehicle_capacity: 4,
    driver_name: '',
    driver_contact: '',
    driver_license: '',
    assignment_date: new Date().toISOString().split('T')[0]
  };

  // Vehicle types
  vehicleTypes = [
    { value: 'COMPANY_VEHICLE', label: 'Company Vehicle' },
    { value: 'HIRED_VEHICLE', label: 'Hired Vehicle' },
    { value: 'RENTAL', label: 'Rental' }
  ];

  constructor(
    private transportService: TransportService,
    private toastService: ToastService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.fetchPendingTransports();
    this.fetchAssignedTransports();
  }

  /**
   * Fetch pending transport requests (Approved status)
   */
  fetchPendingTransports(): void {
    this.isLoadingPending = true;
    this.errorPending = null;

    this.transportService.getAllRequests({ status: 'Approved' }).subscribe({
      next: (response: any) => {
        const requests = response.results || response;

        this.pendingTransports = requests.map((req: any) => {
          // Extract transport details from transportDetails array
          const transportDetails = req.transportDetails || [];
          const firstTransport = transportDetails[0] || {};

          // Calculate total passengers
          const totalPassengers = transportDetails.reduce(
            (sum: number, detail: any) => sum + (detail.numberOfPassengers || 0),
            0
          );

          return {
            id: req.id,
            request_number: req.request_number || `TRN-${req.id}`,
            requestorName: req.requestorName || 'N/A',
            department: req.department || 'N/A',
            purpose: req.purpose || 'N/A',
            transportType: firstTransport.transportType || 'N/A',
            passengers: totalPassengers,
            pickupLocation: firstTransport.pickupLocation || 'N/A',
            dropoffLocation: firstTransport.dropoffLocation || 'N/A',
            scheduledDate: firstTransport.departureDate || 'N/A',
            scheduledTime: firstTransport.departureTime || 'N/A',
            status: req.status,
            requestedDate: req.createdAt || req.created_at
          };
        });

        this.isLoadingPending = false;
      },
      error: (err) => {
        console.error('Failed to fetch pending transport requests:', err);
        this.errorPending = 'Failed to load pending requests. Please try again.';
        this.pendingTransports = [];
        this.isLoadingPending = false;
      }
    });
  }

  /**
   * Fetch assigned transport requests (Processing with Transport Admin status)
   */
  fetchAssignedTransports(): void {
    this.isLoadingAssigned = true;

    this.transportService.getAllRequests({ status: 'Processing with Transport Admin' }).subscribe({
      next: (response: any) => {
        const requests = response.results || response;

        this.assignedTransports = requests.map((req: any) => {
          // Extract vehicle assignment data
          const vehicleInfo = req.vehicle_assignment || {};
          const transportDetails = req.transportDetails || [];
          const firstTransport = transportDetails[0] || {};

          return {
            id: req.id,
            request_number: req.request_number || `TRN-${req.id}`,
            requestorName: req.requestorName || 'N/A',
            vehicleNumber: vehicleInfo.vehicle_number || 'N/A',
            vehicleType: vehicleInfo.vehicle_type || 'N/A',
            driverName: vehicleInfo.driver_name || 'N/A',
            driverContact: vehicleInfo.driver_contact || 'N/A',
            scheduledDate: firstTransport.departureDate || 'N/A',
            status: req.status,
            assignmentDate: vehicleInfo.assignment_date || req.updated_at
          };
        });

        this.isLoadingAssigned = false;
      },
      error: (err) => {
        console.error('Failed to fetch assigned transport requests:', err);
        this.assignedTransports = [];
        this.isLoadingAssigned = false;
      }
    });
  }

  /**
   * Select transport request for processing
   */
  selectRequest(request: PendingTransport): void {
    this.selectedRequest = request;
    this.resetFormFields();

    // Pre-fill the assignment date with scheduled date if available
    if (request.scheduledDate && request.scheduledDate !== 'N/A') {
      this.vehicleData.assignment_date = request.scheduledDate;
    }
  }

  /**
   * Reset form fields
   */
  resetFormFields(): void {
    this.vehicleData = {
      vehicle_number: '',
      vehicle_type: 'COMPANY_VEHICLE',
      vehicle_capacity: 4,
      driver_name: '',
      driver_contact: '',
      driver_license: '',
      assignment_date: new Date().toISOString().split('T')[0]
    };
  }

  /**
   * Assign vehicle to transport request
   */
  assignVehicle(): void {
    if (!this.selectedRequest) {
      this.toastService.error('No request selected');
      return;
    }

    if (!this.vehicleData.vehicle_number || !this.vehicleData.driver_name || !this.vehicleData.driver_contact) {
      this.toastService.error('Please fill in all required fields');
      return;
    }

    this.isProcessing = true;

    this.transportService.assignVehicle(this.selectedRequest.id, this.vehicleData).subscribe({
      next: () => {
        this.toastService.success(`Vehicle assigned successfully for ${this.selectedRequest!.requestorName}`);
        this.fetchPendingTransports();
        this.fetchAssignedTransports();
        this.selectedRequest = null;
        this.resetFormFields();
        this.isProcessing = false;
      },
      error: (err) => {
        this.toastService.error('Failed to assign vehicle: ' + (err.error?.message || err.message || 'Unknown error'));
        this.isProcessing = false;
      }
    });
  }

  /**
   * Reject transport request (No vehicles available)
   */
  noVehiclesAvailable(): void {
    if (!this.selectedRequest) {
      this.toastService.error('No request selected');
      return;
    }

    if (!confirm(`Reject transport request ${this.selectedRequest.request_number} due to no available vehicles?`)) {
      return;
    }

    this.isProcessing = true;

    this.transportService.rejectRequest(
      this.selectedRequest.id,
      'No vehicles available for requested dates. Request rejected by Transport Admin.'
    ).subscribe({
      next: () => {
        this.toastService.success(`Request ${this.selectedRequest!.request_number} rejected due to no available vehicles`);
        this.fetchPendingTransports();
        this.selectedRequest = null;
        this.resetFormFields();
        this.isProcessing = false;
      },
      error: (err) => {
        this.toastService.error('Failed to reject request: ' + (err.error?.message || err.message || 'Unknown error'));
        this.isProcessing = false;
      }
    });
  }

  /**
   * Complete transport request
   */
  completeTransport(transport: AssignedTransport): void {
    if (!confirm(`Mark transport request ${transport.request_number} as completed?`)) {
      return;
    }

    this.isProcessing = true;

    this.transportService.completeRequest(transport.id).subscribe({
      next: () => {
        this.toastService.success(`Request ${transport.request_number} marked as completed`);
        this.fetchPendingTransports();
        this.fetchAssignedTransports();
        this.isProcessing = false;
      },
      error: (err) => {
        this.toastService.error('Failed to complete request: ' + (err.error?.message || err.message || 'Unknown error'));
        this.isProcessing = false;
      }
    });
  }

  /**
   * Switch tab
   */
  switchTab(tab: 'pending' | 'assigned'): void {
    this.activeTab = tab;
    if (tab === 'pending' && this.pendingTransports.length === 0) {
      this.fetchPendingTransports();
    } else if (tab === 'assigned' && this.assignedTransports.length === 0) {
      this.fetchAssignedTransports();
    }
  }

  /**
   * View request details
   */
  viewRequest(requestId: number): void {
    this.router.navigate(['/transport', requestId]);
  }

  /**
   * Navigate back to overview
   */
  goToOverview(): void {
    this.router.navigate(['/admin/transport']);
  }

  /**
   * Format date
   */
  formatDate(date: string | Date | null | undefined): string {
    if (!date) return 'N/A';
    try {
      const d = typeof date === 'string' ? new Date(date) : date;
      return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    } catch {
      return 'Invalid Date';
    }
  }

  /**
   * Get status badge class
   */
  getStatusClass(status: string): string {
    const statusLower = status.toLowerCase();
    if (statusLower === 'approved') return 'badge-success';
    if (statusLower.includes('processing')) return 'badge-info';
    if (statusLower === 'completed') return 'badge-success';
    return 'badge-secondary';
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
   * Retry loading pending transports
   */
  retryPending(): void {
    this.fetchPendingTransports();
  }

  /**
   * Cancel selection
   */
  cancelSelection(): void {
    this.selectedRequest = null;
    this.resetFormFields();
  }
}
