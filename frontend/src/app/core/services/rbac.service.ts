import { Injectable } from '@angular/core';
import { Observable, map } from 'rxjs';
import { AuthService } from './auth.service';
import { Permission, PermissionGroups } from '../models/permission.models';

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
  [ROLES.FINANCE_CLERK]: [],
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
   * Get role name from user object (handles both string and object role)
   */
  private getRoleName(user: any): string | null {
    if (!user || !user.role) return null;

    // If role is an object, get the name property
    if (typeof user.role === 'object' && user.role.name) {
      return user.role.name;
    }

    // If role is a string, return it directly
    if (typeof user.role === 'string') {
      return user.role;
    }

    return null;
  }

  /**
   * Check if user can see all requests or only their own
   */
  canViewAllRequests(): boolean {
    const user = this.authService.getCurrentUser();
    if (!user || !user.role) return false;

    const roleName = this.getRoleName(user);
    return (roleName && ADMIN_ROLES.includes(roleName as any)) ||
           user.is_admin === true;
  }

  /**
   * Check if user has approval rights
   */
  hasApprovalRights(): boolean {
    const user = this.authService.getCurrentUser();
    if (!user || !user.role) return false;

    const roleName = this.getRoleName(user);
    return roleName ? APPROVAL_ROLES.includes(roleName as any) : false;
  }

  /**
   * Get the appropriate approval queue items for a user's role
   */
  getApprovalQueueFilters(): ApprovalQueueFilters {
    const user = this.authService.getCurrentUser();

    if (!user || !user.role) {
      return { roleSpecificStatuses: [], canApprove: false, roleContext: '' };
    }

    const role = this.getRoleName(user);

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
      roleSpecificStatuses: statusFilters[role || ''] || [],
      canApprove: role ? APPROVAL_ROLES.includes(role as any) : false,
      roleContext: role || ''
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

    const role = this.getRoleName(user);

    // All roles have access to basic request types in top navbar
    const baseNavItems = ['TRF', 'Transport', 'Visa', 'Accommodation'];

    // Determine additional access
    const hasReports = (role && [ROLES.HOD, ROLES.REQUESTOR, ROLES.ADMIN, ROLES.SYSTEM_ADMINISTRATOR].includes(role as any)) || user.is_admin;
    const topNavbar = hasReports ? [...baseNavItems, 'Reports'] : baseNavItems;

    // Get role-specific sidebar access
    const leftSidebar = role ? (ROLE_SIDEBAR_ACCESS[role] || []) : [];

    return {
      topNavbar,
      leftSidebar,
      hasReports
    };
  }

  /**
   * Check if user can perform specific actions based on role and permissions
   */
  canPerformAction(action: string, entityType: string): boolean {
    const user = this.authService.getCurrentUser();

    if (!user || !user.role) {
      return false;
    }

    const role = this.getRoleName(user);

    // Admin roles can perform all actions
    if ((role && ADMIN_ROLES.includes(role as any)) || user.is_admin) {
      return true;
    }

    // Map actions to permission checks using new Permission enum
    const actionToPermissionMap: Record<string, Permission> = {
      'approve_tsr': Permission.APPROVE_TRF,
      'approve_trf': Permission.APPROVE_TRF,
      'approve_visa': Permission.APPROVE_VISA,
      'approve_transport': Permission.APPROVE_TRANSPORT,
      'approve_accommodation': Permission.APPROVE_ACCOMMODATION,
      'process_visa': Permission.PROCESS_VISA_APPLICATIONS,
      'process_flights': Permission.PROCESS_FLIGHTS,
      'manage_accommodation': Permission.MANAGE_ACCOMMODATION_BOOKINGS,
      'manage_transport': Permission.MANAGE_TRANSPORT_REQUESTS,
      'manage_flights': Permission.MANAGE_FLIGHTS,
    };

    // Check if action maps to a permission
    const requiredPermission = actionToPermissionMap[action];
    if (requiredPermission) {
      return this.hasPermission(requiredPermission);
    }

    // Fallback to legacy role-based logic for unmapped actions
    const actionPermissions: Record<string, Record<string, boolean>> = {
      [ROLES.FINANCE_CLERK]: {},
      [ROLES.DEPARTMENT_FOCAL]: {
        'approve_tsr': true,
        'approve_visa': true,
        'approve_transport': true,
        'approve_accommodation': true
      },
      [ROLES.LINE_MANAGER]: {
        'approve_tsr': true,
        'approve_visa': true,
        'approve_transport': true,
        'approve_accommodation': true
      },
      [ROLES.HOD]: {
        'approve_tsr': true,
        'approve_visa': true,
        'approve_transport': true,
        'approve_accommodation': true
      },
      [ROLES.VISA_CLERK]: {
        'process_visa': true
      }
    };

    return (role && actionPermissions[role]?.[action]) || false;
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

    const roleName = this.getRoleName(user);

    // Admin roles have all permissions
    if (roleName === ROLES.SYSTEM_ADMINISTRATOR ||
        roleName === ROLES.ADMIN ||
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

    const roleName = this.getRoleName(user);

    // Admin roles have all permissions
    if (roleName === ROLES.SYSTEM_ADMINISTRATOR ||
        roleName === ROLES.ADMIN ||
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

    const roleName = this.getRoleName(user);

    // Admin roles have all permissions
    if (roleName === ROLES.SYSTEM_ADMINISTRATOR ||
        roleName === ROLES.ADMIN ||
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

  /**
   * Check if user can access admin menu for a specific module
   * Uses new permission-based checks
   */
  canAccessAdminMenu(module: 'accommodation' | 'transport' | 'visa' | 'flights'): boolean {
    const user = this.authService.getCurrentUser();

    if (!user) {
      return false;
    }

    const roleName = this.getRoleName(user);

    // Admin roles have access to all admin menus
    if (roleName === ROLES.SYSTEM_ADMINISTRATOR ||
        roleName === ROLES.ADMIN ||
        user.is_admin) {
      return true;
    }

    // Map module to permission
    const modulePermissionMap: Record<string, Permission> = {
      'accommodation': Permission.VIEW_ADMIN_ACCOMMODATION,
      'transport': Permission.VIEW_ADMIN_TRANSPORT,
      'visa': Permission.VIEW_ADMIN_VISA,
      'flights': Permission.VIEW_ADMIN_FLIGHTS,
    };

    const requiredPermission = modulePermissionMap[module];
    return requiredPermission ? this.hasPermission(requiredPermission) : false;
  }

  /**
   * Check if user can create requests of a specific type
   */
  canCreateRequest(requestType: 'trf' | 'transport' | 'visa' | 'accommodation'): boolean {
    const user = this.authService.getCurrentUser();

    if (!user) {
      return false;
    }

    // All authenticated users can create requests by default
    // But check for specific permissions if configured
    const requestPermissionMap: Record<string, Permission> = {
      'trf': Permission.CREATE_TRF,
      'transport': Permission.CREATE_TRANSPORT_REQUESTS,
      'visa': Permission.CREATE_VISA_REQUESTS,
      'accommodation': Permission.CREATE_ACCOMMODATION_REQUESTS,
    };

    const requiredPermission = requestPermissionMap[requestType];
    return requiredPermission ? this.hasPermission(requiredPermission) : true;
  }
}
