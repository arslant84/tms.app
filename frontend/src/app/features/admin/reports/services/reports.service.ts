import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../../../environments/environment';

export interface ReportMetric {
  name: string;
  value: number;
  change: number;
  trend: 'up' | 'down' | 'neutral';
  icon: string;
}

export interface ChartData {
  labels: string[];
  data?: number[];
  submitted?: number[];
  completed?: number[];
}

export interface DepartmentStats {
  department: string;
  total: number;
  pending: number;
  completed: number;
  avgProcessingTime: number;
}

export interface TopPerformer {
  name: string;
  processed: number;
  avgTime: number;
}

export interface AdminReportsResponse {
  key_metrics: ReportMetric[];
  requests_by_type: ChartData;
  processing_by_type: ChartData;
  monthly_trends: ChartData;
  department_stats: DepartmentStats[];
  top_performers: TopPerformer[];
}

@Injectable({
  providedIn: 'root'
})
export class ReportsService {
  private apiUrl = `${environment.apiUrl}/reports`;

  constructor(private http: HttpClient) {}

  /**
   * Get admin analytics/reports data
   * @param dateRange - week, month, quarter, or year
   */
  getAdminReports(dateRange: 'week' | 'month' | 'quarter' | 'year' = 'month'): Observable<AdminReportsResponse> {
    return this.http.get<AdminReportsResponse>(`${this.apiUrl}/analytics/`, {
      params: { date_range: dateRange }
    });
  }
}
