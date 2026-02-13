import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

export interface Toast {
  message: string;
  type: 'success' | 'error' | 'info' | 'warning';
  autohide?: boolean;
  delay?: number;
}

@Injectable({
  providedIn: 'root'
})
export class ToastService {
  private toastsSubject = new BehaviorSubject<(Toast & { id: number })[]>([]);
  toasts$ = this.toastsSubject.asObservable();
  private idCounter = 0;

  get toasts(): (Toast & { id: number })[] {
    return this.toastsSubject.value;
  }

  /**
   * Show a success toast notification
   */
  success(message: string, autohide = true, delay = 5000): void {
    this.show(message, 'success', autohide, delay);
  }

  /**
   * Show an error toast notification
   */
  error(message: string, autohide = true, delay = 7000): void {
    this.show(message, 'error', autohide, delay);
  }

  /**
   * Show an info toast notification
   */
  info(message: string, autohide = true, delay = 5000): void {
    this.show(message, 'info', autohide, delay);
  }

  /**
   * Show a warning toast notification
   */
  warning(message: string, autohide = true, delay = 6000): void {
    this.show(message, 'warning', autohide, delay);
  }

  /**
   * Show a toast notification
   */
  show(message: string, type: 'success' | 'error' | 'info' | 'warning', autohide = true, delay = 5000): void {
    const id = this.idCounter++;
    const currentToasts = this.toastsSubject.value;
    this.toastsSubject.next([...currentToasts, { id, message, type, autohide, delay }]);

    if (autohide) {
      setTimeout(() => this.remove(id), delay);
    }
  }

  /**
   * Remove a toast notification
   */
  remove(id: number): void {
    const currentToasts = this.toastsSubject.value;
    this.toastsSubject.next(currentToasts.filter(t => t.id !== id));
  }

  /**
   * Clear all toast notifications
   */
  clear(): void {
    this.toastsSubject.next([]);
  }
}
