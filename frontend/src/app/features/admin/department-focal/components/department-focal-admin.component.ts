import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, type OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { HttpErrorHandlerService } from '../../../../core/utils/http-error-handler.service';
import { StatusUtilsService } from '../../../../core/utils/status-utils.service';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';
import {
  DepartmentFocalRequest,
  DepartmentFocalService,
} from '../services/department-focal.service';

/**
 * Read-only queue for the Department Focal role: their own department's
 * travel requests, with per-module arrangement status (flight/meal/
 * transport/accommodation/visa — "Not applicable" for modules a given
 * request never needed). See trf.services.module_status_summary for what
 * each status value means. Toggle "Fully arranged only" to narrow to
 * requests where every applicable module is done.
 */
@Component({
  selector: 'app-department-focal-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, LoadingSpinnerComponent],
  templateUrl: './department-focal-admin.component.html',
  styleUrl: './department-focal-admin.component.scss',
})
export class DepartmentFocalAdminComponent implements OnInit {
  requests: DepartmentFocalRequest[] = [];

  filterCriteria = {
    search: '',
    readyOnly: false,
  };

  currentPage = 1;
  pageSize = 20;
  totalRequests = 0;

  loading = true;
  error = '';

  private departmentFocalService = inject(DepartmentFocalService);
  private statusUtils = inject(StatusUtilsService);
  private errorHandler = inject(HttpErrorHandlerService);
  router = inject(Router);

  ngOnInit(): void {
    this.loadRequests();
  }

  loadRequests(): void {
    this.loading = true;
    this.error = '';

    this.departmentFocalService
      .getQueue({
        page: this.currentPage,
        page_size: this.pageSize,
        search: this.filterCriteria.search || undefined,
        ready: this.filterCriteria.readyOnly,
      })
      .subscribe({
        next: response => {
          this.requests = response.results || [];
          this.totalRequests = response.count || this.requests.length;
          this.loading = false;
        },
        error: (err: HttpErrorResponse) => {
          this.error = this.errorHandler.getErrorMessage(
            err,
            'Failed to load department travel arrangements'
          );
          this.loading = false;
        },
      });
  }

  applyFilters(): void {
    this.currentPage = 1;
    this.loadRequests();
  }

  resetFilters(): void {
    this.filterCriteria = { search: '', readyOnly: false };
    this.currentPage = 1;
    this.loadRequests();
  }

  changePage(page: number): void {
    this.currentPage = page;
    this.loadRequests();
  }

  viewRequest(request: DepartmentFocalRequest): void {
    this.router.navigate(['/trf', request.id]);
  }

  getStatusClass(status: string): string {
    return this.statusUtils.getStatusBadgeClass(status);
  }

  getModuleStatusClass(status: string | undefined): string {
    if (!status) return 'badge-warning';
    if (status === 'Not applicable') return 'badge-secondary';
    if (status === 'Rejected') return 'badge-danger';
    if (['Ticketed', 'Completed', 'Accommodation Assigned'].includes(status)) {
      return 'badge-success';
    }
    if (['Confirmed', 'Requested', 'Arranged', 'Approved'].includes(status)) {
      return 'badge-info';
    }
    // Everything else — "Pending", "Not booked yet", "Pending HOD",
    // "Pending Line Manager", etc. — is a workflow-driven in-progress
    // string still awaiting its own approval, shown as-is.
    return 'badge-warning';
  }

  get totalPages(): number {
    return Math.ceil(this.totalRequests / this.pageSize);
  }

  getPageNumbers(): number[] {
    const pages: number[] = [];
    const maxPages = 5;
    let startPage = Math.max(1, this.currentPage - Math.floor(maxPages / 2));
    const endPage = Math.min(this.totalPages, startPage + maxPages - 1);

    if (endPage - startPage + 1 < maxPages) {
      startPage = Math.max(1, endPage - maxPages + 1);
    }

    for (let i = startPage; i <= endPage; i++) {
      pages.push(i);
    }

    return pages;
  }
}
