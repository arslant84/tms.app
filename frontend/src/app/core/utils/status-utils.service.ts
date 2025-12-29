import { Injectable } from '@angular/core';

/**
 * Shared utility service for status badge styling
 */
@Injectable({
  providedIn: 'root'
})
export class StatusUtilsService {

  /**
   * Get Bootstrap badge class for a given status
   * @param status The status string to get badge class for
   * @returns Bootstrap badge class name
   */
  getStatusBadgeClass(status: string | null | undefined): string {
    if (!status) return 'badge-secondary';

    const statusLower = status.toLowerCase();

    // Success states
    if (statusLower.includes('approved') ||
        statusLower.includes('completed') ||
        statusLower.includes('active') ||
        statusLower.includes('confirmed') ||
        statusLower.includes('assigned')) {
      return 'badge-success';
    }

    // Danger/Error states
    if (statusLower.includes('rejected') ||
        statusLower.includes('cancelled') ||
        statusLower.includes('canceled') ||
        statusLower.includes('failed') ||
        statusLower.includes('inactive') ||
        statusLower.includes('expired')) {
      return 'badge-danger';
    }

    // Warning states
    if (statusLower.includes('pending') ||
        statusLower.includes('in progress') ||
        statusLower.includes('in_progress') ||
        statusLower.includes('processing')) {
      return 'badge-warning';
    }

    // Info states
    if (statusLower.includes('draft') ||
        statusLower.includes('submitted') ||
        statusLower.includes('new')) {
      return 'badge-info';
    }

    // Secondary states
    if (statusLower.includes('not started') ||
        statusLower.includes('on hold')) {
      return 'badge-secondary';
    }

    // Default
    return 'badge-secondary';
  }

  /**
   * Get workflow-specific badge class
   * @param status The workflow status
   * @returns Bootstrap badge class name
   */
  getWorkflowStatusClass(status: string | null | undefined): string {
    if (!status) return 'badge-secondary';

    const statusLower = status.toLowerCase();

    if (statusLower === 'approved') return 'badge-success';
    if (statusLower === 'rejected') return 'badge-danger';
    if (statusLower === 'cancelled' || statusLower === 'canceled') return 'badge-secondary';
    if (statusLower === 'in_progress' || statusLower === 'pending') return 'badge-warning';

    return 'badge-info';
  }

  /**
   * Get visa type badge class
   * @param visaType The visa type
   * @returns Bootstrap badge class name
   */
  getVisaTypeBadgeClass(visaType: string | null | undefined): string {
    if (!visaType) return 'badge-secondary';

    const typeLower = visaType.toLowerCase();

    if (typeLower.includes('business')) return 'badge-primary';
    if (typeLower.includes('tourist')) return 'badge-info';
    if (typeLower.includes('work')) return 'badge-success';
    if (typeLower.includes('student')) return 'badge-warning';
    if (typeLower.includes('diplomatic') || typeLower.includes('official')) return 'badge-danger';

    return 'badge-secondary';
  }

  /**
   * Get user role badge class
   * @param role The user role
   * @returns Bootstrap badge class name
   */
  getUserRoleBadgeClass(role: string | null | undefined): string {
    if (!role) return 'badge-secondary';

    const roleLower = role.toLowerCase();

    if (roleLower.includes('admin') || roleLower.includes('administrator')) return 'badge-danger';
    if (roleLower.includes('manager') || roleLower.includes('supervisor')) return 'badge-warning';
    if (roleLower.includes('approver')) return 'badge-primary';
    if (roleLower.includes('user') || roleLower.includes('employee')) return 'badge-info';

    return 'badge-secondary';
  }

  /**
   * Get priority badge class
   * @param priority The priority level
   * @returns Bootstrap badge class name
   */
  getPriorityBadgeClass(priority: string | number | null | undefined): string {
    if (!priority) return 'badge-secondary';

    const priorityStr = priority.toString().toLowerCase();

    if (priorityStr.includes('high') || priorityStr.includes('urgent') || priorityStr === '1') {
      return 'badge-danger';
    }
    if (priorityStr.includes('medium') || priorityStr.includes('normal') || priorityStr === '2') {
      return 'badge-warning';
    }
    if (priorityStr.includes('low') || priorityStr === '3') {
      return 'badge-info';
    }

    return 'badge-secondary';
  }

  /**
   * Get accommodation status badge class
   * @param status The accommodation status
   * @returns Bootstrap badge class name
   */
  getAccommodationStatusBadgeClass(status: string | null | undefined): string {
    if (!status) return 'badge-secondary';

    const statusLower = status.toLowerCase();

    if (statusLower.includes('confirmed') || statusLower.includes('checked-in')) {
      return 'badge-success';
    }
    if (statusLower.includes('pending') || statusLower.includes('requested')) {
      return 'badge-warning';
    }
    if (statusLower.includes('cancelled') || statusLower.includes('canceled') || statusLower.includes('checked-out')) {
      return 'badge-secondary';
    }

    return 'badge-info';
  }

  /**
   * Get flight status badge class
   * @param status The flight status
   * @returns Bootstrap badge class name
   */
  getFlightStatusBadgeClass(status: string | null | undefined): string {
    if (!status) return 'badge-secondary';

    const statusLower = status.toLowerCase();

    if (statusLower.includes('booked') || statusLower.includes('confirmed')) {
      return 'badge-success';
    }
    if (statusLower.includes('pending') || statusLower.includes('requested')) {
      return 'badge-warning';
    }
    if (statusLower.includes('cancelled') || statusLower.includes('canceled')) {
      return 'badge-danger';
    }

    return 'badge-info';
  }
}
