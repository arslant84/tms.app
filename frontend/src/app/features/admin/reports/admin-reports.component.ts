import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  ReportsService,
  ReportMetric,
  DepartmentStats,
  TopPerformer,
  DepartmentalReportEntry,
} from './services/reports.service';
import { HttpErrorHandlerService } from '../../../core/utils/http-error-handler.service';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { RbacService } from '../../../core/services/rbac.service';
import { AuthService } from '../../../core/services/auth.service';
import { DepartmentService } from '../../../core/services/department.service';
import { Permission } from '../../../core/models/permission.models';
import { DepartmentListItem } from '../../../core/models/user.model';

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
  imports: [CommonModule, FormsModule, LoadingSpinnerComponent],
  templateUrl: './admin-reports.component.html',
  styleUrl: './admin-reports.component.scss',
})
export class AdminReportsComponent implements OnInit {
  // Report chart colors - mirror styles/_variables.scss design tokens
  // ($chart-color-1..6, $primary-color, $success-color, $warning-color) so
  // Chart.js-style inline dataset colors stay in sync with the SCSS palette
  // (TS can't `@use` SCSS variables directly). Do not hand-pick new hex here.
  private readonly CHART_RED = '#ef4444'; // $chart-color-1 / $error-color
  private readonly CHART_AMBER = '#f59e0b'; // $chart-color-2 / $warning-color
  private readonly CHART_CYAN = '#06b6d4'; // $chart-color-3
  private readonly CHART_GREEN = '#10b981'; // $chart-color-4 / $success-color
  private readonly CHART_TEAL = '#0d9488'; // $chart-color-5 / $primary-color
  private readonly CHART_BLUE = '#3b82f6'; // $chart-color-6 / $info-color

  // Date range filter
  dateRange: 'week' | 'month' | 'quarter' | 'year' = 'month';

  // Which top-level view is active
  activeView: 'overview' | 'department' = 'overview';

  // Loading state
  isLoading = false;
  error: string | null = null;

  // Key metrics
  keyMetrics: ReportMetric[] = [];

  // Chart data
  requestsByTypeChart: ChartData = { labels: [], datasets: [] };
  processingTimeChart: ChartData = { labels: [], datasets: [] };
  requestTrendChart: ChartData = { labels: [], datasets: [] };

  // Department statistics (Overview tab - all departments)
  departmentStats: DepartmentStats[] = [];

  // Top performers
  topClerks: TopPerformer[] = [];

  // By Department view
  canViewAnyDepartment = false;
  myDepartmentId: string | null = null;
  availableDepartments: DepartmentListItem[] = [];
  selectedDepartmentId: string | null = null;
  departmentReport: DepartmentalReportEntry | null = null;
  departmentReportError: string | null = null;
  departmentReportLoading = false;
  departmentFrequencyChart: ChartData = { labels: [], datasets: [] };

  constructor(
    private reportsService: ReportsService,
    private errorHandler: HttpErrorHandlerService,
    private rbacService: RbacService,
    private authService: AuthService,
    private departmentService: DepartmentService
  ) {}

  ngOnInit(): void {
    this.loadReportData();
    this.canViewAnyDepartment = this.rbacService.hasPermission(Permission.SYSTEM_ADMIN);
    this.myDepartmentId = this.resolveMyDepartmentId();
    if (this.canViewAnyDepartment) {
      this.departmentService.getActiveDepartments().subscribe({
        next: depts => {
          this.availableDepartments = depts;
          this.selectedDepartmentId = depts[0]?.id ?? null;
          if (this.activeView === 'department' && this.selectedDepartmentId) {
            this.loadDepartmentReport();
          }
        },
        error: () => (this.availableDepartments = []),
      });
    }
  }

  private resolveMyDepartmentId(): string | null {
    const department = this.authService.getCurrentUser()?.department;
    if (!department) return null;
    return typeof department === 'string' ? department : department.id;
  }

