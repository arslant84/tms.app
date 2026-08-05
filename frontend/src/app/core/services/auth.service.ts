import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, of, throwError } from 'rxjs';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Router } from '@angular/router';
import { map, tap, catchError, shareReplay, filter, take, switchMap } from 'rxjs/operators';
import { User, AuthResponse, LoginResult } from '../models/user.model';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private currentUserSubject = new BehaviorSubject<User | null>(null);
  public currentUser$ = this.currentUserSubject.asObservable();
  private apiUrl = environment.apiUrl.replace('/api', ''); // Remove /api suffix for backward compatibility
  private initializationRequest$?: Observable<User>;

  // Track whether initialization has completed
  private initializedSubject = new BehaviorSubject<boolean>(false);
  public initialized$ = this.initializedSubject.asObservable();

  // True while the bootstrap /me check is failing due to a network error (not an
  // actual "invalid session" response) and is being retried in the background.
  private connectionIssueSubject = new BehaviorSubject<boolean>(false);
  public connectionIssue$ = this.connectionIssueSubject.asObservable();
  private connectionRetryCount = 0;
  private readonly MAX_CONNECTION_RETRIES = 5;
  private readonly CONNECTION_RETRY_DELAY_MS = 10000; // ~50s of timed retries total

  constructor(private http: HttpClient, private router: Router) {
    // SECURITY: Token now stored in HttpOnly cookie (not accessible to JavaScript)
    // Try to load user data from backend on init
    this.initializeUser();

    // If a retry is pending when connectivity returns, don't wait for the next
    // timed retry - try immediately and give it a fresh retry budget.
    if (typeof window !== 'undefined') {
      window.addEventListener('online', () => {
        if (this.connectionIssueSubject.value) {
          this.connectionRetryCount = 0;
          this.initializationRequest$ = undefined;
          this.runInitializeUserRequest();
        }
      });
    }
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
    this.runInitializeUserRequest();
  }

  private runInitializeUserRequest(): void {
    // Create shared observable for initialization
    this.initializationRequest$ = this.http.get<User>(`${this.apiUrl}/api/users/me/`, { withCredentials: true }).pipe(
      tap((user) => {
        this.connectionRetryCount = 0;
        this.connectionIssueSubject.next(false);
        this.currentUserSubject.next(user);
        this.initializedSubject.next(true);
      }),
      catchError((error) => {
        // status 0 = no response reached the server at all (offline/DNS/timeout) -
        // that tells us nothing about session validity, so don't treat it as a
        // logout. A real 401/403 (or other server response) means the session
        // genuinely is invalid/expired - no point retrying that.
        const isNetworkError = error?.status === 0;

        if (isNetworkError && this.connectionRetryCount < this.MAX_CONNECTION_RETRIES) {
          this.connectionRetryCount++;
          this.connectionIssueSubject.next(true);
          this.initializationRequest$ = undefined; // allow the next attempt to run
          setTimeout(() => this.runInitializeUserRequest(), this.CONNECTION_RETRY_DELAY_MS);
          // Deliberately do NOT resolve initializedSubject yet - isAuthenticated()
          // stays pending until we either succeed or give up below.
          return of(null as any);
        }

        // Retries exhausted, or a genuine server-confirmed auth failure.
        this.connectionRetryCount = 0;
        this.connectionIssueSubject.next(false);
        this.currentUserSubject.next(null);
        this.initializedSubject.next(true);
        return of(null as any);
      }),
      shareReplay(1) // Share the result with all subscribers
    );

    // Subscribe to trigger the request
    this.initializationRequest$.subscribe();
  }

  /**
   * Wait for initialization to complete before returning user
   * This should be used by guards to ensure user data is loaded
   */
  waitForInit(): Observable<User | null> {
    return this.initialized$.pipe(
      filter(initialized => initialized),
      take(1),
      switchMap(() => of(this.currentUserSubject.value))
    );
  }

  private challengeToken: string | null = null;

  getChallengeToken(): string | null { return this.challengeToken; }

  private mapToUser(data: Partial<User>, fallbackEmail = ''): User {
    return {
      id: data.id!,
      name: data.name || fallbackEmail.split('@')[0],
      email: data.email || fallbackEmail,
      role: data.role || '' as any,
      department: data.department || '',
      is_admin: data.is_admin || false,
      is_active: data.is_active !== undefined ? data.is_active : true,
      permissions: data.permissions || [],
      staff_id: data.staff_id,
      phone: data.phone,
      position: data.position,
      gender: data.gender,
      profile_photo: data.profile_photo,
      last_login_at: data.last_login_at,
      password_change_required: data.password_change_required,
      mfa_enabled: data.mfa_enabled,
      mfa_setup_required: data.mfa_setup_required,
    };
  }

  login(email: string, password: string): Observable<LoginResult> {
    const url = `${this.apiUrl}/api/login/`;
    const body = { email, password };
    const headers = new HttpHeaders({ 'Content-Type': 'application/json' });

    return this.http.post<AuthResponse>(url, body, { headers, withCredentials: true }).pipe(
      map(response => {
        // MFA challenge — backend has NOT set cookies yet
        if (response.data.mfa_required) {
          this.challengeToken = response.data.challenge_token || null;
          return { type: 'mfa_required' as const };
        }

        // Normal login or privileged user needing MFA enrolment — cookies already set
        const user = this.mapToUser(response.data, email);
        this.currentUserSubject.next(user);
        this.initializedSubject.next(true);

        if (response.data.mfa_setup_required) {
          return { type: 'mfa_setup_required' as const, user };
        }

        return { type: 'success' as const, user };
      }),
      catchError(error => {
        let errorMessage = 'Login failed. Please check your credentials.';
        if (error.status === 0) {
          errorMessage = 'Cannot connect to the server. Please check your network connection.';
        } else if (error.status === 404) {
          errorMessage = 'Login service not found. Please contact the administrator.';
        } else if (error.status === 401) {
          errorMessage = 'Invalid email or password. Please try again.';
        } else if (error.error?.message) {
          errorMessage = error.error.message;
        }
        return throwError(() => new Error(errorMessage));
      })
    );
  }

  verifyMfa(challengeToken: string, otp: string): Observable<User> {
    return this.http.post<AuthResponse>(
      `${this.apiUrl}/api/mfa/verify/`,
      { challenge_token: challengeToken, otp },
      { withCredentials: true }
    ).pipe(
      map(response => {
        this.challengeToken = null;
        const user = this.mapToUser(response.data);
        this.currentUserSubject.next(user);
        this.initializedSubject.next(true);
        return user;
      }),
      catchError(error => throwError(() => new Error(
        error.error?.message || error.error?.detail || 'Invalid or expired code.'
      )))
    );
  }

  setupMfa(): Observable<{ secret: string; qr_uri: string }> {
    return this.http.get<{ success: boolean; data: { secret: string; qr_uri: string } }>(
      `${this.apiUrl}/api/mfa/setup/`,
      { withCredentials: true }
    ).pipe(
      map(response => response.data),
      catchError(error => throwError(() => new Error(
        error.error?.message || 'Failed to initialise MFA setup.'
      )))
    );
  }

  confirmMfa(otp: string): Observable<void> {
    return this.http.post<any>(
      `${this.apiUrl}/api/mfa/confirm/`,
      { otp },
      { withCredentials: true }
    ).pipe(
      tap(() => {
        const user = this.currentUserSubject.value;
        if (user) {
          this.currentUserSubject.next({ ...user, mfa_enabled: true, mfa_setup_required: false });
        }
      }),
      map(() => void 0),
      catchError(error => throwError(() => new Error(
        error.error?.message || 'Invalid code. Please try again.'
      )))
    );
  }

  disableMfa(password: string, otp: string): Observable<void> {
    return this.http.post<any>(
      `${this.apiUrl}/api/mfa/disable/`,
      { password, otp },
      { withCredentials: true }
    ).pipe(
      tap(() => {
        const user = this.currentUserSubject.value;
        if (user) {
          this.currentUserSubject.next({ ...user, mfa_enabled: false });
        }
      }),
      map(() => void 0),
      catchError(error => throwError(() => new Error(
        error.error?.message || 'Failed to disable MFA.'
      )))
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
    // Wait for initialization before checking authentication
    return this.initialized$.pipe(
      filter(initialized => initialized),
      take(1),
      switchMap(() => this.currentUser$),
      take(1),
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
   * Register a new user account (self-registration)
   * Note: Users cannot select their own role - admin assigns roles later
   */
  register(userData: {
    email: string;
    name: string;
    password: string;
    password_confirm: string;
    staff_id?: string;
    phone?: string;
    department: string;
    gender?: string;
    profile_photo?: string;
  }): Observable<{ success: boolean; message: string; data?: any }> {
    return this.http.post<any>(`${this.apiUrl}/api/register/`, userData).pipe(
      map(response => {
        // Handle standardized response format
        if (response.success) {
          return {
            success: true,
            message: response.message || 'Registration successful',
            data: response.data
          };
        }
        return response;
      }),
      catchError(error => {
        // Extract error message
        const message = this.getErrorMessage(error);
        return throwError(() => ({ success: false, message, error }));
      })
    );
  }

  private getErrorMessage(error: any): string {
    if (error.error?.message) {
      return error.error.message;
    }
    if (error.error?.errors) {
      // Extract first field error
      const firstError = Object.values(error.error.errors)[0];
      if (Array.isArray(firstError)) {
        return firstError[0];
      }
    }
    return 'Registration failed. Please try again.';
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
