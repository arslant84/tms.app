import { Component, OnInit, Output, EventEmitter, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { Observable, map } from 'rxjs';
import { AuthService } from '../../../core/services/auth.service';
import { User, UserRole } from '../../../core/models/user.model';

interface Notification {
  id: number;
  message: string;
  type: 'info' | 'success' | 'warning' | 'danger';
  time: Date;
  read: boolean;
  link: string;
}

@Component({
  selector: 'app-header',
  templateUrl: './header.component.html',
  styleUrls: ['./header.component.scss'],
  standalone: true,
  imports: [CommonModule, RouterModule]
})
export class HeaderComponent implements OnInit {
  isCollapsed = true;
  currentUser$: Observable<User | null>;
  isAdmin$: Observable<boolean>;
  notifications: Notification[] = [];
  notificationCount = 0;
  isNotificationsOpen = false;
  isProfileOpen = false;
  
  @Output() toggleSidebarEvent = new EventEmitter<void>();

  constructor(private authService: AuthService) {
    this.currentUser$ = this.authService.currentUser$;
    this.isAdmin$ = this.currentUser$.pipe(
      map(user => user?.is_admin === true)
    );
  }

  ngOnInit(): void {
    // Mock notifications for demonstration
    this.loadNotifications();
    
    // Add click event listener to close dropdowns when clicking outside
    this.setupClickOutsideListener();
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
        this.isNotificationsOpen = false;
        const dropdownMenu = document.querySelector('.notifications-dropdown .dropdown-menu');
        if (dropdownMenu) {
          dropdownMenu.classList.remove('show');
        }
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
   * Load notifications from service
   * This is a mock implementation - would be replaced with actual API call
   */
  loadNotifications(): void {
    // Mock data - in a real app, this would come from a service
    this.notifications = [
      {
        id: 1,
        message: 'Your travel request TRF-2025-001 has been approved',
        type: 'success',
        time: new Date(),
        read: false,
        link: '/trf/view/1'
      },
      {
        id: 2,
        message: 'New expense claim requires your approval',
        type: 'info',
        time: new Date(Date.now() - 3600000), // 1 hour ago
        read: false,
        link: '/approvals/pending'
      },
      {
        id: 3,
        message: 'Your flight booking has been confirmed',
        type: 'info',
        time: new Date(Date.now() - 86400000), // 1 day ago
        read: true,
        link: '/booking/view/1'
      }
    ];
    
    this.updateNotificationCount();
  }
  
  /**
   * Update the notification count badge
   */
  updateNotificationCount(): void {
    this.notificationCount = this.notifications.filter(n => !n.read).length;
  }
  
  /**
   * Mark a notification as read
   */
  markAsRead(id: number): void {
    const notification = this.notifications.find(n => n.id === id);
    if (notification) {
      notification.read = true;
      this.updateNotificationCount();
    }
  }
  
  /**
   * Get the appropriate icon for notification type
   */
  getNotificationIcon(type: string): string {
    switch (type) {
      case 'success': return 'bi-check-circle-fill';
      case 'warning': return 'bi-exclamation-triangle-fill';
      case 'danger': return 'bi-x-circle-fill';
      case 'info':
      default: return 'bi-info-circle-fill';
    }
  }
  
  /**
   * View all notifications
   */
  viewAllNotifications(event: Event): void {
    event.preventDefault();
    // Navigate to notifications page or mark all as read
    this.notifications.forEach(n => n.read = true);
    this.updateNotificationCount();
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
}
