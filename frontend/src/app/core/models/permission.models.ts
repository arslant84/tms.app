/**
 * Permission Models and Constants
 *
 * This file defines all permissions used in the TMS application.
 * Permissions are organized by category for easy maintenance.
 */

/**
 * Permission enumeration - all available permissions in the system
 */
export enum Permission {
  // ============================================================================
  // MODULE ACCESS (Admin Menus)
  // ============================================================================
  VIEW_ADMIN_ACCOMMODATION = 'view_admin_accommodation',
  MANAGE_ACCOMMODATION_BOOKINGS = 'manage_accommodation_bookings',

  VIEW_ADMIN_TRANSPORT = 'view_admin_transport',
  MANAGE_TRANSPORT_REQUESTS = 'manage_transport_requests',

  VIEW_ADMIN_VISA = 'view_admin_visa',
  PROCESS_VISA_APPLICATIONS = 'process_visa_applications',

  VIEW_ADMIN_FLIGHTS = 'view_admin_flights',
  MANAGE_FLIGHTS = 'manage_flights',
  PROCESS_FLIGHTS = 'process_flights',

  VIEW_ADMIN_COMBINED = 'view_admin_combined',
  MANAGE_COMBINED_REQUESTS = 'manage_combined_requests',
  PROCESS_COMBINED_REQUESTS = 'process_combined_requests',

  // ============================================================================
  // REQUEST CREATION
  // ============================================================================
  CREATE_TRF = 'create_trf',
  CREATE_TRANSPORT = 'create_transport',
  CREATE_VISA = 'create_visa',
  CREATE_ACCOMMODATION = 'create_accommodation',
  CREATE_COMBINED = 'create_combined',

  // ============================================================================
  // APPROVAL CAPABILITIES (Workflow-based)
  // ============================================================================
  APPROVE_ACCOMMODATION = 'approve_accommodation',
  APPROVE_TRANSPORT = 'approve_transport',
  APPROVE_VISA = 'approve_visa',
  APPROVE_TRF = 'approve_trf',
  APPROVE_COMBINED = 'approve_combined',

  // ============================================================================
  // SYSTEM ADMINISTRATION
  // ============================================================================
  SYSTEM_ADMIN = 'system_admin',
  MANAGE_APPLICATION_SETTINGS = 'manage_application_settings',
  MANAGE_ROLES = 'manage_roles',
  MANAGE_USERS = 'manage_users',
  VIEW_SYSTEM_SETTINGS = 'view_system_settings',
  ACCESS_DEBUG_ENDPOINTS = 'access_debug_endpoints',

  // ============================================================================
  // REPORTING & DATA
  // ============================================================================
  VIEW_ALL_TRF = 'view_all_trf',
  VIEW_ALL_TRANSPORT = 'view_all_transport',
  GENERATE_ADMIN_REPORTS = 'generate_admin_reports',
  EXPORT_DATA = 'export_data',

  // ============================================================================
  // NOTIFICATIONS
  // ============================================================================
  MANAGE_NOTIFICATIONS = 'manage_notifications',
  SEND_NOTIFICATIONS = 'send_notifications',

  // ============================================================================
  // USER & PROFILE
  // ============================================================================
  VIEW_USERS = 'view_users',
  VIEW_PROFILES = 'view_profiles',
  MANAGE_OWN_PROFILE = 'manage_own_profile',

  // ============================================================================
  // DOCUMENTS & TEMPLATES
  // ============================================================================
  UPLOAD_DOCUMENTS = 'upload_documents',
  MANAGE_DOCUMENT_TEMPLATES = 'manage_document_templates',

  // ============================================================================
  // OTHER
  // ============================================================================
  VIEW_ACTIVITY_LOGS = 'view_activity_logs',
  VIEW_DASHBOARD_SUMMARY = 'view_dashboard_summary',
  VIEW_SIDEBAR_COUNTS = 'view_sidebar_counts',
  VIEW_OWN_REQUESTS = 'view_own_requests',
  VIEW_DEPARTMENT_REQUESTS = 'view_department_requests',
  VIEW_PENDING_APPROVALS = 'view_pending_approvals',
  VIEW_VISA_APPLICATIONS = 'view_visa_applications',
  VIEW_VISA_REPORTS = 'view_visa_reports',
}

