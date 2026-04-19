import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { Subject, takeUntil } from 'rxjs';
import { CombinedRequestService } from './services/combined-request.service';
import { CombinedRequest } from './models/combined-request.model';
import { ToastService } from '../../../core/services/toast.service';
import { ConfirmationService } from '../../../core/services/confirmation.service';
import { WorkflowService } from '../../../core/services/workflow.service';
import { DateUtilsService } from '../../../core/utils/date-utils.service';
import { StatusUtilsService } from '../../../core/utils/status-utils.service';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { WorkflowStatusComponent } from '../../../shared/components/workflow-status/workflow-status.component';
import { ApprovalActionsComponent } from '../../../shared/components/approval-actions/approval-actions.component';
import { WorkflowInstance, WorkflowStepExecution } from '../../../core/models/workflow.models';

@Component({
  selector: 'app-combined-detail',
  standalone: true,
  imports: [CommonModule, RouterModule, LoadingSpinnerComponent, WorkflowStatusComponent, ApprovalActionsComponent],
  templateUrl: './combined-detail.component.html',
  styleUrls: ['./combined-detail.component.scss']
})
export class CombinedDetailComponent implements OnInit {
  request: CombinedRequest | null = null;
  loading = true;
  error = '';
  requestId!: number;

  workflow: WorkflowInstance | null = null;
  workflowLoading = false;
  currentStepExecution: WorkflowStepExecution | null = null;

  private readonly EDITABLE_STATUSES = ['Draft', 'Rejected'];
  private readonly DELETABLE_STATUSES = ['Draft', 'Rejected'];
  private readonly APPROVED_KEYWORDS = ['Approved', 'Completed', 'Assigned'];

