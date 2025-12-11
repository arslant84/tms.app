import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Subject, takeUntil } from 'rxjs';
import { NotificationService, UserNotification } from '../../services/notification.service';

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
  isLoading = false;

  // Filters
  filterStatus: 'all' | 'unread' | 'read' = 'all';
  filterPriority: string = 'all';

  // Pagination
  currentPage = 1;
  pageSize = 20;
  totalNotifications = 0;
  totalPages = 1;

  // Expose Math to template
  Math = Math;

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
  }

  loadNotifications(): void {
    this.isLoading = true;
    const filters: any = {
      page: this.currentPage,
      page_size: this.pageSize
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
        this.totalNotifications = response.count || this.notifications.length;
        this.totalPages = Math.ceil(this.totalNotifications / this.pageSize);
        this.applyFilters();
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Error loading notifications:', err);
        this.isLoading = false;
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
    this.currentPage = 1;
    this.loadNotifications();
  }

  onNotificationClick(notification: UserNotification): void {
    if (!notification.is_read) {
      this.notificationService.markAsRead(notification.id).subscribe({
        next: () => {
          if (notification.action_url) {
            this.router.navigate([notification.action_url]);
          }
        },
        error: (err) => {
          console.error('Error marking notification as read:', err);
        }
      });
    } else {
      if (notification.action_url) {
        this.router.navigate([notification.action_url]);
      }
    }
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
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage = page;
      this.loadNotifications();
    }
  }

  previousPage(): void {
    if (this.currentPage > 1) {
      this.currentPage--;
      this.loadNotifications();
    }
  }

  nextPage(): void {
    if (this.currentPage < this.totalPages) {
      this.currentPage++;
      this.loadNotifications();
    }
  }

  get paginationPages(): number[] {
    const pages: number[] = [];
    const maxPagesToShow = 5;
    let startPage = Math.max(1, this.currentPage - Math.floor(maxPagesToShow / 2));
    let endPage = Math.min(this.totalPages, startPage + maxPagesToShow - 1);

    if (endPage - startPage + 1 < maxPagesToShow) {
      startPage = Math.max(1, endPage - maxPagesToShow + 1);
    }

    for (let i = startPage; i <= endPage; i++) {
      pages.push(i);
    }

    return pages;
  }
}
