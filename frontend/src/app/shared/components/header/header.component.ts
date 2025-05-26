import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { Observable, map } from 'rxjs';
import { AuthService } from '../../../core/services/auth.service';
import { User, UserRole } from '../../../core/models/user.model';

@Component({
  selector: 'app-header',
  templateUrl: './header.component.html',
  styleUrls: ['./header.component.scss'],
  standalone: true,
  imports: [CommonModule, RouterModule]
})
export class HeaderComponent implements OnInit {
  isCollapsed = true;
  currentUser$: Observable<User | null>;
  isAdmin$: Observable<boolean>;

  constructor(private authService: AuthService) {
    this.currentUser$ = this.authService.currentUser$;
    this.isAdmin$ = this.currentUser$.pipe(
      map(user => user?.is_admin === true)
    );
  }

  ngOnInit(): void {
  }

  toggleNavbar(): void {
    this.isCollapsed = !this.isCollapsed;
  }

  logout(event: Event): void {
    event.preventDefault();
    this.authService.logout();
  }
}
