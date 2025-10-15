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
  total_expense_claims: number;
  active_bookings: number;
  pending_approvals: number;
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
export interface TravelPatternAnalytics {
  total_trips: number;
  domestic_trips: number;
  international_trips: number;
  top_destinations: any[];
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
  total_hotel_bookings: number;
  flight_cost: number;
  hotel_cost: number;
  average_booking_lead_time: number;
  preferred_airlines: string[];
  preferred_hotels: string[];
  booking_class_distribution: { [key: string]: number };
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
  top_expense_categories: any[];
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

// Travel Insight Interface
export interface TravelInsight {
  id: number;
  user: number;
  user_name: string;
  title: string;
  description: string;
  insight_type: string;
  potential_savings?: number;
  relevance_score: number;
  expiry_date?: string;
  is_expired: boolean;
  created_at: string;
}

// Travel Analytics Interface
export interface TravelAnalytics {
  id: number;
  user?: number;
  user_name?: string;
  total_trips: number;
  total_spend: number;
  average_trip_cost: number;
  savings_opportunities: number;
  top_destinations: any[];
  spend_by_category: any[];
  monthly_trend: any[];
  created_at: string;
  updated_at: string;
}

@Injectable({
  providedIn: 'root'
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

    return this.http.get<TravelSpendAnalytics>(
      `${this.apiUrl}/analytics/travel-spend/`,
      { params }
    );
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

  // ============ Travel Insights APIs ============

  /**
   * Get all travel insights
   */
  getInsights(insightType?: string, includeExpired: boolean = false): Observable<TravelInsight[]> {
    let params = new HttpParams();
    if (insightType) params = params.set('insight_type', insightType);
    if (includeExpired) params = params.set('include_expired', 'true');

    return this.http.get<TravelInsight[]>(`${this.apiUrl}/insights/`, { params });
  }

  /**
   * Get a specific travel insight by ID
   */
  getInsight(id: number): Observable<TravelInsight> {
    return this.http.get<TravelInsight>(`${this.apiUrl}/insights/${id}/`);
  }

  /**
   * Create a new travel insight
   */
  createInsight(insight: Partial<TravelInsight>): Observable<TravelInsight> {
    return this.http.post<TravelInsight>(`${this.apiUrl}/insights/`, insight);
  }

  /**
   * Update a travel insight
   */
  updateInsight(id: number, insight: Partial<TravelInsight>): Observable<TravelInsight> {
    return this.http.patch<TravelInsight>(`${this.apiUrl}/insights/${id}/`, insight);
  }

  /**
   * Delete a travel insight
   */
  deleteInsight(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/insights/${id}/`);
  }

  // ============ Travel Analytics APIs ============

  /**
   * Get all travel analytics
   */
  getAllTravelAnalytics(): Observable<TravelAnalytics[]> {
    return this.http.get<TravelAnalytics[]>(`${this.apiUrl}/analytics/`);
  }

  /**
   * Get user's own analytics
   */
  getMyAnalytics(): Observable<TravelAnalytics> {
    return this.http.get<TravelAnalytics>(`${this.apiUrl}/analytics/my_analytics/`);
  }

  /**
   * Get company-wide analytics (admin only)
   */
  getCompanyAnalytics(): Observable<TravelAnalytics> {
    return this.http.get<TravelAnalytics>(`${this.apiUrl}/analytics/company_analytics/`);
  }

  // ============ Helper Methods ============

  /**
   * Format currency for display
   */
  formatCurrency(amount: number, currency: string = 'USD'): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency
    }).format(amount);
  }

  /**
   * Calculate percentage
   */
  calculatePercentage(value: number, total: number): number {
    if (total === 0) return 0;
    return Math.round((value / total) * 100);
  }

  /**
   * Get insight type label
   */
  getInsightTypeLabel(type: string): string {
    const labels: { [key: string]: string } = {
      'COST_SAVING': 'Cost Saving',
      'BOOKING_TIMING': 'Booking Timing',
      'PREFERRED_VENDOR': 'Preferred Vendor',
      'TRAVEL_PATTERN': 'Travel Pattern',
      'POLICY_COMPLIANCE': 'Policy Compliance'
    };
    return labels[type] || type;
  }

  /**
   * Get insight type color
   */
  getInsightTypeColor(type: string): string {
    const colors: { [key: string]: string } = {
      'COST_SAVING': 'success',
      'BOOKING_TIMING': 'info',
      'PREFERRED_VENDOR': 'primary',
      'TRAVEL_PATTERN': 'warning',
      'POLICY_COMPLIANCE': 'danger'
    };
    return colors[type] || 'secondary';
  }
}
