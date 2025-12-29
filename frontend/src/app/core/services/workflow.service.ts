import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  WorkflowTemplate,
  WorkflowStep,
  WorkflowInstance,
  WorkflowInstanceList,
  WorkflowStepExecution,
  WorkflowDelegation,
  WorkflowAuditLog,
  PendingApproval,
  ApprovalAction,
  DelegationAction,
  WorkflowActionRequest,
  WorkflowUser
} from '../models/workflow.models';

@Injectable({
  providedIn: 'root'
})
export class WorkflowService {
  private apiUrl = `${environment.apiUrl}/workflows`;

  constructor(private http: HttpClient) {}

  // ==================== Workflow Templates ====================

  /**
   * Get all workflow templates (Admin only)
   */
  getTemplates(filters?: { entity_type?: string; is_active?: boolean }): Observable<WorkflowTemplate[]> {
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
   * Duplicate a workflow template (Admin only)
   */
  duplicateTemplate(id: string): Observable<WorkflowTemplate> {
    return this.http.post<WorkflowTemplate>(`${this.apiUrl}/templates/${id}/duplicate/`, {});
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
    return this.http.get<WorkflowInstanceList[]>(`${this.apiUrl}/instances/`, { params });
  }

  /**
   * Get a specific workflow instance with full details
   */
  getInstance(id: string): Observable<WorkflowInstance> {
    return this.http.get<WorkflowInstance>(`${this.apiUrl}/instances/${id}/`);
  }

  /**
   * Create a new workflow instance
   */
  createInstance(data: {
    workflow_template_id: number;
    entity_type: string;
    entity_id: number;
    additional_data?: any;
  }): Observable<WorkflowInstance> {
    return this.http.post<WorkflowInstance>(`${this.apiUrl}/instances/`, data);
  }

  /**
   * Start a workflow instance (transition from pending to in_progress)
   */
  startInstance(id: string): Observable<WorkflowInstance> {
    return this.http.post<WorkflowInstance>(`${this.apiUrl}/instances/${id}/start/`, {});
  }

  /**
   * Cancel a workflow instance
   */
  cancelInstance(id: string, reason?: string): Observable<WorkflowInstance> {
    return this.http.post<WorkflowInstance>(`${this.apiUrl}/instances/${id}/cancel/`, { reason });
  }

  /**
   * Get current user's pending approvals
   */
  getMyPendingApprovals(): Observable<WorkflowInstanceList[]> {
    return this.http.get<WorkflowInstanceList[]>(`${this.apiUrl}/instances/my_pending_approvals/`);
  }

  /**
   * Get workflow status for a specific entity
   */
  getWorkflowForEntity(entityType: string, entityId: number): Observable<WorkflowInstance | null> {
    return this.http.get<WorkflowInstance>(`${this.apiUrl}/instances/`, {
      params: new HttpParams()
        .set('entity_type', entityType)
        .set('entity_id', entityId.toString())
    });
  }

  // ==================== Step Executions ====================

  /**
   * Get step executions for an instance
   */
  getStepExecutions(instanceId: string): Observable<WorkflowStepExecution[]> {
    return this.http.get<WorkflowStepExecution[]>(`${this.apiUrl}/executions/`, {
      params: new HttpParams().set('instance', instanceId)
    });
  }

  /**
   * Get a specific step execution
   */
  getStepExecution(id: string): Observable<WorkflowStepExecution> {
    return this.http.get<WorkflowStepExecution>(`${this.apiUrl}/executions/${id}/`);
  }

  /**
   * Take action on a workflow step (approve/reject/skip/delegate)
   */
  takeAction(executionId: string, action: WorkflowActionRequest): Observable<WorkflowStepExecution> {
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
      comments
    });
  }

  /**
   * Reject a workflow step
   */
  rejectStep(executionId: string, comments: string): Observable<WorkflowStepExecution> {
    return this.takeAction(executionId, {
      action: 'reject',
      comments
    });
  }

  /**
   * Skip a workflow step
   */
  skipStep(executionId: string, comments?: string): Observable<WorkflowStepExecution> {
    return this.takeAction(executionId, {
      action: 'skip',
      comments
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
      delegated_to_id: delegatedToId
    });
  }

  // ==================== Delegations ====================

  /**
   * Get delegations (filtered by user)
   */
  getDelegations(): Observable<WorkflowDelegation[]> {
    return this.http.get<WorkflowDelegation[]>(`${this.apiUrl}/delegations/`);
  }

  /**
   * Get a specific delegation
   */
  getDelegation(id: string): Observable<WorkflowDelegation> {
    return this.http.get<WorkflowDelegation>(`${this.apiUrl}/delegations/${id}/`);
  }

  // ==================== Audit Logs ====================

  /**
   * Get audit logs for a workflow instance
   */
  getAuditLogs(instanceId: string): Observable<WorkflowAuditLog[]> {
    return this.http.get<WorkflowAuditLog[]>(`${this.apiUrl}/audit-logs/`, {
      params: new HttpParams().set('instance', instanceId)
    });
  }

  /**
   * Get a specific audit log entry
   */
  getAuditLog(id: string): Observable<WorkflowAuditLog> {
    return this.http.get<WorkflowAuditLog>(`${this.apiUrl}/audit-logs/${id}/`);
  }

  // ==================== Helper Methods ====================

  /**
   * Check if current user can action a specific step
   */
  canActionStep(stepExecution: WorkflowStepExecution): boolean {
    return stepExecution.can_action === true && stepExecution.status === 'pending';
  }

  /**
   * Get status badge class for workflow instance
   */
  getStatusClass(status: string): string {
    const statusMap: { [key: string]: string } = {
      'pending': 'badge-secondary',
      'in_progress': 'badge-warning',
      'approved': 'badge-success',
      'completed': 'badge-success',
      'rejected': 'badge-danger',
      'cancelled': 'badge-secondary',
      'on_hold': 'badge-info'
    };
    return statusMap[status] || 'badge-secondary';
  }

  /**
   * Get status badge class for step execution
   */
  getStepStatusClass(status: string): string {
    const statusMap: { [key: string]: string } = {
      'pending': 'badge-warning',
      'approved': 'badge-success',
      'rejected': 'badge-danger',
      'skipped': 'badge-secondary',
      'delegated': 'badge-info'
    };
    return statusMap[status] || 'badge-secondary';
  }

  /**
   * Format user name
   */
  formatUserName(user: WorkflowUser | undefined): string {
    if (!user) return 'N/A';
    return user.full_name || user.name || `${user.first_name || ''} ${user.last_name || ''}`.trim() || user.email;
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
