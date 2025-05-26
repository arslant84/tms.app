export interface TravelInsight {
  id: string;
  userId: string;
  title: string;
  description: string;
  insightType: InsightType;
  potentialSavings?: number;
  relevanceScore: number;
  expiryDate?: Date;
  createdAt: Date;
}

export enum InsightType {
  COST_SAVING = 'COST_SAVING',
  BOOKING_TIMING = 'BOOKING_TIMING',
  PREFERRED_VENDOR = 'PREFERRED_VENDOR',
  TRAVEL_PATTERN = 'TRAVEL_PATTERN',
  POLICY_COMPLIANCE = 'POLICY_COMPLIANCE'
}

export interface TravelAnalytics {
  totalTrips: number;
  totalSpend: number;
  averageTripCost: number;
  topDestinations: DestinationStat[];
  spendByCategory: CategorySpend[];
  monthlyTrend: MonthlyTrend[];
  savingsOpportunities: number;
}

export interface DestinationStat {
  destination: string;
  count: number;
  averageCost: number;
}

export interface CategorySpend {
  category: string;
  amount: number;
  percentage: number;
}

export interface MonthlyTrend {
  month: string;
  year: number;
  tripCount: number;
  totalSpend: number;
}
