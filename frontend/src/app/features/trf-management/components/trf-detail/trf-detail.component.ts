import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { TrfService } from '../../services/trf.service';
import { ToastService } from '../../../../core/services/toast.service';

@Component({
  selector: 'app-trf-detail',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './trf-detail.component.html',
  styleUrls: ['./trf-detail.component.scss']
})
export class TrfDetailComponent implements OnInit {
  trfData: any = null;
  loading: boolean = true;
  error: string = '';
  trfId!: number;

  // Status-based visibility constants (from pctsb.syntra)
  private readonly EDITABLE_STATUSES = ['Pending Department Focal', 'Rejected', 'Draft'];
  private readonly CANCELLABLE_STATUSES = ['Pending Department Focal', 'Pending HOD', 'Pending Travel Desk'];
  private readonly DELETABLE_STATUSES = ['Pending Department Focal', 'Rejected', 'Draft'];

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private trfService: TrfService,
    private toastService: ToastService
  ) {}

  ngOnInit(): void {
    // Get TRF ID from route params
    this.route.params.subscribe(params => {
      this.trfId = +params['id'];
      if (this.trfId) {
        this.loadTrfDetails();
      }
    });
  }

  loadTrfDetails(): void {
    this.loading = true;
    this.error = '';

    // Fetch TRF details from the backend
    fetch(`http://localhost:8000/api/trf/travel-requests/${this.trfId}/`, {
      credentials: 'include',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      }
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      return response.json();
    })
    .then(data => {
      this.trfData = this.transformTrfData(data);
      this.loading = false;
    })
    .catch(err => {
      this.error = 'Failed to load TRF details: ' + (err.message || 'Unknown error');
      this.loading = false;
      console.error('Error loading TRF:', err);
    });
  }

  /**
   * Transform backend data to match the view structure
   */
  private transformTrfData(data: any): any {
    return {
      id: data.id,
      travelType: data.travel_type || data.travelType,
      status: data.status,
      requestorName: data.requestor_name || data.requestorName,
      staffId: data.staff_id || data.staffId,
      department: data.department,
      position: data.position,
      costCenter: data.cost_center || data.costCenter,
      telEmail: data.tel_email || data.telEmail,
      purpose: data.purpose,
      additionalComments: data.additional_comments || data.additionalComments,
      // External party fields
      externalPartyName: data.external_party_name || data.externalPartyName,
      externalPartyOrganization: data.external_party_organization || data.externalPartyOrganization,
      externalRefToAuthorityLetter: data.external_ref_to_authority_letter || data.externalRefToAuthorityLetter,
      externalCostCenter: data.external_cost_center || data.externalCostCenter,
      // Nested data (will be loaded separately or included in response)
      itinerary: data.itinerary || [],
      mealSelections: data.daily_meal_selections || data.mealSelections || [],
      accommodationDetails: data.accommodation_details || data.accommodationDetails || [],
      transportDetails: data.company_transport_details || data.transportDetails || [],
      passportDetails: data.passport_details || data.passportDetails,
      bankDetails: data.advance_bank_details || data.bankDetails,
      advanceAmounts: data.advance_amount_items || data.advanceAmounts || [],
      approvalSteps: data.approval_steps || data.approvalSteps || [],
      createdAt: data.created_at || data.createdAt,
      updatedAt: data.updated_at || data.updatedAt
    };
  }

  /**
   * Check if TRF is for external parties
   */
  get isExternal(): boolean {
    return this.trfData?.travelType === 'External Parties';
  }

  /**
   * Check if TRF is overseas or home leave
   */
  get isOverseas(): boolean {
    return this.trfData?.travelType === 'Overseas' || this.trfData?.travelType === 'Home Leave';
  }

  /**
   * Check if TRF is domestic
   */
  get isDomestic(): boolean {
    return this.trfData?.travelType === 'Domestic';
  }

  /**
   * Check if TRF can be edited based on status
   */
  canEdit(): boolean {
    return this.EDITABLE_STATUSES.includes(this.trfData?.status);
  }

  /**
   * Check if TRF can be cancelled based on status
   */
  canCancel(): boolean {
    return this.CANCELLABLE_STATUSES.includes(this.trfData?.status);
  }

  /**
   * Check if TRF can be deleted based on status
   */
  canDelete(): boolean {
    return this.DELETABLE_STATUSES.includes(this.trfData?.status);
  }

  /**
   * Get status badge class
   */
  getStatusClass(): string {
    const status = this.trfData?.status?.toLowerCase() || '';
    if (status.includes('approved')) return 'badge-success';
    if (status.includes('rejected')) return 'badge-danger';
    if (status.includes('pending')) return 'badge-warning';
    if (status.includes('draft')) return 'badge-secondary';
    return 'badge-info';
  }

  /**
   * Format date for display
   */
  formatDate(date: string | Date | null | undefined): string {
    if (!date) return 'N/A';
    try {
      const d = typeof date === 'string' ? new Date(date) : date;
      return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    } catch {
      return 'Invalid Date';
    }
  }

  /**
   * Format time for display
   */
  formatTime(time: string | null | undefined): string {
    if (!time) return 'N/A';
    try {
      // Handle HH:MM or HH:MM:SS format
      const timeMatch = time.match(/^([01]\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?$/);
      if (!timeMatch) return 'N/A';

      const [, hours, minutes] = timeMatch;
      const date = new Date();
      date.setHours(parseInt(hours), parseInt(minutes));
      return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    } catch {
      return 'N/A';
    }
  }

  /**
   * Format number for display
   */
  formatNumber(num: number | string | null | undefined, decimals: number = 0): string {
    if (num === null || num === undefined || String(num).trim() === '') return 'N/A';
    const parsedNum = Number(num);
    return isNaN(parsedNum) ? String(num) : parsedNum.toLocaleString(undefined, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    });
  }

  /**
   * Calculate meal totals
   */
  getMealTotal(mealType: string): number {
    if (!this.trfData?.mealSelections) return 0;
    return this.trfData.mealSelections.reduce((acc: number, meal: any) => {
      return acc + (meal[mealType] ? 1 : 0);
    }, 0);
  }

  /**
   * Navigate back to list
   */
  goBack(): void {
    this.router.navigate(['/trf']);
  }

  /**
   * Edit TRF
   */
  onEdit(): void {
    this.router.navigate(['/trf/edit', this.trfId]);
  }

  /**
   * Cancel TRF
   */
  onCancel(): void {
    if (confirm('Are you sure you want to cancel this TRF? This action cannot be undone.')) {
      // Call the cancel action endpoint (from Django backend)
      const url = `http://localhost:8000/api/trf/travel-requests/${this.trfId}/cancel/`;

      // Use HttpClient directly for custom endpoint
      const headers = { 'Content-Type': 'application/json' };

      // Make the POST request
      fetch(url, {
        method: 'POST',
        headers: headers,
        credentials: 'include',
        body: JSON.stringify({})
      }).then(response => {
        if (response.ok) {
          this.toastService.success('TRF cancelled successfully');
          // Refresh the TRF data to show updated status
          this.loadTrfDetails();
        } else {
          throw new Error('Failed to cancel TRF');
        }
      }).catch(err => {
        this.toastService.error('Failed to cancel TRF: ' + (err.message || 'Unknown error'));
        console.error('Error cancelling TRF:', err);
      });
    }
  }

  /**
   * Delete TRF
   */
  onDelete(): void {
    if (confirm('Are you sure you want to delete this TRF? This action cannot be undone.')) {
      // Call delete endpoint
      const url = `http://localhost:8000/api/trf/travel-requests/${this.trfId}/`;

      fetch(url, {
        method: 'DELETE',
        credentials: 'include'
      }).then(response => {
        if (response.ok || response.status === 204) {
          this.toastService.success('TRF deleted successfully');
          this.router.navigate(['/trf']);
        } else {
          throw new Error('Failed to delete TRF');
        }
      }).catch(err => {
        this.toastService.error('Failed to delete TRF: ' + (err.message || 'Unknown error'));
        console.error('Error deleting TRF:', err);
      });
    }
  }

  /**
   * Print TRF
   */
  onPrint(): void {
    window.print();
  }

  /**
   * Export to PDF
   */
  onExportPdf(): void {
    this.trfService.exportTrfToPdf(this.trfId).subscribe({
      next: (blob: Blob) => {
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `TRF-${this.trfId}.pdf`;
        link.click();
        window.URL.revokeObjectURL(url);
      },
      error: (err: any) => {
        alert('Failed to export PDF: ' + (err.error?.message || err.message || 'Unknown error'));
        console.error('Error exporting PDF:', err);
      }
    });
  }
}
