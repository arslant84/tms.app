import { Component, EventEmitter, Input, Output, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AccommodationStaffHouse } from '../../../accommodation/services/accommodation.service';

export interface RoomDialogData {
  id?: number;
  staff_house: number | null;
  name: string;
  room_type: string;
  capacity: number;
  status: 'Available' | 'Maintenance' | 'Reserved';
}

@Component({
  selector: 'app-room-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule],
  styleUrls: ['./room-dialog.component.scss'],
  template: `
    <div class="modal-overlay" *ngIf="isOpen" (click)="onOverlayClick($event)">
      <div class="modal-container" (click)="$event.stopPropagation()">
        <div class="modal-header">
          <h2>{{ isEditMode ? 'Edit Room' : 'Add New Room' }}</h2>
          <button class="close-button" (click)="onClose()">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form (ngSubmit)="onSubmit()" #roomForm="ngForm">
          <div class="modal-body">
            <!-- Staff House -->
            <div class="form-group">
              <label for="staffHouse">Staff House *</label>
              <select
                id="staffHouse"
                name="staffHouse"
                [(ngModel)]="formData.staff_house"
                required
                #staffHouseInput="ngModel">
                <option [value]="null">Select a staff house</option>
                <option *ngFor="let house of staffHouses" [value]="house.id">
                  {{ house.name }} - {{ house.location }}
                </option>
              </select>
              <div class="error-message" *ngIf="staffHouseInput.invalid && staffHouseInput.touched">
                Staff house is required
              </div>
            </div>

            <!-- Room Name -->
            <div class="form-group">
              <label for="roomName">Room Name/Number *</label>
              <input
                type="text"
                id="roomName"
                name="roomName"
                [(ngModel)]="formData.name"
                placeholder="e.g., Room 101, Tent 1"
                required
                #roomNameInput="ngModel">
              <div class="error-message" *ngIf="roomNameInput.invalid && roomNameInput.touched">
                Room name is required
              </div>
            </div>

            <!-- Room Type -->
            <div class="form-group">
              <label for="roomType">Room Type *</label>
              <select
                id="roomType"
                name="roomType"
                [(ngModel)]="formData.room_type"
                required
                #roomTypeInput="ngModel">
                <option value="">Select room type</option>
                <option value="Single">Single</option>
                <option value="Double">Double</option>
                <option value="Suite">Suite</option>
                <option value="Tent">Tent</option>
                <option value="Shared">Shared</option>
              </select>
              <div class="error-message" *ngIf="roomTypeInput.invalid && roomTypeInput.touched">
                Room type is required
              </div>
            </div>

            <!-- Capacity -->
            <div class="form-group">
              <label for="capacity">Capacity *</label>
              <input
                type="number"
                id="capacity"
                name="capacity"
                [(ngModel)]="formData.capacity"
                min="1"
                max="20"
                required
                #capacityInput="ngModel">
              <div class="helper-text">Number of people this room can accommodate</div>
              <div class="error-message" *ngIf="capacityInput.invalid && capacityInput.touched">
                Capacity must be between 1 and 20
              </div>
            </div>

            <!-- Status -->
            <div class="form-group">
              <label for="status">Status *</label>
              <select
                id="status"
                name="status"
                [(ngModel)]="formData.status"
                required
                #statusInput="ngModel">
                <option value="Available">Available</option>
                <option value="Maintenance">Maintenance</option>
                <option value="Reserved">Reserved</option>
              </select>
              <div class="error-message" *ngIf="statusInput.invalid && statusInput.touched">
                Status is required
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button type="button" class="btn-secondary" (click)="onClose()">
              Cancel
            </button>
            <button type="submit" class="btn-primary" [disabled]="!roomForm.form.valid || isSubmitting">
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
export class RoomDialogComponent {
  @Input() isOpen = false;
  @Input() staffHouses: AccommodationStaffHouse[] = [];
  @Input() set data(value: RoomDialogData | null) {
    if (value) {
      this.formData = { ...value };
      this.isEditMode = !!value.id;
    } else {
      this.resetForm();
    }
  }
  @Output() close = new EventEmitter<void>();
  @Output() save = new EventEmitter<RoomDialogData>();

  isEditMode = false;
  isSubmitting = false;

  formData: RoomDialogData = {
    staff_house: null,
    name: '',
    room_type: '',
    capacity: 1,
    status: 'Available'
  };

  resetForm(): void {
    this.formData = {
      staff_house: null,
      name: '',
      room_type: '',
      capacity: 1,
      status: 'Available'
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
