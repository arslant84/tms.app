import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { UserRole, User } from '../../../core/models/user.model';
import { AuthService } from '../../../core/services/auth.service';
import { Subscription } from 'rxjs';

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

  constructor(private authService: AuthService) {}

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
      }
    });

    // Fetch pending approvals
    this.fetchPendingApprovals();
  }

  ngOnDestroy(): void {
    // Clean up subscriptions to prevent memory leaks
    if (this.userSubscription) {
      this.userSubscription.unsubscribe();
    }
  }

  private fetchPendingApprovals(): void {
    // This would be replaced with an actual service call
    this.pendingApprovals = Math.floor(Math.random() * 10);
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
