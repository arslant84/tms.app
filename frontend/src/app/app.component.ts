import { Component, OnInit, OnDestroy } from '@angular/core';
import { Router, RouterOutlet, NavigationStart, NavigationEnd, NavigationCancel, NavigationError } from '@angular/router';
import { AuthService } from './core/services/auth.service';
import { GlobalLoadingService } from './core/services/global-loading.service';
import { Observable, Subject } from 'rxjs';
import { filter, takeUntil } from 'rxjs/operators';
import { CommonModule } from '@angular/common';
import { ToastContainerComponent } from './shared/components/toast-container/toast-container.component';
import { ConfirmationDialogComponent } from './shared/components/confirmation-dialog/confirmation-dialog.component';
import { RootModalModule } from './core/components/root-modal/root-modal.module';
import { LoadingSpinnerComponent } from './shared/components/loading-spinner/loading-spinner.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    RouterOutlet,
    ToastContainerComponent,
    ConfirmationDialogComponent,
    RootModalModule,
    LoadingSpinnerComponent
  ],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent implements OnInit, OnDestroy {
  title = 'SynTra';
  isAuthenticated$: Observable<boolean>;
  loading$: Observable<boolean>;
  private destroy$ = new Subject<void>();

  constructor(
    private authService: AuthService,
    private router: Router,
    private globalLoading: GlobalLoadingService
  ) {
    this.isAuthenticated$ = this.authService.isAuthenticated();
    this.loading$ = this.globalLoading.loading$;
    this.setupRouterLoading();
  }

  ngOnInit(): void {
    // Initialize any app-wide services or configurations here
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /**
   * Setup global loading indicator for route transitions
   */
  private setupRouterLoading(): void {
    this.router.events
      .pipe(takeUntil(this.destroy$))
      .subscribe(event => {
        if (event instanceof NavigationStart) {
          this.globalLoading.show();
        } else if (
          event instanceof NavigationEnd ||
          event instanceof NavigationCancel ||
          event instanceof NavigationError
        ) {
          // Small delay to prevent flashing on fast transitions
          setTimeout(() => this.globalLoading.hide(), 200);
        }
      });
  }
}