/**
 * Permission categories for organizing permissions in UI
 */
export enum PermissionCategory {
  MODULE_ACCESS = 'Module Access',
  REQUEST_CREATION = 'Request Creation',
  APPROVALS = 'Approvals',
  SYSTEM_ADMIN = 'System Administration',
  REPORTING = 'Reporting & Data',
  NOTIFICATIONS = 'Notifications',
  USERS = 'User Management',
  DOCUMENTS = 'Documents',
  OTHER = 'Other',
}

/**
 * Map permissions to their categories
 */
export const PERMISSION_CATEGORIES: Record<Permission, PermissionCategory> = {
  // Module Access
  [Permission.VIEW_ADMIN_ACCOMMODATION]: PermissionCategory.MODULE_ACCESS,
  [Permission.MANAGE_ACCOMMODATION_BOOKINGS]: PermissionCategory.MODULE_ACCESS,
  [Permission.VIEW_ADMIN_TRANSPORT]: PermissionCategory.MODULE_ACCESS,
  [Permission.MANAGE_TRANSPORT_REQUESTS]: PermissionCategory.MODULE_ACCESS,
  [Permission.VIEW_ADMIN_VISA]: PermissionCategory.MODULE_ACCESS,
  [Permission.PROCESS_VISA_APPLICATIONS]: PermissionCategory.MODULE_ACCESS,
  [Permission.VIEW_ADMIN_FLIGHTS]: PermissionCategory.MODULE_ACCESS,
  [Permission.MANAGE_FLIGHTS]: PermissionCategory.MODULE_ACCESS,
  [Permission.PROCESS_FLIGHTS]: PermissionCategory.MODULE_ACCESS,
  [Permission.VIEW_ADMIN_COMBINED]: PermissionCategory.MODULE_ACCESS,
  [Permission.MANAGE_COMBINED_REQUESTS]: PermissionCategory.MODULE_ACCESS,
  [Permission.PROCESS_COMBINED_REQUESTS]: PermissionCategory.MODULE_ACCESS,

  // Request Creation
  [Permission.CREATE_TRF]: PermissionCategory.REQUEST_CREATION,
  [Permission.CREATE_TRANSPORT]: PermissionCategory.REQUEST_CREATION,
  [Permission.CREATE_VISA]: PermissionCategory.REQUEST_CREATION,
  [Permission.CREATE_ACCOMMODATION]: PermissionCategory.REQUEST_CREATION,
  [Permission.CREATE_COMBINED]: PermissionCategory.REQUEST_CREATION,

  // Approvals
  [Permission.APPROVE_ACCOMMODATION]: PermissionCategory.APPROVALS,
  [Permission.APPROVE_TRANSPORT]: PermissionCategory.APPROVALS,
  [Permission.APPROVE_VISA]: PermissionCategory.APPROVALS,
  [Permission.APPROVE_TRF]: PermissionCategory.APPROVALS,
  [Permission.APPROVE_COMBINED]: PermissionCategory.APPROVALS,

  // System Admin
  [Permission.SYSTEM_ADMIN]: PermissionCategory.SYSTEM_ADMIN,
  [Permission.MANAGE_APPLICATION_SETTINGS]: PermissionCategory.SYSTEM_ADMIN,
  [Permission.MANAGE_ROLES]: PermissionCategory.SYSTEM_ADMIN,
  [Permission.MANAGE_USERS]: PermissionCategory.SYSTEM_ADMIN,
  [Permission.VIEW_SYSTEM_SETTINGS]: PermissionCategory.SYSTEM_ADMIN,
  [Permission.ACCESS_DEBUG_ENDPOINTS]: PermissionCategory.SYSTEM_ADMIN,

  // Reporting
  [Permission.VIEW_ALL_TRF]: PermissionCategory.REPORTING,
  [Permission.VIEW_ALL_TRANSPORT]: PermissionCategory.REPORTING,
  [Permission.GENERATE_ADMIN_REPORTS]: PermissionCategory.REPORTING,
  [Permission.EXPORT_DATA]: PermissionCategory.REPORTING,

  // Notifications
  [Permission.MANAGE_NOTIFICATIONS]: PermissionCategory.NOTIFICATIONS,
  [Permission.SEND_NOTIFICATIONS]: PermissionCategory.NOTIFICATIONS,

  // Users
  [Permission.VIEW_USERS]: PermissionCategory.USERS,
  [Permission.VIEW_PROFILES]: PermissionCategory.USERS,
  [Permission.MANAGE_OWN_PROFILE]: PermissionCategory.USERS,

  // Documents
  [Permission.UPLOAD_DOCUMENTS]: PermissionCategory.DOCUMENTS,
  [Permission.MANAGE_DOCUMENT_TEMPLATES]: PermissionCategory.DOCUMENTS,

  // Other
  [Permission.VIEW_ACTIVITY_LOGS]: PermissionCategory.OTHER,
  [Permission.VIEW_DASHBOARD_SUMMARY]: PermissionCategory.OTHER,
  [Permission.VIEW_SIDEBAR_COUNTS]: PermissionCategory.OTHER,
  [Permission.VIEW_OWN_REQUESTS]: PermissionCategory.OTHER,
  [Permission.VIEW_DEPARTMENT_REQUESTS]: PermissionCategory.OTHER,
  [Permission.VIEW_PENDING_APPROVALS]: PermissionCategory.OTHER,
  [Permission.VIEW_VISA_APPLICATIONS]: PermissionCategory.OTHER,
  [Permission.VIEW_VISA_REPORTS]: PermissionCategory.OTHER,
};

