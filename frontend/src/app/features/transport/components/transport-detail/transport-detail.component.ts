import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { TransportService, TransportRequestDetail } from '../../services/transport.service';
import { ToastService } from '../../../../core/services/toast.service';

@Component({
  selector: 'app-transport-detail',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './transport-detail.component.html',
  styleUrls: ['./transport-detail.component.scss']
})
export class TransportDetailComponent implements OnInit {
  request: TransportRequestDetail | null = null;
  loading: boolean = true;
  error: string = '';
  requestId!: number;

  // Status-based visibility constants
  private readonly EDITABLE_STATUSES = ['Draft', 'Rejected'];
  private readonly CANCELLABLE_STATUSES = ['Pending'];
  private readonly DELETABLE_STATUSES = ['Draft', 'Rejected'];

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private transportService: TransportService,
    private toastService: ToastService
  ) {}

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      this.requestId = +params['id'];
      if (this.requestId) {
        this.loadRequestDetails();
      }
    });
  }

  loadRequestDetails(): void {
    this.loading = true;
    this.error = '';

    this.transportService.getRequestById(this.requestId).subscribe({
      next: (data) => {
        this.request = data;
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load transport request: ' + (err.error?.message || err.message || 'Unknown error');
        this.loading = false;
        console.error('Error loading request:', err);
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

  getStatusClass(): string {
    const status = this.request?.status?.toLowerCase() || '';
    if (status.includes('approved') || status.includes('completed')) return 'badge-success';
    if (status.includes('rejected')) return 'badge-danger';
    if (status.includes('pending')) return 'badge-warning';
    if (status.includes('draft')) return 'badge-secondary';
    if (status.includes('cancelled')) return 'badge-secondary';
    return 'badge-info';
  }

  goBack(): void {
    this.router.navigate(['/transport']);
  }

  onEdit(): void {
    this.router.navigate(['/transport/edit', this.requestId]);
  }

  onCancel(): void {
    if (confirm('Are you sure you want to cancel this transport request? This action cannot be undone.')) {
      this.transportService.cancelRequest(this.requestId).subscribe({
        next: () => {
          this.toastService.success('Transport request cancelled successfully');
          this.loadRequestDetails();
        },
        error: (err) => {
          this.toastService.error('Failed to cancel request: ' + (err.error?.message || err.message));
          console.error('Error cancelling request:', err);
        }
      });
    }
  }

  onDelete(): void {
    if (confirm('Are you sure you want to delete this transport request? This action cannot be undone.')) {
      this.transportService.deleteRequest(this.requestId).subscribe({
        next: () => {
          this.toastService.success('Transport request deleted successfully');
          this.router.navigate(['/transport']);
        },
        error: (err) => {
          this.toastService.error('Failed to delete request: ' + (err.error?.message || err.message));
          console.error('Error deleting request:', err);
        }
      });
    }
  }

  onPrint(): void {
    window.print();
  }

  formatCurrency(amount: number | undefined, currency: string = 'USD'): string {
    if (!amount && amount !== 0) return '$0.00';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency
    }).format(amount);
  }

  formatDate(dateString: string | undefined): string {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  }

  formatTime(timeString: string | undefined): string {
    if (!timeString) return 'N/A';
    return timeString;
  }
}