  private destroy$ = new Subject<void>();

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private combinedRequestService: CombinedRequestService,
    private toastService: ToastService,
    private confirmationService: ConfirmationService,
    public workflowService: WorkflowService,
    public dateUtils: DateUtilsService,
    public statusUtils: StatusUtilsService
  ) {}

  ngOnInit(): void {
    this.route.params.pipe(takeUntil(this.destroy$)).subscribe(params => {
      this.requestId = +params['id'];
      if (this.requestId) {
        this.loadRequest();
        this.loadWorkflow();
      }
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadRequest(): void {
    this.loading = true;
    this.error = '';
    this.combinedRequestService.getById(this.requestId).pipe(takeUntil(this.destroy$)).subscribe({
      next: (data) => {
        this.request = data;
        this.loading = false;
      },
      error: (err) => {
        this.error = err.message || 'Failed to load request details';
        this.loading = false;
      }
    });
  }

  loadWorkflow(): void {
    this.workflowLoading = true;
    this.workflowService.getInstances({
      entity_type: 'combinedrequest',
      object_id: this.requestId
    }).subscribe({
      next: (response: any) => {
        const instances = Array.isArray(response) ? response : (response.results || []);
        const instance = instances.find((i: any) =>
          i.object_id === this.requestId ||
          i.entity_info?.id === this.requestId ||
          i.entity_id === this.requestId
        );
        if (instance?.id) {
          this.workflowService.getInstance(instance.id).subscribe({
            next: (wf) => {
              this.workflow = wf;
              this.updateCurrentStepExecution();
              this.workflowLoading = false;
            },
            error: () => { this.workflowLoading = false; }
          });
        } else {
          this.workflowLoading = false;
        }
      },
      error: () => { this.workflowLoading = false; }
    });
  }

  updateCurrentStepExecution(): void {
    if (!this.workflow?.step_executions) {
      this.currentStepExecution = null;
      return;
    }
    this.currentStepExecution = this.workflow.step_executions.find(
      step => step.status === 'pending' &&
              step.workflow_step_detail?.step_order === this.workflow?.current_step_order &&
              step.can_action === true
    ) || null;
  }

  // ── Status helpers ──────────────────────────────────────────

  canEdit(): boolean {
    if (!this.request?.status) return false;
    const status = this.request.status;
    if (this.EDITABLE_STATUSES.includes(status)) return true;
    const isApproved = this.APPROVED_KEYWORDS.some(keyword => status.includes(keyword));
    if (isApproved) return false;
    return status.includes('Pending');
  }

  canCancel(): boolean {
    const status = this.request?.status || '';
    if (status.includes('Pending')) {
      return !this.APPROVED_KEYWORDS.some(keyword => status.includes(keyword));
    }
    return false;
  }

  canSubmit(): boolean {
    return this.request?.status === 'Draft';
  }

  canDelete(): boolean {
    return !!this.request?.status && this.DELETABLE_STATUSES.includes(this.request.status);
  }

  getStatusClass(): string {
    return this.statusUtils.getStatusBadgeClass(this.request?.status ?? '');
  }

  getWorkflowStatusClass(): string {
    return this.statusUtils.getWorkflowStatusClass(this.workflow?.status);
  }

  getWorkflowStatus(): string {
    if (!this.workflow) return '';
    const s = this.workflow.status;
    if (s === 'approved') return 'Approved';
    if (s === 'rejected') return 'Rejected';
    if (s === 'cancelled') return 'Cancelled';
    if (s === 'in_progress' || s === 'pending') {
      const cur = this.workflow.current_step_order;
      const tot = this.workflow.step_executions?.length || 0;
      return cur && tot ? `Pending Approval (Step ${cur} of ${tot})` : 'Pending Approval';
    }
    return s.charAt(0).toUpperCase() + s.slice(1);
  }

  // ── Module helpers ──────────────────────────────────────────

  getIncludedModules(): { icon: string; label: string }[] {
    const mods: { icon: string; label: string }[] = [];
    if (this.request?.includeTravel)        mods.push({ icon: 'bi-airplane',    label: 'Travel / TSR' });
    if (this.request?.includeTransport)     mods.push({ icon: 'bi-truck',       label: 'Transport' });
    if (this.request?.includeAccommodation) mods.push({ icon: 'bi-house-door',  label: 'Accommodation' });
    if (this.request?.includeVisa)          mods.push({ icon: 'bi-passport',    label: 'Visa' });
    return mods;
  }

  getTravelTypeLabel(type: string | undefined): string {
    const labels: Record<string, string> = {
      domestic: 'Domestic',
      international: 'International',
      home_leave: 'Home Leave',
      external: 'External Parties'
    };
    return (type && labels[type]) ? labels[type] : (type || 'N/A');
  }

  getMealSelections(): { date: string | null; breakfast: boolean; lunch: boolean; dinner: boolean; supper: boolean; refreshment: boolean }[] {
    type MealRow = { date: string | null; breakfast: boolean; lunch: boolean; dinner: boolean; supper: boolean; refreshment: boolean };
    const raw = (this.request?.travelData as { meal_selections?: MealRow[] } | undefined);
    return raw?.['meal_selections'] ?? [];
  }

  getAdvanceAmountItems(): { dateFrom: string; dateTo: string; lh: number; ma: number; oa: number; tr: number; oe: number; usd: number; remarks: string }[] {
    type RawItem = { date_from?: string; dateFrom?: string; date_to?: string; dateTo?: string; lh?: number; ma?: number; oa?: number; tr?: number; oe?: number; usd?: number; remarks?: string };
    const raw = (this.request?.travelData as { advance_amount_items?: RawItem[] } | undefined);
    const items: RawItem[] = raw?.['advance_amount_items'] ?? [];
    return items.map(item => ({
      dateFrom: item.date_from || item.dateFrom || '',
      dateTo: item.date_to || item.dateTo || '',
      lh: item.lh || 0,
      ma: item.ma || 0,
      oa: item.oa || 0,
      tr: item.tr || 0,
      oe: item.oe || 0,
      usd: item.usd || 0,
      remarks: item.remarks || ''
    }));
  }

  // ── Actions ─────────────────────────────────────────────────

  onExportPdf(): void {
    this.combinedRequestService.exportToPdf(this.requestId).pipe(takeUntil(this.destroy$)).subscribe({
      next: (blob: Blob) => {
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `Combined-Request-${this.requestId}.pdf`;
        link.click();
        window.URL.revokeObjectURL(url);
        this.toastService.success('PDF exported successfully');
      },
      error: (err) => this.toastService.error('Failed to export PDF: ' + (err.message || 'Unknown error'))
    });
  }

  onSubmit(): void {
    // Redirect to wizard so the user can select approvers before submitting
    this.router.navigate(['/combined/edit', this.requestId]);
  }

  onEdit(): void {
    this.router.navigate(['/combined/edit', this.requestId]);
  }

  onCancel(): void {
    this.confirmationService.confirmDestructive('Cancel', 'this combined request').subscribe(confirmed => {
      if (!confirmed) return;
      this.combinedRequestService.cancel(this.requestId).pipe(takeUntil(this.destroy$)).subscribe({
        next: () => { this.toastService.success('Request cancelled'); this.loadRequest(); },
        error: (err) => this.toastService.error('Failed to cancel: ' + (err.message || 'Unknown error'))
      });
    });
  }

  onDelete(): void {
    this.confirmationService.confirmDelete('this combined request').subscribe(confirmed => {
      if (!confirmed) return;
      this.combinedRequestService.delete(this.requestId).pipe(takeUntil(this.destroy$)).subscribe({
        next: () => { this.toastService.success('Request deleted'); this.router.navigate(['/combined']); },
        error: (err) => this.toastService.error('Failed to delete: ' + (err.message || 'Unknown error'))
      });
    });
  }

  onWorkflowApproved(): void {
    this.toastService.success('Approval successful');
    this.loadRequest();
    this.loadWorkflow();
  }

  onWorkflowRejected(): void {
    this.toastService.success('Request rejected');
    this.loadRequest();
    this.loadWorkflow();
  }

  onWorkflowDelegated(): void {
    this.toastService.success('Successfully delegated');
    this.loadWorkflow();
  }
}
