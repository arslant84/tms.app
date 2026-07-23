import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

// Dashboard Summary Interface
export interface DashboardSummary {
  total_trfs: number;
  pending_trfs: number;
  approved_trfs: number;
  rejected_trfs: number;
  total_travel_cost: number;
  pending_expense_claims: number;
  active_bookings: number;
  pending_approvals: number;
  pending_transport_requests: number;
  pending_visa_applications: number;
  recent_activities: RecentActivity[];
}

export interface RecentActivity {
  type: string;
  id: number;
  title: string;
  status: string;
  date: string;
}

// Travel Spend Analytics Interface
export interface TravelSpendAnalytics {
  total_spend: number;
  by_category: { [key: string]: number };
  by_department: { [key: string]: number };
  by_month: MonthlySpend[];
  top_spenders: TopSpender[];
  budget_utilization?: number;
}

export interface MonthlySpend {
  month: string;
  amount: number;
}

export interface TopSpender {
  user_id: number;
  user_name: string;
  total_spend: number;
}

// Travel Pattern Analytics Interface
export interface Destination {
  name: string;
  city?: string;
  country?: string;
  trip_count: number;
  total_spend?: number;
}

export interface TravelPatternAnalytics {
  total_trips: number;
  domestic_trips: number;
  international_trips: number;
  top_destinations: Destination[];
  average_trip_duration: number;
  most_frequent_travelers: FrequentTraveler[];
  travel_by_purpose: { [key: string]: number };
}

export interface FrequentTraveler {
  user_id: number;
  user_name: string;
  trip_count: number;
}

// Booking Analytics Interface
export interface BookingAnalytics {
  total_flight_bookings: number;
  flight_cost: number;
  average_booking_lead_time: number;
  preferred_airlines: string[];
  booking_class_distribution: { [key: string]: number };
}

export interface ExpenseCategory {
  name: string;
  amount: number;
  count: number;
  percentage?: number;
}

// Expense Analytics Interface
export interface ExpenseAnalytics {
  total_claims: number;
  total_amount: number;
  approved_amount: number;
  pending_amount: number;
  by_category: { [key: string]: number };
  by_status: { [key: string]: number };
  average_claim_amount: number;
  top_expense_categories: ExpenseCategory[];
}

// Department Analytics Interface
export interface DepartmentAnalytics {
  department_name: string;
  total_trips: number;
  total_spend: number;
  active_travelers: number;
  average_trip_cost: number;
  pending_approvals: number;
}

// User Activity Interface
export interface UserActivity {
  user_id: number;
  user_name: string;
  email: string;
  total_trfs: number;
  total_bookings: number;
  total_claims: number;
  total_spend: number;
  last_activity: string;
}

@Injectable({
  providedIn: 'root',
})
export class InsightsService {
  private apiUrl = `${environment.apiUrl}/insights`;

  constructor(private http: HttpClient) {}

  // ============ Dashboard APIs ============

  /**
   * Get dashboard summary statistics
   */
  getDashboardSummary(): Observable<DashboardSummary> {
    return this.http.get<DashboardSummary>(`${this.apiUrl}/dashboard/summary/`);
  }

  // ============ Analytics APIs ============

  /**
   * Get travel spend analytics with optional date range
   */
  getTravelSpendAnalytics(dateFrom?: string, dateTo?: string): Observable<TravelSpendAnalytics> {
    let params = new HttpParams();
    if (dateFrom) params = params.set('date_from', dateFrom);
    if (dateTo) params = params.set('date_to', dateTo);

    return this.http.get<TravelSpendAnalytics>(`${this.apiUrl}/analytics/travel-spend/`, {
      params,
    });
  }

  /**
   * Get travel pattern analytics
   */
  getTravelPatternAnalytics(): Observable<TravelPatternAnalytics> {
    return this.http.get<TravelPatternAnalytics>(`${this.apiUrl}/analytics/travel-patterns/`);
  }

  /**
   * Get booking analytics
   */
  getBookingAnalytics(): Observable<BookingAnalytics> {
    return this.http.get<BookingAnalytics>(`${this.apiUrl}/analytics/bookings/`);
  }

  /**
   * Get expense analytics
   */
  getExpenseAnalytics(): Observable<ExpenseAnalytics> {
    return this.http.get<ExpenseAnalytics>(`${this.apiUrl}/analytics/expenses/`);
  }

  /**
   * Get department-wise analytics (admin only)
   */
  getDepartmentAnalytics(): Observable<DepartmentAnalytics[]> {
    return this.http.get<DepartmentAnalytics[]>(`${this.apiUrl}/analytics/departments/`);
  }

  // ============ Reports APIs ============

  /**
   * Get user activity report (admin only)
   */
  getUserActivityReport(): Observable<UserActivity[]> {
    return this.http.get<UserActivity[]>(`${this.apiUrl}/reports/user-activity/`);
  }

  // ============ Helper Methods ============

  /**
   * Format currency for display
   */
  formatCurrency(amount: number, currency: string = 'USD'): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
    }).format(amount);
  }

  /**
   * Calculate percentage
   */
  calculatePercentage(value: number, total: number): number {
    if (total === 0) return 0;
    return Math.round((value / total) * 100);
  }
}