  // Load real data from API
  loadReportData(): void {
    this.isLoading = true;
    this.error = null;

    this.reportsService.getAdminReports(this.dateRange).subscribe({
      next: data => {
        // Set key metrics
        this.keyMetrics = data.key_metrics;

        // Set requests by type chart
        this.requestsByTypeChart = {
          labels: data.requests_by_type.labels,
          datasets: [
            {
              label: 'Requests by Type',
              data: data.requests_by_type.data || [],
              backgroundColor: [
                this.CHART_BLUE,
                this.CHART_CYAN,
                this.CHART_AMBER,
                this.CHART_GREEN,
              ] as string[],
            },
          ],
        };

        // Set processing time chart
        this.processingTimeChart = {
          labels: data.processing_by_type.labels,
          datasets: [
            {
              label: 'Average Processing Time (hours)',
              data: data.processing_by_type.data || [],
              backgroundColor: ['rgba(59, 130, 246, 0.2)'] as string[],
              borderColor: this.CHART_BLUE,
              borderWidth: 2,
              fill: true,
            },
          ],
        };

        // Set request trend chart
        this.requestTrendChart = {
          labels: data.monthly_trends.labels,
          datasets: [
            {
              label: 'Submitted',
              data: data.monthly_trends.submitted || [],
              borderColor: this.CHART_BLUE,
              backgroundColor: ['rgba(59, 130, 246, 0.05)'] as string[],
              fill: true,
            },
            {
              label: 'Completed',
              data: data.monthly_trends.completed || [],
              borderColor: this.CHART_GREEN,
              backgroundColor: ['rgba(16, 185, 129, 0.05)'] as string[],
              fill: true,
            },
          ],
        };

        // Set department statistics
        this.departmentStats = data.department_stats;

        // Set top performers
        this.topClerks = data.top_performers;

        this.isLoading = false;
      },
      error: err => {
        console.error('Error loading reports:', err);
        this.error = 'Failed to load reports data. Please try again.';
        this.isLoading = false;
      },
    });
  }

  // Change date range and update data
  changeDateRange(range: 'week' | 'month' | 'quarter' | 'year'): void {
    this.dateRange = range;
    this.loadReportData();
    if (this.activeView === 'department') {
      this.loadDepartmentReport();
    }
  }

  // Switch between the Overview and By Department views
  switchView(view: 'overview' | 'department'): void {
    this.activeView = view;
    if (view === 'department' && !this.departmentReport && !this.departmentReportError) {
      this.loadDepartmentReport();
    }
  }

  // Called when a System Admin picks a different department from the dropdown
  onDepartmentSelectChange(): void {
    this.loadDepartmentReport();
  }

  private loadDepartmentReport(): void {
    if (!this.canViewAnyDepartment && !this.myDepartmentId) {
      this.departmentReportError =
        'No department assigned to your account - contact your administrator.';
      this.departmentReport = null;
      return;
    }
    if (this.canViewAnyDepartment && !this.selectedDepartmentId) {
      // Department list hasn't loaded yet - the getActiveDepartments callback
      // will call this again once a default selection is available.
      return;
    }

    const targetDepartmentId = this.canViewAnyDepartment
      ? this.selectedDepartmentId!
      : this.myDepartmentId!;

    this.departmentReportLoading = true;
    this.departmentReportError = null;

    this.reportsService.getDepartmentalReports(targetDepartmentId, this.dateRange).subscribe({
      next: data => {
        this.departmentReport = data.reports[0] || null;
        if (!this.departmentReport) {
          this.departmentReportError = 'No data available for this department yet.';
        } else {
          this.departmentFrequencyChart = {
            labels: this.departmentReport.monthlyFrequency.labels,
            datasets: [
              // Colors match the breakdown-row above (.bg-primary Travel / .bg-success Transport)
              // so the same category reads as the same color everywhere on this page.
              {
                label: 'Travel',
                data: this.departmentReport.monthlyFrequency.travel,
                borderColor: this.CHART_TEAL,
                backgroundColor: ['rgba(13, 148, 136, 0.05)'],
                fill: true,
              },
              {
                label: 'Transport',
                data: this.departmentReport.monthlyFrequency.transport,
                borderColor: this.CHART_GREEN,
                backgroundColor: ['rgba(16, 185, 129, 0.05)'],
                fill: true,
              },
              {
                label: 'Visa',
                data: this.departmentReport.monthlyFrequency.visa,
                borderColor: this.CHART_AMBER,
                backgroundColor: ['rgba(245, 158, 11, 0.05)'],
                fill: true,
              },
              {
                label: 'Accommodation',
                data: this.departmentReport.monthlyFrequency.accommodation,
                borderColor: this.CHART_CYAN,
                backgroundColor: ['rgba(6, 182, 212, 0.05)'],
                fill: true,
              },
            ],
          };
        }
        this.departmentReportLoading = false;
      },
      error: err => {
        this.departmentReportError = this.errorHandler.getErrorMessage(
          err,
          'Failed to load departmental report'
        );
        this.departmentReportLoading = false;
      },
    });
  }

