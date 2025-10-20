import { Injectable } from '@angular/core';
import { Observable, map } from 'rxjs';
import { AuthService } from './auth.service';

// Role definitions based on source project requirements
export const ROLES = {
  ACCOMMODATION_ADMIN: 'Accommodation Admin',
  TICKETING_ADMIN: 'Ticketing Admin',
  TRANSPORT_ADMIN: 'Transport Admin',
  VISA_CLERK: 'Visa Clerk',
  FINANCE_CLERK: 'Finance Clerk',
  DEPARTMENT_FOCAL: 'Department Focal',
  LINE_MANAGER: 'Line Manager',
  HOD: 'HOD',
  REQUESTOR: 'Requestor',
  ADMIN: 'Admin',
  SYSTEM_ADMINISTRATOR: 'System Administrator'
} as const;

// Define which roles have approval rights
export const APPROVAL_ROLES = [
  ROLES.DEPARTMENT_FOCAL,
  ROLES.LINE_MANAGER,
  ROLES.HOD,
  ROLES.FINANCE_CLERK,
  ROLES.ADMIN,
  ROLES.SYSTEM_ADMINISTRATOR
];

// Define which roles can see all requests (not just their own)
export const ADMIN_ROLES = [
  ROLES.ADMIN,
  ROLES.SYSTEM_ADMINISTRATOR,
  ROLES.TICKETING_ADMIN  // Ticketing Admin needs to see all pending flights for processing
];

// Define role-specific sidebar access based on requirements
export const ROLE_SIDEBAR_ACCESS: Record<string, string[]> = {
  [ROLES.ACCOMMODATION_ADMIN]: ['Accommodation Admin'],
  [ROLES.TICKETING_ADMIN]: ['Flights Admin'],
  [ROLES.TRANSPORT_ADMIN]: ['Transport Admin'],
  [ROLES.VISA_CLERK]: ['Visa Admin'],
  [ROLES.FINANCE_CLERK]: ['Claims Admin'],
  [ROLES.DEPARTMENT_FOCAL]: ['Approvals'],
  [ROLES.LINE_MANAGER]: ['Approvals'],
  [ROLES.HOD]: ['Approvals', 'Reports'],
  [ROLES.REQUESTOR]: [],
  [ROLES.ADMIN]: ['All'],
  [ROLES.SYSTEM_ADMINISTRATOR]: ['All']
};

export interface ApprovalQueueFilters {
  roleSpecificStatuses: string[];
  canApprove: boolean;
  roleContext: string;
}

