import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { VisaService, VisaApplication, VisaApprovalStep, VisaDocument } from '../visa.service';

@Component({
  selector: 'app-visa-detail',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './visa-detail.component.html',
  styleUrl: './visa-detail.component.scss'
})
export class VisaDetailComponent implements OnInit {
  application!: VisaApplication;
  approvalSteps: VisaApprovalStep[] = [];
  documents: VisaDocument[] = [];
  isLoading = true;
  applicationId!: number;

  private readonly EDITABLE_STATUSES = ['Pending Department Focal', 'Rejected'];
  private readonly CANCELLABLE_STATUSES = ['Pending Department Focal', 'Submitted', 'Under Review'];

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private visaService: VisaService
  ) {}

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      this.applicationId = +params['id'];
      this.loadApplicationDetails();
    });
  }

  loadApplicationDetails(): void {
    this.isLoading = true;
    this.visaService.getApplicationById(this.applicationId).subscribe({
      next: (application) => {
        this.application = application;
        this.isLoading = false;
        this.loadApprovalSteps();
        this.loadDocuments();
      },
      error: (error) => {
        console.error('Error loading visa application:', error);
        this.isLoading = false;
        alert('Failed to load visa application details');
      }
    });
  }

  loadApprovalSteps(): void {
    this.visaService.getApprovalSteps(this.applicationId).subscribe({
      next: (steps) => {
        this.approvalSteps = steps;
      },
      error: (error) => {
        console.error('Error loading approval steps:', error);
      }
    });
  }

  loadDocuments(): void {
    this.visaService.getDocuments(this.applicationId).subscribe({
      next: (documents) => {
        this.documents = documents;
      },
      error: (error) => {
        console.error('Error loading documents:', error);
      }
    });
  }

  canEdit(): boolean {
    return this.EDITABLE_STATUSES.includes(this.application?.status || '');
  }

  canCancel(): boolean {
    return this.CANCELLABLE_STATUSES.includes(this.application?.status || '');
  }

  onEdit(): void {
    this.router.navigate(['/visa', this.applicationId, 'edit']);
  }

  onCancel(): void {
    if (confirm('Are you sure you want to cancel this visa application?')) {
      this.visaService.cancelApplication(this.applicationId).subscribe({
        next: () => {
          alert('Visa application cancelled successfully');
          this.loadApplicationDetails();
        },
        error: (error) => {
          console.error('Error cancelling visa application:', error);
          alert('Failed to cancel visa application');
        }
      });
    }
  }

  onDelete(): void {
    if (confirm('Are you sure you want to delete this visa application? This action cannot be undone.')) {
      this.visaService.deleteApplication(this.applicationId).subscribe({
        next: () => {
          alert('Visa application deleted successfully');
          this.router.navigate(['/visa']);
        },
        error: (error) => {
          console.error('Error deleting visa application:', error);
          alert('Failed to delete visa application');
        }
      });
    }
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

  getStatusBadgeClass(status: string): string {
    const statusMap: { [key: string]: string } = {
      'Pending Department Focal': 'bg-warning',
      'Submitted': 'bg-info',
      'Under Review': 'bg-primary',
      'Approved': 'bg-success',
      'Rejected': 'bg-danger',
      'Cancelled': 'bg-secondary',
      'Processing': 'bg-info',
      'Completed': 'bg-success'
    };
    return statusMap[status] || 'bg-secondary';
  }
}
