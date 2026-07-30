import { CommonModule } from '@angular/common';
import { Component, inject, type OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { DepartmentNamePipe } from '../../../../core/pipes/department-name.pipe';
import { ToastService } from '../../../../core/services/toast.service';
import { DateUtilsService } from '../../../../core/utils/date-utils.service';
import { StatusUtilsService } from '../../../../core/utils/status-utils.service';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';
import { TrfService } from '../../../trf-management/services/trf.service';

interface ItinerarySegment {
  from_location?: string;
  from?: string;
  to_location?: string;
  to?: string;
}

interface TrfRaw {
  id: number;
  travel_type: string;
  status: string;
  purpose?: string;
  request_number?: string;
  requestor_name?: string;
  staff_id?: string;
  department?: string;
  submitted_at?: string;
  created_at?: string;
  has_flight_booking?: boolean;
  flight_details?: unknown;
  overseas_travel_details?: { itinerary?: ItinerarySegment[] };
  home_leave_details?: { itinerary?: ItinerarySegment[] };
  domestic_travel_details?: { itinerary?: ItinerarySegment[] };
}

interface FlightApplication {
  id: string;
  requestNumber: string;
  requestorName: string;
  staffId: string;
  department: string;
  purpose: string;
  status: string;
  travelType: string;
  submittedAt: string;
  destinationSummary?: string;
  hasFlightBooking?: boolean;
  flightDetails?: unknown;
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
  imports: [CommonModule, FormsModule, DepartmentNamePipe, LoadingSpinnerComponent],
  templateUrl: './flights-admin-overview.component.html',
  styleUrl: './flights-admin-overview.component.scss',
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
    processing: 0,
  };

  // Status options
  statusOptions = [{ value: 'all', label: 'All Statuses' }];

  // Travel type options
  travelTypeOptions = [{ value: 'all', label: 'All Types' }];

  private trfService = inject(TrfService);
  private toastService = inject(ToastService);
  private router = inject(Router);
  dateUtils = inject(DateUtilsService);
  private statusUtils = inject(StatusUtilsService);

  ngOnInit(): void {
    this.fetchFlightApplications();
  }

  /**
   * Fetch flight applications and derive stats in a single call.
   */
  fetchFlightApplications(): void {
    this.isLoading = true;
    this.error = null;

    this.trfService.getAllTrfs({ adminView: true, page_size: 1000 }).subscribe({
      next: (response: { results?: TrfRaw[]; trfs?: TrfRaw[] }) => {
        const trfs: TrfRaw[] = response.results || response.trfs || [];

        const flightTrfs = trfs.filter(trf => {
          if (
            trf.travel_type === 'Overseas' ||
            trf.travel_type === 'Home Leave Passage' ||
            trf.travel_type === 'Home Leave'
          ) {
            return true;
          }
          if (trf.travel_type === 'Domestic') {
            return (trf.domestic_travel_details?.itinerary?.length ?? 0) > 0;
          }
          return false;
        });

        const segmentLabel = (s: ItinerarySegment) =>
          `${s.from_location || s.from || ''} → ${s.to_location || s.to || ''}`;

        this.applications = flightTrfs.map(trf => {
          let destinationSummary = 'N/A';
          if (trf.overseas_travel_details?.itinerary?.length) {
            destinationSummary = trf.overseas_travel_details.itinerary.map(segmentLabel).join(', ');
          } else if (trf.home_leave_details?.itinerary?.length) {
            destinationSummary = trf.home_leave_details.itinerary.map(segmentLabel).join(', ');
          } else if (trf.domestic_travel_details?.itinerary?.length) {
            destinationSummary = trf.domestic_travel_details.itinerary.map(segmentLabel).join(', ');
          } else if (trf.purpose) {
            destinationSummary = `${trf.purpose.substring(0, 50)}...`;
          }
          return {
            id: String(trf.id),
            requestNumber: trf.request_number || `#${trf.id}`,
            requestorName: trf.requestor_name || 'N/A',
            staffId: trf.staff_id || 'N/A',
            department: trf.department || 'N/A',
            purpose: trf.purpose || 'N/A',
            status: trf.status,
            travelType: trf.travel_type,
            submittedAt: trf.submitted_at || trf.created_at || '',
            destinationSummary,
            hasFlightBooking: trf.has_flight_booking,
            flightDetails: trf.flight_details,
          };
        });

        this.stats = {
          total: flightTrfs.length,
          pending: flightTrfs.filter(trf => trf.status?.includes('Pending')).length,
          approved: flightTrfs.filter(trf => trf.status === 'Approved' && !trf.has_flight_booking)
            .length,
          processing: flightTrfs.filter(trf => trf.has_flight_booking === true).length,
        };

        this.applyFilters();
        const uniqueStatuses = [
          ...new Set(this.applications.map(a => a.status).filter(Boolean)),
        ].sort();
        this.statusOptions = [
          { value: 'all', label: 'All Statuses' },
          ...uniqueStatuses.map(s => ({ value: s, label: s })),
        ];
        const uniqueTypes = [
          ...new Set(this.applications.map(a => a.travelType).filter(Boolean)),
        ].sort();
        this.travelTypeOptions = [
          { value: 'all', label: 'All Types' },
          ...uniqueTypes.map(t => ({ value: t, label: t })),
        ];
        this.isLoading = false;
      },
      error: err => {
        console.error('Failed to fetch flight applications:', err);
        this.error = 'Failed to load flight applications. Please try again.';
        this.applications = [];
        this.filteredApplications = [];
        this.isLoading = false;
      },
    });
  }

  /**
   * Apply filters to applications
   */
  applyFilters(): void {
    this.filteredApplications = this.applications.filter(app => {
      // Search filter
      const matchesSearch =
        !this.searchTerm ||
        app.requestNumber.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
        app.requestorName.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
        app.purpose.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
        app.destinationSummary?.toLowerCase().includes(this.searchTerm.toLowerCase());

      // Status filter
      const matchesStatus = this.statusFilter === 'all' || app.status === this.statusFilter;

      // Travel type filter
      const matchesType =
        this.travelTypeFilter === 'all' || app.travelType === this.travelTypeFilter;

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
   * Get status badge class - delegates to StatusUtilsService so the same
   * status renders the same color everywhere in the app.
   */
  getStatusClass(status: string): string {
    return this.statusUtils.getStatusBadgeClass(status);
  }

  /**
   * Get travel type badge class
   */
  getTravelTypeBadge(travelType: string): string {
    switch (travelType) {
      case 'Overseas':
        return 'badge-blue';
      case 'Home Leave Passage':
      case 'Home Leave':
        return 'badge-purple';
      case 'Domestic':
        return 'badge-green';
      default:
        return 'badge-gray';
    }
  }

  /**
   * Retry loading
   */
  retry(): void {
    this.fetchFlightApplications();
  }
}
