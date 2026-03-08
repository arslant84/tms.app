import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class GlobalLoadingService {
  private loadingSubject = new BehaviorSubject<boolean>(false);
  private loadingCount = 0;

  public loading$: Observable<boolean> = this.loadingSubject.asObservable();

  /**
   * Show global loading indicator
   */
  show(): void {
    this.loadingCount++;
    this.loadingSubject.next(true);
  }

  /**
   * Hide global loading indicator
   * Only hides when all loading requests are complete
   */
  hide(): void {
    this.loadingCount = Math.max(0, this.loadingCount - 1);
    if (this.loadingCount === 0) {
      this.loadingSubject.next(false);
    }
  }

  /**
   * Force hide loading indicator regardless of count
   */
  forceHide(): void {
    this.loadingCount = 0;
    this.loadingSubject.next(false);
  }

  /**
   * Check if currently loading
   */
  isLoading(): boolean {
    return this.loadingSubject.value;
  }
}
