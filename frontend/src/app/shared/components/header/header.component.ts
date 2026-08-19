import { Component, OnInit, Output, EventEmitter, HostListener, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NavigationExtras, RouterModule, Router } from '@angular/router';
import { Observable, map, Subject, takeUntil } from 'rxjs';
import { AuthService } from '../../../core/services/auth.service';
import { User } from '../../../core/models/user.model';
import {
  NotificationService,
  UserNotification,
} from '../../../features/notifications/services/notification.service';
import { AppSettingsService } from '../../../core/services/app-settings.service';

@Component({
  selector: 'app-header',
  templateUrl: './header.component.html',
  styleUrls: ['./header.component.scss'],
  standalone: true,
  imports: [CommonModule, RouterModule],
})
export class HeaderComponent implements OnInit, OnDestroy {
  isCollapsed = true;
  currentUser$: Observable<User | null>;
  isAdmin$: Observable<boolean>;
  notifications: UserNotification[] = [];
  notificationCount$: Observable<number>;
  isNotificationsOpen = false;
  isProfileOpen = false;
  applicationName$: Observable<string>;

  private destroy$ = new Subject<void>();

  @Output() toggleSidebarEvent = new EventEmitter<void>();

  constructor(
    private authService: AuthService,
    private notificationService: NotificationService,
    private router: Router,
    private appSettingsService: AppSettingsService
  ) {
    this.currentUser$ = this.authService.currentUser$;
    this.isAdmin$ = this.currentUser$.pipe(map(user => user?.is_admin === true));
    this.notificationCount$ = this.notificationService.unreadCount$;
    this.applicationName$ = this.appSettingsService.settings$.pipe(
      map(settings => settings.application_name || 'TMS')
    );
  }

  ngOnInit(): void {
    // SECURITY: NotificationService now auto-initializes when user is authenticated
    // Subscribe to notifications updates
    this.notificationService.notifications$
      .pipe(takeUntil(this.destroy$))
      .subscribe(notifications => {
        // Only show first 5 recent notifications in dropdown
        this.notifications = notifications.slice(0, 5);
      });

    // Add click event listener to close dropdowns when clicking outside
    this.setupClickOutsideListener();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /**
   * Handle document clicks to close dropdowns when clicking outside
   */
  @HostListener('document:click', ['$event'])
  handleDocumentClick(event: MouseEvent): void {
    // Close notifications dropdown if clicking outside
    if (this.isNotificationsOpen) {
      const notificationsDropdown = document.querySelector('.notifications-dropdown');
      if (notificationsDropdown && !notificationsDropdown.contains(event.target as Node)) {
        this.closeNotificationsDropdown();
      }
    }

    // Close profile dropdown if clicking outside
    if (this.isProfileOpen) {
      const profileDropdown = document.querySelector('.profile-dropdown');
      if (profileDropdown && !profileDropdown.contains(event.target as Node)) {
        this.isProfileOpen = false;
        const dropdownMenu = document.querySelector('.profile-dropdown .dropdown-menu');
        if (dropdownMenu) {
          dropdownMenu.classList.remove('show');
        }
      }
    }
  }

  /**
   * Setup click outside listener
   */
  private setupClickOutsideListener(): void {
    // This is handled by the HostListener above
  }

  /**
   * Mark a notification as read and navigate to its action URL
   */
  onNotificationClick(notification: UserNotification): void {
    const navigate = () => {
      if (notification.action_url) {
        const nav = this.buildNavigation(notification);
        this.router.navigate(nav.commands, nav.extras);
      }
      this.closeNotificationsDropdown();
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

  private buildNavigation(notification: UserNotification): {
    commands: unknown[];
    extras?: NavigationExtras;
  } {
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
          extras: { queryParams: { type: entityInfo.type, id: entityInfo.id, action: 'approve' } },
        };
      }
      return { commands: ['/admin/approvals'] };
    }

    const mappings: Record<string, string> = {
      '/travelrequest/': '/trf/',
      '/transportrequest/': '/transport/',
      '/visaapplication/': '/visa/',
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
      travelrequest: 'trf',
      transportrequest: 'transport',
      visaapplication: 'visa',
      accommodation: 'accommodation',
      expenseclaim: 'expenses',
    };

    for (const [backendType, frontendType] of Object.entries(entityMappings)) {
      const pattern = new RegExp(`/${backendType}/(\\d+)`);
      const match = actionUrl.match(pattern);
      if (match) {
        return {
          type: frontendType,
          id: match[1],
        };
      }
    }

    return null;
  }

