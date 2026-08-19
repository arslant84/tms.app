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
  providedIn: 'root',
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
  canAccessAdminMenu(module: 'accommodation' | 'transport' | 'visa' | 'flights' | 'meal'): boolean {
    // System admins have access to all admin modules
    if (this.hasPermission(Permission.SYSTEM_ADMIN)) return true;

    const modulePermissionMap: Record<string, string> = {
      accommodation: Permission.VIEW_ADMIN_ACCOMMODATION,
      transport: Permission.VIEW_ADMIN_TRANSPORT,
      visa: Permission.VIEW_ADMIN_VISA,
      flights: Permission.VIEW_ADMIN_FLIGHTS,
      meal: Permission.VIEW_ADMIN_MEAL,
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
      Permission.VIEW_PENDING_APPROVALS,
    ]);
  }

  // ============================================================================
  // REPORTS & DATA
  // ============================================================================

  /**
   * Check if user has report permissions
   */
  hasReportPermissions(): boolean {
    return this.hasAnyPermission([Permission.GENERATE_ADMIN_REPORTS, Permission.EXPORT_DATA]);
  }

  // ============================================================================
  // USER MANAGEMENT
  // ============================================================================

  /**
   * Check if user has system administrator permissions
   */
  hasAdminPermissions(): boolean {
    return this.hasAnyPermission([Permission.SYSTEM_ADMIN, Permission.MANAGE_USERS]);
  }
}
