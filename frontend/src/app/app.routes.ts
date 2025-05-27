import { Routes } from '@angular/router';
import { AuthGuard } from './core/guards/auth.guard';
import { UserRole } from './core/models/user.model';
import { StyleGuideComponent } from './components/style-guide/style-guide.component';
import { MainLayoutComponent } from './components/main-layout/main-layout.component';
import { TravelRequestWizardComponent } from './features/requests/travel/travel-request-wizard.component';
import { AccommodationRequestComponent } from './features/requests/accommodation/accommodation-request.component';
import { TransportRequestComponent } from './features/requests/transport/transport-request.component';
import { VisaRequestComponent } from './features/requests/visa/visa-request.component';
import { ExpenseClaimComponent } from './features/requests/expense/expense-claim.component';
import { PendingApprovalsComponent } from './features/approvals/pending/pending-approvals.component';
import { ClerkPanelComponent } from './features/admin/clerk-panel/clerk-panel.component';
import { AdminReportsComponent } from './features/admin/reports/admin-reports.component';
import { SuccessComponent } from './features/requests/success/success.component';
import { RequestTypeSelectionComponent } from './features/requests/components/request-type-selection/request-type-selection.component';

export const routes: Routes = [
  { 
    path: '', 
    redirectTo: 'dashboard', 
    pathMatch: 'full' 
  },
  {
    path: 'auth',
    loadChildren: () => import('./features/auth/auth.module').then(m => m.AuthModule)
  },
  {
    path: '',
    component: MainLayoutComponent,
    canActivate: [AuthGuard],
    children: [
      // Dashboard route
      {
        path: 'dashboard',
        loadChildren: () => import('./features/dashboard/dashboard.module').then(m => m.DashboardModule)
      },
      // Requests routes
      {
        path: 'requests',
        children: [
          { path: '', redirectTo: 'select-type', pathMatch: 'full' },
          { path: 'select-type', component: RequestTypeSelectionComponent },
          { 
            path: 'travel', 
            children: [
              { path: '', component: TravelRequestWizardComponent },
              { path: 'domestic', component: TravelRequestWizardComponent },
              { path: 'international', component: TravelRequestWizardComponent },
              { path: 'home-leave', component: TravelRequestWizardComponent },
              { path: 'external', component: TravelRequestWizardComponent }
            ]
          },
          { path: 'accommodation', component: AccommodationRequestComponent },
          { path: 'transport', component: TransportRequestComponent },
          { path: 'visa', component: VisaRequestComponent },
          { path: 'expense', component: ExpenseClaimComponent },
          { path: 'success', component: SuccessComponent }
        ]
      },
      // Approvals routes
      {
        path: 'approvals',
        children: [
          { path: '', redirectTo: 'pending', pathMatch: 'full' },
          { path: 'pending', component: PendingApprovalsComponent },
          // Approval history will be added here
        ],
        data: { roles: [UserRole.HOD, UserRole.FOCAL, UserRole.ADMIN] }
      },
      // Admin routes
      {
        path: 'admin',
        children: [
          { path: '', redirectTo: 'clerk-panel', pathMatch: 'full' },
          { path: 'clerk-panel', component: ClerkPanelComponent },
          { path: 'reports', component: AdminReportsComponent }
        ],
        data: { roles: [UserRole.ADMIN, UserRole.TICKETING_CLERK] }
      },
      // TRF Management
      {
        path: 'trf',
        loadChildren: () => import('./features/trf-management/trf-management.module').then(m => m.TrfManagementModule)
      },
      // Booking Portal
      {
        path: 'booking',
        loadChildren: () => import('./features/booking-portal/booking-portal.module').then(m => m.BookingPortalModule)
      },
      // Expense Claims
      {
        path: 'expenses',
        loadChildren: () => import('./features/expense-claims/expense-claims.module').then(m => m.ExpenseClaimsModule)
      },
      // Travel Insights
      {
        path: 'insights',
        loadChildren: () => import('./features/travel-insights/travel-insights.module').then(m => m.TravelInsightsModule)
      },
      // User Management
      {
        path: 'users',
        loadChildren: () => import('./features/user-management/user-management.module').then(m => m.UserManagementModule),
        data: { roles: [UserRole.HOD, UserRole.FOCAL] }
      },
      // User Profile
      {
        path: 'profile',
        loadChildren: () => import('./features/user-management/user-management.module').then(m => m.UserManagementModule)
      },
      // Style Guide
      {
        path: 'style-guide',
        component: StyleGuideComponent
      }
    ]
  },
  { 
    path: '**', 
    redirectTo: 'dashboard' 
  }
];
