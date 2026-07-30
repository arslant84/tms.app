import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';

/**
 * Self-contained passport upload dropzone + preview + remove control, shared across
 * every TSR travel-type form. Parent still owns the raw File object (it needs to send
 * it in FormData to the backend) - this component owns validation, preview and the
 * remove-file UI, and reports back via (fileSelected)/(fileRemoved).
 */
@Component({
  selector: 'app-passport-upload',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './passport-upload.component.html',
  styleUrls: ['./passport-upload.component.scss']
})
export class PassportUploadComponent implements OnChanges {
  /** Existing file name to restore, e.g. when editing a previously-submitted TSR. */
  @Input() fileName: string = '';
  /** Existing file URL to restore, e.g. when editing a previously-submitted TSR. */
  @Input() fileUrl: string = '';
  @Output() fileSelected = new EventEmitter<File>();
  @Output() fileRemoved = new EventEmitter<void>();

  /** Unique id suffix so multiple instances on one page don't collide on the input's id/label. */
  @Input() inputId: string = 'passportFile';

  file: File | null = null;
  displayFileName: string = '';
  displayFileUrl: string = '';
  fileError: string = '';

  allowedFileTypes = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png'];
  maxFileSize = 10 * 1024 * 1024; // 10MB

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['fileName']) {
      this.displayFileName = this.fileName || '';
    }
    if (changes['fileUrl']) {
      this.displayFileUrl = this.fileUrl || '';
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      const file = input.files[0];

      // Validate file type
      if (!this.allowedFileTypes.includes(file.type)) {
        this.fileError = 'Please upload a PDF, JPG, or PNG file.';
        this.file = null;
        this.displayFileName = '';
        return;
      }

      // Validate file size
      if (file.size > this.maxFileSize) {
        this.fileError = 'File size must not exceed 10MB.';
        this.file = null;
        this.displayFileName = '';
        return;
      }

      this.fileError = '';
      this.file = file;
      this.displayFileName = file.name;
      this.fileSelected.emit(file);
    }
  }

  removeFile(): void {
    this.file = null;
    this.displayFileName = '';
    this.displayFileUrl = '';
    this.fileError = '';
    this.fileRemoved.emit();
  }
}
