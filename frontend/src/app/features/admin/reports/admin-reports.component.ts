import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  ReportsService,
  ReportMetric,
  DepartmentStats,
  TopPerformer
} from './services/reports.service';
import { HttpErrorHandlerService } from '../../../core/utils/http-error-handler.service';

interface ChartData {
  labels: string[];
  datasets: {
    label: string;
    data: number[];
    backgroundColor?: string[];
    borderColor?: string;
    borderWidth?: number;
    fill?: boolean;
  }[];
}

@Component({
  selector: 'app-admin-reports',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './admin-reports.component.html',
  styleUrl: './admin-reports.component.scss'
})
export class AdminReportsComponent implements OnInit {
  // Date range filter
  dateRange: 'week' | 'month' | 'quarter' | 'year' = 'month';

  // Loading state
  isLoading = false;
  error: string | null = null;

  // Key metrics
  keyMetrics: ReportMetric[] = [];

  // Chart data
  requestsByTypeChart: ChartData = { labels: [], datasets: [] };
  processingTimeChart: ChartData = { labels: [], datasets: [] };
  requestTrendChart: ChartData = { labels: [], datasets: [] };

  // Department statistics
  departmentStats: DepartmentStats[] = [];

  // Top performers
  topClerks: TopPerformer[] = [];

  constructor(
    private reportsService: ReportsService,
    private errorHandler: HttpErrorHandlerService
  ) {}

  ngOnInit(): void {
    this.loadReportData();
  }
  
  // Load real data from API
  loadReportData(): void {
    this.isLoading = true;
    this.error = null;

    this.reportsService.getAdminReports(this.dateRange).subscribe({
      next: (data) => {
        // Set key metrics
        this.keyMetrics = data.key_metrics;

        // Set requests by type chart
        this.requestsByTypeChart = {
          labels: data.requests_by_type.labels,
          datasets: [{
            label: 'Requests by Type',
            data: data.requests_by_type.data || [],
            backgroundColor: ['#4e73df', '#36b9cc', '#f6c23e', '#1cc88a'] as string[]
          }]
        };

        // Set processing time chart
        this.processingTimeChart = {
          labels: data.processing_by_type.labels,
          datasets: [{
            label: 'Average Processing Time (hours)',
            data: data.processing_by_type.data || [],
            backgroundColor: ['rgba(78, 115, 223, 0.2)'] as string[],
            borderColor: '#4e73df',
            borderWidth: 2,
            fill: true
          }]
        };

        // Set request trend chart
        this.requestTrendChart = {
          labels: data.monthly_trends.labels,
          datasets: [
            {
              label: 'Submitted',
              data: data.monthly_trends.submitted || [],
              borderColor: '#4e73df',
              backgroundColor: ['rgba(78, 115, 223, 0.05)'] as string[],
              fill: true
            },
            {
              label: 'Completed',
              data: data.monthly_trends.completed || [],
              borderColor: '#1cc88a',
              backgroundColor: ['rgba(28, 200, 138, 0.05)'] as string[],
              fill: true
            }
          ]
        };

        // Set department statistics
        this.departmentStats = data.department_stats;

        // Set top performers
        this.topClerks = data.top_performers;

        this.isLoading = false;
      },
      error: (err) => {
        console.error('Error loading reports:', err);
        this.error = 'Failed to load reports data. Please try again.';
        this.isLoading = false;
      }
    });
  }
  
  // Change date range and update data
  changeDateRange(range: 'week' | 'month' | 'quarter' | 'year'): void {
    this.dateRange = range;
    this.loadReportData();
  }
  
  // Get CSS class for trend
  getTrendClass(trend: 'up' | 'down' | 'neutral'): string {
    switch(trend) {
      case 'up': return 'trend-up';
      case 'down': return 'trend-down';
      default: return 'trend-neutral';
    }
  }
  
  // Get trend icon
  getTrendIcon(trend: 'up' | 'down' | 'neutral'): string {
    switch(trend) {
      case 'up': return 'bi-arrow-up';
      case 'down': return 'bi-arrow-down';
      default: return 'bi-dash';
    }
  }
  
  // Format percentage
  formatPercentage(value: number): string {
    return value > 0 ? `+${value}%` : `${value}%`;
  }
  
  // Calculate completion percentage
  getCompletionPercentage(department: DepartmentStats): number {
    return Math.round((department.completed / department.total) * 100);
  }
  
  // Export report data
  exportReport(format: 'pdf' | 'excel' | 'csv'): void {
    this.reportsService.exportReports(format, this.dateRange).subscribe({
      next: (blob) => {
        // Create download link
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;

        // Set filename based on format
        const extensions: Record<string, string> = {
          'pdf': 'pdf',
          'excel': 'xlsx',
          'csv': 'csv'
        };
        const filename = `tms-report-${this.dateRange}-${new Date().toISOString().split('T')[0]}.${extensions[format]}`;
        link.download = filename;

        // Trigger download
        link.click();

        // Cleanup
        window.URL.revokeObjectURL(url);
      },
      error: (err) => {
        this.error = this.errorHandler.getErrorMessage(err, 'Failed to export report');
      }
    });
  }

  // Print report
  printReport(): void {
    window.print();
  }
}
