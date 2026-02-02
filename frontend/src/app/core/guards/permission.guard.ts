import { inject } from '@angular/core';
import { Router, CanActivateFn, ActivatedRouteSnapshot } from '@angular/router';
import { RbacService } from '../services/rbac.service';
import { AuthService } from '../services/auth.service';
import { Permission } from '../models/permission.models';

/**
 * Permission Guard
 *
 * Checks if user has required permissions to access a route.
 * Usage in routes:
 *
 * {
 *   path: 'admin/accommodation',
 *   component: AccommodationAdminComponent,
 *   canActivate: [PermissionGuard],
 *   data: {
 *     permissions: [Permission.VIEW_ADMIN_ACCOMMODATION],
 *     requireAll: false  // true = must have ALL permissions, false = must have ANY permission
 *   }
 * }
 */
export const PermissionGuard: CanActivateFn = (route: ActivatedRouteSnapshot) => {
  const rbacService = inject(RbacService);
  const router = inject(Router);
  const authService = inject(AuthService);

  // Get required permissions from route data
  const requiredPermissions = route.data['permissions'] as Permission[] | undefined;
  const requireAll = route.data['requireAll'] as boolean | undefined ?? false;

  // If no permissions specified, allow access
  if (!requiredPermissions || requiredPermissions.length === 0) {
    return true;
  }

  // SECURITY: Admin users have access to everything
  const currentUser = authService.getCurrentUser();
  if (currentUser?.is_admin) {
    return true;
  }

  // Check permissions
  const hasPermission = requireAll
    ? rbacService.hasAllPermissions(requiredPermissions)
    : rbacService.hasAnyPermission(requiredPermissions);

  if (!hasPermission) {
    console.warn('PermissionGuard: Access denied', {
      requiredPermissions,
      requireAll,
      userPermissions: currentUser?.permissions,
      is_admin: currentUser?.is_admin,
      role: currentUser?.role
    });

    // Redirect to dashboard if user doesn't have permission
    router.navigate(['/dashboard']);
    return false;
  }

  return true;
};

/**
 * Admin Menu Guard
 *
 * Checks if user can access admin menu for a specific module.
 * Usage in routes:
 *
 * {
 *   path: 'admin/accommodation',
 *   component: AccommodationAdminComponent,
 *   canActivate: [AdminMenuGuard],
 *   data: { adminModule: 'accommodation' }
 * }
 */
export const AdminMenuGuard: CanActivateFn = (route: ActivatedRouteSnapshot) => {
  const rbacService = inject(RbacService);
  const router = inject(Router);

  // Get admin module from route data
  const adminModule = route.data['adminModule'] as 'accommodation' | 'transport' | 'visa' | 'flights' | undefined;

  // If no module specified, deny access
  if (!adminModule) {
    console.error('AdminMenuGuard: No adminModule specified in route data');
    router.navigate(['/dashboard']);
    return false;
  }

  // Check if user can access admin menu
  const hasAccess = rbacService.canAccessAdminMenu(adminModule);

  if (!hasAccess) {
    console.warn(`Access denied: User cannot access ${adminModule} admin menu`);
    router.navigate(['/dashboard']);
    return false;
  }

  return true;
};
