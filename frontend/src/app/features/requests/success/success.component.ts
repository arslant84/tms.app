import { Component, OnInit, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';

@Component({
  selector: 'app-success',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './success.component.html',
  styleUrl: './success.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class SuccessComponent implements OnInit {
  successMessage: string = 'Your request has been submitted successfully!';
  
  constructor(private router: Router) {
    // Get the success message from router state if available
    const navigation = this.router.getCurrentNavigation();
    if (navigation?.extras.state) {
      const state = navigation.extras.state as { message: string };
      if (state.message) {
        this.successMessage = state.message;
      }
    }
  }
  
  ngOnInit(): void {}
  
  goToRequests(): void {
    this.router.navigate(['/requests']);
  }
  
  createNewRequest(): void {
    this.router.navigate(['/requests']);
  }
}
