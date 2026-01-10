import { Component, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NgbToastModule } from '@ng-bootstrap/ng-bootstrap';
import { ToastService } from '../../../core/services/toast.service';

@Component({
  selector: 'app-toast-container',
  standalone: true,
  imports: [CommonModule, NgbToastModule],
  templateUrl: './toast-container.component.html',
  styleUrls: ['./toast-container.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ToastContainerComponent {
  constructor(public toastService: ToastService) {}

  /**
   * Get icon class based on toast type
   */
  getIconClass(type: string): string {
    switch (type) {
      case 'success':
        return 'bi-check-circle-fill';
      case 'error':
        return 'bi-x-circle-fill';
      case 'warning':
        return 'bi-exclamation-triangle-fill';
      case 'info':
        return 'bi-info-circle-fill';
      default:
        return 'bi-info-circle-fill';
    }
  }

  /**
   * Get toast class based on type
   */
  getToastClass(type: string): string {
    switch (type) {
      case 'success':
        return 'toast-success';
      case 'error':
        return 'toast-error';
      case 'warning':
        return 'toast-warning';
      case 'info':
        return 'toast-info';
      default:
        return 'toast-info';
    }
  }
}
