import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-delete-confirm',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './delete-confirm.component.html',
  styleUrls: ['./delete-confirm.component.scss']
})
export class DeleteConfirmComponent {
  @Input() itemName = 'this item';
  @Input() message = 'Are you sure you want to delete';
  @Output() confirm = new EventEmitter<void>();
  @Output() close = new EventEmitter<void>();

  isSaving = false;

  onConfirm(): void {
    this.isSaving = true;
    this.confirm.emit();
  }

  onCancel(): void {
    this.close.emit();
  }
}
