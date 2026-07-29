import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { extractData } from '../utils/api-response.handler';
import { StatusUtilsService } from '../utils/status-utils.service';
import {
  WorkflowTemplate,
  WorkflowInstance,
  WorkflowInstanceList,
  WorkflowStepExecution,
  WorkflowActionRequest,
  WorkflowUser,
} from '../models/workflow.models';

// Eligible Approvers Interfaces
export interface EligibleApprover {
  id: number;
  email: string;
  full_name: string;
  department: string | null;
  role: string | null;
}

export interface WorkflowStepWithApprovers {
  step_order: number;
  step_name: string;
  step_description: string | null;
  is_required: boolean;
  can_skip: boolean;
  approver_role: string | null;
  approver_permission: string | null;
  eligible_approvers: EligibleApprover[];
}

export interface EligibleApproversResponse {
  template_id: string;
  template_name: string;
  entity_type: string;
  steps: WorkflowStepWithApprovers[];
}

export interface ApproverSelection {
  [stepOrder: number]: number; // step_order -> user_id
}

@Injectable({
  providedIn: 'root',
})
export class WorkflowService {
  private apiUrl = `${environment.apiUrl}/workflows`;

  constructor(
    private http: HttpClient,
    private statusUtils: StatusUtilsService
  ) {}

  // ==================== Workflow Templates ====================

  /**
   * Get all workflow templates (Admin only)
   */
  getTemplates(filters?: {
    entity_type?: string;
    is_active?: boolean;
  }): Observable<WorkflowTemplate[]> {
    let params = new HttpParams();
    if (filters?.entity_type) {
      params = params.set('entity_type', filters.entity_type);
    }
    if (filters?.is_active !== undefined) {
      params = params.set('is_active', filters.is_active.toString());
    }
    return this.http.get<WorkflowTemplate[]>(`${this.apiUrl}/templates/`, { params });
  }

  /**
   * Get a specific workflow template
   */
  getTemplate(id: string): Observable<WorkflowTemplate> {
    return this.http.get<WorkflowTemplate>(`${this.apiUrl}/templates/${id}/`);
  }

  /**
   * Create a new workflow template (Admin only)
   */
  createTemplate(template: Partial<WorkflowTemplate>): Observable<WorkflowTemplate> {
    return this.http.post<WorkflowTemplate>(`${this.apiUrl}/templates/`, template);
  }

  /**
   * Update a workflow template (Admin only)
   */
  updateTemplate(id: string, template: Partial<WorkflowTemplate>): Observable<WorkflowTemplate> {
    return this.http.put<WorkflowTemplate>(`${this.apiUrl}/templates/${id}/`, template);
  }

