import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { User } from '../../../core/models/user.model';
import { AuthService } from '../../../core/services/auth.service';
import { RbacService } from '../../../core/services/rbac.service';
import { Permission } from '../../../core/models/permission.models';
import { HttpClient } from '@angular/common/http';
import { Subscription } from 'rxjs';
import { environment } from '../../../../environments/environment';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.scss'
})
export class SidebarComponent implements OnInit, OnDestroy {
  pendingApprovals: number = 0;
  currentUser: User | null = null;
  private userSubscription: Subscription | null = null;
  private approvalsSubscription: Subscription | null = null;
  private apiUrl = environment.apiUrl;

  constructor(
    private authService: AuthService,
    private rbacService: RbacService,
    private http: HttpClient
  ) {}

  ngOnInit(): void {
    // Fetch the current user from the auth service (using Observable for reactive updates)
    this.userSubscription = this.authService.getCurrentUser$Obs().subscribe(user => {
      this.currentUser = user;
      if (user) {

        // Fetch pending approvals only if user has approval permissions
        if (this.hasApprovalPermissions) {
          this.fetchPendingApprovals();
        }
      }
    });
  }

  ngOnDestroy(): void {
    // Clean up subscriptions to prevent memory leaks
    if (this.userSubscription) {
      this.userSubscription.unsubscribe();
    }
    if (this.approvalsSubscription) {
      this.approvalsSubscription.unsubscribe();
    }
  }

  private fetchPendingApprovals(): void {
    // Fetch the actual pending approvals count from the unified admin endpoint
    // This matches the endpoint used by the pending approvals page
    const url = `${this.apiUrl}/admin/approvals/?page=1&limit=100`;

    this.approvalsSubscription = this.http.get<any>(url, { withCredentials: true }).subscribe({
      next: (response) => {
        this.pendingApprovals = response.totalCount || 0;
        console.log('=== SIDEBAR APPROVALS DEBUG ===');
        console.log('API URL:', url);
        console.log('Full Response:', response);
        console.log('Total Count from API:', response.totalCount);
        console.log('Items Count:', response.items?.length);
        console.log('Setting badge count to:', this.pendingApprovals);
        console.log('===============================');
      },
      error: (error) => {
        console.error('Error fetching pending approvals count:', error);
        this.pendingApprovals = 0;
      }
    });
  }

  // Check if user has approval permissions
  get hasApprovalPermissions(): boolean {
    // Use RBAC service for consistent permission checking
    return this.rbacService.hasApprovalRights();
  }

  // Check if user has system administrator permissions (for User Management and System Settings)
  get hasAdminPermissions(): boolean {
    // Only system administrators and users with manage_users permission can access these features
    return this.rbacService.hasAnyPermission([
      Permission.SYSTEM_ADMIN,
      Permission.MANAGE_USERS
    ]);
  }

  // Check if user has any admin module access (for showing admin-related UI elements)
  get hasAnyAdminModuleAccess(): boolean {
    return this.rbacService.hasAnyPermission([
      Permission.SYSTEM_ADMIN,
      Permission.MANAGE_USERS,
      Permission.VIEW_ADMIN_FLIGHTS,
      Permission.VIEW_ADMIN_ACCOMMODATION,
      Permission.VIEW_ADMIN_VISA,
      Permission.VIEW_ADMIN_TRANSPORT
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

  get hasReportPermissions(): boolean {
    // Reports accessible to users with export or generate reports permissions
    return this.rbacService.hasAnyPermission([
      Permission.GENERATE_ADMIN_REPORTS,
      Permission.EXPORT_DATA
    ]) || this.hasApprovalPermissions;
  }

  // Get user name safely
  getUserName(): string {
    return this.currentUser?.name || 'User';
  }
}
