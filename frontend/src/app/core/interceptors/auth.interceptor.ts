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

  // SECURITY: Token is now in HttpOnly cookie (automatically sent by browser)
  // No need to manually add Authorization header

  // Clone the request and add withCredentials to include cookies
  const authReq = request.clone({
    withCredentials: true  // Enables sending/receiving cookies
  });

  // Handle the authenticated request
  return next(authReq).pipe(
    catchError((error: HttpErrorResponse) => {
      // Handle 401 Unauthorized errors (expired token or invalid session)
      if (error.status === 401) {
        // Logout the user and redirect to login
        authService.logout();
        router.navigate(['/auth/login']);
      }
      return throwError(() => error);
    })
  );
};
