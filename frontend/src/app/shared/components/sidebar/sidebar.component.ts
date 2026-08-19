import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { User } from '../../../core/models/user.model';
import { AuthService } from '../../../core/services/auth.service';
import { RbacService } from '../../../core/services/rbac.service';
import { Permission } from '../../../core/models/permission.models';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.scss',
})
export class SidebarComponent implements OnInit, OnDestroy {
  currentUser: User | null = null;
  private userSubscription: Subscription | null = null;

  constructor(
    private authService: AuthService,
    private rbacService: RbacService
  ) {}

  ngOnInit(): void {
    // Fetch the current user from the auth service (using Observable for reactive updates)
    this.userSubscription = this.authService.getCurrentUser$Obs().subscribe(user => {
      this.currentUser = user;
    });
  }

  ngOnDestroy(): void {
    // Clean up subscriptions to prevent memory leaks
    if (this.userSubscription) {
      this.userSubscription.unsubscribe();
    }
  }

  // Check if user has approval permissions
  get hasApprovalPermissions(): boolean {
    // Use RBAC service for consistent permission checking
    return this.rbacService.hasApprovalRights();
  }

  // Check if user has system administrator permissions (for User Management and System Settings)
  get hasAdminPermissions(): boolean {
    // Only system administrators and users with manage_users permission can access these features
    return this.rbacService.hasAnyPermission([Permission.SYSTEM_ADMIN, Permission.MANAGE_USERS]);
  }

  // Check if user has any admin module access (for showing admin-related UI elements)
  get hasAnyAdminModuleAccess(): boolean {
    return this.rbacService.hasAnyPermission([
      Permission.SYSTEM_ADMIN,
      Permission.MANAGE_USERS,
      Permission.VIEW_ADMIN_FLIGHTS,
      Permission.VIEW_ADMIN_ACCOMMODATION,
      Permission.VIEW_ADMIN_VISA,
      Permission.VIEW_ADMIN_TRANSPORT,
      Permission.VIEW_ADMIN_MEAL,
    ]);
  }

  // Individual module admin permissions - now using permission-based checks
  get hasFlightsAdminPermission(): boolean {
    return this.rbacService.canAccessAdminMenu('flights');
  }

  get hasAccommodationAdminPermission(): boolean {
    return this.rbacService.canAccessAdminMenu('accommodation');
  }

  get hasVisaAdminPermission(): boolean {
    return this.rbacService.canAccessAdminMenu('visa');
  }

  get hasTransportAdminPermission(): boolean {
    return this.rbacService.canAccessAdminMenu('transport');
  }

  get hasMealAdminPermission(): boolean {
    return this.rbacService.canAccessAdminMenu('meal');
  }

  get hasReportPermissions(): boolean {
    // Reports accessible to users with report permissions
    return this.rbacService.hasReportPermissions();
  }

  // Get user name safely
  getUserName(): string {
    return this.currentUser?.name || 'User';
  }
}
