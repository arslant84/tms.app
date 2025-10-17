import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Subject, debounceTime, distinctUntilChanged } from 'rxjs';
import { VisaService, VisaApplication } from '../visa.service';

@Component({
  selector: 'app-visa-list',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './visa-list.component.html',
  styleUrl: './visa-list.component.scss'
})
export class VisaListComponent implements OnInit, OnDestroy {
  applications: VisaApplication[] = [];
  isLoading = false;
  searchTerm = '';
  filterStatus = '';
  filterVisaType = '';

  // Pagination
  currentPage = 1;
  pageSize = 20;
  totalCount = 0;
  Math = Math; // Expose Math to template

  // Filter options
  statuses = [
    'Pending Department Focal',
    'Submitted',
    'Under Review',
    'Approved',
    'Rejected',
    'Cancelled',
    'Processing',
    'Completed'
  ];

  visaTypes = [
    'Tourist',
    'Business',
    'Work',
    'Student',
    'Transit',
    'Diplomatic',
    'Official'
  ];

  private searchSubject = new Subject<string>();
  private destroy$ = new Subject<void>();

  constructor(private visaService: VisaService) {}

  ngOnInit(): void {
    this.setupSearch();
    this.fetchApplications();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  setupSearch(): void {
    this.searchSubject.pipe(
      debounceTime(500),
      distinctUntilChanged()
    ).subscribe(searchTerm => {
      this.searchTerm = searchTerm;
      this.resetToFirstPage();
      this.fetchApplications();
    });
  }

  onSearchChange(value: string): void {
    this.searchSubject.next(value);
  }

  onFilterChange(): void {
    this.resetToFirstPage();
    this.fetchApplications();
  }

  fetchApplications(): void {
    this.isLoading = true;
    const filters = {
      status: this.filterStatus,
      visa_type: this.filterVisaType,
      search: this.searchTerm,
      page: this.currentPage,
      page_size: this.pageSize
    };

    this.visaService.getAllApplications(filters).subscribe({
      next: (response) => {
        this.applications = response.results || response;
        this.totalCount = response.count || this.applications.length;
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error fetching visa applications:', error);
        this.isLoading = false;
      }
    });
  }

  resetToFirstPage(): void {
    this.currentPage = 1;
  }

  onPageChange(page: number): void {
    this.currentPage = page;
    this.fetchApplications();
  }

  navigateToDetail(id: number): void {
    // Navigation handled by routerLink in template
  }

  navigateToEdit(id: number): void {
    // Navigation handled by routerLink in template
  }

  deleteApplication(id: number, event: Event): void {
    event.stopPropagation();
    if (confirm('Are you sure you want to delete this visa application?')) {
      this.visaService.deleteApplication(id).subscribe({
        next: () => {
          this.fetchApplications();
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
      month: 'short',
      day: 'numeric'
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
