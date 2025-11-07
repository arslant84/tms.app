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
    // The backend login endpoint is at /api/login/
    const url = `${this.apiUrl}/api/login/`;
    
    // Django expects JSON data
    const body = {
      email: email,
      password: password
    };

    const headers = new HttpHeaders({
      'Content-Type': 'application/json'
    });

    console.log('Attempting login to:', url);
    console.log('With credentials:', { email });

    return this.http.post<AuthResponse>(url, body, { headers }).pipe(
      map(response => {
        console.log('Login successful, response:', response);
        console.log('Full user data from backend:', response.user);

        // Store token in local storage
        localStorage.setItem(this.tokenKey, response.token);

        // Store ALL user data from backend response
        const user: User = {
          id: response.user.id!,
          name: response.user.name || email.split('@')[0],
          email: response.user.email || email,
          role: response.user.role || '' as any,
          department: response.user.department || '',
          is_admin: response.user.is_admin || false,
          is_active: response.user.is_active !== undefined ? response.user.is_active : true,
          // Include all additional fields from backend
          staff_id: response.user.staff_id,
          phone: response.user.phone,
          gender: response.user.gender,
          profile_photo: response.user.profile_photo,
          last_login_at: response.user.last_login_at
        };

        console.log('Stored user data:', user);

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
    // Call the backend logout endpoint
    const url = `${this.apiUrl}/api/logout/`;
    const token = this.getToken();
    
    if (token) {
      const headers = new HttpHeaders({
        'Authorization': `Token ${token}`
      });
      
      this.http.post(url, {}, { headers }).pipe(
        catchError(error => {
          console.error('Logout failed', error);
          return of(null);
        })
      ).subscribe(() => {
        // Remove token and user data from local storage
        localStorage.removeItem(this.tokenKey);
        localStorage.removeItem('user_data');
        this.currentUserSubject.next(null);
        this.router.navigate(['/auth/login']);
      });
    } else {
      // If no token, just clear local storage
      localStorage.removeItem(this.tokenKey);
      localStorage.removeItem('user_data');
      this.currentUserSubject.next(null);
      this.router.navigate(['/auth/login']);
    }
  }

  isAuthenticated(): Observable<boolean> {
    // For development purposes, always return true
    // In production, this should check if the user is actually authenticated
    return of(true);
    
    // Original implementation:
    // return this.currentUser$.pipe(
    //   map(user => !!user)
    // );
  }

  getCurrentUser(): User | null {
    return this.currentUserSubject.value;
  }

  getCurrentUser$Obs(): Observable<User | null> {
    return this.currentUser$;
  }

  getCurrentUserId(): number | null {
    const user = this.currentUserSubject.value;
    return user?.id || null;
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

  /**
   * Get user's position/role name
   * The role can be either a string or an object with {id, name, description, permissions}
   */
  getUserPosition(user: User | null): string {
    if (!user || !user.role) return '';

    // If role is an object, return the name property
    if (typeof user.role === 'object' && user.role.name) {
      return user.role.name;
    }

    // If role is a string, return it directly
    if (typeof user.role === 'string') {
      return user.role;
    }

    return '';
  }
}
