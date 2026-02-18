import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-confirm-delete-modal',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="modal fade show" style="display: flex;" tabindex="-1" role="dialog">
      <div class="modal-dialog" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ title }}</h5>
            <button type="button" class="btn-close" (click)="onCancel()" [disabled]="isDeleting" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <p class="mb-2">{{ message }}</p>
            <p class="text-muted small mb-0" *ngIf="warningMessage">{{ warningMessage }}</p>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" (click)="onCancel()" [disabled]="isDeleting">
              Cancel
            </button>
            <button type="button" class="btn btn-danger" (click)="onConfirm()" [disabled]="isDeleting">
              <span *ngIf="isDeleting" class="spinner-border spinner-border-sm me-2"></span>
              {{ confirmButtonText }}
            </button>
          </div>
        </div>
      </div>
    </div>
    <div class="modal-backdrop fade show"></div>
  `,
  styles: []
})
export class ConfirmDeleteModalComponent {
  @Input() title = 'Confirm Delete';
  @Input() message = 'Are you sure you want to delete this item?';
  @Input() warningMessage = 'This action cannot be undone.';
  @Input() confirmButtonText = 'Delete';
  @Input() isDeleting = false;

  @Output() confirm = new EventEmitter<void>();
  @Output() close = new EventEmitter<void>();

  onConfirm(): void {
    this.confirm.emit();
  }

  onCancel(): void {
    this.close.emit();
  }
}
