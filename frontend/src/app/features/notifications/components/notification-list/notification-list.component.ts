import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Subject, takeUntil } from 'rxjs';
import { NotificationService, UserNotification } from '../../services/notification.service';
import { ListStateService } from '../../../../core/services/list-state.service';

@Component({
  selector: 'app-notification-list',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
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
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadNotifications();

    // Subscribe to notification updates
    this.notificationService.notifications$
      .pipe(takeUntil(this.destroy$))
      .subscribe(notifications => {
        this.notifications = notifications;
        this.applyFilters();
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

    this.notificationService.getAllNotifications(filters).subscribe({
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
    if (!notification.is_read) {
      this.notificationService.markAsRead(notification.id).subscribe({
        next: () => {
          if (notification.action_url) {
            const mappedUrl = this.mapActionUrlToRoute(notification);
            this.router.navigate([mappedUrl]);
          }
        },
        error: (err) => {
          console.error('Error marking notification as read:', err);
        }
      });
    } else {
      if (notification.action_url) {
        const mappedUrl = this.mapActionUrlToRoute(notification);
        this.router.navigate([mappedUrl]);
      }
    }
  }

  /**
   * Maps backend entity types to frontend route paths and handles approval notifications
   * Backend sends: /travelrequest/123, /transportrequest/123, /visaapplication/123
   * Frontend needs: /trf/123, /transport/123, /visa/123
   *
   * For approval notifications, routes to admin approvals page with entity info
   */
  private mapActionUrlToRoute(notification: UserNotification): string {
    const actionUrl = notification.action_url;
    if (!actionUrl) return '/dashboard';

    // Check if this is an approval notification
    const isApprovalNotification =
      notification.title?.toLowerCase().includes('approval required') ||
      notification.title?.toLowerCase().includes('approval delegated') ||
      notification.title?.toLowerCase().includes('review') ||
      notification.action_text?.toLowerCase().includes('approve') ||
      notification.action_text?.toLowerCase().includes('review');

    // If it's an approval notification, extract entity info and route to admin approvals
    if (isApprovalNotification) {
      const entityInfo = this.extractEntityInfo(actionUrl);
      if (entityInfo) {
        // Navigate with query params to auto-select the item
        this.router.navigate(['/admin/approvals'], {
          queryParams: {
            type: entityInfo.type,
            id: entityInfo.id,
            action: 'approve'
          }
        });
        return '/admin/approvals'; // Return for fallback
      }
      return '/admin/approvals';
    }

    // Map backend entity types to frontend routes
    const mappings: { [key: string]: string } = {
      '/travelrequest/': '/trf/',
      '/transportrequest/': '/transport/',
      '/visaapplication/': '/visa/',
      '/expenseclaim/': '/expenses/',
      // accommodation already matches: /accommodation/
    };

    let mappedUrl = actionUrl;
    for (const [backendPath, frontendPath] of Object.entries(mappings)) {
      if (mappedUrl.includes(backendPath)) {
        mappedUrl = mappedUrl.replace(backendPath, frontendPath);
        break;
      }
    }

    return mappedUrl;
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
      this.notificationService.markAsRead(notification.id).subscribe({
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
    this.notificationService.markAllAsRead().subscribe({
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
    if (confirm('Are you sure you want to delete this notification?')) {
      this.notificationService.deleteNotification(id).subscribe({
        next: () => {
          this.loadNotifications();
        },
        error: (err) => {
          console.error('Error deleting notification:', err);
        }
      });
    }
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
