import { Component, OnInit, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

// These interfaces would typically come from a shared models directory
interface AuditTrailEntry {
  id: number;
  timestamp: string;
  user: {
    id: number;
    name: string;
    role: string;
    avatar?: string;
  };
  action: string;
  details?: string;
}

interface Comment {
  id: number;
  timestamp: string;
  user: {
    id: number;
    name: string;
    role: string;
    avatar?: string;
  };
  content: string;
  attachments?: {
    id: number;
    name: string;
    type: string;
    url: string;
  }[];
}

@Component({
  selector: 'app-right-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './right-panel.component.html',
  styleUrl: './right-panel.component.scss'
})
export class RightPanelComponent implements OnInit {
  @Input() requestId!: number;
  @Input() requestType!: string;
  
  @Output() close = new EventEmitter<void>();
  
  activeTab: 'audit' | 'comments' = 'audit';
  auditTrail: AuditTrailEntry[] = [];
  comments: Comment[] = [];
  newComment: string = '';
  
  // For file attachments
  selectedFiles: File[] = [];
  
  constructor() {}
  
  ngOnInit(): void {
    this.loadAuditTrail();
    this.loadComments();
  }
  
  // Load audit trail data
  loadAuditTrail(): void {
    // In a real app, this would be an API call
    this.auditTrail = [
      {
        id: 1,
        timestamp: '2025-05-20T09:15:30',
        user: {
          id: 101,
          name: 'John Smith',
          role: 'Employee',
          avatar: 'assets/avatars/user1.jpg'
        },
        action: 'Created request',
        details: 'Initial submission'
      },
      {
        id: 2,
        timestamp: '2025-05-20T10:22:45',
        user: {
          id: 102,
          name: 'Emily Davis',
          role: 'Focal Person',
          avatar: 'assets/avatars/user2.jpg'
        },
        action: 'Reviewed request',
        details: 'Added additional notes'
      },
      {
        id: 3,
        timestamp: '2025-05-21T14:05:12',
        user: {
          id: 102,
          name: 'Emily Davis',
          role: 'Focal Person',
          avatar: 'assets/avatars/user2.jpg'
        },
        action: 'Approved request',
        details: 'First level approval'
      },
      {
        id: 4,
        timestamp: '2025-05-22T11:30:08',
        user: {
          id: 103,
          name: 'Robert Wilson',
          role: 'HoD',
          avatar: 'assets/avatars/user3.jpg'
        },
        action: 'Approved request',
        details: 'Second level approval'
      },
      {
        id: 5,
        timestamp: '2025-05-23T09:45:22',
        user: {
          id: 104,
          name: 'Sarah Johnson',
          role: 'Clerk',
          avatar: 'assets/avatars/user4.jpg'
        },
        action: 'Started processing',
        details: 'Assigned to clerk'
      },
      {
        id: 6,
        timestamp: '2025-05-24T16:18:40',
        user: {
          id: 104,
          name: 'Sarah Johnson',
          role: 'Clerk',
          avatar: 'assets/avatars/user4.jpg'
        },
        action: 'Updated request',
        details: 'Added booking information'
      },
      {
        id: 7,
        timestamp: '2025-05-25T10:05:33',
        user: {
          id: 104,
          name: 'Sarah Johnson',
          role: 'Clerk',
          avatar: 'assets/avatars/user4.jpg'
        },
        action: 'Completed request',
        details: 'All processing completed'
      }
    ];
  }
  
  // Load comments data
  loadComments(): void {
    // In a real app, this would be an API call
    this.comments = [
      {
        id: 1,
        timestamp: '2025-05-20T09:30:15',
        user: {
          id: 101,
          name: 'John Smith',
          role: 'Employee',
          avatar: 'assets/avatars/user1.jpg'
        },
        content: 'I\'ve submitted this request for my upcoming business trip to New York. Please let me know if you need any additional information.'
      },
      {
        id: 2,
        timestamp: '2025-05-20T10:45:22',
        user: {
          id: 102,
          name: 'Emily Davis',
          role: 'Focal Person',
          avatar: 'assets/avatars/user2.jpg'
        },
        content: 'Could you please upload your invitation letter for this trip?',
      },
      {
        id: 3,
        timestamp: '2025-05-20T11:20:08',
        user: {
          id: 101,
          name: 'John Smith',
          role: 'Employee',
          avatar: 'assets/avatars/user1.jpg'
        },
        content: 'I\'ve attached the invitation letter as requested.',
        attachments: [
          {
            id: 1,
            name: 'Invitation_Letter.pdf',
            type: 'application/pdf',
            url: 'assets/documents/invitation_letter.pdf'
          }
        ]
      },
      {
        id: 4,
        timestamp: '2025-05-21T09:15:30',
        user: {
          id: 102,
          name: 'Emily Davis',
          role: 'Focal Person',
          avatar: 'assets/avatars/user2.jpg'
        },
        content: 'Thank you for providing the invitation letter. I\'ve approved your request and forwarded it to the department head for final approval.'
      },
      {
        id: 5,
        timestamp: '2025-05-22T14:30:45',
        user: {
          id: 103,
          name: 'Robert Wilson',
          role: 'HoD',
          avatar: 'assets/avatars/user3.jpg'
        },
        content: 'Request approved. The travel clerk will now process your booking.'
      },
      {
        id: 6,
        timestamp: '2025-05-24T16:45:12',
        user: {
          id: 104,
          name: 'Sarah Johnson',
          role: 'Clerk',
          avatar: 'assets/avatars/user4.jpg'
        },
        content: 'I\'ve booked your flight and hotel. Please find the details attached.',
        attachments: [
          {
            id: 2,
            name: 'Flight_Itinerary.pdf',
            type: 'application/pdf',
            url: 'assets/documents/flight_itinerary.pdf'
          },
          {
            id: 3,
            name: 'Hotel_Booking.pdf',
            type: 'application/pdf',
            url: 'assets/documents/hotel_booking.pdf'
          }
        ]
      }
    ];
  }
  
  // Switch between tabs
  switchTab(tab: 'audit' | 'comments'): void {
    this.activeTab = tab;
  }
  
  // Close the right panel
  closePanel(): void {
    this.close.emit();
  }
  
  // Format timestamp for display
  formatTimestamp(timestamp: string): string {
    const date = new Date(timestamp);
    return date.toLocaleString();
  }
  
  // Get time elapsed since timestamp
  getTimeElapsed(timestamp: string): string {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const diffHours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
    
    if (diffDays > 0) {
      return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    } else if (diffHours > 0) {
      return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    } else if (diffMinutes > 0) {
      return `${diffMinutes} minute${diffMinutes > 1 ? 's' : ''} ago`;
    } else {
      return 'Just now';
    }
  }
  
  // Handle file selection
  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files) {
      for (let i = 0; i < input.files.length; i++) {
        this.selectedFiles.push(input.files[i]);
      }
    }
  }
  
  // Remove selected file
  removeFile(index: number): void {
    this.selectedFiles.splice(index, 1);
  }
  
  // Submit a new comment
  submitComment(): void {
    if (!this.newComment.trim() && this.selectedFiles.length === 0) return;
    
    // In a real app, this would be an API call
    const newComment: Comment = {
      id: this.comments.length + 1,
      timestamp: new Date().toISOString(),
      user: {
        id: 101, // This would be the current user's ID
        name: 'John Smith', // This would be the current user's name
        role: 'Employee', // This would be the current user's role
        avatar: 'assets/avatars/user1.jpg' // This would be the current user's avatar
      },
      content: this.newComment.trim(),
      attachments: this.selectedFiles.length > 0 ? this.selectedFiles.map((file, index) => ({
        id: this.comments.length + index + 1,
        name: file.name,
        type: file.type,
        url: URL.createObjectURL(file) // In a real app, this would be the URL from the server
      })) : undefined
    };
    
    this.comments.push(newComment);
    this.newComment = '';
    this.selectedFiles = [];
  }
  
  // Get CSS class for user role
  getRoleClass(role: string): string {
    switch(role.toLowerCase()) {
      case 'employee': return 'role-employee';
      case 'focal person': return 'role-focal';
      case 'hod': return 'role-hod';
      case 'clerk': return 'role-clerk';
      case 'admin': return 'role-admin';
      default: return '';
    }
  }
  
  // Get icon for file type
  getFileIcon(fileType: string): string {
    if (fileType.includes('pdf')) {
      return 'bi-file-pdf';
    } else if (fileType.includes('word') || fileType.includes('document')) {
      return 'bi-file-word';
    } else if (fileType.includes('excel') || fileType.includes('sheet')) {
      return 'bi-file-excel';
    } else if (fileType.includes('image')) {
      return 'bi-file-image';
    } else {
      return 'bi-file-earmark';
    }
  }
}
