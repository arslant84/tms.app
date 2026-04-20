import { CommonModule } from '@angular/common';
import { Component, type OnDestroy, type OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { type Observable, Subject, map, takeUntil } from 'rxjs';
import { finalize } from 'rxjs/operators';
import { AppSettingsService } from '../../../../core/services/app-settings.service';
import { InsightsService, type DashboardSummary, type RecentActivity } from '../../../../core/services/insights.service';
import { extractData } from '../../../../core/utils/api-response.handler';
import { StatusUtilsService } from '../../../../core/utils/status-utils.service';

@Component({
  selector: 'app-dashboard-home',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './dashboard-home.component.html',
  styleUrls: ['./dashboard-home.component.scss']
})
export class DashboardHomeComponent implements OnInit, OnDestroy {
  // Summary statistics
  summary: DashboardSummary = {
    total_trfs: 0,
    pending_trfs: 0,
    approved_trfs: 0,
    rejected_trfs: 0,
    total_travel_cost: 0,
    pending_expense_claims: 0,
    active_bookings: 0,
    pending_approvals: 0,
    pending_transport_requests: 0,
    pending_visa_applications: 0,
    recent_activities: []
  };

  // Recent activities
  activities: RecentActivity[] = [];
  filteredActivities: RecentActivity[] = [];
  searchQuery = '';

  // Loading states
  isLoading = false;
  isFetching = false;
  error = '';

  // Application name
  applicationName$: Observable<string>;

  private destroy$ = new Subject<void>();

  private insightsService = inject(InsightsService);
  private appSettingsService = inject(AppSettingsService);
  statusUtils = inject(StatusUtilsService);

  constructor() {
    this.applicationName$ = this.appSettingsService.settings$.pipe(
      map(settings => settings.application_name || 'TMS')
    );
  }

  ngOnInit(): void {
    setTimeout(() => {
      this.fetchDashboardData();
    }, 100);
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  fetchDashboardData(): void {
    if (this.isFetching) {
      return;
    }

    this.isLoading = true;
    this.isFetching = true;
    this.error = '';

    this.insightsService.getDashboardSummary()
      .pipe(
        takeUntil(this.destroy$),
        map(response => extractData<DashboardSummary>(response)),
        finalize(() => {
          this.isLoading = false;
          this.isFetching = false;
        })
      )
      .subscribe({
        next: (data) => {
          if (data) {
            this.summary = data;
            this.activities = data.recent_activities || [];
            this.filteredActivities = this.activities;
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
    return this.statusUtils.getStatusBadgeClass(status);
  }

  getActivityIcon(type: string): string {
    const iconMap: Record<string, string> = {
      'TRF': 'bi-clipboard-check',
      'TSR': 'bi-clipboard-check',
      'VISA': 'bi-file-earmark-text',
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

  getActivityRoute(item: RecentActivity): string {
    const type = item.type.toUpperCase();

    switch (type) {
      case 'TRF':
      case 'TSR':
        return `/trf/${item.id}`;
      case 'VISA':
        return `/visa/${item.id}`;
      case 'ACCOMMODATION':
        return `/accommodation/${item.id}`;
      case 'TRANSPORT':
        return `/transport/${item.id}`;
      default:
        console.warn(`Unknown activity type: ${item.type}, ID: ${item.id}`);
        return `/trf/${item.id}`;
    }
  }
}
