import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
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

export interface DepartmentMonthlyFrequency {
  labels: string[];
  travel: number[];
  transport: number[];
  visa: number[];
  accommodation: number[];
}

export interface DepartmentTopRequestor {
  name: string;
  email: string;
  requests: number;
}

export interface DepartmentalReportEntry {
  department: string;
  totalRequests: number;
  breakdown: {
    travel: number;
    transport: number;
    visa: number;
    accommodation: number;
  };
  status: {
    approved: number;
    pending: number;
    rejected: number;
  };
  avgProcessingTime: number;
  topRequestors: DepartmentTopRequestor[];
  activeUsers: number;
  monthlyFrequency: DepartmentMonthlyFrequency;
}

export interface DepartmentalReportsResponse {
  reports: DepartmentalReportEntry[];
  dateRange: string;
  startDate: string;
  endDate: string;
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
    return this.http.get<any>(`${this.apiUrl}/analytics/`, {
      params: { date_range: dateRange },
      withCredentials: true
    }).pipe(
      map(response => response.data)
    );
  }

  /**
   * Get departmental reports data. Non-System-Admin callers (e.g. HODs) are
   * always scoped server-side to their own department regardless of the
   * `department` param - pass it only to let a System Admin pick a
   * specific department to inspect.
   * @param department - department id (System Admin only; ignored server-side otherwise)
   * @param dateRange - week, month, quarter, or year
   */
  getDepartmentalReports(
    department?: string,
    dateRange: 'week' | 'month' | 'quarter' | 'year' = 'month'
  ): Observable<DepartmentalReportsResponse> {
    const params: Record<string, string> = { date_range: dateRange };
    if (department) {
      params['department'] = department;
    }
    return this.http.get<any>(`${this.apiUrl}/departmental/`, {
      params,
      withCredentials: true
    }).pipe(
      map(response => response.data)
    );
  }

  /**
   * Export reports in specified format
   * @param format - pdf, excel, or csv
   * @param dateRange - week, month, quarter, or year
   */
  exportReports(format: 'pdf' | 'excel' | 'csv', dateRange: 'week' | 'month' | 'quarter' | 'year' = 'month'): Observable<Blob> {
    return this.http.get(`${this.apiUrl}/export/`, {
      params: {
        report_type: 'admin',
        export_format: format,  // Use 'export_format' to avoid conflict with DRF's format negotiation
        date_range: dateRange
      },
      responseType: 'blob',
      withCredentials: true
    });
  }
}