export interface RoleBasedNavigation {
  topNavbar: string[];
  leftSidebar: string[];
  hasReports: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class RbacService {
  constructor(private authService: AuthService) {}

  /**
   * Check if user can see all requests or only their own
   */
  canViewAllRequests(): boolean {
    const user = this.authService.getCurrentUser();
    if (!user || !user.role) return false;

    return ADMIN_ROLES.includes(user.role as any) ||
           user.is_admin === true;
  }

  /**
   * Check if user has approval rights
   */
  hasApprovalRights(): boolean {
    const user = this.authService.getCurrentUser();
    if (!user || !user.role) return false;

    return APPROVAL_ROLES.includes(user.role as any);
  }

  /**
   * Get the appropriate approval queue items for a user's role
   */
  getApprovalQueueFilters(): ApprovalQueueFilters {
    const user = this.authService.getCurrentUser();

    if (!user || !user.role) {
      return { roleSpecificStatuses: [], canApprove: false, roleContext: '' };
    }

    const role = user.role;

    // Define what statuses each role should see in their approval queue
    const statusFilters: Record<string, string[]> = {
      [ROLES.DEPARTMENT_FOCAL]: [
        'Pending Department Focal',
        'Pending Focal Approval'
      ],
      [ROLES.LINE_MANAGER]: [
        'Pending Line Manager',
        'Pending Line Manager/HOD',
        'Pending Line Approval'
      ],
      [ROLES.HOD]: [
        'Pending HOD',
        'Pending HOD Approval',
        'Pending Line Manager/HOD'
      ],
      [ROLES.FINANCE_CLERK]: [
        'Pending Finance Approval'
      ],
      [ROLES.VISA_CLERK]: [
        'Pending Visa Clerk'
      ],
      [ROLES.TICKETING_ADMIN]: [
        'Approved',  // Ticketing Admin processes all approved TRFs for flight booking
        'Flights Booked'  // Can also view completed flight bookings
      ],
      [ROLES.ADMIN]: [
        'Pending Department Focal',
        'Pending Focal Approval',
        'Pending Line Manager',
        'Pending Line Approval',
        'Pending Line Manager/HOD',
        'Pending HOD',
        'Pending HOD Approval',
        'Pending Finance Approval',
        'Pending Visa Clerk',
        'Pending Verification'
      ],
      [ROLES.SYSTEM_ADMINISTRATOR]: [
        'Pending Department Focal',
        'Pending Focal Approval',
        'Pending Line Manager',
        'Pending Line Approval',
        'Pending Line Manager/HOD',
        'Pending HOD',
        'Pending HOD Approval',
        'Pending Finance Approval',
        'Pending Visa Clerk',
        'Pending Verification'
      ]
    };

    return {
      roleSpecificStatuses: statusFilters[role] || [],
      canApprove: APPROVAL_ROLES.includes(role as any),
      roleContext: role
    };
  }

  /**
   * Filter requests based on user's role and visibility permissions
   */
  filterRequestsByUserRole<T extends {
    requestorId?: string;
    userId?: string;
    staff_id?: string;
    staff_no?: string;
    created_by?: string;
  }>(requests: T[]): T[] {
    if (this.canViewAllRequests()) {
      return requests; // Admin roles see everything
    }

    // Regular users see only their own requests
    const user = this.authService.getCurrentUser();

    if (!user) {
      return [];
    }

    const currentUserId = user.id?.toString();
    const currentEmail = user.email;

    // Filter to show only user's own requests
    return requests.filter(request => {
      // Try different fields that might contain user identifier
      return request.requestorId?.toString() === currentUserId ||
             request.userId?.toString() === currentUserId ||
             request.staff_id?.toString() === currentUserId ||
             request.staff_no === user.staff_id ||
             request.created_by === currentEmail;
    });
  }

  /**
   * Get navigation menu items based on user role
   */
  getRoleBasedNavigation(): RoleBasedNavigation {
    const user = this.authService.getCurrentUser();

    if (!user || !user.role) {
      return { topNavbar: [], leftSidebar: [], hasReports: false };
    }

    const role = user.role;

    // All roles have access to basic request types in top navbar
    const baseNavItems = ['TRF', 'Transport', 'Visa', 'Accommodation', 'Claims'];

    // Determine additional access
    const hasReports = [ROLES.HOD, ROLES.REQUESTOR, ROLES.ADMIN, ROLES.SYSTEM_ADMINISTRATOR].includes(role as any) || user.is_admin;
    const topNavbar = hasReports ? [...baseNavItems, 'Reports'] : baseNavItems;

    // Get role-specific sidebar access
    const leftSidebar = ROLE_SIDEBAR_ACCESS[role] || [];

    return {
      topNavbar,
      leftSidebar,
      hasReports
    };
  }

  /**
   * Check if user can perform specific actions based on role
   */
  canPerformAction(action: string, entityType: string): boolean {
    const user = this.authService.getCurrentUser();

    if (!user || !user.role) {
      return false;
    }

    const role = user.role;

    // Admin roles can perform all actions
    if (ADMIN_ROLES.includes(role as any) || user.is_admin) {
      return true;
    }

    // Define role-specific action permissions
    const actionPermissions: Record<string, Record<string, boolean>> = {
      [ROLES.FINANCE_CLERK]: {
        'process_claims': true,
        'approve_claims_finance': true
      },
      [ROLES.DEPARTMENT_FOCAL]: {
        'approve_tsr': true,
        'approve_claims': true,
        'approve_visa': true,
        'approve_transport': true,
        'approve_accommodation': true
      },
      [ROLES.LINE_MANAGER]: {
        'approve_tsr': true,
        'approve_claims': true,
        'approve_visa': true,
        'approve_transport': true,
        'approve_accommodation': true
      },
      [ROLES.HOD]: {
        'approve_tsr': true,
        'approve_claims_hod': true,
        'approve_visa': true,
        'approve_transport': true,
        'approve_accommodation': true
      },
      [ROLES.VISA_CLERK]: {
        'process_visa': true
      }
    };

    return actionPermissions[role]?.[action] || false;
  }

  /**
   * Get user's department for department-specific filtering
   */
  getCurrentUserDepartment(): string | null {
    const user = this.authService.getCurrentUser();
    return user?.department || null;
  }

  /**
   * Check if user has a specific permission
   */
  hasPermission(permissionName: string): boolean {
    const user = this.authService.getCurrentUser();

    if (!user) {
      return false;
    }

    // Admin roles have all permissions
    if (user.role === ROLES.SYSTEM_ADMINISTRATOR ||
        user.role === ROLES.ADMIN ||
        user.is_admin) {
      return true;
    }

    // Check if the user has the specific permission
    return user.permissions?.includes(permissionName) || false;
  }

  /**
   * Check if user has any of the specified permissions
   */
  hasAnyPermission(permissionNames: string[]): boolean {
    const user = this.authService.getCurrentUser();

    if (!user) {
      return false;
    }

    // Admin roles have all permissions
    if (user.role === ROLES.SYSTEM_ADMINISTRATOR ||
        user.role === ROLES.ADMIN ||
        user.is_admin) {
      return true;
    }

    // Check if the user has any of the specified permissions
    return permissionNames.some(permission =>
      user.permissions?.includes(permission) || false
    );
  }

  /**
   * Check if user has all of the specified permissions
   */
  hasAllPermissions(permissionNames: string[]): boolean {
    const user = this.authService.getCurrentUser();

    if (!user) {
      return false;
    }

    // Admin roles have all permissions
    if (user.role === ROLES.SYSTEM_ADMINISTRATOR ||
        user.role === ROLES.ADMIN ||
        user.is_admin) {
      return true;
    }

    // Check if the user has all of the specified permissions
    return permissionNames.every(permission =>
      user.permissions?.includes(permission) || false
    );
  }

  /**
   * Check if user should see a specific menu item
   */
  canSeeMenuItem(menuItem: string): boolean {
    const navigation = this.getRoleBasedNavigation();

    // Check if 'All' access
    if (navigation.leftSidebar.includes('All')) {
      return true;
    }

    // Check specific menu item access
    return navigation.leftSidebar.includes(menuItem) ||
           navigation.topNavbar.includes(menuItem);
  }
}
