import { Component, type OnInit, type OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { type NavigationExtras, RouterModule, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Subject, takeUntil } from 'rxjs';
import { NotificationService, UserNotification } from '../../services/notification.service';
import { ConfirmationService } from '../../../../core/services/confirmation.service';
import { ListFilters, ListStateService } from '../../../../core/services/list-state.service';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';

@Component({
  selector: 'app-notification-list',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule, LoadingSpinnerComponent],
  templateUrl: './notification-list.component.html',
  styleUrls: ['./notification-list.component.scss'],
})
export class NotificationListComponent implements OnInit, OnDestroy {
  notifications: UserNotification[] = [];
  filteredNotifications: UserNotification[] = [];

  // Filters
  filterStatus: 'all' | 'unread' | 'read' = 'all';
  filterPriority: string = 'all';

  // Expose Math to template
  Math = Math;

  // Create list state service manually (not via DI)
  listState = new ListStateService({ pageSize: 20 });

  private destroy$ = new Subject<void>();

  constructor(
    private notificationService: NotificationService,
    private confirmationService: ConfirmationService,
    private router: Router
  ) {}

  ngOnInit(): void {
    // Load this page's own paginated data rather than reusing
    // notificationService.notifications$ - that shared stream is always
    // capped at page_size: 20 (it exists for the header bell dropdown/badge),
    // so seeding totalItems from its .length silently capped this list's
    // pagination at "1 page" no matter how many notifications actually
    // exist, hiding the pager entirely on first load.
    this.loadNotifications();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    this.listState.destroy();
  }

