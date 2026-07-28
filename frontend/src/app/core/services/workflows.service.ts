import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface TmsApp_Workflows_WorkflowStep {
  id: string;
  name: string;
  order: number;
  approverRoleId?: string;
  approverRole?: string;
  escalationRoleId?: string | null;
  escalationRole?: string | null;
  escalationHours?: number | null;
  moduleId: string;
}

export interface TmsApp_Workflows_WorkflowModuleWithSteps {
  id: string;
  name: string;
  description?: string;
  created_at?: string;
  updated_at?: string;
  steps: TmsApp_Workflows_WorkflowStep[];
}

export interface TmsApp_Workflows_WorkflowStepFormValues {
  name: string;
  approverRoleId: string;
  escalationRoleId?: string | null;
  escalationHours?: number | null;
  order?: number | null;
}

/**
 * TmsApp_Core_Services_WorkflowsService
 * Purpose
 * - CRUD workflow steps and fetch workflow modules with steps.
 * Endpoints
 * - GET, POST, PUT, DELETE at `${apiBase}/admin/settings/workflows`
 */
@Injectable({ providedIn: 'root' })
export class TmsApp_Core_Services_WorkflowsService {
  private base = `${environment.apiUrl}/workflows/templates/`;

  constructor(private http: HttpClient) {}

  getModulesWithSteps(): Observable<
    | { success?: boolean; data?: TmsApp_Workflows_WorkflowModuleWithSteps[] }
    | TmsApp_Workflows_WorkflowModuleWithSteps[]
  > {
    return this.http.get<
      | { success?: boolean; data?: TmsApp_Workflows_WorkflowModuleWithSteps[] }
      | TmsApp_Workflows_WorkflowModuleWithSteps[]
    >(this.base);
  }

  createStep(
    moduleId: string,
    stepData: TmsApp_Workflows_WorkflowStepFormValues
  ): Observable<TmsApp_Workflows_WorkflowStep> {
    return this.http.post<TmsApp_Workflows_WorkflowStep>(this.base, { moduleId, stepData });
  }

  updateStep(
    stepId: string,
    stepData: TmsApp_Workflows_WorkflowStepFormValues
  ): Observable<TmsApp_Workflows_WorkflowStep> {
    return this.http.put<TmsApp_Workflows_WorkflowStep>(this.base, { stepId, stepData });
  }

  deleteStep(stepId: string): Observable<{ success: boolean }> {
    return this.http.delete<{ success: boolean }>(
      `${this.base}?stepId=${encodeURIComponent(stepId)}`
    );
  }
}
