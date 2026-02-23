import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { TrfService } from '../../../trf-management/services/trf.service';
import { ToastService } from '../../../../core/services/toast.service';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { DepartmentNamePipe } from '../../../../core/pipes/department-name.pipe';

interface FlightApplication {
  id: string;
  requestNumber: string;
  requestorName: string;
  department: string;
  purpose: string;
  status: string;
  travelType: string;
  submittedAt: string;
  destinationSummary?: string;
  hasFlightBooking?: boolean;
  flightDetails?: any;
}

interface FlightStats {
  total: number;
  pending: number;
  approved: number;
  processing: number;
}

@Component({
  selector: 'app-flights-admin-overview',
  standalone: true,
  imports: [CommonModule, FormsModule, DepartmentNamePipe],
  templateUrl: './flights-admin-overview.component.html',
  styleUrl: './flights-admin-overview.component.scss'
})
export class FlightsAdminOverviewComponent implements OnInit {
  applications: FlightApplication[] = [];
  filteredApplications: FlightApplication[] = [];
  isLoading = false;
  isLoadingMore = false;
  error: string | null = null;

  // Filters
  searchTerm = '';
  statusFilter = 'all';
  travelTypeFilter = 'all';

  // Stats
  stats: FlightStats = {
    total: 0,
    pending: 0,
    approved: 0,
    processing: 0
  };

  // Status options
  statusOptions = [
    { value: 'all', label: 'All Statuses' },
    { value: 'Approved', label: 'Approved' },
    { value: 'Awaiting Visa', label: 'Awaiting Visa' },
    { value: 'TRF Processed', label: 'TRF Processed' },
    { value: 'Rejected', label: 'Rejected' }
  ];

  // Travel type options
  travelTypeOptions = [
    { value: 'all', label: 'All Types' },
    { value: 'Overseas', label: 'Overseas' },
    { value: 'Home Leave Passage', label: 'Home Leave Passage' },
    { value: 'Home Leave', label: 'Home Leave' }
  ];

  constructor(
    private trfService: TrfService,
    private toastService: ToastService,
    private router: Router,
    public dateUtils: DateUtilsService
  ) {}

  ngOnInit(): void {
    this.fetchFlightStats();
    this.fetchFlightApplications();
  }

  /**
   * Fetch flight statistics
   */
  fetchFlightStats(): void {
    // Calculate stats from TRFs
    this.trfService.getAllTrfs({ adminView: true }).subscribe({
      next: (response: any) => {
        const trfs = response.results || response.trfs || [];

        // Filter for TRFs requiring flights (Overseas, Home Leave, Domestic with itinerary)
        const flightTrfs = trfs.filter((trf: any) => {
          if (trf.travel_type === 'Overseas' || trf.travel_type === 'Home Leave Passage' || trf.travel_type === 'Home Leave') {
            return true;
          }
          if (trf.travel_type === 'Domestic' && trf.domestic_travel_details?.itinerary?.length > 0) {
            return true;
          }
          return false;
        });

        this.stats = {
          total: flightTrfs.length,
          pending: flightTrfs.filter((trf: any) =>
            trf.status.includes('Pending')
          ).length,
          approved: flightTrfs.filter((trf: any) =>
            trf.status === 'Approved' && !trf.has_flight_booking
          ).length,
          processing: flightTrfs.filter((trf: any) =>
            trf.has_flight_booking === true
          ).length
        };
      },
      error: (err) => {
        console.error('Failed to fetch flight statistics:', err);
        this.stats = { total: 0, pending: 0, approved: 0, processing: 0 };
      }
    });
  }

