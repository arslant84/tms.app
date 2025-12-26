/**
 * Workflow Models and Interfaces
 * Matches backend Django models for workflow approval system
 */

export interface WorkflowUser {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  full_name?: string;
  department?: string;
  name?: string;
}

export interface WorkflowCondition {
  id: string;
  condition_type: 'field_equals' | 'field_greater_than' | 'field_less_than' | 'field_contains' | 'field_exists' | 'custom_logic';
  field_name: string;
  field_value?: string;
  logical_operator: 'AND' | 'OR';
  is_active: boolean;
}

export interface WorkflowStepNotificationConfig {
  id?: string;
  workflow_step?: string;
  event_type: 'assignment' | 'approval' | 'rejection' | 'escalation' | 'reminder' | 'delegation';
  event_type_display?: string;
  notification_template: string;
  notification_template_name?: string;
  recipient_types: RecipientType[];
  custom_recipients: string[];
  is_active: boolean;
  send_email: boolean;
  send_system_notification: boolean;
  priority: 'low' | 'normal' | 'high' | 'urgent';
  priority_display?: string;
  created_at?: string;
  updated_at?: string;
}

// RecipientType now supports both predefined types and dynamic role IDs (role_*)
export type RecipientType =
  | 'current_approver'
  | 'requester'
  | 'previous_approvers'
  | 'next_approvers'
  | 'all_stakeholders'
  | 'custom_emails'
  | string; // Allow dynamic role IDs like 'role_123'

export const EVENT_TYPE_OPTIONS = [
  // Step-level events (during workflow)
  { value: 'assignment', label: 'On Step Assignment' },
  { value: 'approval', label: 'On Step Approval' },
  { value: 'rejection', label: 'On Step Rejection' },
  { value: 'escalation', label: 'On Step Escalation' },
  { value: 'reminder', label: 'Reminder Notification' },
  { value: 'delegation', label: 'On Step Delegation' },

  // Workflow-level events (after all approvals)
  { value: 'workflow_completed', label: 'When All Approvals Complete' },
  { value: 'workflow_cancelled', label: 'When Workflow Cancelled' },
];

export interface WorkflowStep {
  id: string;
  workflow_template?: string;
  step_order: number;
  step_name: string;
  step_description?: string;
  approver_role: string;
  approver_user?: string;
  approver_user_detail?: WorkflowUser;
  is_required: boolean;
  can_skip: boolean;
  requires_comments: boolean;
  sla_hours?: number;
  escalation_hours?: number;
  conditions?: WorkflowCondition[];
  notification_configs?: WorkflowStepNotificationConfig[];
  created_at: string;
  updated_at: string;
}

export interface WorkflowTemplate {
  id: string;
  name: string;
  description?: string;
  entity_type: string;
  is_active: boolean;
  allow_parallel_steps: boolean;
  auto_approve_on_condition: boolean;
  step_count?: number;
  steps?: WorkflowStep[];
  created_by?: string;
  created_by_user?: WorkflowUser;
  created_at: string;
  updated_at: string;
}

export interface WorkflowDelegation {
  id: string;
  workflow_step_execution?: string;
  delegated_from: string;
  delegated_from_user?: WorkflowUser;
  delegated_to: string;
  delegated_to_user?: WorkflowUser;
  reason?: string;
  is_active: boolean;
  delegated_at: string;
  expires_at?: string;
}

export interface WorkflowStepExecution {
  id: string;
  workflow_instance?: string;
  workflow_step: string;
  workflow_step_detail?: WorkflowStep;
  status: 'pending' | 'approved' | 'rejected' | 'skipped' | 'delegated';
  assigned_to?: string;
  assigned_to_user?: WorkflowUser;
  actioned_by?: string;
  actioned_by_user?: WorkflowUser;
  comments?: string;
  action_date?: string;
  sla_due_date?: string;
  escalation_date?: string;
  is_overdue: boolean;
  is_escalated: boolean;
  delegations?: WorkflowDelegation[];
  can_action?: boolean;
  created_at: string;
  updated_at: string;
}

export interface WorkflowAuditLog {
  id: string;
  workflow_instance: string;
  action_type: 'created' | 'started' | 'step_completed' | 'approved' | 'rejected' | 'delegated' | 'cancelled' | 'on_hold' | 'resumed' | 'escalated';
  action_description: string;
  performed_by?: string;
  performed_by_user?: WorkflowUser;
  workflow_state_snapshot?: any;
  ip_address?: string;
  user_agent?: string;
  created_at: string;
}

export interface EntityInfo {
  type: string;
  id: number;
  title?: string;
  requestor_name?: string;
  status?: string;
}

export interface WorkflowInstance {
  id: string;
  workflow_template: string;
  workflow_template_detail?: WorkflowTemplate;
  content_type?: number;
  object_id?: number;
  entity_info?: EntityInfo;
  status: 'pending' | 'in_progress' | 'approved' | 'rejected' | 'cancelled' | 'on_hold';
  current_step_order: number;
  current_step_info?: WorkflowStepExecution;
  progress_percentage?: number;
  step_executions?: WorkflowStepExecution[];
  audit_logs?: WorkflowAuditLog[];
  initiated_by: string;
  initiated_by_user?: WorkflowUser;
  started_at: string;
  completed_at?: string;
  additional_data?: any;
  created_at: string;
  updated_at: string;
}

export interface WorkflowInstanceList {
  id: string;
  workflow_template_name: string;
  entity_info?: EntityInfo;
  status: string;
  current_step_order: number;
  current_step_name?: string;
  initiated_by_user?: WorkflowUser;
  started_at: string;
  completed_at?: string;
}

export interface PendingApproval {
  workflow_instance_id: string;
  workflow_name: string;
  entity_type: string;
  entity_id: number;
  entity_title: string;
  step_execution_id: string;
  step_name: string;
  step_order: number;
  assigned_to: string;
  sla_due_date?: string;
  is_overdue: boolean;
  is_escalated: boolean;
  initiated_by: string;
  initiated_at: string;
}

export interface ApprovalAction {
  action: 'approve' | 'reject' | 'skip';
  comments?: string;
}

export interface DelegationAction {
  delegated_to: string;
  reason?: string;
  expires_at?: string;
}

export interface WorkflowActionRequest {
  action: 'approve' | 'reject' | 'skip' | 'delegate';
  comments?: string;
  delegated_to_id?: string;
}
