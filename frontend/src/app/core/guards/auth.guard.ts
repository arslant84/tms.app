import { Injectable } from '@angular/core';
import { CanActivate, ActivatedRouteSnapshot, RouterStateSnapshot, Router, UrlTree } from '@angular/router';
import { Observable } from 'rxjs';
import { AuthService } from '../services/auth.service';
import { UserRole } from '../models/user.model';
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
          // Check if route has required roles
          const roleStrings = route.data['roles'] as Array<string>;
          if (roleStrings) {
            // Convert string[] to UserRole[]
            const requiredRoles = roleStrings.map(role => role as UserRole);
            // Check if user has required role
            const hasRequiredRole = this.authService.hasRole(requiredRoles);
            if (!hasRequiredRole) {
              // Redirect to unauthorized page if user doesn't have required role
              return this.router.createUrlTree(['/unauthorized']);
            }
          }
          return true;
        }

        // Redirect to login page if not authenticated
        return this.router.createUrlTree(['/auth/login'], { queryParams: { returnUrl: state.url } });
      })
    );
  }
}
