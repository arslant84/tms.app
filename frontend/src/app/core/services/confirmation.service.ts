import { Injectable } from '@angular/core';
import { Observable, Subject } from 'rxjs';

export interface ConfirmationConfig {
  title?: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  type?: 'danger' | 'warning' | 'info' | 'success';
}

export interface ConfirmationResult {
  confirmed: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class ConfirmationService {
  private confirmationSubject = new Subject<ConfirmationConfig & { result: Subject<boolean> }>();
  public confirmation$ = this.confirmationSubject.asObservable();

  constructor() {}

  /**
   * Show a confirmation dialog
   * @param config Configuration for the confirmation dialog
   * @returns Observable that emits true if confirmed, false if cancelled
   */
  confirm(config: ConfirmationConfig | string): Observable<boolean> {
    const resultSubject = new Subject<boolean>();

    const confirmConfig: ConfirmationConfig = typeof config === 'string'
      ? { message: config }
      : config;

    // Set defaults
    const fullConfig = {
      title: confirmConfig.title || 'Confirm Action',
      message: confirmConfig.message,
      confirmText: confirmConfig.confirmText || 'Confirm',
      cancelText: confirmConfig.cancelText || 'Cancel',
      type: confirmConfig.type || 'warning',
      result: resultSubject
    };

    this.confirmationSubject.next(fullConfig);

    return resultSubject.asObservable();
  }

  /**
   * Convenience method for delete confirmation
   */
  confirmDelete(itemName: string = 'this item'): Observable<boolean> {
    return this.confirm({
      title: 'Confirm Delete',
      message: `Are you sure you want to delete ${itemName}? This action cannot be undone.`,
      confirmText: 'Delete',
      cancelText: 'Cancel',
      type: 'danger'
    });
  }

  /**
   * Convenience method for cancel confirmation
   */
  confirmCancel(message: string = 'Are you sure you want to cancel? Any unsaved changes will be lost.'): Observable<boolean> {
    return this.confirm({
      title: 'Confirm Cancel',
      message: message,
      confirmText: 'Yes, Cancel',
      cancelText: 'No, Go Back',
      type: 'warning'
    });
  }

  /**
   * Convenience method for generic destructive action
   */
  confirmDestructive(action: string, itemName: string): Observable<boolean> {
    return this.confirm({
      title: `Confirm ${action}`,
      message: `Are you sure you want to ${action.toLowerCase()} ${itemName}? This action cannot be undone.`,
      confirmText: action,
      cancelText: 'Cancel',
      type: 'danger'
    });
  }
}
