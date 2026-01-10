import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

export interface LocationDialogData {
  id?: number;
  name: string;
  location: 'Ashgabat' | 'Kiyanly' | 'Turkmenbashy';
  address: string;
  description: string;
}

@Component({
  selector: 'app-location-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="modal-overlay" *ngIf="isOpen" (click)="onOverlayClick($event)">
      <div class="modal-container" (click)="$event.stopPropagation()">
        <div class="modal-header">
          <h2>{{ isEditMode ? 'Edit Location' : 'Add New Location' }}</h2>
          <button class="close-button" (click)="onClose()">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form (ngSubmit)="onSubmit()" #locationForm="ngForm">
          <div class="modal-body">
            <!-- Name -->
            <div class="form-group">
              <label for="name">Staff House Name *</label>
              <input
                type="text"
                id="name"
                name="name"
                [(ngModel)]="formData.name"
                placeholder="e.g., Staff House 41"
                required
                #nameInput="ngModel">
              <div class="error-message" *ngIf="nameInput.invalid && nameInput.touched">
                Staff house name is required
              </div>
            </div>

            <!-- Location -->
            <div class="form-group">
              <label for="location">Location *</label>
              <select
                id="location"
                name="location"
                [(ngModel)]="formData.location"
                required
                #locationInput="ngModel">
                <option value="">Select a location</option>
                <option value="Ashgabat">Ashgabat</option>
                <option value="Kiyanly">Kiyanly</option>
                <option value="Turkmenbashy">Turkmenbashy</option>
              </select>
              <div class="error-message" *ngIf="locationInput.invalid && locationInput.touched">
                Location is required
              </div>
            </div>

            <!-- Address -->
            <div class="form-group">
              <label for="address">Address *</label>
              <input
                type="text"
                id="address"
                name="address"
                [(ngModel)]="formData.address"
                placeholder="Full address"
                required
                #addressInput="ngModel">
              <div class="error-message" *ngIf="addressInput.invalid && addressInput.touched">
                Address is required
              </div>
            </div>

            <!-- Description -->
            <div class="form-group">
              <label for="description">Description</label>
              <textarea
                id="description"
                name="description"
                [(ngModel)]="formData.description"
                rows="3"
                placeholder="Additional details about this location..."></textarea>
            </div>
          </div>

          <div class="modal-footer">
            <button type="button" class="btn-secondary" (click)="onClose()">
              Cancel
            </button>
            <button type="submit" class="btn-primary" [disabled]="!locationForm.form.valid || isSubmitting">
              <span *ngIf="!isSubmitting">{{ isEditMode ? 'Update' : 'Create' }}</span>
              <span *ngIf="isSubmitting">
                <div class="btn-spinner"></div>
                {{ isEditMode ? 'Updating...' : 'Creating...' }}
              </span>
            </button>
          </div>
        </form>
      </div>
    </div>
  `,
  styles: [`
    .modal-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background-color: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      padding: 1rem;
    }

    .modal-container {
      background: white;
      border-radius: 0.5rem;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
      max-width: 500px;
      width: 100%;
      max-height: 90vh;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }

    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1.5rem;
      border-bottom: 1px solid #e5e7eb;

      h2 {
        font-size: 1.25rem;
        font-weight: 600;
        color: #111827;
        margin: 0;
      }

      .close-button {
        background: none;
        border: none;
        cursor: pointer;
        padding: 0.5rem;
        color: #6b7280;
        transition: color 0.2s;

        &:hover {
          color: #111827;
        }

        svg {
          width: 1.5rem;
          height: 1.5rem;
        }
      }
    }

    .modal-body {
      padding: 1.5rem;
      overflow-y: auto;
      flex: 1;
    }

    .form-group {
      margin-bottom: 1.25rem;

      label {
        display: block;
        font-size: 0.875rem;
        font-weight: 500;
        color: #374151;
        margin-bottom: 0.5rem;
      }

      input,
      select,
      textarea {
        width: 100%;
        padding: 0.625rem 0.75rem;
        border: 1px solid #d1d5db;
        border-radius: 0.375rem;
        font-size: 0.875rem;
        color: #111827;
        transition: border-color 0.2s, box-shadow 0.2s;

        &:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        &::placeholder {
          color: #9ca3af;
        }
      }

      textarea {
        resize: vertical;
      }

      .error-message {
        margin-top: 0.5rem;
        font-size: 0.75rem;
        color: #ef4444;
      }
    }

    .modal-footer {
      display: flex;
      justify-content: flex-end;
      gap: 0.75rem;
      padding: 1.5rem;
      border-top: 1px solid #e5e7eb;

      button {
        padding: 0.625rem 1.25rem;
        border: none;
        border-radius: 0.375rem;
        font-size: 0.875rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;
        display: flex;
        align-items: center;
        gap: 0.5rem;

        &:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
      }

      .btn-primary {
        background-color: #3b82f6;
        color: white;

        &:hover:not(:disabled) {
          background-color: #2563eb;
        }
      }

      .btn-secondary {
        background-color: #f3f4f6;
        color: #374151;

        &:hover:not(:disabled) {
          background-color: #e5e7eb;
        }
      }
    }

    .btn-spinner {
      width: 1rem;
      height: 1rem;
      border: 2px solid white;
      border-top: 2px solid transparent;
      border-radius: 50%;
      animation: spin 0.6s linear infinite;
    }

    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
  `]
})
export class LocationDialogComponent {
  @Input() isOpen = false;
  @Input() set data(value: LocationDialogData | null) {
    if (value) {
      this.formData = { ...value };
      this.isEditMode = !!value.id;
    } else {
      this.resetForm();
    }
  }
  @Output() close = new EventEmitter<void>();
  @Output() save = new EventEmitter<LocationDialogData>();

  isEditMode = false;
  isSubmitting = false;

  formData: LocationDialogData = {
    name: '',
    location: 'Ashgabat',
    address: '',
    description: ''
  };

  resetForm(): void {
    this.formData = {
      name: '',
      location: 'Ashgabat',
      address: '',
      description: ''
    };
    this.isEditMode = false;
  }

  onOverlayClick(event: MouseEvent): void {
    if (event.target === event.currentTarget) {
      this.onClose();
    }
  }

  onClose(): void {
    this.close.emit();
    this.resetForm();
  }

  onSubmit(): void {
    if (this.isSubmitting) return;
    this.isSubmitting = true;
    this.save.emit(this.formData);
  }

  setSubmitting(value: boolean): void {
    this.isSubmitting = value;
  }
}
