import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

// This interface would typically come from a shared models directory
interface PendingRequest {
  id: number;
  type: 'travel' | 'accommodation' | 'transport' | 'visa' | 'expense';
  title: string;
  requester: {
    id: number;
    name: string;
    department: string;
    email: string;
  };
  dateSubmitted: string;
  deadline: string | null;
  priority: 'low' | 'medium' | 'high';
  status: 'pending' | 'approved' | 'rejected';
  details: any; // This would be more specific in a real implementation
}

@Component({
  selector: 'app-pending-approvals',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './pending-approvals.component.html',
  styleUrl: './pending-approvals.component.scss'
})
export class PendingApprovalsComponent implements OnInit {
  pendingRequests: PendingRequest[] = [];
  filteredRequests: PendingRequest[] = [];
  selectedRequest: PendingRequest | null = null;
  
  // Filter criteria
  filterCriteria = {
    type: 'all',
    department: 'all',
    priority: 'all',
    search: ''
  };
  
  // For comments when approving/rejecting
  approvalComment: string = '';
  isProcessing: boolean = false;
  
  constructor() {}
  
  ngOnInit(): void {
    // In a real app, this would be fetched from an API
    this.loadMockData();
    this.applyFilters();
  }
  
  // Load mock data for demonstration
  private loadMockData(): void {
    this.pendingRequests = [
      {
        id: 1,
        type: 'travel',
        title: 'Conference in New York',
        requester: {
          id: 101,
          name: 'John Smith',
          department: 'Marketing',
          email: 'john.smith@example.com'
        },
        dateSubmitted: '2025-05-25',
        deadline: '2025-06-01',
        priority: 'high',
        status: 'pending',
        details: {
          departureDate: '2025-06-15',
          returnDate: '2025-06-20',
          origin: 'Islamabad',
          destination: 'New York',
          estimatedBudget: 2500,
          currency: 'USD'
        }
      },
      {
        id: 2,
        type: 'accommodation',
        title: 'Hotel for Client Meeting',
        requester: {
          id: 102,
          name: 'Sarah Johnson',
          department: 'Sales',
          email: 'sarah.johnson@example.com'
        },
        dateSubmitted: '2025-05-26',
        deadline: '2025-05-30',
        priority: 'medium',
        status: 'pending',
        details: {
          checkInDate: '2025-06-05',
          checkOutDate: '2025-06-07',
          location: 'Lahore',
          accommodationType: 'Hotel',
          estimatedBudget: 300,
          currency: 'USD'
        }
      },
      {
        id: 3,
        type: 'visa',
        title: 'Business Visa for Germany',
        requester: {
          id: 103,
          name: 'Michael Brown',
          department: 'Engineering',
          email: 'michael.brown@example.com'
        },
        dateSubmitted: '2025-05-20',
        deadline: '2025-05-28',
        priority: 'high',
        status: 'pending',
        details: {
          visaType: 'Business',
          country: 'Germany',
          travelDate: '2025-07-10',
          duration: '14 days',
          estimatedBudget: 200,
          currency: 'EUR'
        }
      },
      {
        id: 4,
        type: 'transport',
        title: 'Car Rental for Site Visit',
        requester: {
          id: 104,
          name: 'Emily Davis',
          department: 'Operations',
          email: 'emily.davis@example.com'
        },
        dateSubmitted: '2025-05-24',
        deadline: null,
        priority: 'low',
        status: 'pending',
        details: {
          transportType: 'Car Rental',
          startDate: '2025-06-02',
          endDate: '2025-06-03',
          location: 'Karachi',
          estimatedBudget: 100,
          currency: 'USD'
        }
      },
      {
        id: 5,
        type: 'expense',
        title: 'Conference Expenses Reimbursement',
        requester: {
          id: 105,
          name: 'David Wilson',
          department: 'Finance',
          email: 'david.wilson@example.com'
        },
        dateSubmitted: '2025-05-22',
        deadline: '2025-05-29',
        priority: 'medium',
        status: 'pending',
        details: {
          expenseType: 'Conference',
          totalAmount: 1200,
          currency: 'USD',
          receiptsAttached: true
        }
      }
    ];
  }
  
  // Apply filters to the requests
  applyFilters(): void {
    this.filteredRequests = this.pendingRequests.filter(request => {
      // Type filter
      if (this.filterCriteria.type !== 'all' && request.type !== this.filterCriteria.type) {
        return false;
      }
      
      // Department filter
      if (this.filterCriteria.department !== 'all' && 
          request.requester.department.toLowerCase() !== this.filterCriteria.department) {
        return false;
      }
      
      // Priority filter
      if (this.filterCriteria.priority !== 'all' && request.priority !== this.filterCriteria.priority) {
        return false;
      }
      
      // Search filter (search in title and requester name)
      if (this.filterCriteria.search) {
        const searchTerm = this.filterCriteria.search.toLowerCase();
        return request.title.toLowerCase().includes(searchTerm) || 
               request.requester.name.toLowerCase().includes(searchTerm);
      }
      
      return true;
    });
  }
  
  // Reset all filters
  resetFilters(): void {
    this.filterCriteria = {
      type: 'all',
      department: 'all',
      priority: 'all',
      search: ''
    };
    this.applyFilters();
  }
  
  // Select a request to view details
  selectRequest(request: PendingRequest): void {
    this.selectedRequest = request;
    this.approvalComment = '';
  }
  
  // Close the details panel
  closeDetails(): void {
    this.selectedRequest = null;
  }
  
  // Approve a request
  approveRequest(): void {
    if (!this.selectedRequest) return;
    
    this.isProcessing = true;
    
    // In a real app, this would be an API call
    setTimeout(() => {
      const index = this.pendingRequests.findIndex(r => r.id === this.selectedRequest!.id);
      if (index !== -1) {
        this.pendingRequests[index].status = 'approved';
        // Remove from pending list
        this.pendingRequests = this.pendingRequests.filter(r => r.id !== this.selectedRequest!.id);
        this.applyFilters();
      }
      
      this.isProcessing = false;
      this.selectedRequest = null;
      this.approvalComment = '';
    }, 1000);
  }
  
  // Reject a request
  rejectRequest(): void {
    if (!this.selectedRequest) return;
    
    this.isProcessing = true;
    
    // In a real app, this would be an API call
    setTimeout(() => {
      const index = this.pendingRequests.findIndex(r => r.id === this.selectedRequest!.id);
      if (index !== -1) {
        this.pendingRequests[index].status = 'rejected';
        // Remove from pending list
        this.pendingRequests = this.pendingRequests.filter(r => r.id !== this.selectedRequest!.id);
        this.applyFilters();
      }
      
      this.isProcessing = false;
      this.selectedRequest = null;
      this.approvalComment = '';
    }, 1000);
  }
  
  // Get CSS class based on priority
  getPriorityClass(priority: string): string {
    switch(priority) {
      case 'high': return 'priority-high';
      case 'medium': return 'priority-medium';
      case 'low': return 'priority-low';
      default: return '';
    }
  }
  
  // Get icon based on request type
  getTypeIcon(type: string): string {
    switch(type) {
      case 'travel': return 'bi-airplane';
      case 'accommodation': return 'bi-building';
      case 'transport': return 'bi-car-front';
      case 'visa': return 'bi-file-text';
      case 'expense': return 'bi-cash-coin';
      default: return 'bi-file-earmark';
    }
  }
  
  // Check if a request is overdue
  isOverdue(request: PendingRequest): boolean {
    if (!request.deadline) return false;
    
    const deadlineDate = new Date(request.deadline);
    const today = new Date();
    
    return deadlineDate < today;
  }
}
