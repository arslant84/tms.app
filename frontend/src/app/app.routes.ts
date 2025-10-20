import { Routes } from '@angular/router';
import { AuthGuard } from './core/guards/auth.guard';
import { UserRole } from './core/models/user.model';
import { MainLayoutComponent } from './components/main-layout/main-layout.component';
import { TravelRequestWizardComponent } from './features/requests/travel/travel-request-wizard.component';
import { AccommodationRequestComponent } from './features/requests/accommodation/accommodation-request.component';
import { TransportRequestComponent } from './features/requests/transport/transport-request.component';
import { VisaRequestComponent } from './features/requests/visa/visa-request.component';
import { ExpenseClaimComponent } from './features/requests/expense/expense-claim.component';
import { PendingApprovalsComponent } from './features/approvals/pending/pending-approvals.component';
import { ClerkPanelComponent } from './features/admin/clerk-panel/clerk-panel.component';
import { AdminReportsComponent } from './features/admin/reports/admin-reports.component';
import { ClaimsAdminComponent } from './features/admin/claims-admin/claims-admin.component';
import { TransportAdminComponent } from './features/admin/transport-admin/transport-admin.component';
import { FlightsAdminComponent } from './features/admin/flights-admin/flights-admin.component';
import { AccommodationAdminComponent } from './features/admin/accommodation-admin/accommodation-admin.component';
import { VisaAdminComponent } from './features/admin/visa-admin/visa-admin.component';
import { SystemSettingsComponent } from './features/admin/system-settings/system-settings.component';
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
          { path: 'reports', component: AdminReportsComponent },
          { path: 'approvals', component: PendingApprovalsComponent },
          { path: 'claims', component: ClaimsAdminComponent },
          { path: 'transport', component: TransportAdminComponent },
          { path: 'flights', component: FlightsAdminComponent },
          { path: 'accommodation', component: AccommodationAdminComponent },
          { path: 'visa', component: VisaAdminComponent },
          { path: 'settings', component: SystemSettingsComponent }
        ],
        data: { roles: [UserRole.ADMIN, UserRole.TICKETING_CLERK, UserRole.HOD, UserRole.FOCAL] }
      },
      // TRF Management
      {
        path: 'trf',
        loadChildren: () => import('./features/trf-management/trf-management.module').then(m => m.TrfManagementModule)
      },

      // Expense Claims
      {
        path: 'expenses',
        loadChildren: () => import('./features/expense-claims/expense-claims.module').then(m => m.ExpenseClaimsModule)
      },

      // Transport Management
      {
        path: 'transport',
        loadChildren: () => import('./features/transport/transport.module').then(m => m.TransportModule)
      },

      // Accommodation Management
      {
        path: 'accommodation',
        loadChildren: () => import('./features/accommodation/accommodation.module').then(m => m.AccommodationModule)
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

      // Notifications
      {
        path: 'notifications',
        loadChildren: () => import('./features/notifications/notifications.module').then(m => m.NotificationsModule)
      },

      // Bookings (Flights & Hotels)
      {
        path: 'bookings',
        loadChildren: () => import('./features/bookings/bookings.module').then(m => m.BookingsModule)
      },

      // Visa Management
      {
        path: 'visa',
        loadChildren: () => import('./visa/visa.module').then(m => m.VisaModule)
      }
    ]
  },
  { 
    path: '**', 
    redirectTo: 'dashboard' 
  }
];