  /**
   * Mark all notifications as read
   */
  markAllAsRead(event: Event): void {
    event.preventDefault();
    event.stopPropagation();
    this.notificationService
      .markAllAsRead()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        error: err => {
          console.error('Error marking all as read:', err);
        },
      });
  }

  /**
   * Navigate to notifications page
   */
  viewAllNotifications(event: Event): void {
    event.preventDefault();
    event.stopPropagation();
    this.router.navigate(['/notifications']);
    this.closeNotificationsDropdown();
  }

  /**
   * Close the notifications dropdown, keeping isNotificationsOpen and the
   * manually-toggled .show class in sync (this dropdown isn't Angular-bound
   * to the DOM class - see toggleNotificationsDropdown/updateDropdownVisibility).
   */
  private closeNotificationsDropdown(): void {
    this.isNotificationsOpen = false;
    const dropdownMenu = document.querySelector('.notifications-dropdown .dropdown-menu');
    if (dropdownMenu) {
      dropdownMenu.classList.remove('show');
    }
  }

  /**
   * Get the appropriate icon for notification priority
   */
  getNotificationIcon(priority: string): string {
    switch (priority) {
      case 'urgent':
        return 'bi-exclamation-triangle-fill text-danger';
      case 'high':
        return 'bi-exclamation-circle-fill text-warning';
      case 'normal':
        return 'bi-info-circle-fill text-info';
      case 'low':
      default:
        return 'bi-bell-fill text-secondary';
    }
  }

  /**
   * Get formatted time difference
   */
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

  /**
   * Toggle notifications dropdown
   */
  toggleNotificationsDropdown(event: Event): void {
    event.stopPropagation();

    // If notifications dropdown is already open, close it
    // Otherwise, open it and close profile dropdown
    if (this.isNotificationsOpen) {
      this.isNotificationsOpen = false;
    } else {
      this.isNotificationsOpen = true;
      this.isProfileOpen = false; // Always close profile dropdown when opening notifications
    }

    // Toggle bootstrap dropdown manually
    this.updateDropdownVisibility();
  }

  /**
   * Toggle profile dropdown
   */
  toggleProfileDropdown(event: Event): void {
    event.stopPropagation();

    // If profile dropdown is already open, close it
    // Otherwise, open it and close notifications dropdown
    if (this.isProfileOpen) {
      this.isProfileOpen = false;
    } else {
      this.isProfileOpen = true;
      this.isNotificationsOpen = false; // Always close notifications dropdown when opening profile
    }

    // Toggle bootstrap dropdown manually
    this.updateDropdownVisibility();
  }

  /**
   * Update dropdown visibility based on state
   */
  private updateDropdownVisibility(): void {
    // Handle notifications dropdown
    const notificationsMenu = document.querySelector('.notifications-dropdown .dropdown-menu');
    if (notificationsMenu) {
      if (this.isNotificationsOpen) {
        notificationsMenu.classList.add('show');
      } else {
        notificationsMenu.classList.remove('show');
      }
    }

    // Handle profile dropdown
    const profileMenu = document.querySelector('.profile-dropdown .dropdown-menu');
    if (profileMenu) {
      if (this.isProfileOpen) {
        profileMenu.classList.add('show');
      } else {
        profileMenu.classList.remove('show');
      }
    }
  }

  toggleNavbar(): void {
    this.isCollapsed = !this.isCollapsed;
  }

  toggleSidebar(): void {
    this.toggleSidebarEvent.emit();
  }

  logout(event: Event): void {
    event.preventDefault();
    this.authService.logout();
  }

  /**
   * Get user initials from name for avatar fallback
   */
  getUserInitials(name: string): string {
    if (!name) return 'U';

    const parts = name.trim().split(' ');
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
  }

  /**
   * Get user avatar URL (supports both avatar and profile_photo fields)
   */
  getUserAvatar(user: User): string | null {
    return user.avatar || user.profile_photo || null;
  }
}
