import { inject } from '@angular/core';
import {
  HttpRequest,
  HttpHandlerFn,
  HttpInterceptorFn,
  HttpEvent,
  HttpErrorResponse,
} from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, switchMap } from 'rxjs/operators';
import { AuthService } from '../services/auth.service';
import { Router } from '@angular/router';

// Functional interceptor for Angular 16+
export const AuthInterceptor: HttpInterceptorFn = (
  request: HttpRequest<unknown>,
  next: HttpHandlerFn
): Observable<HttpEvent<unknown>> => {
  const authService = inject(AuthService);
  const router = inject(Router);

  // SECURITY: Token is now in HttpOnly cookie (automatically sent by browser)
  // No need to manually add Authorization header

  // Skip sending credentials for public endpoints
  const isPublicEndpoint =
    request.url.includes('/api/register/') ||
    request.url.includes('/api/departments/active/') ||
    request.url.includes('/api/login/') ||
    request.url.includes('/api/password/reset/');

  // Clone the request and add withCredentials to include cookies (except for public endpoints)
  const authReq = request.clone({
    withCredentials: !isPublicEndpoint, // Only send cookies for protected endpoints
  });

  // Handle the authenticated request
  return next(authReq).pipe(
    catchError((error: HttpErrorResponse) => {
      // Handle 401 Unauthorized errors (expired token or invalid session)
      if (error.status === 401) {
        // Endpoints where a 401 should never trigger a redirect - either they're public
        // (no session to lose) or, for /api/users/me/, the app's own bootstrap check
        // (AuthGuard, not this interceptor, decides what to do once auth state settles).
        const noRedirectOnFailure =
          request.url.includes('/api/users/me/') ||
          request.url.includes('/api/password/reset/') ||
          request.url.includes('/api/logout/') ||
          request.url.includes('/api/register/') ||
          request.url.includes('/api/departments/active/');

        // Endpoints that must never attempt a token refresh, to avoid infinite loops.
        // Note /api/users/me/ is deliberately NOT here: it's the bootstrap "am I still
        // logged in" check that runs on every page load, and its access-token cookie is
        // only 1 hour old - without attempting a refresh here, any refresh after the
        // access token (but not the 7-day refresh token) expires forced a full logout.
        const skipRefreshEntirely =
          request.url.includes('/api/login/') ||
          request.url.includes('/api/logout/') ||
          request.url.includes('/api/token/refresh/') ||
          request.url.includes('/api/password/reset/') ||
          request.url.includes('/api/register/') ||
          request.url.includes('/api/departments/active/');

        if (skipRefreshEntirely) {
          if (noRedirectOnFailure) {
            return throwError(() => error);
          }
          // For login/refresh failures, clear state and redirect (don't call logout to avoid loop)
          authService.clearUserState();
          router.navigate(['/auth/login']);
          return throwError(() => error);
        }

        // SECURITY: Try to refresh the JWT token automatically
        return authService.refreshToken().pipe(
          switchMap((success: boolean) => {
            if (success) {
              // Refresh successful - retry the original request
              return next(authReq);
            } else if (noRedirectOnFailure) {
              return throwError(() => error);
            } else {
              // Refresh failed - clear state and redirect (don't call logout to avoid loop)
              authService.clearUserState();
              router.navigate(['/auth/login']);
              return throwError(() => error);
            }
          })
        );
      }
      return throwError(() => error);
    })
  );
};
