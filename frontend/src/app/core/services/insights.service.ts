import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { TravelInsight, InsightType, TravelAnalytics, DestinationStat, CategorySpend, MonthlyTrend } from '../models/insights.model';

@Injectable({
  providedIn: 'root'
})
export class InsightsService {
  private mockInsights: TravelInsight[] = [
    {
      id: '1',
      userId: '1',
      title: 'Book New York flights 3 months in advance',
      description: 'Based on your travel history, booking flights to New York 3 months in advance could save up to 25% on airfare.',
      insightType: InsightType.BOOKING_TIMING,
      potentialSavings: 250,
      relevanceScore: 0.85,
      createdAt: new Date('2025-05-10')
    },
    {
      id: '2',
      userId: '1',
      title: 'Consider Hilton for London stays',
      description: 'Your company has a preferred rate with Hilton in London that could save 15% on accommodation costs.',
      insightType: InsightType.PREFERRED_VENDOR,
      potentialSavings: 180,
      relevanceScore: 0.75,
      createdAt: new Date('2025-05-12')
    },
    {
      id: '3',
      userId: '1',
      title: 'Combine upcoming trips to reduce costs',
      description: 'You have two trips to Chicago scheduled within the same week. Combining them could save on travel costs.',
      insightType: InsightType.COST_SAVING,
      potentialSavings: 500,
      relevanceScore: 0.9,
      expiryDate: new Date('2025-06-30'),
      createdAt: new Date('2025-05-15')
    }
  ];

  private mockAnalytics: TravelAnalytics = {
    totalTrips: 24,
    totalSpend: 45000,
    averageTripCost: 1875,
    topDestinations: [
      { destination: 'New York', count: 8, averageCost: 2200 },
      { destination: 'Chicago', count: 6, averageCost: 1500 },
      { destination: 'London', count: 4, averageCost: 3500 },
      { destination: 'San Francisco', count: 3, averageCost: 2800 },
      { destination: 'Tokyo', count: 2, averageCost: 4500 }
    ],
    spendByCategory: [
      { category: 'Flights', amount: 22000, percentage: 49 },
      { category: 'Hotels', amount: 15000, percentage: 33 },
      { category: 'Meals', amount: 5000, percentage: 11 },
      { category: 'Transportation', amount: 2000, percentage: 4 },
      { category: 'Miscellaneous', amount: 1000, percentage: 3 }
    ],
    monthlyTrend: [
      { month: 'January', year: 2025, tripCount: 2, totalSpend: 3800 },
      { month: 'February', year: 2025, tripCount: 3, totalSpend: 5200 },
      { month: 'March', year: 2025, tripCount: 2, totalSpend: 4100 },
      { month: 'April', year: 2025, tripCount: 3, totalSpend: 5500 },
      { month: 'May', year: 2025, tripCount: 2, totalSpend: 4200 },
      { month: 'June', year: 2025, tripCount: 1, totalSpend: 2100 },
      { month: 'July', year: 2025, tripCount: 0, totalSpend: 0 },
      { month: 'August', year: 2025, tripCount: 0, totalSpend: 0 },
      { month: 'September', year: 2025, tripCount: 0, totalSpend: 0 },
      { month: 'October', year: 2025, tripCount: 0, totalSpend: 0 },
      { month: 'November', year: 2025, tripCount: 0, totalSpend: 0 },
      { month: 'December', year: 2025, tripCount: 0, totalSpend: 0 }
    ],
    savingsOpportunities: 2500
  };

  constructor(private http: HttpClient) { }

  // Get all insights for a user
  getInsights(userId: string): Observable<TravelInsight[]> {
    // In a real app, this would make an API call
    return of(this.mockInsights.filter(insight => insight.userId === userId));
  }

  // Get travel analytics for a user
  getTravelAnalytics(userId: string): Observable<TravelAnalytics> {
    // In a real app, this would make an API call
    return of(this.mockAnalytics);
  }

  // Get travel analytics for a specific date range
  getTravelAnalyticsForDateRange(userId: string, startDate: Date, endDate: Date): Observable<TravelAnalytics> {
    // In a real app, this would make an API call with date range parameters
    // For demo purposes, we'll return the same mock data
    return of(this.mockAnalytics);
  }

  // Generate new insights based on travel history
  generateInsights(userId: string): Observable<TravelInsight[]> {
    // In a real app, this would trigger an AI analysis of travel data
    // For demo purposes, we'll return the existing mock insights
    return of(this.mockInsights.filter(insight => insight.userId === userId));
  }

  // Get cost-saving opportunities
  getCostSavingOpportunities(userId: string): Observable<TravelInsight[]> {
    // In a real app, this would make an API call
    return of(this.mockInsights.filter(insight => 
      insight.userId === userId && 
      insight.insightType === InsightType.COST_SAVING
    ));
  }

  // Get booking timing recommendations
  getBookingTimingRecommendations(userId: string): Observable<TravelInsight[]> {
    // In a real app, this would make an API call
    return of(this.mockInsights.filter(insight => 
      insight.userId === userId && 
      insight.insightType === InsightType.BOOKING_TIMING
    ));
  }

  // Get preferred vendor recommendations
  getPreferredVendorRecommendations(userId: string): Observable<TravelInsight[]> {
    // In a real app, this would make an API call
    return of(this.mockInsights.filter(insight => 
      insight.userId === userId && 
      insight.insightType === InsightType.PREFERRED_VENDOR
    ));
  }

  // Get travel pattern insights
  getTravelPatternInsights(userId: string): Observable<TravelInsight[]> {
    // In a real app, this would make an API call
    return of(this.mockInsights.filter(insight => 
      insight.userId === userId && 
      insight.insightType === InsightType.TRAVEL_PATTERN
    ));
  }

  // Get policy compliance insights
  getPolicyComplianceInsights(userId: string): Observable<TravelInsight[]> {
    // In a real app, this would make an API call
    return of(this.mockInsights.filter(insight => 
      insight.userId === userId && 
      insight.insightType === InsightType.POLICY_COMPLIANCE
    ));
  }
}
