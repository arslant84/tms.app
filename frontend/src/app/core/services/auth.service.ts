import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, of, throwError } from 'rxjs';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Router } from '@angular/router';
import { map, tap, catchError, shareReplay } from 'rxjs/operators';
import { User, AuthResponse } from '../models/user.model';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private currentUserSubject = new BehaviorSubject<User | null>(null);
  public currentUser$ = this.currentUserSubject.asObservable();
  private apiUrl = environment.apiUrl.replace('/api', ''); // Remove /api suffix for backward compatibility
  private initializationRequest$?: Observable<User>;

  constructor(private http: HttpClient, private router: Router) {
    // SECURITY: Token now stored in HttpOnly cookie (not accessible to JavaScript)
    // Try to load user data from backend on init
    this.initializeUser();
  }

  /**
   * SECURITY: Initialize user from backend instead of localStorage
   * Token is in HttpOnly cookie, automatically sent by browser
   * Uses shareReplay to prevent multiple concurrent initialization requests
   */
  private initializeUser(): void {
    // Prevent multiple concurrent initialization requests
    if (this.initializationRequest$) {
      return;
    }

    // Create shared observable for initialization
    this.initializationRequest$ = this.http.get<User>(`${this.apiUrl}/api/users/me/`, { withCredentials: true }).pipe(
      tap((user) => {
        this.currentUserSubject.next(user);
      }),
      catchError(() => {
        // No valid session, user not logged in
        this.currentUserSubject.next(null);
        return of(null as any);
      }),
      shareReplay(1) // Share the result with all subscribers
    );

    // Subscribe to trigger the request
    this.initializationRequest$.subscribe();
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

    // SECURITY: withCredentials: true allows cookies to be sent/received
    return this.http.post<AuthResponse>(url, body, { headers, withCredentials: true }).pipe(
      map(response => {
        // SECURITY: No localStorage - token is in HttpOnly cookie
        // Backend sets the cookie, we just store user data in memory

        const user: User = {
          id: response.data.id!,
          name: response.data.name || email.split('@')[0],
          email: response.data.email || email,
          role: response.data.role || '' as any,
          department: response.data.department || '',
          is_admin: response.data.is_admin || false,
          is_active: response.data.is_active !== undefined ? response.data.is_active : true,
          // Include permissions array from backend
          permissions: response.data.permissions || [],
          // Include all additional fields from backend
          staff_id: response.data.staff_id,
          phone: response.data.phone,
          gender: response.data.gender,
          profile_photo: response.data.profile_photo,
          last_login_at: response.data.last_login_at
        };

        // Store user data in memory (not localStorage)
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

  /**
   * Clear user state without making API call (used by interceptor to avoid loops)
   */
  clearUserState(): void {
    this.currentUserSubject.next(null);
    this.initializationRequest$ = undefined;
  }

  logout(): void {
    // Call the backend logout endpoint
    const url = `${this.apiUrl}/api/logout/`;

    // SECURITY: withCredentials: true sends the HttpOnly cookie
    this.http.post(url, {}, { withCredentials: true }).pipe(
      catchError(error => {
        console.error('Logout failed', error);
        return of(null);
      })
    ).subscribe(() => {
      // SECURITY: Cookie is cleared by backend
      // Just clear user data from memory
      this.clearUserState();
      this.router.navigate(['/auth/login']);
    });
  }

  /**
   * SECURITY: Refresh JWT access token using refresh token from HttpOnly cookie
   * Called automatically when access token expires (401 error)
   */
  refreshToken(): Observable<boolean> {
    const url = `${this.apiUrl}/api/token/refresh/`;
    return this.http.post(url, {}, { withCredentials: true }).pipe(
      map(() => true),  // Refresh successful, new tokens set in cookies
      catchError(error => {
        console.error('Token refresh failed', error);
        return of(false);  // Refresh failed
      })
    );
  }

  isAuthenticated(): Observable<boolean> {
    return this.currentUser$.pipe(
      map(user => {
        // SECURITY: Check if user exists
        // Token validation is handled by backend
        return user !== null;
      })
    );
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

  isAdmin(): boolean {
    const user = this.currentUserSubject.value;
    return user?.is_admin || false;
  }

  // SECURITY: No getToken() method - token is in HttpOnly cookie
  // Token is automatically sent by browser with withCredentials: true

  // Get user profile
  getUserProfile(): Observable<User> {
    const url = `${this.apiUrl}/api/users/me/`;
    return this.http.get<User>(url, { withCredentials: true }).pipe(
      catchError(error => {
        console.error('Failed to get user profile', error);
        return throwError(() => new Error('Failed to get user profile'));
      })
    );
  }

  // Create a new user (admin only)
  createUser(userData: Partial<User>): Observable<User> {
    const url = `${this.apiUrl}/api/users/`;
    return this.http.post<User>(url, userData, { withCredentials: true }).pipe(
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
