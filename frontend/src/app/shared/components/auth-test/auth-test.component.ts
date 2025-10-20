import { Component, OnInit } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { AuthService } from '../../../core/services/auth.service';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-auth-test',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="auth-test-container">
      <h3>Authentication Test</h3>
      
      <div class="login-section" *ngIf="!isLoggedIn">
        <h4>Login</h4>
        <div class="form-group">
          <label for="email">Email:</label>
          <input type="email" id="email" [(ngModel)]="email" class="form-control">
        </div>
        <div class="form-group">
          <label for="password">Password:</label>
          <input type="password" id="password" [(ngModel)]="password" class="form-control">
        </div>
        <button (click)="login()" class="test-button">Login</button>
      </div>
      
      <div class="auth-actions" *ngIf="isLoggedIn">
        <h4>Logged in as: {{ currentUser?.name }}</h4>
        <button (click)="testAuth()" class="test-button">Test Authentication</button>
        <button (click)="logout()" class="test-button logout">Logout</button>
      </div>
      
      <div *ngIf="result" class="result-container">
        <h4>Result:</h4>
        <pre>{{ result | json }}</pre>
      </div>
      <div *ngIf="error" class="error-container">
        <h4>Error:</h4>
        <pre>{{ error }}</pre>
      </div>
    </div>
  `,
  styles: [`
    .auth-test-container {
      padding: 20px;
      border: 1px solid #ccc;
      border-radius: 5px;
      margin: 20px;
      background-color: #f9f9f9;
      max-width: 500px;
    }
    .form-group {
      margin-bottom: 15px;
    }
    .form-group label {
      display: block;
      margin-bottom: 5px;
      font-weight: 500;
    }
    .form-control {
      width: 100%;
      padding: 8px 12px;
      border: 1px solid #ccc;
      border-radius: 4px;
      font-size: 16px;
      box-sizing: border-box;
    }
    .login-section {
      margin-bottom: 20px;
    }
    .auth-actions {
      margin-bottom: 20px;
    }
    .auth-actions button {
      margin-right: 10px;
      margin-bottom: 10px;
    }
    .test-button {
      background-color: #4CAF50;
      color: white;
      padding: 10px 15px;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 16px;
      margin-top: 10px;
    }
    .test-button:hover {
      background-color: #45a049;
    }
    .test-button.logout {
      background-color: #f44336;
    }
    .test-button.logout:hover {
      background-color: #d32f2f;
    }
    .result-container {
      margin-top: 20px;
      padding: 10px;
      background-color: #e8f5e9;
      border-radius: 4px;
    }
    .error-container {
      margin-top: 20px;
      padding: 10px;
      background-color: #ffebee;
      border-radius: 4px;
      color: #d32f2f;
    }
  `]
})
export class AuthTestComponent implements OnInit {
  result: any = null;
  error: string | null = null;
  isLoggedIn = false;
  currentUser: any = null;
  email = '';
  password = '';

  constructor(private http: HttpClient, private authService: AuthService) {}

  ngOnInit(): void {
    // Check if user is already logged in
    this.authService.isAuthenticated().subscribe(isAuth => {
      this.isLoggedIn = isAuth;
      if (isAuth) {
        this.authService.getCurrentUser$Obs().subscribe(user => {
          this.currentUser = user;
        });
      }
    });
  }

  login(): void {
    this.result = null;
    this.error = null;

    if (!this.email || !this.password) {
      this.error = 'Email and password are required';
      return;
    }

    console.log('Attempting login with:', { email: this.email });

    this.authService.login(this.email, this.password).subscribe({
      next: (user) => {
        this.isLoggedIn = true;
        this.currentUser = user;
        this.result = { message: 'Login successful', user };
        console.log('Login successful:', user);
      },
      error: (err) => {
        console.error('Login failed:', err);
        if (err.status === 401) {
          this.error = 'Invalid email or password. Please try again.';
        } else if (err.status === 0) {
          this.error = 'Cannot connect to the server. Please check if the backend is running.';
        } else {
          this.error = err.message || 'Login failed. Please try again.';
        }
      }
    });
  }

  logout(): void {
    this.authService.logout();
    this.isLoggedIn = false;
    this.currentUser = null;
    this.result = { message: 'Logged out successfully' };
  }

  testAuth(): void {
    this.result = null;
    this.error = null;

    // Get the current user profile from the backend
    this.http.get('http://localhost:8000/api/users/me/').subscribe({
      next: (response) => {
        this.result = response;
        console.log('Authentication successful:', response);
      },
      error: (err) => {
        this.error = `Authentication failed: ${err.message}`;
        console.error('Authentication failed:', err);
      }
    });
  }
}