  // Sum of a monthly frequency series, for a small "total" caption alongside the chart
  sumSeries(data: number[]): number {
    return data.reduce((sum, v) => sum + v, 0);
  }

  // Total requests (all types) for a given month index in the frequency chart
  getFrequencyMonthTotal(monthIndex: number): number {
    return this.departmentFrequencyChart.datasets.reduce(
      (sum, ds) => sum + (ds.data[monthIndex] || 0),
      0
    );
  }

  // Highest month total across the frequency chart, for proportional bar scaling
  getFrequencyMax(): number {
    const labels = this.departmentFrequencyChart.labels;
    const max = Math.max(0, ...labels.map((_, i) => this.getFrequencyMonthTotal(i)));
    return max > 0 ? max * 1.2 : 1;
  }

  // Proportional stacked-segment height (%) for one series' value within a month's bar
  getFrequencySegmentHeightPercent(value: number): number {
    return Math.min((value / this.getFrequencyMax()) * 100, 100);
  }

  // Get CSS class for trend
  getTrendClass(trend: 'up' | 'down' | 'neutral'): string {
    switch (trend) {
      case 'up':
        return 'trend-up';
      case 'down':
        return 'trend-down';
      default:
        return 'trend-neutral';
    }
  }

  // Get trend icon
  getTrendIcon(trend: 'up' | 'down' | 'neutral'): string {
    switch (trend) {
      case 'up':
        return 'bi-arrow-up';
      case 'down':
        return 'bi-arrow-down';
      default:
        return 'bi-dash';
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
      next: blob => {
        // Create download link
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;

        // Set filename based on format
        const extensions: Record<string, string> = {
          pdf: 'pdf',
          excel: 'xlsx',
          csv: 'csv',
        };
        const filename = `tms-report-${this.dateRange}-${new Date().toISOString().split('T')[0]}.${extensions[format]}`;
        link.download = filename;

        // Trigger download
        link.click();

        // Cleanup
        window.URL.revokeObjectURL(url);
      },
      error: err => {
        this.error = this.errorHandler.getErrorMessage(err, 'Failed to export report');
      },
    });
  }

  // Print report
  printReport(): void {
    window.print();
  }

  // Get max value from processing time chart for proper scaling
  getProcessingTimeMax(): number {
    const data = this.processingTimeChart.datasets[0]?.data || [];
    if (data.length === 0) return 100;
    const max = Math.max(...data);
    // Add 20% padding to the max value for better visualization
    return max > 0 ? max * 1.2 : 100;
  }

  // Calculate bar height percentage based on max value
  getBarHeightPercent(value: number): number {
    const max = this.getProcessingTimeMax();
    return Math.min((value / max) * 100, 100);
  }
}