/**
 * Helper function to check if user has a specific permission
 */
export function hasPermission(userPermissions: string[], permission: Permission): boolean {
  return userPermissions.includes(permission);
}

/**
 * Helper function to check if user has any of the specified permissions
 */
export function hasAnyPermission(userPermissions: string[], permissions: Permission[]): boolean {
  return permissions.some(p => userPermissions.includes(p));
}

/**
 * Helper function to check if user has all of the specified permissions
 */
export function hasAllPermissions(userPermissions: string[], permissions: Permission[]): boolean {
  return permissions.every(p => userPermissions.includes(p));
}

/**
 * Permission groups for common role configurations
 */
export const PermissionGroups = {
  /**
   * Basic user permissions - can create requests
   */
  BASIC_USER: [
    Permission.CREATE_TRF,
    Permission.CREATE_TRANSPORT,
    Permission.CREATE_VISA,
    Permission.CREATE_ACCOMMODATION,
    Permission.CREATE_COMBINED,
    Permission.VIEW_OWN_REQUESTS,
    Permission.MANAGE_OWN_PROFILE,
    Permission.UPLOAD_DOCUMENTS,
  ],

  /**
   * Approver permissions - can approve requests via workflows
   */
  APPROVER: [
    Permission.APPROVE_TRF,
    Permission.APPROVE_TRANSPORT,
    Permission.APPROVE_VISA,
    Permission.APPROVE_ACCOMMODATION,
    Permission.APPROVE_COMBINED,
    Permission.VIEW_PENDING_APPROVALS,
  ],

  /**
   * Admin menu access permissions
   */
  ADMIN_MENUS: [
    Permission.VIEW_ADMIN_ACCOMMODATION,
    Permission.VIEW_ADMIN_TRANSPORT,
    Permission.VIEW_ADMIN_VISA,
    Permission.VIEW_ADMIN_FLIGHTS,
    Permission.VIEW_ADMIN_COMBINED,
  ],

  /**
   * System administrator permissions
   */
  SYSTEM_ADMIN: [
    Permission.SYSTEM_ADMIN,
    Permission.MANAGE_APPLICATION_SETTINGS,
    Permission.MANAGE_ROLES,
    Permission.MANAGE_USERS,
    Permission.VIEW_SYSTEM_SETTINGS,
    Permission.MANAGE_NOTIFICATIONS,
  ],
};

/**
 * Interface for permission display in UI
 */
export interface PermissionDisplay {
  id: string;
  name: string;
  description: string;
  category: PermissionCategory;
}
