import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { UserRole, User } from '../../../core/models/user.model';
import { AuthService } from '../../../core/services/auth.service';
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
  userRole: string = 'Employee'; // Default role, will be fetched from auth service
  pendingApprovals: number = 0;
  currentUser: User | null = null;
  private userSubscription: Subscription | null = null;
  private approvalsSubscription: Subscription | null = null;
  private apiUrl = environment.apiUrl;

  constructor(
    private authService: AuthService,
    private http: HttpClient
  ) {}

  ngOnInit(): void {
    // Fetch the current user from the auth service (using Observable for reactive updates)
    this.userSubscription = this.authService.getCurrentUser$Obs().subscribe(user => {
      this.currentUser = user;
      if (user) {
        // Handle the role properly
        this.userRole = user.role || 'Employee';
        console.log('Current user role:', this.userRole);
        console.log('User is_admin flag:', user.is_admin);

        // If user has is_admin flag set to true, ensure they have admin role
        if (user.is_admin) {
          console.log('User has admin flag, setting ADMIN role');
          this.userRole = UserRole.ADMIN;
        }

        console.log('Final user role:', this.userRole);
        console.log('Has approval permissions:', this.hasApprovalPermissions);
        console.log('Has admin permissions:', this.hasAdminPermissions);

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
    return this.userRole === UserRole.FOCAL ||
           this.userRole === UserRole.HOD ||
           this.userRole === UserRole.ADMIN ||
           this.userRole === 'admin' ||
           this.userRole === 'focal' ||
           this.userRole === 'hod';
  }

  // Check if user has admin permissions (general)
  get hasAdminPermissions(): boolean {
    return this.userRole === UserRole.ADMIN ||
           this.userRole === UserRole.TICKETING_CLERK ||
           this.userRole === 'admin' ||
           this.userRole === 'ticketing_clerk';
  }

  // Individual module admin permissions
  get hasFlightsAdminPermission(): boolean {
    // For now, use admin role. TODO: Implement permission-based checks
    return this.hasAdminPermissions;
  }

  get hasAccommodationAdminPermission(): boolean {
    return this.hasAdminPermissions;
  }

  get hasVisaAdminPermission(): boolean {
    return this.hasAdminPermissions;
  }

  get hasClaimsAdminPermission(): boolean {
    return this.hasAdminPermissions;
  }

  get hasTransportAdminPermission(): boolean {
    return this.hasAdminPermissions;
  }

  get hasReportPermissions(): boolean {
    // Reports accessible to HOD, Focal, and Admins
    return this.hasApprovalPermissions || this.hasAdminPermissions;
  }

  // Get user name safely
  getUserName(): string {
    return this.currentUser?.name || 'User';
  }
}