  /**
   * Fetch flight applications (TRFs requiring flights)
   */
  fetchFlightApplications(): void {
    this.isLoading = true;
    this.error = null;

    this.trfService.getAllTrfs({ adminView: true }).subscribe({
      next: (response: any) => {
        const trfs = response.results || response.trfs || [];

        // Filter for TRFs requiring flights (any approved TRF with travel)
        // Include: Overseas, Home Leave Passage, and Domestic trips with flight segments
        const flightTrfs = trfs.filter((trf: any) => {
          // Include Overseas and Home Leave (always require flights)
          if (trf.travel_type === 'Overseas' || trf.travel_type === 'Home Leave Passage' || trf.travel_type === 'Home Leave') {
            return true;
          }

          // Include Domestic if it has itinerary (flight segments)
          if (trf.travel_type === 'Domestic') {
            const hasItinerary = trf.domestic_travel_details?.itinerary?.length > 0;
            return hasItinerary;
          }

          return false;
        });

        // Format TRF data for display
        this.applications = flightTrfs.map((trf: any) => {
          let destinationSummary = 'N/A';

          // Extract destination from itinerary
          if (trf.overseas_travel_details?.itinerary?.length) {
            destinationSummary = trf.overseas_travel_details.itinerary
              .map((s: any) => `${s.from_location || s.from} → ${s.to_location || s.to}`)
              .join(', ');
          } else if (trf.home_leave_details?.itinerary?.length) {
            destinationSummary = trf.home_leave_details.itinerary
              .map((s: any) => `${s.from_location || s.from} → ${s.to_location || s.to}`)
              .join(', ');
          } else if (trf.domestic_travel_details?.itinerary?.length) {
            destinationSummary = trf.domestic_travel_details.itinerary
              .map((s: any) => `${s.from_location || s.from} → ${s.to_location || s.to}`)
              .join(', ');
          } else if (trf.purpose) {
            destinationSummary = trf.purpose.substring(0, 50) + '...';
          }

          return {
            id: trf.id,
            requestNumber: trf.request_number || `#${trf.id}`,
            requestorName: trf.requestor_name || 'N/A',
            department: trf.department || 'N/A',
            purpose: trf.purpose || 'N/A',
            status: trf.status,
            travelType: trf.travel_type,
            submittedAt: trf.submitted_at || trf.created_at,
            destinationSummary,
            hasFlightBooking: trf.has_flight_booking,
            flightDetails: trf.flight_details
          };
        });

        this.applyFilters();
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Failed to fetch flight applications:', err);
        this.error = 'Failed to load flight applications. Please try again.';
        this.applications = [];
        this.filteredApplications = [];
        this.isLoading = false;
      }
    });
  }

  /**
   * Apply filters to applications
   */
  applyFilters(): void {
    this.filteredApplications = this.applications.filter(app => {
      // Search filter
      const matchesSearch = !this.searchTerm ||
        app.requestNumber.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
        app.requestorName.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
        app.purpose.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
        (app.destinationSummary && app.destinationSummary.toLowerCase().includes(this.searchTerm.toLowerCase()));

      // Status filter
      const matchesStatus = this.statusFilter === 'all' || app.status === this.statusFilter;

      // Travel type filter
      const matchesType = this.travelTypeFilter === 'all' || app.travelType === this.travelTypeFilter;

      return matchesSearch && matchesStatus && matchesType;
    });
  }

  /**
   * Handle search term change
   */
  onSearchChange(): void {
    this.applyFilters();
  }

  /**
   * Handle status filter change
   */
  onStatusFilterChange(): void {
    this.applyFilters();
  }

  /**
   * Handle travel type filter change
   */
  onTravelTypeFilterChange(): void {
    this.applyFilters();
  }

  /**
   * Load more applications (pagination placeholder)
   */
  loadMoreApplications(): void {
    this.isLoadingMore = true;
    setTimeout(() => {
      this.isLoadingMore = false;
      this.toastService.info('All applications loaded');
    }, 1000);
  }

  /**
   * Navigate to processing dashboard
   */
  goToProcessingDashboard(): void {
    this.router.navigate(['/admin/flights/processing']);
  }

  /**
   * View TRF details
   */
  viewTrf(trfId: string): void {
    this.router.navigate(['/trf', trfId]);
  }

  /**
   * Get status badge class
   */
  getStatusClass(status: string): string {
    const statusLower = status.toLowerCase();
    if (statusLower === 'approved') return 'badge-success';
    if (statusLower.includes('awaiting')) return 'badge-warning';
    if (statusLower.includes('processed')) return 'badge-info';
    if (statusLower.includes('pending')) return 'badge-warning';
    if (statusLower === 'rejected') return 'badge-red';
    if (statusLower === 'completed') return 'badge-green';
    return 'badge-gray';
  }

  /**
   * Get travel type badge class
   */
  getTravelTypeBadge(travelType: string): string {
    switch (travelType) {
      case 'Overseas': return 'badge-blue';
      case 'Home Leave Passage':
      case 'Home Leave': return 'badge-purple';
      case 'Domestic': return 'badge-green';
      default: return 'badge-gray';
    }
  }

  /**
   * Retry loading
   */
  retry(): void {
    this.fetchFlightStats();
    this.fetchFlightApplications();
  }
}
