import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AccommodationService, AccommodationRequest } from '../../../core/services/accommodation.service';

// This interface would typically come from a shared models directory
interface Task {
  id: number;
  requestId: number;
  requestType: 'travel' | 'accommodation' | 'transport' | 'visa' | 'expense';
  title: string;
  requester: {
    id: number;
    name: string;
    department: string;
    email: string;
  };
  dateAssigned: string;
  deadline: string | null;
  priority: 'low' | 'medium' | 'high';
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled';
  details: any; // This would be more specific in a real implementation
  assignedTo: {
    id: number;
    name: string;
  } | null;
}

@Component({
  selector: 'app-clerk-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './clerk-panel.component.html',
  styleUrl: './clerk-panel.component.scss'
})
export class ClerkPanelComponent implements OnInit {
  tasks: Task[] = [];
  filteredTasks: Task[] = [];
  selectedTask: Task | null = null;
  
  // Filter criteria
  filterCriteria = {
    type: 'all',
    status: 'all',
    priority: 'all',
    search: ''
  };
  
  // For processing tasks
  processingNotes: string = '';
  isProcessing: boolean = false;
  
  // Vendor integration options
  vendorOptions = {
    flights: [
      { id: 1, name: 'SkyBooker', url: 'https://skybooker.example.com' },
      { id: 2, name: 'FlightDeals', url: 'https://flightdeals.example.com' },
      { id: 3, name: 'AirConnect', url: 'https://airconnect.example.com' }
    ],
    hotels: [
      { id: 1, name: 'HotelHub', url: 'https://hotelhub.example.com' },
      { id: 2, name: 'StayFinder', url: 'https://stayfinder.example.com' },
      { id: 3, name: 'RoomBooker', url: 'https://roombooker.example.com' }
    ],
    transport: [
      { id: 1, name: 'RideShare', url: 'https://rideshare.example.com' },
      { id: 2, name: 'CarRental', url: 'https://carrental.example.com' },
      { id: 3, name: 'LocalTransport', url: 'https://localtransport.example.com' }
    ],
    visa: [
      { id: 1, name: 'VisaExpress', url: 'https://visaexpress.example.com' },
      { id: 2, name: 'TravelDocs', url: 'https://traveldocs.example.com' },
      { id: 3, name: 'VisaServices', url: 'https://visaservices.example.com' }
    ]
  };
  
  constructor(private accommodationService: AccommodationService) {}
  
  ngOnInit(): void {
    // Load mock data for non-accommodation tasks
    this.loadMockData();
    
    // Subscribe to accommodation requests from the service
    this.accommodationService.getAccommodationRequests().subscribe(requests => {
      // Convert accommodation requests to tasks
      const accommodationTasks = requests.map(request => this.convertAccommodationRequestToTask(request));
      
      // Filter out any existing accommodation tasks
      const nonAccommodationTasks = this.tasks.filter(task => task.requestType !== 'accommodation');
      
      // Combine tasks and update filtered tasks
      this.tasks = [...nonAccommodationTasks, ...accommodationTasks];
      this.applyFilters();
    });
  }
  
