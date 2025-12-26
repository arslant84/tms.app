import { Component, OnInit } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { AuthService } from './core/services/auth.service';
import { Observable } from 'rxjs';
import { CommonModule } from '@angular/common';
import { ToastContainerComponent } from './shared/components/toast-container/toast-container.component';
import { ConfirmationDialogComponent } from './shared/components/confirmation-dialog/confirmation-dialog.component';
import { RootModalModule } from './core/components/root-modal/root-modal.module';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    RouterOutlet,
    ToastContainerComponent,
    ConfirmationDialogComponent,
    RootModalModule
  ],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent implements OnInit {
  title = 'SynTra';
  isAuthenticated$: Observable<boolean>;

  constructor(private authService: AuthService) {
    this.isAuthenticated$ = this.authService.isAuthenticated();
  }

  ngOnInit(): void {
    // Initialize any app-wide services or configurations here
  }
}
