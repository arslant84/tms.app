import { HttpInterceptorFn, HttpRequest, HttpHandlerFn } from '@angular/common/http';

export const CsrfInterceptor: HttpInterceptorFn = (
  req: HttpRequest<unknown>,
  next: HttpHandlerFn
) => {
  // Only add CSRF token for state-changing methods
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(req.method)) {
    const csrfToken = getCookie('csrftoken');
    
    if (csrfToken) {
      req = req.clone({
        setHeaders: {
          'X-CSRFToken': csrfToken
        }
      });
    }
  }
  
  return next(req);
};

// Helper function to get cookie value
function getCookie(name: string): string | null {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop()?.split(';').shift() || null;
  }
  return null;
}
