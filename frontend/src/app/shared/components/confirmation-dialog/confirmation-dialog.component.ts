import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subject, Subscription } from 'rxjs';
import { ConfirmationService } from '../../../core/services/confirmation.service';

interface ActiveConfirmation {
  title: string;
  message: string;
  confirmText: string;
  cancelText: string;
  type: 'danger' | 'warning' | 'info' | 'success';
  result: Subject<boolean>;
}

@Component({
  selector: 'app-confirmation-dialog',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="confirmation-overlay" *ngIf="activeConfirmation" (click)="onCancel()">
      <div class="confirmation-dialog" [ngClass]="'type-' + activeConfirmation.type" (click)="$event.stopPropagation()">
        <div class="dialog-header">
          <h3>{{ activeConfirmation.title }}</h3>
          <button type="button" class="btn-close" (click)="onCancel()" aria-label="Close">
            <span>&times;</span>
          </button>
        </div>
        <div class="dialog-body">
          <p>{{ activeConfirmation.message }}</p>
        </div>
        <div class="dialog-footer">
          <button
            type="button"
            class="btn btn-secondary"
            (click)="onCancel()">
            {{ activeConfirmation.cancelText }}
          </button>
          <button
            type="button"
            class="btn"
            [ngClass]="getConfirmButtonClass()"
            (click)="onConfirm()">
            {{ activeConfirmation.confirmText }}
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .confirmation-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 10000;
      animation: fadeIn 0.2s ease-in-out;
    }

    @keyframes fadeIn {
      from {
        opacity: 0;
      }
      to {
        opacity: 1;
      }
    }

    .confirmation-dialog {
      background: white;
      border-radius: 8px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
      max-width: 500px;
      width: 90%;
      animation: slideIn 0.2s ease-in-out;
    }

    @keyframes slideIn {
      from {
        transform: translateY(-20px);
        opacity: 0;
      }
      to {
        transform: translateY(0);
        opacity: 1;
      }
    }

    .dialog-header {
      padding: 1.5rem;
      border-bottom: 1px solid #dee2e6;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .dialog-header h3 {
      margin: 0;
      font-size: 1.25rem;
      font-weight: 600;
    }

    .btn-close {
      background: none;
      border: none;
      font-size: 1.5rem;
      cursor: pointer;
      color: #6c757d;
      padding: 0;
      width: 30px;
      height: 30px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 4px;
    }

    .btn-close:hover {
      background: #f8f9fa;
      color: #000;
    }

    .dialog-body {
      padding: 1.5rem;
    }

    .dialog-body p {
      margin: 0;
      color: #495057;
      line-height: 1.6;
    }

    .dialog-footer {
      padding: 1rem 1.5rem;
      border-top: 1px solid #dee2e6;
      display: flex;
      gap: 0.75rem;
      justify-content: flex-end;
    }

    .btn {
      padding: 0.5rem 1.25rem;
      border-radius: 6px;
      font-weight: 500;
      font-size: 0.95rem;
      cursor: pointer;
      border: 1px solid transparent;
      transition: all 0.2s ease;
    }

    .btn-secondary {
      background: #6c757d;
      color: white;
      border-color: #6c757d;
    }

    .btn-secondary:hover {
      background: #5a6268;
      border-color: #545b62;
    }

    .btn-danger {
      background: #dc3545;
      color: white;
      border-color: #dc3545;
    }

    .btn-danger:hover {
      background: #c82333;
      border-color: #bd2130;
    }

    .btn-warning {
      background: #ffc107;
      color: #212529;
      border-color: #ffc107;
    }

    .btn-warning:hover {
      background: #e0a800;
      border-color: #d39e00;
    }

    .btn-info {
      background: #17a2b8;
      color: white;
      border-color: #17a2b8;
    }

    .btn-info:hover {
      background: #138496;
      border-color: #117a8b;
    }

    .btn-success {
      background: #28a745;
      color: white;
      border-color: #28a745;
    }

    .btn-success:hover {
      background: #218838;
      border-color: #1e7e34;
    }
  `]
})
export class ConfirmationDialogComponent implements OnInit, OnDestroy {
  activeConfirmation: ActiveConfirmation | null = null;
  private subscription?: Subscription;

  constructor(private confirmationService: ConfirmationService) {}

  ngOnInit(): void {
    this.subscription = this.confirmationService.confirmation$.subscribe(
      (confirmation) => {
        this.activeConfirmation = confirmation as ActiveConfirmation;
      }
    );
  }

  ngOnDestroy(): void {
    this.subscription?.unsubscribe();
  }

  onConfirm(): void {
    if (this.activeConfirmation) {
      this.activeConfirmation.result.next(true);
      this.activeConfirmation.result.complete();
      this.activeConfirmation = null;
    }
  }

  onCancel(): void {
    if (this.activeConfirmation) {
      this.activeConfirmation.result.next(false);
      this.activeConfirmation.result.complete();
      this.activeConfirmation = null;
    }
  }

  getConfirmButtonClass(): string {
    if (!this.activeConfirmation) return 'btn-primary';
    return `btn-${this.activeConfirmation.type}`;
  }
}
