import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { InsightsService, DashboardSummary, RecentActivity } from '../../../../core/services/insights.service';
import { AppSettingsService } from '../../../../core/services/app-settings.service';
import { Observable, map } from 'rxjs';
import { finalize } from 'rxjs/operators';

@Component({
  selector: 'app-dashboard-home',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './dashboard-home.component.html',
  styleUrls: ['./dashboard-home.component.scss']
})
export class DashboardHomeComponent implements OnInit {
  // Summary statistics
  summary: DashboardSummary = {
    total_trfs: 0,
    pending_trfs: 0,
    approved_trfs: 0,
    rejected_trfs: 0,
    total_travel_cost: 0,
    total_expense_claims: 0,
    active_bookings: 0,
    pending_approvals: 0,
    recent_activities: []
  };

  // Recent activities
  activities: RecentActivity[] = [];
  filteredActivities: RecentActivity[] = [];
  searchQuery: string = '';

  // Loading states
  isLoading = false;
  isFetching = false;
  error = '';

  // Application name
  applicationName$: Observable<string>;

  constructor(
    private insightsService: InsightsService,
    private appSettingsService: AppSettingsService
  ) {
    this.applicationName$ = this.appSettingsService.settings$.pipe(
      map(settings => settings.application_name || 'TMS')
    );
  }

  ngOnInit(): void {
    // Small delay to ensure component is mounted
    setTimeout(() => {
      this.fetchDashboardData();
    }, 100);
  }

  fetchDashboardData(): void {
    // Prevent multiple concurrent requests
    if (this.isFetching) {
      console.log('⏸️ Skipping fetch - already fetching');
      return;
    }

    console.log('🚀 Starting fetchDashboardData...');
    this.isLoading = true;
    this.isFetching = true;
    this.error = '';

    this.insightsService.getDashboardSummary()
      .pipe(
        finalize(() => {
          this.isLoading = false;
          this.isFetching = false;
        })
      )
      .subscribe({
        next: (data) => {
          console.log('✅ Dashboard data loaded:', data);
          this.summary = data;
          this.activities = data.recent_activities || [];
          this.filteredActivities = this.activities;

          if (this.activities.length === 0) {
            console.log('📋 No recent activities found');
          }
        },
        error: (err) => {
          console.error('❌ Error fetching dashboard data:', err);
          this.error = `Failed to load dashboard data: ${err.message || 'Unknown error'}`;
        }
      });
  }

  refresh(): void {
    this.fetchDashboardData();
  }

  onSearchChange(): void {
    if (this.searchQuery.trim() === '') {
      this.filteredActivities = this.activities;
    } else {
      const query = this.searchQuery.toLowerCase();
      this.filteredActivities = this.activities.filter(item =>
        item.title.toLowerCase().includes(query) ||
        item.type.toLowerCase().includes(query) ||
        item.status.toLowerCase().includes(query) ||
        item.date.toLowerCase().includes(query)
      );
    }
  }

  getStatusBadgeClass(status: string): string {
    const statusMap: { [key: string]: string } = {
      'PENDING': 'badge-warning',
      'APPROVED': 'badge-success',
      'REJECTED': 'badge-danger',
      'DRAFT': 'badge-secondary',
      'SUBMITTED': 'badge-info',
      'CONFIRMED': 'badge-success',
      'CANCELLED': 'badge-danger'
    };
    return statusMap[status.toUpperCase()] || 'badge-secondary';
  }

  getActivityIcon(type: string): string {
    const iconMap: { [key: string]: string } = {
      'TRF': 'bi-clipboard-check',
      'TSR': 'bi-clipboard-check',
      'EXPENSE_CLAIM': 'bi-receipt',
      'CLAIM': 'bi-receipt',
      'VISA': 'bi-file-earmark-text',
      'FLIGHT': 'bi-airplane',
      'HOTEL': 'bi-building',
      'ACCOMMODATION': 'bi-building',
      'TRANSPORT': 'bi-car-front'
    };
    return iconMap[type.toUpperCase()] || 'bi-file-earmark-text';
  }

  getActivityIconColor(status: string): string {
    return status.toUpperCase() === 'APPROVED' ? 'text-success' : 'text-primary';
  }

  getActivityIconBg(status: string): string {
    return status.toUpperCase() === 'APPROVED' ? 'bg-success-light' : 'bg-muted-light';
  }

  /**
   * Get the correct route for viewing an activity item based on its type
   */
  getActivityRoute(item: RecentActivity): string {
    const type = item.type.toUpperCase();

    switch (type) {
      case 'TRF':
      case 'TSR':
        return `/trf/view/${item.id}`;
      case 'EXPENSE_CLAIM':
      case 'CLAIM':
        return `/expenses/${item.id}`;
      case 'VISA':
        return `/visa/${item.id}`;
      case 'FLIGHT':
        return `/bookings/flights/${item.id}`;
      case 'HOTEL':
      case 'ACCOMMODATION':
        return `/accommodation/${item.id}`;
      case 'TRANSPORT':
        return `/transport/${item.id}`;
      default:
        // Fallback to TRF view if type is unknown
        return `/trf/view/${item.id}`;
    }
  }
}