  // Load mock data for demonstration
  private loadMockData(): void {
    this.tasks = [
      {
        id: 1,
        requestId: 101,
        requestType: 'travel',
        title: 'Book flight to New York',
        requester: {
          id: 201,
          name: 'John Smith',
          department: 'Marketing',
          email: 'john.smith@example.com'
        },
        dateAssigned: '2025-05-25',
        deadline: '2025-06-01',
        priority: 'high',
        status: 'pending',
        details: {
          departureDate: '2025-06-15',
          returnDate: '2025-06-20',
          origin: 'Islamabad',
          destination: 'New York',
          preferredAirline: 'Any',
          travelClass: 'Economy'
        },
        assignedTo: {
          id: 301,
          name: 'Sarah Johnson'
        }
      },
      {
        id: 2,
        requestId: 102,
        requestType: 'accommodation',
        title: 'Book hotel in Dubai',
        requester: {
          id: 202,
          name: 'Emily Davis',
          department: 'Sales',
          email: 'emily.davis@example.com'
        },
        dateAssigned: '2025-05-26',
        deadline: '2025-05-30',
        priority: 'medium',
        status: 'in_progress',
        details: {
          checkInDate: '2025-06-05',
          checkOutDate: '2025-06-07',
          location: 'Dubai',
          accommodationType: 'Hotel',
          preferredHotel: 'Any 4-star hotel',
          numberOfGuests: 1
        },
        assignedTo: {
          id: 302,
          name: 'Michael Brown'
        }
      },
      {
        id: 3,
        requestId: 103,
        requestType: 'visa',
        title: 'Process business visa for Germany',
        requester: {
          id: 203,
          name: 'Robert Wilson',
          department: 'Engineering',
          email: 'robert.wilson@example.com'
        },
        dateAssigned: '2025-05-20',
        deadline: '2025-05-28',
        priority: 'high',
        status: 'pending',
        details: {
          visaType: 'Business',
          country: 'Germany',
          travelDate: '2025-07-10',
          duration: '14 days',
          passportNumber: 'AB1234567',
          passportExpiryDate: '2027-05-15'
        },
        assignedTo: null
      },
      {
        id: 4,
        requestId: 104,
        requestType: 'transport',
        title: 'Arrange car rental in Karachi',
        requester: {
          id: 204,
          name: 'David Miller',
          department: 'Operations',
          email: 'david.miller@example.com'
        },
        dateAssigned: '2025-05-24',
        deadline: null,
        priority: 'low',
        status: 'pending',
        details: {
          transportType: 'Car Rental',
          startDate: '2025-06-02',
          endDate: '2025-06-03',
          location: 'Karachi',
          carType: 'Sedan',
          additionalRequirements: 'GPS navigation'
        },
        assignedTo: null
      },
      {
        id: 5,
        requestId: 105,
        requestType: 'travel',
        title: 'Book flight to London',
        requester: {
          id: 205,
          name: 'Jennifer White',
          department: 'Finance',
          email: 'jennifer.white@example.com'
        },
        dateAssigned: '2025-05-22',
        deadline: '2025-05-29',
        priority: 'medium',
        status: 'completed',
        details: {
          departureDate: '2025-06-10',
          returnDate: '2025-06-15',
          origin: 'Lahore',
          destination: 'London',
          preferredAirline: 'British Airways',
          travelClass: 'Business'
        },
        assignedTo: {
          id: 303,
          name: 'Thomas Lee'
        }
      }
    ];
  }
  
  // Apply filters to the tasks
  applyFilters(): void {
    this.filteredTasks = this.tasks.filter(task => {
      // Type filter
      if (this.filterCriteria.type !== 'all' && task.requestType !== this.filterCriteria.type) {
        return false;
      }
      
      // Status filter
      if (this.filterCriteria.status !== 'all' && task.status !== this.filterCriteria.status) {
        return false;
      }
      
      // Priority filter
      if (this.filterCriteria.priority !== 'all' && task.priority !== this.filterCriteria.priority) {
        return false;
      }
      
      // Search filter (search in title and requester name)
      if (this.filterCriteria.search) {
        const searchTerm = this.filterCriteria.search.toLowerCase();
        return task.title.toLowerCase().includes(searchTerm) || 
               task.requester.name.toLowerCase().includes(searchTerm);
      }
      
      return true;
    });
  }
  
  // Reset all filters
  resetFilters(): void {
    this.filterCriteria = {
      type: 'all',
      status: 'all',
      priority: 'all',
      search: ''
    };
    this.applyFilters();
  }
  
  // Select a task to view details
  selectTask(task: Task): void {
    this.selectedTask = task;
    this.processingNotes = '';
  }
  
  // Close the details panel
  closeDetails(): void {
    this.selectedTask = null;
  }
  
