/* eslint-disable @typescript-eslint/no-explicit-any -- pre-existing loose typing against raw API responses, unrelated to this change */
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';
import { ToastService } from '../../../core/services/toast.service';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';

interface PendingApproval {
  id: string;
  workflowInstance: {
    id: string;
    entityType: string;
    entityId: number;
    status: string;
    initiatedBy: {
      id: string;
      email: string;
      first_name: string;
      last_name: string;
    };
    createdAt: string;
  };
  workflowStep: {
    id: string;
    stepName: string;
    stepOrder: number;
    approverRole: string;
  };
  status: string;
  assignedTo: any;
  createdAt: string;
  slaDueDate: string | null;
  isOverdue: boolean;
}

@Component({
  selector: 'app-approvals-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule, LoadingSpinnerComponent],
  templateUrl: './approvals-dashboard.component.html',
  styleUrls: ['./approvals-dashboard.component.scss'],
})
export class ApprovalsDashboardComponent implements OnInit {
  pendingApprovals: PendingApproval[] = [];
  filteredApprovals: PendingApproval[] = [];
  isLoading = false;
  filterModule = 'all';
  searchQuery = '';

  modules = [
    { value: 'all', label: 'All Modules' },
    { value: 'travelrequest', label: 'Travel Service Request' },
    { value: 'transportrequest', label: 'Transport Request' },
    { value: 'visaapplication', label: 'Visa Application' },
  ];

  selectedApproval: PendingApproval | null = null;
  showModal = false;
  actionComments = '';
  isProcessing = false;

  constructor(
    private http: HttpClient,
    private toast: ToastService
  ) {}

  ngOnInit(): void {
    this.loadPendingApprovals();
  }

  loadPendingApprovals(): void {
    this.isLoading = true;
    this.http
      .get<PendingApproval[]>(`${environment.apiUrl}/workflows/executions/my-pending/`)
      .subscribe({
        next: approvals => {
          this.pendingApprovals = approvals;
          this.applyFilters();
          this.isLoading = false;
        },
        error: () => {
          this.toast.error('Failed to load pending approvals');
          this.isLoading = false;
        },
      });
  }

  applyFilters(): void {
    let filtered = [...this.pendingApprovals];

    if (this.filterModule !== 'all') {
      filtered = filtered.filter(a => a.workflowInstance.entityType === this.filterModule);
    }

    if (this.searchQuery.trim()) {
      const query = this.searchQuery.toLowerCase();
      filtered = filtered.filter(
        a =>
          a.workflowStep.stepName.toLowerCase().includes(query) ||
          a.workflowInstance.initiatedBy.email.toLowerCase().includes(query) ||
          a.workflowInstance.initiatedBy.first_name.toLowerCase().includes(query) ||
          a.workflowInstance.initiatedBy.last_name.toLowerCase().includes(query)
      );
    }

    this.filteredApprovals = filtered;
  }

  getModuleName(entityType: string): string {
    const module = this.modules.find(m => m.value === entityType);
    return module ? module.label : entityType;
  }

  getModuleColor(entityType: string): string {
    const colors: any = {
      travelrequest: 'primary',
      transportrequest: 'success',
      visaapplication: 'warning',
      accommodation: 'info',
      expenseclaim: 'danger',
    };
    return colors[entityType] || 'secondary';
  }

  openApprovalModal(approval: PendingApproval): void {
    this.selectedApproval = approval;
    this.actionComments = '';
    this.showModal = true;
  }

  closeModal(): void {
    this.showModal = false;
    this.selectedApproval = null;
    this.actionComments = '';
  }

  takeAction(action: 'approve' | 'reject'): void {
    if (!this.selectedApproval) return;

    if (action === 'reject' && !this.actionComments.trim()) {
      this.toast.error('Please provide comments for rejection');
      return;
    }

    this.isProcessing = true;

    const payload = {
      action,
      comments: this.actionComments.trim(),
    };

    this.http
      .post(
        `${environment.apiUrl}/workflows/executions/${this.selectedApproval.id}/take-action/`,
        payload
      )
      .subscribe({
        next: () => {
          this.toast.success(
            `Request ${action === 'approve' ? 'approved' : 'rejected'} successfully`
          );
          this.closeModal();
          this.loadPendingApprovals();
        },
        error: error => {
          console.error('Error taking action:', error);
          this.toast.error(error.error?.error || 'Failed to process action');
          this.isProcessing = false;
        },
        complete: () => (this.isProcessing = false),
      });
  }

  viewRequestDetails(approval: PendingApproval): void {
    const entityType = approval.workflowInstance.entityType;
    const entityId = approval.workflowInstance.entityId;

    const routes: any = {
      travelrequest: `/trf/details/${entityId}`,
      transportrequest: `/transport/details/${entityId}`,
      visaapplication: `/visa/${entityId}`,
      accommodation: `/accommodation/${entityId}`,
      expenseclaim: `/expense-claims/${entityId}`,
    };

    const route = routes[entityType];
    if (route) {
      window.open(route, '_blank');
    }
  }

  isOverdueSoon(approval: PendingApproval): boolean {
    if (!approval.slaDueDate) return false;

    const now = new Date().getTime();
    const dueDate = new Date(approval.slaDueDate).getTime();
    const hoursUntilDue = (dueDate - now) / (1000 * 60 * 60);

    return hoursUntilDue <= 24 && hoursUntilDue > 0;
  }

  getTimeRemaining(dateString: string | null): string {
    if (!dateString) return 'No deadline';

    const now = new Date().getTime();
    const target = new Date(dateString).getTime();
    const diff = target - now;

    if (diff < 0) return 'Overdue';

    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));

    if (days > 0) return `${days}d ${hours}h`;
    return `${hours}h`;
  }

  getInitiatorName(initiator: any): string {
    if (initiator.first_name || initiator.last_name) {
      return `${initiator.first_name || ''} ${initiator.last_name || ''}`.trim();
    }
    return initiator.email;
  }
}