  loadNotifications(): void {
    this.listState.setLoading(true);
    this.listState.clearError();
    const filters: ListFilters = {
      ...this.listState.getFilters(),
    };

    if (this.filterStatus !== 'all') {
      filters['is_read'] = this.filterStatus === 'read';
    }

    if (this.filterPriority !== 'all') {
      filters['priority'] = this.filterPriority;
    }

    this.notificationService
      .getAllNotifications(filters)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: response => {
          this.notifications = Array.isArray(response) ? response : response.results || [];
          this.listState.setTotalItems(response.count || this.notifications.length);
          this.applyFilters();
          this.listState.setLoading(false);
        },
        error: err => {
          console.error('Error loading notifications:', err);
          this.listState.setError('Failed to load notifications');
          this.listState.setLoading(false);
        },
      });
  }

  applyFilters(): void {
    let filtered = [...this.notifications];

    // Apply status filter
    if (this.filterStatus === 'unread') {
      filtered = filtered.filter(n => !n.is_read);
    } else if (this.filterStatus === 'read') {
      filtered = filtered.filter(n => n.is_read);
    }

    // Apply priority filter
    if (this.filterPriority !== 'all') {
      filtered = filtered.filter(n => n.priority === this.filterPriority);
    }

    this.filteredNotifications = filtered;
  }

  onFilterChange(): void {
    this.listState.resetToFirstPage();
    this.loadNotifications();
  }

  onNotificationClick(notification: UserNotification): void {
    const navigate = () => {
      if (notification.action_url) {
        const nav = this.buildNavigation(notification, notification.action_url);
        this.router.navigate(nav.commands, nav.extras);
      }
    };

    if (!notification.is_read) {
      this.notificationService
        .markAsRead(notification.id)
        .pipe(takeUntil(this.destroy$))
        .subscribe({ next: navigate, error: () => navigate() });
    } else {
      navigate();
    }
  }

  // Maps backend action_url + notification context to a router navigation object.
  // The backend (workflows/notifications.py _get_action_url) already sends the
  // real Angular route with the correct segment - /trf/123, /transport/123,
  // /visa/123, /accommodation/123 - as an absolute URL (http://host/trf/123).
  // Approval notifications route to admin approvals with query params instead
  // of the entity detail page directly.
  private buildNavigation(
    notification: UserNotification,
    actionUrl: string
  ): {
    commands: unknown[];
    extras?: NavigationExtras;
  } {
    const pathname = this.extractPathname(actionUrl);

    const isApproval =
      notification.title?.toLowerCase().includes('approval required') ||
      notification.title?.toLowerCase().includes('approval delegated') ||
      notification.action_text?.toLowerCase().includes('approve');

    if (isApproval) {
      const entityInfo = this.extractEntityInfo(pathname);
      if (entityInfo) {
        return {
          commands: ['/admin/approvals'],
          extras: { queryParams: { type: entityInfo.type, id: entityInfo.id, action: 'approve' } },
        };
      }
      return { commands: ['/admin/approvals'] };
    }

    return { commands: [pathname] };
  }

  /**
   * action_url may be absolute (http://host/trf/123, the current format) or
   * a bare path (/trf/123, from older notifications) - the router only
   * understands the path, so strip the origin when present.
   */
  private extractPathname(actionUrl: string): string {
    try {
      return new URL(actionUrl).pathname;
    } catch {
      return actionUrl;
    }
  }

  /**
   * Extracts entity type and ID from the action URL's path.
   * Example: /transport/37 -> { type: 'transport', id: '37' }
   */
  private extractEntityInfo(pathname: string): { type: string; id: string } | null {
    const routeTypes = ['trf', 'transport', 'visa', 'accommodation', 'expenses'];

    for (const type of routeTypes) {
      const match = pathname.match(new RegExp(`/${type}/(\\d+)`));
      if (match) {
        return {
          type,
          id: match[1],
        };
      }
    }

    return null;
  }

  markAsRead(notification: UserNotification, event: Event): void {
    event.stopPropagation();
    if (!notification.is_read) {
      this.notificationService
        .markAsRead(notification.id)
        .pipe(takeUntil(this.destroy$))
        .subscribe({
          next: () => {
            // Backend deletes the notification once read, so drop it from
            // the local lists too instead of just flipping is_read.
            this.notifications = this.notifications.filter(n => n.id !== notification.id);
            this.filteredNotifications = this.filteredNotifications.filter(
              n => n.id !== notification.id
            );
          },
          error: err => {
            console.error('Error marking notification as read:', err);
          },
        });
    }
  }

  viewNotification(notification: UserNotification, event: Event): void {
    event.stopPropagation();
    this.onNotificationClick(notification);
  }

  markAllAsRead(): void {
    this.notificationService
      .markAllAsRead()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.loadNotifications();
        },
        error: err => {
          console.error('Error marking all as read:', err);
        },
      });
  }

  deleteNotification(id: number, event: Event): void {
    event.stopPropagation();
    this.confirmationService.confirmDelete('this notification').subscribe(confirmed => {
      if (confirmed) {
        this.notificationService
          .deleteNotification(id)
          .pipe(takeUntil(this.destroy$))
          .subscribe({
            next: () => {
              this.loadNotifications();
            },
            error: err => {
              console.error('Error deleting notification:', err);
            },
          });
      }
    });
  }

  getNotificationIcon(priority: string): string {
    switch (priority) {
      case 'urgent':
        return 'bi-exclamation-triangle-fill text-danger';
      case 'high':
        return 'bi-exclamation-circle-fill text-warning';
      case 'normal':
        return 'bi-info-circle-fill text-info';
      default:
        return 'bi-bell-fill text-secondary';
    }
  }

  getPriorityBadgeClass(priority: string): string {
    switch (priority) {
      case 'urgent':
        return 'badge-danger';
      case 'high':
        return 'badge-warning';
      case 'normal':
        return 'badge-info';
      default:
        return 'badge-secondary';
    }
  }

  getTimeAgo(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min${diffMins > 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    return date.toLocaleDateString();
  }

  // Pagination
  goToPage(page: number): void {
    this.listState.setCurrentPage(page);
    this.loadNotifications();
  }

  previousPage(): void {
    this.listState.previousPage();
    this.loadNotifications();
  }

  nextPage(): void {
    this.listState.nextPage();
    this.loadNotifications();
  }
}
