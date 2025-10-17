import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, ActivatedRoute, Router } from '@angular/router';
import { AccommodationService, AccommodationRequest } from '../../services/accommodation.service';
import { ToastService } from '../../../../core/services/toast.service';

@Component({
  selector: 'app-accommodation-detail',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './accommodation-detail.component.html',
  styleUrls: ['./accommodation-detail.component.scss']
})
export class AccommodationDetailComponent implements OnInit {
  request!: AccommodationRequest;
  requestId!: number;
  isLoading = false;

  // Status-based visibility
  private readonly EDITABLE_STATUSES = ['Draft', 'Pending', 'Rejected'];
  private readonly CANCELLABLE_STATUSES = ['Pending', 'Confirmed'];
  private readonly DELETABLE_STATUSES = ['Draft', 'Rejected'];

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private accommodationService: AccommodationService,
    private toastService: ToastService
  ) {}

  ngOnInit(): void {
    this.requestId = Number(this.route.snapshot.paramMap.get('id'));
    this.loadRequestDetails();
  }

  loadRequestDetails(): void {
    this.isLoading = true;
    this.accommodationService.getRequestById(this.requestId).subscribe({
      next: (request) => {
        this.request = request;
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Error loading accommodation request:', err);
        this.toastService.error('Failed to load accommodation request details');
        this.isLoading = false;
        this.router.navigate(['/accommodation']);
      }
    });
  }

  canEdit(): boolean {
    return this.EDITABLE_STATUSES.includes(this.request?.status || '');
  }

  canCancel(): boolean {
    return this.CANCELLABLE_STATUSES.includes(this.request?.status || '');
  }

  canDelete(): boolean {
    return this.DELETABLE_STATUSES.includes(this.request?.status || '');
  }

  onEdit(): void {
    this.router.navigate(['/accommodation/edit', this.requestId]);
  }

  onCancel(): void {
    if (confirm('Are you sure you want to cancel this accommodation request?')) {
      this.accommodationService.cancelRequest(this.requestId).subscribe({
        next: () => {
          this.toastService.success('Accommodation request cancelled successfully');
          this.loadRequestDetails();
        },
        error: (err) => {
          console.error('Error cancelling request:', err);
          this.toastService.error('Failed to cancel accommodation request');
        }
      });
    }
  }

  onDelete(): void {
    if (confirm('Are you sure you want to delete this accommodation request? This action cannot be undone.')) {
      this.accommodationService.deleteRequest(this.requestId).subscribe({
        next: () => {
          this.toastService.success('Accommodation request deleted successfully');
          this.router.navigate(['/accommodation']);
        },
        error: (err) => {
          console.error('Error deleting request:', err);
          this.toastService.error('Failed to delete accommodation request');
        }
      });
    }
  }

  getStatusBadgeClass(status: string): string {
    switch (status) {
      case 'Draft': return 'badge-secondary';
      case 'Pending': return 'badge-warning';
      case 'Confirmed': return 'badge-success';
      case 'Checked In': return 'badge-info';
      case 'Checked Out': return 'badge-primary';
      case 'Cancelled': return 'badge-danger';
      case 'Rejected': return 'badge-danger';
      default: return 'badge-secondary';
    }
  }

  formatCurrency(amount: number | null | undefined): string {
    if (amount === null || amount === undefined) {
      return 'N/A';
    }
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  }

  formatDate(dateString: string | null | undefined): string {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  }

  formatDateTime(dateString: string | null | undefined): string {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  goBack(): void {
    this.router.navigate(['/accommodation']);
  }
}
