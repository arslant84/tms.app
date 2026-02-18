import { Injectable } from '@angular/core';
import { AuthService } from './auth.service';
import { Permission } from '../models/permission.models';

/**
 * RBAC Service - Permission-Based Access Control
 *
 * All access control is determined by the user.permissions array from the backend.
 * Permissions are assigned to roles via the Role Management UI.
 * No hardcoded role names - only database permissions.
 */
@Injectable({
  providedIn: 'root'
})
export class RbacService {
  constructor(private authService: AuthService) {}

  // ============================================================================
  // CORE PERMISSION METHODS
  // ============================================================================

  /**
   * Check if user has a specific permission
   * This is the foundation of all access control
   */
  hasPermission(permissionName: string): boolean {
    const user = this.authService.getCurrentUser();
    if (!user) return false;
    return user.permissions?.includes(permissionName) || false;
  }

  /**
   * Check if user has any of the specified permissions
   */
  hasAnyPermission(permissionNames: string[]): boolean {
    const user = this.authService.getCurrentUser();
    if (!user?.permissions) return false;
    return permissionNames.some(p => user.permissions!.includes(p));
  }

  /**
   * Check if user has all of the specified permissions
   */
  hasAllPermissions(permissionNames: string[]): boolean {
    const user = this.authService.getCurrentUser();
    if (!user?.permissions) return false;
    return permissionNames.every(p => user.permissions!.includes(p));
  }

  // ============================================================================
  // ADMIN MODULE ACCESS
  // ============================================================================

  /**
   * Check if user can access admin menu for a specific module
   */
  canAccessAdminMenu(module: 'accommodation' | 'transport' | 'visa' | 'flights'): boolean {
    const modulePermissionMap: Record<string, string> = {
      'accommodation': Permission.VIEW_ADMIN_ACCOMMODATION,
      'transport': Permission.VIEW_ADMIN_TRANSPORT,
      'visa': Permission.VIEW_ADMIN_VISA,
      'flights': Permission.VIEW_ADMIN_FLIGHTS,
    };
    const requiredPermission = modulePermissionMap[module];
    return requiredPermission ? this.hasPermission(requiredPermission) : false;
  }

  // ============================================================================
  // APPROVAL PERMISSIONS
  // ============================================================================

  /**
   * Check if user has any approval permissions
   */
  hasApprovalRights(): boolean {
    return this.hasAnyPermission([
      Permission.APPROVE_TRF,
      Permission.APPROVE_TRANSPORT,
      Permission.APPROVE_VISA,
      Permission.APPROVE_ACCOMMODATION,
      Permission.VIEW_PENDING_APPROVALS
    ]);
  }

  // ============================================================================
  // REQUEST PERMISSIONS
  // ============================================================================

  /**
   * Check if user can view all requests (not just their own)
   */
  canViewAllRequests(): boolean {
    return this.hasAnyPermission([
      Permission.VIEW_ALL_TRF,
      Permission.VIEW_ALL_TRANSPORT,
      Permission.SYSTEM_ADMIN,
      Permission.MANAGE_USERS
    ]);
  }

  /**
   * Check if user can create requests of a specific type
   */
  canCreateRequest(requestType: 'trf' | 'transport' | 'visa' | 'accommodation'): boolean {
    const user = this.authService.getCurrentUser();
    if (!user) return false;

    const requestPermissionMap: Record<string, string> = {
      'trf': Permission.CREATE_TRF,
      'transport': Permission.CREATE_TRANSPORT,
      'visa': Permission.CREATE_VISA,
      'accommodation': Permission.CREATE_ACCOMMODATION,
    };

    const requiredPermission = requestPermissionMap[requestType];
    // If permission exists, check it; otherwise allow (for backward compatibility)
    return requiredPermission ? this.hasPermission(requiredPermission) : true;
  }

  // ============================================================================
  // REPORTS & DATA
  // ============================================================================

  /**
   * Check if user has report permissions
   */
  hasReportPermissions(): boolean {
    return this.hasAnyPermission([
      Permission.GENERATE_ADMIN_REPORTS,
      Permission.EXPORT_DATA
    ]);
  }

  // ============================================================================
  // USER MANAGEMENT
  // ============================================================================

  /**
   * Check if user has system administrator permissions
   */
  hasAdminPermissions(): boolean {
    return this.hasAnyPermission([
      Permission.SYSTEM_ADMIN,
      Permission.MANAGE_USERS
    ]);
  }

  // ============================================================================
  // HELPER METHODS
  // ============================================================================

  /**
   * Get user's department name for department-specific filtering
   */
  getCurrentUserDepartment(): string | null {
    const user = this.authService.getCurrentUser();
    if (!user?.department) return null;

    if (typeof user.department === 'string') {
      return user.department;
    }
    return user.department.name || null;
  }

  /**
   * Filter requests based on user's visibility permissions
   */
  filterRequestsByUserRole<T extends {
    requestorId?: string;
    userId?: string;
    staff_id?: string;
    staff_no?: string;
    created_by?: string;
  }>(requests: T[]): T[] {
    // Users with view_all permissions see everything
    if (this.canViewAllRequests()) {
      return requests;
    }

    // Regular users see only their own requests
    const user = this.authService.getCurrentUser();
    if (!user) return [];

    const currentUserId = user.id?.toString();
    const currentEmail = user.email;

    return requests.filter(request => {
      return request.requestorId?.toString() === currentUserId ||
             request.userId?.toString() === currentUserId ||
             request.staff_id?.toString() === currentUserId ||
             request.staff_no === user.staff_id ||
             request.created_by === currentEmail;
    });
  }

  /**
   * Check if user can perform specific actions
   */
  canPerformAction(action: string, entityType: string): boolean {
    const actionToPermissionMap: Record<string, string> = {
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

    const requiredPermission = actionToPermissionMap[action];
    return requiredPermission ? this.hasPermission(requiredPermission) : false;
  }
}