  // Start processing a task
  startProcessing(): void {
    if (!this.selectedTask) return;
    
    this.isProcessing = true;
    
    // If it's an accommodation request, use the accommodation service
    if (this.selectedTask.requestType === 'accommodation') {
      this.accommodationService.updateRequestStatus(this.selectedTask.id, 'in_progress')
        .subscribe(success => {
          if (success) {
            // Update local task data
            const index = this.tasks.findIndex(t => t.id === this.selectedTask!.id);
            if (index !== -1) {
              this.tasks[index].status = 'in_progress';
              this.tasks[index].assignedTo = {
                id: 301, // This would be the current user's ID
                name: 'Sarah Johnson' // This would be the current user's name
              };
            }
          }
          this.isProcessing = false;
          this.applyFilters();
        });
    } else {
      // For other request types, use the existing mock implementation
      setTimeout(() => {
        const index = this.tasks.findIndex(t => t.id === this.selectedTask!.id);
        if (index !== -1) {
          this.tasks[index].status = 'in_progress';
          this.tasks[index].assignedTo = {
            id: 301, // This would be the current user's ID
            name: 'Sarah Johnson' // This would be the current user's name
          };
        }
        
        this.isProcessing = false;
        this.applyFilters();
      }, 1000);
    }
  }
  
  // Complete a task
  completeTask(): void {
    if (!this.selectedTask) return;
    
    this.isProcessing = true;
    
    // If it's an accommodation request, use the accommodation service
    if (this.selectedTask.requestType === 'accommodation') {
      this.accommodationService.updateRequestStatus(this.selectedTask.id, 'completed')
        .subscribe(success => {
          if (success) {
            // Update local task data
            const index = this.tasks.findIndex(t => t.id === this.selectedTask!.id);
            if (index !== -1) {
              this.tasks[index].status = 'completed';
            }
          }
          this.isProcessing = false;
          this.selectedTask = null;
          this.applyFilters();
        });
    } else {
      // For other request types, use the existing mock implementation
      setTimeout(() => {
        const index = this.tasks.findIndex(t => t.id === this.selectedTask!.id);
        if (index !== -1) {
          this.tasks[index].status = 'completed';
        }
        
        this.isProcessing = false;
        this.selectedTask = null;
        this.applyFilters();
      }, 1000);
    }
  }
  
  // Open vendor website
  openVendorWebsite(vendorType: string, vendorId: number): void {
    const vendorList = this.vendorOptions[vendorType as keyof typeof this.vendorOptions];
    const vendor = vendorList.find(v => v.id === vendorId);
    
    if (vendor) {
      window.open(vendor.url, '_blank');
    }
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
  
  // Get CSS class based on status
  getStatusClass(status: string): string {
    switch(status) {
      case 'pending': return 'status-pending';
      case 'in_progress': return 'status-in-progress';
      case 'completed': return 'status-completed';
      case 'cancelled': return 'status-cancelled';
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
  
  // Check if a task is overdue
  isOverdue(task: Task): boolean {
    if (!task.deadline) return false;
    
    const deadlineDate = new Date(task.deadline);
    const today = new Date();
    
    return deadlineDate < today;
  }
  
  // Convert accommodation request to task format
  private convertAccommodationRequestToTask(request: AccommodationRequest): Task {
    // Calculate deadline based on check-in date (3 days before check-in)
    const checkInDate = new Date(request.checkInDate);
    const deadline = new Date(checkInDate);
    deadline.setDate(deadline.getDate() - 3);
    
    return {
      id: request.id,
      requestId: parseInt(request.requestId.split('-')[2]), // Extract number from BT reference
      requestType: 'accommodation',
      title: `Book ${request.accommodationName} - Room ${request.roomNumber}`,
      requester: request.requester,
      dateAssigned: request.dateSubmitted,
      deadline: deadline.toISOString().split('T')[0], // Format as YYYY-MM-DD
      priority: request.priority,
      status: request.status,
      details: {
        accommodationType: request.accommodationType,
        accommodationName: request.accommodationName,
        roomNumber: request.roomNumber,
        checkInDate: request.checkInDate,
        checkOutDate: request.checkOutDate,
        gender: request.gender,
        reason: request.reason,
        specialRequirements: request.specialRequirements,
        relatedTravelRequest: request.relatedTravelRequest
      },
      assignedTo: null // Initially unassigned
    };
  }
}
