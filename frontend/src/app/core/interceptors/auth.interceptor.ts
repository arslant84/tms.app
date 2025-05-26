import { inject } from '@angular/core';
import {
  HttpRequest,
  HttpHandlerFn,
  HttpInterceptorFn,
  HttpEvent,
  HttpErrorResponse
} from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { AuthService } from '../services/auth.service';
import { Router } from '@angular/router';

// Functional interceptor for Angular 16+
export const AuthInterceptor: HttpInterceptorFn = (
  request: HttpRequest<unknown>,
  next: HttpHandlerFn
): Observable<HttpEvent<unknown>> => {
  const authService = inject(AuthService);
  const router = inject(Router);
  
  // Get the auth token from the service
  const token = authService.getToken();

  // Skip adding token for login and public endpoints
  if (request.url.includes('/token') || request.url.includes('/public/')) {
    return next(request);
  }

  // Clone the request and add the token if available
  if (token) {
    // Make sure we're using the correct format for the Authorization header
    // The backend expects: Bearer <token>
    const authReq = request.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    });
    
    console.log('Adding auth token to request:', request.url);
    
    // Handle the authenticated request
    return next(authReq).pipe(
      catchError((error: HttpErrorResponse) => {
        // Handle 401 Unauthorized errors (expired token)
        if (error.status === 401) {
          // Logout the user and redirect to login
          authService.logout();
          router.navigate(['/auth/login']);
        }
        return throwError(() => error);
      })
    );
  }
  
  // If no token is available, just pass the request through
  return next(request);
};
