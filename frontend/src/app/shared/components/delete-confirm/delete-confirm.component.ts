import { Component, Input, Output, EventEmitter, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { LoadingSpinnerComponent } from '../../shared/components/loading-spinner/loading-spinner.component';

@Component({
  selector: 'app-delete-confirm',
  standalone: true,
  imports: [CommonModule, LoadingSpinnerComponent],
  templateUrl: './delete-confirm.component.html',
  styleUrls: ['./delete-confirm.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
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
