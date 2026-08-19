import { Injectable } from '@angular/core';

/**
 * Shared utility service for status badge styling
 */
@Injectable({
  providedIn: 'root',
})
export class StatusUtilsService {
  /**
   * Get the unified badge class for a given status. This is the single
   * source of truth for status -> color across the whole app (TRF,
   * Transport, Visa, Accommodation, Approvals, and every admin
   * screen) - every component should call this instead of maintaining its
   * own local status->class mapping, so the same status always renders
   * the same color everywhere.
   * @param status The status string to get badge class for
   * @returns Unified badge class name (see styles.scss "Unified Badge Styles")
   */
  // Ordered list of (badge class -> matching keywords). Order matters:
  // the first category with a matching keyword wins, mirroring the
  // original if-chain's precedence (success > danger > info > warning > secondary).
  private static readonly STATUS_BADGE_KEYWORDS: ReadonlyArray<{
    badgeClass: string;
    keywords: readonly string[];
  }> = [
    {
      // Success states - the request/booking has reached a finalized, positive state
      badgeClass: 'badge-success',
      keywords: [
        'approved',
        'completed',
        'processed',
        'booked',
        'active',
        'confirmed',
        'checked-out',
        'assigned',
      ],
    },
    {
      // Danger/Error states - terminal negative outcome
      badgeClass: 'badge-danger',
      keywords: ['rejected', 'cancelled', 'canceled', 'failed', 'inactive', 'blocked', 'expired'],
    },
    {
      // Info states - actively being worked on (distinct from "pending", which means waiting on someone else to act)
      badgeClass: 'badge-info',
      keywords: [
        'processing',
        'in progress',
        'in_progress',
        'checked-in',
        'delegated',
        'under review',
      ],
    },
    {
      // Warning states - awaiting action from an approver/admin
      badgeClass: 'badge-warning',
      keywords: ['pending', 'awaiting', 'submitted', 'on hold', 'on_hold'],
    },
    {
      // Secondary states - not yet started / no action taken
      badgeClass: 'badge-secondary',
      keywords: ['draft', 'new', 'not started'],
    },
  ];

  getStatusBadgeClass(status: string | null | undefined): string {
    if (!status) return 'badge-secondary';

    const statusLower = status.toLowerCase();
    const match = StatusUtilsService.STATUS_BADGE_KEYWORDS.find(({ keywords }) =>
      keywords.some(keyword => statusLower.includes(keyword))
    );

    return match?.badgeClass || 'badge-secondary';
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
