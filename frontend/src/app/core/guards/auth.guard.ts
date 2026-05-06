import { Injectable } from '@angular/core';
import { CanActivate, ActivatedRouteSnapshot, RouterStateSnapshot, Router, UrlTree } from '@angular/router';
import { Observable } from 'rxjs';
import { AuthService } from '../services/auth.service';
import { map } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class AuthGuard implements CanActivate {
  
  constructor(private authService: AuthService, private router: Router) {}
  
  canActivate(
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ): Observable<boolean | UrlTree> | Promise<boolean | UrlTree> | boolean | UrlTree {
    return this.authService.isAuthenticated().pipe(
      map(isAuthenticated => {
        // If user is authenticated, allow access
        if (isAuthenticated) {
          const user = this.authService.getCurrentUser();

          if (user?.password_change_required && !state.url.includes('/auth/change-password')) {
            return this.router.createUrlTree(['/auth/change-password']);
          }

          if (user?.mfa_setup_required && !state.url.includes('/auth/mfa-setup')) {
            return this.router.createUrlTree(['/auth/mfa-setup']);
          }

          return true;
        }

        // Redirect to login page if not authenticated
        return this.router.createUrlTree(['/auth/login'], { queryParams: { returnUrl: state.url } });
      })
    );
  }
}
