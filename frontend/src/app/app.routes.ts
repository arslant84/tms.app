import { Routes } from '@angular/router';
import { AuthGuard } from './core/guards/auth.guard';
import { UserRole } from './core/models/user.model';
import { StyleGuideComponent } from './components/style-guide/style-guide.component';

export const routes: Routes = [
  { 
    path: '', 
    redirectTo: 'auth/login', 
    pathMatch: 'full' 
  },
  {
    path: 'dashboard',
    loadChildren: () => import('./features/dashboard/dashboard.module').then(m => m.DashboardModule),
    canActivate: [AuthGuard]
  },
  {
    path: 'trf',
    loadChildren: () => import('./features/trf-management/trf-management.module').then(m => m.TrfManagementModule),
    canActivate: [AuthGuard]
  },
  {
    path: 'booking',
    loadChildren: () => import('./features/booking-portal/booking-portal.module').then(m => m.BookingPortalModule),
    canActivate: [AuthGuard]
  },
  {
    path: 'expenses',
    loadChildren: () => import('./features/expense-claims/expense-claims.module').then(m => m.ExpenseClaimsModule),
    canActivate: [AuthGuard]
  },
  {
    path: 'insights',
    loadChildren: () => import('./features/travel-insights/travel-insights.module').then(m => m.TravelInsightsModule),
    canActivate: [AuthGuard]
  },
  {
    path: 'users',
    loadChildren: () => import('./features/user-management/user-management.module').then(m => m.UserManagementModule),
    canActivate: [AuthGuard],
    data: { roles: [UserRole.HOD, UserRole.FOCAL] }
  },
  {
    path: 'profile',
    loadChildren: () => import('./features/user-management/user-management.module').then(m => m.UserManagementModule),
    canActivate: [AuthGuard]
  },
  {
    path: 'auth',
    loadChildren: () => import('./features/auth/auth.module').then(m => m.AuthModule)
  },
  {
    path: 'style-guide',
    component: StyleGuideComponent
  },
  { 
    path: '**', 
    redirectTo: 'dashboard' 
  }
];
