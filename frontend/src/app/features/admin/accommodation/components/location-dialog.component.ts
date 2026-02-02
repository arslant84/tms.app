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
  styleUrls: ['./location-dialog.component.scss'],
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
  `
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
