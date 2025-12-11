import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

// This would typically be imported from a shared models directory
interface ReportMetric {
  name: string;
  value: number;
  change: number; // percentage change from previous period
  trend: 'up' | 'down' | 'neutral';
  icon: string;
}

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

interface DepartmentStats {
  department: string;
  total: number;
  pending: number;
  completed: number;
  avgProcessingTime: number; // in hours
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
  
  // Key metrics
  keyMetrics: ReportMetric[] = [];
  
  // Chart data
  requestsByTypeChart: ChartData = { labels: [], datasets: [] };
  processingTimeChart: ChartData = { labels: [], datasets: [] };
  requestTrendChart: ChartData = { labels: [], datasets: [] };
  
  // Department statistics
  departmentStats: DepartmentStats[] = [];
  
  // Top performers
  topClerks: { name: string; processed: number; avgTime: number }[] = [];
  
  constructor() {}
  
  ngOnInit(): void {
    this.loadReportData();
  }
  
  // Load mock data for demonstration
  loadReportData(): void {
    // Update key metrics
    this.keyMetrics = [
      {
        name: 'Total Requests',
        value: 157,
        change: 12.5,
        trend: 'up',
        icon: 'bi-file-earmark-text'
      },
      {
        name: 'Avg. Processing Time',
        value: 36, // hours
        change: -8.2,
        trend: 'down',
        icon: 'bi-clock'
      },
      {
        name: 'Completion Rate',
        value: 92, // percentage
        change: 3.7,
        trend: 'up',
        icon: 'bi-check-circle'
      },
      {
        name: 'Pending Requests',
        value: 23,
        change: -15.4,
        trend: 'down',
        icon: 'bi-hourglass-split'
      }
    ];
    
    // Update chart data
    this.requestsByTypeChart = {
      labels: ['Travel', 'Accommodation', 'Transport', 'Visa', 'Expense'],
      datasets: [{
        label: 'Requests by Type',
        data: [65, 42, 28, 15, 7],
        backgroundColor: ['#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b'] as string[]
      }]
    };
    
    this.processingTimeChart = {
      labels: ['Travel', 'Accommodation', 'Transport', 'Visa', 'Expense'],
      datasets: [{
        label: 'Average Processing Time (hours)',
        data: [48, 24, 18, 72, 12],
        backgroundColor: ['rgba(78, 115, 223, 0.2)'] as string[],
        borderColor: '#4e73df',
        borderWidth: 2,
        fill: true
      }]
    };
    
    // Generate dates for the last 12 months
    const months = [];
    const now = new Date();
    for (let i = 11; i >= 0; i--) {
      const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
      months.push(d.toLocaleString('default', { month: 'short' }));
    }
    
    this.requestTrendChart = {
      labels: months,
      datasets: [
        {
          label: 'Submitted',
          data: [12, 19, 15, 17, 14, 22, 25, 18, 21, 24, 20, 18],
          borderColor: '#4e73df',
          backgroundColor: ['rgba(78, 115, 223, 0.05)'] as string[],
          fill: true
        },
        {
          label: 'Completed',
          data: [10, 15, 12, 14, 13, 20, 22, 16, 19, 22, 18, 16],
          borderColor: '#1cc88a',
          backgroundColor: ['rgba(28, 200, 138, 0.05)'] as string[],
          fill: true
        }
      ]
    };
    
    // Department statistics
    this.departmentStats = [
      {
        department: 'Marketing',
        total: 42,
        pending: 5,
        completed: 37,
        avgProcessingTime: 28.5
      },
      {
        department: 'Sales',
        total: 35,
        pending: 8,
        completed: 27,
        avgProcessingTime: 32.1
      },
      {
        department: 'Engineering',
        total: 29,
        pending: 3,
        completed: 26,
        avgProcessingTime: 24.7
      },
      {
        department: 'Finance',
        total: 18,
        pending: 2,
        completed: 16,
        avgProcessingTime: 18.3
      },
      {
        department: 'Operations',
        total: 22,
        pending: 4,
        completed: 18,
        avgProcessingTime: 30.2
      },
      {
        department: 'Human Resources',
        total: 11,
        pending: 1,
        completed: 10,
        avgProcessingTime: 22.8
      }
    ];
    
    // Top clerks
    this.topClerks = [
      { name: 'Sarah Johnson', processed: 42, avgTime: 22.5 },
      { name: 'Michael Brown', processed: 38, avgTime: 24.8 },
      { name: 'Thomas Lee', processed: 35, avgTime: 26.2 },
      { name: 'Jessica Williams', processed: 30, avgTime: 28.7 },
      { name: 'David Clark', processed: 28, avgTime: 30.1 }
    ];
  }
  
  // Change date range and update data
  changeDateRange(range: 'week' | 'month' | 'quarter' | 'year'): void {
    this.dateRange = range;
    this.loadReportData();
    // In a real app, this would fetch new data based on the selected range
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
  
  // Export report data (mock function)
  exportReport(format: 'pdf' | 'excel' | 'csv'): void {
    // In a real app, this would generate and download a report file
    console.log(`Exporting report in ${format} format...`);
    alert(`Report would be exported as ${format.toUpperCase()} in a real application.`);
  }
  
  // Print report (mock function)
  printReport(): void {
    // In a real app, this would open the print dialog
    console.log('Printing report...');
    alert('Print dialog would open in a real application.');
  }
}