  /**
   * Delete a workflow template (Admin only)
   */
  deleteTemplate(id: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/templates/${id}/`);
  }

  // ==================== Workflow Instances ====================

  /**
   * Get all workflow instances (filtered by permissions)
   */
  getInstances(filters?: {
    status?: string;
    entity_type?: string;
    template?: string;
    object_id?: number;
  }): Observable<WorkflowInstanceList[]> {
    let params = new HttpParams();
    if (filters?.status) {
      params = params.set('status', filters.status);
    }
    if (filters?.entity_type) {
      params = params.set('entity_type', filters.entity_type);
    }
    if (filters?.template) {
      params = params.set('template', filters.template);
    }
    if (filters?.object_id) {
      params = params.set('object_id', filters.object_id.toString());
    }
    return this.http
      .get<
        WorkflowInstanceList[] | { results: WorkflowInstanceList[] }
      >(`${this.apiUrl}/instances/`, { params })
      .pipe(map(response => (Array.isArray(response) ? response : response.results || [])));
  }

  /**
   * Get a specific workflow instance with full details
   */
  getInstance(id: string): Observable<WorkflowInstance> {
    return this.http.get<WorkflowInstance>(`${this.apiUrl}/instances/${id}/`);
  }

  // ==================== Step Executions ====================

  /**
   * Take action on a workflow step (approve/reject/skip/delegate)
   */
  takeAction(
    executionId: string,
    action: WorkflowActionRequest
  ): Observable<WorkflowStepExecution> {
    return this.http.post<WorkflowStepExecution>(
      `${this.apiUrl}/executions/${executionId}/take_action/`,
      action
    );
  }

  /**
   * Approve a workflow step
   */
  approveStep(executionId: string, comments?: string): Observable<WorkflowStepExecution> {
    return this.takeAction(executionId, {
      action: 'approve',
      comments,
    });
  }

  /**
   * Reject a workflow step
   */
  rejectStep(executionId: string, comments: string): Observable<WorkflowStepExecution> {
    return this.takeAction(executionId, {
      action: 'reject',
      comments,
    });
  }

  /**
   * Skip a workflow step
   */
  skipStep(executionId: string, comments?: string): Observable<WorkflowStepExecution> {
    return this.takeAction(executionId, {
      action: 'skip',
      comments,
    });
  }

  /**
   * Delegate a workflow step to another user
   */
  delegateStep(
    executionId: string,
    delegatedToId: string,
    reason?: string
  ): Observable<WorkflowStepExecution> {
    return this.takeAction(executionId, {
      action: 'delegate',
      comments: reason,
      delegated_to_id: delegatedToId,
    });
  }

  // ==================== Approver Selection ====================

  /**
   * Get eligible approvers for all steps in a workflow template.
   * Use this to allow users to select specific approvers before submitting a request.
   *
   * @param entityType The entity type (e.g., 'travelrequest', 'visaapplication')
   * @param options Optional parameters for filtering:
   *   - requesterId: User ID of the original requester
   *   - staffId: Staff ID of the original requester (fallback when requesterId is not available)
   * @returns Observable of eligible approvers for each workflow step
   *
   * Usage:
   * ```typescript
   * // For new requests (uses current user's department)
   * this.workflowService.getEligibleApprovers('travelrequest').subscribe({
   *   next: (response) => {
   *     this.workflowSteps = response.steps;
   *   }
   * });
   *
   * // For edit mode (uses original requester's department)
   * this.workflowService.getEligibleApprovers('travelrequest', { requesterId: 123 }).subscribe({...});
   * this.workflowService.getEligibleApprovers('accommodation', { staffId: 'EMP001' }).subscribe({...});
   * ```
   */
  getEligibleApprovers(
    entityType: string,
    options?: { requesterId?: number; staffId?: string }
  ): Observable<EligibleApproversResponse | null> {
    let url = `${this.apiUrl}/eligible-approvers/${entityType}/`;
    const params: string[] = [];

    if (options?.requesterId) {
      params.push(`requester_id=${options.requesterId}`);
    }
    if (options?.staffId) {
      params.push(`staff_id=${encodeURIComponent(options.staffId)}`);
    }

    if (params.length > 0) {
      url += `?${params.join('&')}`;
    }

    return this.http.get<unknown>(url).pipe(
      map(response => extractData<EligibleApproversResponse>(response)),
      catchError(error => {
        console.error('Error fetching eligible approvers:', error);
        return of(null);
      })
    );
  }

  // ==================== Helper Methods ====================

  /**
   * Get status badge class for workflow instance - delegates to
   * StatusUtilsService so the same status renders the same color
   * everywhere in the app.
   */
  getStatusClass(status: string): string {
    return this.statusUtils.getStatusBadgeClass(status);
  }

  /**
   * Get status badge class for step execution - delegates to
   * StatusUtilsService so the same status renders the same color
   * everywhere in the app.
   */
  getStepStatusClass(status: string): string {
    return this.statusUtils.getStatusBadgeClass(status);
  }

  /**
   * Format user name
   */
  formatUserName(user: WorkflowUser | undefined): string {
    if (!user) return 'N/A';
    return (
      user.full_name ||
      user.name ||
      `${user.first_name || ''} ${user.last_name || ''}`.trim() ||
      user.email
    );
  }

  /**
   * Check if step is overdue
   */
  isStepOverdue(stepExecution: WorkflowStepExecution): boolean {
    if (!stepExecution.sla_due_date) return false;
    return new Date(stepExecution.sla_due_date) < new Date() && stepExecution.status === 'pending';
  }

  /**
   * Get time remaining for SLA
   */
  getTimeRemaining(dueDate: string | undefined): string {
    if (!dueDate) return 'No deadline';

    const now = new Date();
    const due = new Date(dueDate);
    const diffMs = due.getTime() - now.getTime();

    if (diffMs < 0) return 'Overdue';

    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);

    if (diffDays > 0) {
      return `${diffDays} day${diffDays > 1 ? 's' : ''} remaining`;
    } else if (diffHours > 0) {
      return `${diffHours} hour${diffHours > 1 ? 's' : ''} remaining`;
    } else {
      const diffMinutes = Math.floor(diffMs / (1000 * 60));
      return `${diffMinutes} minute${diffMinutes > 1 ? 's' : ''} remaining`;
    }
  }

  /**
   * Get status display text for workflow instance
   */
  getWorkflowStatus(workflow: WorkflowInstance | WorkflowInstanceList | null): string {
    if (!workflow) return '';

    const status = workflow.status;
    const currentStep = 'current_step_order' in workflow ? workflow.current_step_order : undefined;
    const totalSteps = 'step_executions' in workflow ? workflow.step_executions?.length || 0 : 0;

    if (status === 'approved') return 'Approved';
    if (status === 'rejected') return 'Rejected';
    if (status === 'cancelled') return 'Cancelled';
    if (status === 'in_progress') {
      if (currentStep && totalSteps) {
        return `In Progress (Step ${currentStep} of ${totalSteps})`;
      }
      return 'In Progress';
    }
    if (status === 'pending') return 'Pending Approval';

    return status.charAt(0).toUpperCase() + status.slice(1);
  }

  /**
   * Get status badge class for workflow instance
   */
  getWorkflowStatusClass(workflow: WorkflowInstance | WorkflowInstanceList | null): string {
    if (!workflow) return 'badge-secondary';
    return this.getStatusClass(workflow.status);
  }
}
