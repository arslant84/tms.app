import { Injectable } from '@angular/core';

/**
 * Shared utility service for status badge styling
 */
@Injectable({
  providedIn: 'root'
})
export class StatusUtilsService {

  /**
   * Get the unified badge class for a given status. This is the single
   * source of truth for status -> color across the whole app (TRF,
   * Transport, Visa, Accommodation, Combined, Approvals, and every admin
   * screen) - every component should call this instead of maintaining its
   * own local status->class mapping, so the same status always renders
   * the same color everywhere.
   * @param status The status string to get badge class for
   * @returns Unified badge class name (see styles.scss "Unified Badge Styles")
   */
  getStatusBadgeClass(status: string | null | undefined): string {
    if (!status) return 'badge-secondary';

    const statusLower = status.toLowerCase();

    // Success states - the request/booking has reached a finalized,
    // positive state
    if (statusLower.includes('approved') ||
        statusLower.includes('completed') ||
        statusLower.includes('processed') ||
        statusLower.includes('booked') ||
        statusLower.includes('active') ||
        statusLower.includes('confirmed') ||
        statusLower.includes('checked-out') ||
        statusLower.includes('assigned')) {
      return 'badge-success';
    }

    // Danger/Error states - terminal negative outcome
    if (statusLower.includes('rejected') ||
        statusLower.includes('cancelled') ||
        statusLower.includes('canceled') ||
        statusLower.includes('failed') ||
        statusLower.includes('inactive') ||
        statusLower.includes('blocked') ||
        statusLower.includes('expired')) {
      return 'badge-danger';
    }

    // Info states - actively being worked on (distinct from "pending",
    // which means waiting on someone else to act)
    if (statusLower.includes('processing') ||
        statusLower.includes('in progress') ||
        statusLower.includes('in_progress') ||
        statusLower.includes('checked-in') ||
        statusLower.includes('delegated') ||
        statusLower.includes('under review')) {
      return 'badge-info';
    }

    // Warning states - awaiting action from an approver/admin
    if (statusLower.includes('pending') ||
        statusLower.includes('awaiting') ||
        statusLower.includes('submitted') ||
        statusLower.includes('on hold') ||
        statusLower.includes('on_hold')) {
      return 'badge-warning';
    }

    // Secondary states - not yet started / no action taken
    if (statusLower.includes('draft') ||
        statusLower.includes('new') ||
        statusLower.includes('not started')) {
      return 'badge-secondary';
    }

    // Default
    return 'badge-secondary';
  }

  /**
   * Get workflow-specific badge class
   * @param status The workflow status
   * @returns Unified badge class name
   */
  getWorkflowStatusClass(status: string | null | undefined): string {
    return this.getStatusBadgeClass(status);
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
    if (status.toLowerCase().includes('requested')) return 'badge-warning';
    return this.getStatusBadgeClass(status);
  }

  /**
   * Get flight status badge class
   * @param status The flight status
   * @returns Bootstrap badge class name
   */
  getFlightStatusBadgeClass(status: string | null | undefined): string {
    if (!status) return 'badge-secondary';
    if (status.toLowerCase().includes('booked')) return 'badge-success';
    return this.getStatusBadgeClass(status);
  }
}
