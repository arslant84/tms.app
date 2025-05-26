import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, of, throwError } from 'rxjs';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Router } from '@angular/router';
import { map, tap, catchError } from 'rxjs/operators';
import { User, UserRole, AuthResponse } from '../models/user.model';
// Define a fallback environment if the import fails
const API_URL = 'http://localhost:8000';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private currentUserSubject = new BehaviorSubject<User | null>(null);
  public currentUser$ = this.currentUserSubject.asObservable();
  private tokenKey = 'auth_token';
  private apiUrl = API_URL;

  constructor(private http: HttpClient, private router: Router) {
    // Check if user is already logged in from local storage
    this.loadUserFromLocalStorage();
  }

  private loadUserFromLocalStorage(): void {
    const token = localStorage.getItem(this.tokenKey);
    const userJson = localStorage.getItem('user_data');
    
    if (token && userJson) {
      try {
        const userData = JSON.parse(userJson);
        this.currentUserSubject.next(userData);
      } catch (error) {
        console.error('Failed to parse user data from localStorage', error);
        this.logout();
      }
    }
  }

  login(email: string, password: string): Observable<User> {
    // The backend token endpoint is at /token
    const url = `${this.apiUrl}/token`;
    
    // For FastAPI's OAuth2 form, we need to use application/x-www-form-urlencoded
    const body = new URLSearchParams();
    body.set('username', email); // FastAPI expects 'username' field even though we're using email
    body.set('password', password);

    const headers = new HttpHeaders({
      'Content-Type': 'application/x-www-form-urlencoded'
    });

    console.log('Attempting login to:', url);
    console.log('With credentials:', { email });
    console.log('Request body:', body.toString());

    return this.http.post<AuthResponse>(url, body.toString(), { headers }).pipe(
      map(response => {
        console.log('Login successful, response:', response);
        
        // Store token in local storage
        localStorage.setItem(this.tokenKey, response.access_token);
        
        // Create user object from response
        const user: User = {
          id: response.user_id,
          name: response.name,
          email: email,
          role: response.role as UserRole,
          department: '', // We don't get this from the token response
          is_admin: response.is_admin,
          is_active: true
        };
        
        // Store user data
        localStorage.setItem('user_data', JSON.stringify(user));
        this.currentUserSubject.next(user);
        return user;
      }),
      catchError(error => {
        console.error('Login failed', error);
        console.error('Error status:', error.status);
        console.error('Error message:', error.message);
        console.error('Error details:', error.error);
        
        let errorMessage = 'Login failed. Please check your credentials.';
        
        if (error.status === 0) {
          errorMessage = 'Cannot connect to the server. Please check your network connection.';
        } else if (error.status === 404) {
          errorMessage = 'Login service not found. Please contact the administrator.';
        } else if (error.status === 401) {
          errorMessage = 'Invalid email or password. Please try again.';
        } else if (error.error?.detail) {
          errorMessage = error.error.detail;
        }
        
        return throwError(() => new Error(errorMessage));
      })
    );
  }

  logout(): void {
    // Remove token and user data from local storage
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem('user_data');
    this.currentUserSubject.next(null);
    this.router.navigate(['/auth/login']);
  }

  isAuthenticated(): Observable<boolean> {
    return this.currentUser$.pipe(
      map(user => !!user)
    );
  }

  getCurrentUser(): Observable<User | null> {
    return this.currentUser$;
  }

  hasRole(allowedRoles: UserRole[]): boolean {
    const user = this.currentUserSubject.value;
    if (!user) return false;
    
    return allowedRoles.includes(user.role);
  }
  
  isAdmin(): boolean {
    const user = this.currentUserSubject.value;
    return user?.is_admin || false;
  }

  // Get the JWT token for API requests
  getToken(): string | null {
    return localStorage.getItem(this.tokenKey);
  }
  
  // Get user profile
  getUserProfile(): Observable<User> {
    const url = `${this.apiUrl}/users/me`;
    return this.http.get<User>(url).pipe(
      catchError(error => {
        console.error('Failed to get user profile', error);
        return throwError(() => new Error('Failed to get user profile'));
      })
    );
  }
  
  // Create a new user (admin only)
  createUser(userData: Partial<User>): Observable<User> {
    const url = `${this.apiUrl}/users`;
    return this.http.post<User>(url, userData).pipe(
      catchError(error => {
        console.error('Failed to create user', error);
        return throwError(() => new Error(error.error?.detail || 'Failed to create user'));
      })
    );
  }
}
