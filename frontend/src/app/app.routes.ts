import { Routes } from '@angular/router';
import { AuthGuard } from './core/guards/auth.guard';
import { AdminMenuGuard, PermissionGuard } from './core/guards/permission.guard';
import { UserRole } from './core/models/user.model';
import { Permission } from './core/models/permission.models';
import { MainLayoutComponent } from './components/main-layout/main-layout.component';
import { TravelRequestWizardComponent } from './features/requests/travel/travel-request-wizard.component';
import { AccommodationRequestComponent } from './features/requests/accommodation/accommodation-request.component';
import { TransportRequestComponent } from './features/requests/transport/transport-request.component';
import { VisaRequestComponent } from './features/visa/components/visa-request/visa-request.component';
import { PendingApprovalsComponent } from './features/approvals/pending/pending-approvals.component';
import { PendingApprovalsComponent as UnifiedApprovalsComponent } from './features/admin/approvals/components/pending-approvals/pending-approvals.component';
import { ClerkPanelComponent } from './features/admin/clerk-panel/clerk-panel.component';
import { AdminReportsComponent } from './features/admin/reports/admin-reports.component';
import { TransportAdminComponent } from './features/admin/transport-admin/transport-admin.component';
import { TransportProcessingComponent } from './features/admin/transport-processing/transport-processing.component';
import { FlightsAdminComponent } from './features/admin/flights-admin/flights-admin.component';
import { FlightsAdminOverviewComponent } from './features/admin/flights-admin-overview/flights-admin-overview.component';
import { FlightsProcessingComponent } from './features/admin/flights-processing/flights-processing.component';
import { AccommodationAdminComponent } from './features/admin/accommodation-admin/accommodation-admin.component';
import { AccommodationProcessingComponent } from './features/admin/accommodation-processing/accommodation-processing.component';
import { VisaAdminComponent } from './features/admin/visa-admin/visa-admin.component';
import { VisaProcessingComponent } from './features/admin/visa-processing/visa-processing.component';
import { SystemSettingsComponent } from './features/admin/system-settings/system-settings.component';
import { TmsApp_Admin_SystemSettings_NotificationTemplatesComponent } from './features/admin/system-settings/notification-templates/notification-templates.component';
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
          { path: 'success', component: SuccessComponent }
        ]
      },
      // Approvals routes (for users with approval permissions)
      {
        path: 'approvals',
        children: [
          { path: '', redirectTo: 'pending', pathMatch: 'full' },
          { path: 'pending', component: PendingApprovalsComponent },
          // Approval history will be added here
        ],
        canActivate: [PermissionGuard],
        data: {
          permissions: [
            Permission.VIEW_PENDING_APPROVALS,
            Permission.APPROVE_TRF,
            Permission.APPROVE_VISA,
            Permission.APPROVE_TRANSPORT,
            Permission.APPROVE_ACCOMMODATION
          ]
        }
      },
      // Admin routes
      {
        path: 'admin',
        children: [
          { path: '', redirectTo: 'clerk-panel', pathMatch: 'full' },
          { path: 'clerk-panel', component: ClerkPanelComponent },
          { path: 'reports', component: AdminReportsComponent },
          { path: 'approvals', component: UnifiedApprovalsComponent },
          {
            path: 'transport',
            canActivate: [AdminMenuGuard],
            data: { adminModule: 'transport' },
            children: [
              { path: '', component: TransportAdminComponent },
              { path: 'processing', component: TransportProcessingComponent }
            ]
          },
          {
            path: 'flights',
            canActivate: [AdminMenuGuard],
            data: { adminModule: 'flights' },
            children: [
              { path: '', component: FlightsAdminOverviewComponent },
              { path: 'processing', component: FlightsProcessingComponent }
            ]
          },
          {
            path: 'accommodation',
            canActivate: [AdminMenuGuard],
            data: { adminModule: 'accommodation' },
            children: [
              { path: '', component: AccommodationAdminComponent },
              { path: 'processing', component: AccommodationProcessingComponent }
            ]
          },
          {
            path: 'visa',
            canActivate: [AdminMenuGuard],
            data: { adminModule: 'visa' },
            children: [
              { path: '', component: VisaAdminComponent },
              { path: 'processing', component: VisaProcessingComponent }
            ]
          },
          {
            path: 'settings',
            component: SystemSettingsComponent,
            canActivate: [PermissionGuard],
            data: { permissions: [Permission.VIEW_SYSTEM_SETTINGS, Permission.SYSTEM_ADMIN] }
          },
          {
            path: 'settings/notifications',
            component: TmsApp_Admin_SystemSettings_NotificationTemplatesComponent,
            canActivate: [PermissionGuard],
            data: { permissions: [Permission.MANAGE_NOTIFICATIONS, Permission.SYSTEM_ADMIN] }
          }
        ],
        // Admin routes require ANY admin module permission or system admin
        canActivate: [PermissionGuard],
        data: {
          permissions: [
            Permission.SYSTEM_ADMIN,
            Permission.VIEW_ADMIN_FLIGHTS,
            Permission.VIEW_ADMIN_ACCOMMODATION,
            Permission.VIEW_ADMIN_VISA,
            Permission.VIEW_ADMIN_TRANSPORT,
            Permission.MANAGE_USERS
          ]
        }
      },
      // TRF Management
      {
        path: 'trf',
        loadChildren: () => import('./features/trf-management/trf-management.module').then(m => m.TrfManagementModule)
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

      // User Management (Admins only with manage_users permission)
      {
        path: 'users',
        loadChildren: () => import('./features/user-management/user-management.module').then(m => m.UserManagementModule),
        canActivate: [PermissionGuard],
        data: {
          permissions: [Permission.MANAGE_USERS, Permission.SYSTEM_ADMIN]
        }
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
        loadChildren: () => import('./features/visa/visa.module').then(m => m.VisaModule)
      }
      ,
      // Secondary Settings entry from avatar menu
      { path: 'settings', component: SystemSettingsComponent }
    ]
  },
  { 
    path: '**', 
    redirectTo: 'dashboard' 
  }
];
