import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { TrfService } from '../../../../core/services/trf.service';
import { ExpenseService } from '../../../../core/services/expense.service';
import { BookingService } from '../../../../core/services/booking.service';
import { AuthService } from '../../../../core/services/auth.service';
import { TravelRequestForm } from '../../../../core/models/trf.model';
import { ExpenseClaim } from '../../../../core/models/expense.model';
import { FlightBooking, HotelBooking } from '../../../../core/models/booking.model';

@Component({
  selector: 'app-dashboard-home',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './dashboard-home.component.html',
  styleUrls: ['./dashboard-home.component.scss']
})
export class DashboardHomeComponent implements OnInit {
  pendingTrfs: TravelRequestForm[] = [];
  upcomingTrips: TravelRequestForm[] = [];
  draftClaims: ExpenseClaim[] = [];
  pendingBookings: (FlightBooking | HotelBooking)[] = [];
  recentActivities: any[] = [];

  pendingTrfCount = 3;
  upcomingTripCount = 2;
  draftClaimCount = 5;
  pendingBookingCount = 2;

  constructor(
    private trfService: TrfService,
    private expenseService: ExpenseService,
    private bookingService: BookingService,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    this.loadDashboardData();
  }

  loadDashboardData(): void {
    // In a real application, we would load this data from the services
    // For now, we're using mock data that's already in the template
    
    // Example of how we would load the data in a real application:
    /*
    this.authService.getCurrentUser().subscribe(user => {
      if (user) {
        this.trfService.getAllTrfs().subscribe(trfs => {
          this.pendingTrfs = trfs.filter(trf => trf.status === 'PENDING_APPROVAL');
          this.upcomingTrips = trfs.filter(trf => 
            trf.status === 'APPROVED' && 
            new Date(trf.departureDate) > new Date()
          );
          this.pendingTrfCount = this.pendingTrfs.length;
          this.upcomingTripCount = this.upcomingTrips.length;
        });

        this.expenseService.getExpenseClaims(user.id).subscribe(claims => {
          this.draftClaims = claims.filter(claim => claim.status === 'DRAFT');
          this.draftClaimCount = this.draftClaims.length;
        });

        // Load recent activities
        // This would be a combination of recent TRFs, bookings, and expense claims
        // For now, we're using mock data
      }
    });
    */
  }
}
