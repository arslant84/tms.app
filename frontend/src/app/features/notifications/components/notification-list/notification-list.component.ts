import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Subject, takeUntil } from 'rxjs';
import { NotificationService, UserNotification } from '../../services/notification.service';
import { ConfirmationService } from '../../../../core/services/confirmation.service';
import { ListStateService } from '../../../../core/services/list-state.service';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';

@Component({
  selector: 'app-notification-list',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule, LoadingSpinnerComponent],
  templateUrl: './notification-list.component.html',
  styleUrls: ['./notification-list.component.scss']
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
    // Service already fetched notifications on auth via startPolling().
    // Subscribe to the stream for the initial render; loadNotifications() is called
    // explicitly when the user changes filters or pages.
    this.notificationService.notifications$
      .pipe(takeUntil(this.destroy$))
      .subscribe(notifications => {
        this.notifications = notifications;
        this.listState.setTotalItems(notifications.length);
        this.applyFilters();
        this.listState.setLoading(false);
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    this.listState.destroy();
  }

  loadNotifications(): void {
    this.listState.setLoading(true);
    const filters: any = {
      ...this.listState.getFilters()
    };

    if (this.filterStatus !== 'all') {
      filters.is_read = this.filterStatus === 'read';
    }

    if (this.filterPriority !== 'all') {
      filters.priority = this.filterPriority;
    }

    this.notificationService.getAllNotifications(filters)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response) => {
          this.notifications = Array.isArray(response) ? response : response.results || [];
          this.listState.setTotalItems(response.count || this.notifications.length);
          this.applyFilters();
          this.listState.setLoading(false);
        },
        error: (err) => {
          console.error('Error loading notifications:', err);
          this.listState.setLoading(false);
        }
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
        const nav = this.buildNavigation(notification);
        this.router.navigate(nav.commands, nav.extras);
      }
    };

    if (!notification.is_read) {
      this.notificationService.markAsRead(notification.id)
        .pipe(takeUntil(this.destroy$))
        .subscribe({ next: navigate, error: () => navigate() });
    } else {
      navigate();
    }
  }

  // Maps backend action_url + notification context to a router navigation object.
  // Backend sends entity-type URLs: /travelrequest/123, /transportrequest/123, etc.
  // Approval notifications route to admin approvals with query params.
  private buildNavigation(notification: UserNotification): { commands: any[]; extras?: any } {
    const actionUrl = notification.action_url!;

    const isApproval =
      notification.title?.toLowerCase().includes('approval required') ||
      notification.title?.toLowerCase().includes('approval delegated') ||
      notification.action_text?.toLowerCase().includes('approve');

    if (isApproval) {
      const entityInfo = this.extractEntityInfo(actionUrl);
      if (entityInfo) {
        return {
          commands: ['/admin/approvals'],
          extras: { queryParams: { type: entityInfo.type, id: entityInfo.id, action: 'approve' } }
        };
      }
      return { commands: ['/admin/approvals'] };
    }

    const mappings: Record<string, string> = {
      '/travelrequest/': '/trf/',
      '/transportrequest/': '/transport/',
      '/visaapplication/': '/visa/',
      '/combinedrequest/': '/combined/',
      '/expenseclaim/': '/expenses/',
    };

    let url = actionUrl;
    for (const [backend, frontend] of Object.entries(mappings)) {
      if (url.includes(backend)) {
        url = url.replace(backend, frontend);
        break;
      }
    }

    return { commands: [url] };
  }

  /**
   * Extracts entity type and ID from action URL
   * Example: /transportrequest/37 -> { type: 'transport', id: '37' }
   */
  private extractEntityInfo(actionUrl: string): { type: string; id: string } | null {
    const entityMappings: { [key: string]: string } = {
      'travelrequest': 'trf',
      'transportrequest': 'transport',
      'visaapplication': 'visa',
      'accommodation': 'accommodation',
      'expenseclaim': 'expenses'
    };

    for (const [backendType, frontendType] of Object.entries(entityMappings)) {
      const pattern = new RegExp(`/${backendType}/(\\d+)`);
      const match = actionUrl.match(pattern);
      if (match) {
        return {
          type: frontendType,
          id: match[1]
        };
      }
    }

    return null;
  }

  markAsRead(notification: UserNotification, event: Event): void {
    event.stopPropagation();
    if (!notification.is_read) {
      this.notificationService.markAsRead(notification.id)
        .pipe(takeUntil(this.destroy$))
        .subscribe({
          next: () => {
            notification.is_read = true;
          },
          error: (err) => {
            console.error('Error marking notification as read:', err);
          }
        });
    }
  }

  markAllAsRead(): void {
    this.notificationService.markAllAsRead()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.loadNotifications();
        },
        error: (err) => {
          console.error('Error marking all as read:', err);
        }
      });
  }

  deleteNotification(id: number, event: Event): void {
    event.stopPropagation();
    this.confirmationService.confirmDelete('this notification').subscribe(confirmed => {
      if (confirmed) {
        this.notificationService.deleteNotification(id)
          .pipe(takeUntil(this.destroy$))
          .subscribe({
            next: () => {
              this.loadNotifications();
            },
            error: (err) => {
              console.error('Error deleting notification:', err);
            }
          });
      }
    });
  }

  getNotificationIcon(priority: string): string {
    switch (priority) {
      case 'urgent': return 'bi-exclamation-triangle-fill text-danger';
      case 'high': return 'bi-exclamation-circle-fill text-warning';
      case 'normal': return 'bi-info-circle-fill text-info';
      case 'low':
      default: return 'bi-bell-fill text-secondary';
    }
  }

  getPriorityBadgeClass(priority: string): string {
    switch (priority) {
      case 'urgent': return 'badge-danger';
      case 'high': return 'badge-warning';
      case 'normal': return 'badge-info';
      case 'low':
      default: return 'badge-secondary';
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
