import { Routes } from '@angular/router';
import { AuthGuard } from './core/guards/auth.guard';
import { AdminMenuGuard, PermissionGuard } from './core/guards/permission.guard';
import { Permission } from './core/models/permission.models';
import { MainLayoutComponent } from './components/main-layout/main-layout.component';
import { PendingApprovalsComponent } from './features/approvals/pending/pending-approvals.component';
import { PendingApprovalsComponent as UnifiedApprovalsComponent } from './features/admin/approvals/components/pending-approvals/pending-approvals.component';
import { ClerkPanelComponent } from './features/admin/clerk-panel/clerk-panel.component';
import { AdminReportsComponent } from './features/admin/reports/admin-reports.component';
import { TransportAdminComponent } from './features/admin/transport/components/transport-admin.component';
import { TransportProcessingComponent } from './features/admin/transport/components/transport-processing.component';
import { FlightsAdminOverviewComponent } from './features/admin/flights/components/flights-admin-overview.component';
import { FlightsProcessingComponent } from './features/admin/flights/components/flights-processing.component';
import { AccommodationAdminComponent } from './features/admin/accommodation/components/accommodation-admin.component';
import { AccommodationProcessingComponent } from './features/admin/accommodation/components/accommodation-processing.component';
import { VisaAdminComponent } from './features/admin/visa/components/visa-admin.component';
import { VisaProcessingComponent } from './features/admin/visa/components/visa-processing.component';
import { CombinedAdminComponent } from './features/admin/combined/components/combined-admin.component';
import { CombinedProcessingComponent } from './features/admin/combined/components/combined-processing.component';
import { MealAdminComponent } from './features/admin/meal/components/meal-admin.component';
import { SystemSettingsComponent } from './features/admin/settings/system-settings.component';
import { TmsApp_Admin_SystemSettings_NotificationTemplatesComponent } from './features/admin/settings/notification-templates/notification-templates.component';
import { CombinedRequestWizardComponent } from './features/requests/combined/combined-request-wizard.component';
import { CombinedListComponent } from './features/requests/combined/combined-list.component';
import { CombinedDetailComponent } from './features/requests/combined/combined-detail.component';

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
      // Admin approvals - separate route with its own guard (bypasses parent /admin guard)
      {
        path: 'admin/approvals',
        component: UnifiedApprovalsComponent,
        canActivate: [PermissionGuard],
        data: {
          permissions: [
            Permission.VIEW_PENDING_APPROVALS,
            Permission.APPROVE_TRF,
            Permission.APPROVE_TRANSPORT,
            Permission.APPROVE_VISA,
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
          {
            path: 'reports',
            component: AdminReportsComponent,
            canActivate: [PermissionGuard],
            data: {
              permissions: [
                Permission.GENERATE_ADMIN_REPORTS,
                Permission.EXPORT_DATA,
                Permission.SYSTEM_ADMIN
              ]
            }
          },
          // Note: /admin/approvals is handled by a separate route above to bypass parent guard
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
            path: 'combined',
            canActivate: [AdminMenuGuard],
            data: { adminModule: 'combined' },
            children: [
              { path: '', component: CombinedAdminComponent },
              { path: 'processing', component: CombinedProcessingComponent }
            ]
          },
          {
            path: 'meal',
            canActivate: [AdminMenuGuard],
            data: { adminModule: 'meal' },
            children: [{ path: '', component: MealAdminComponent }]
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
        // Admin routes require ANY admin module permission, system admin, reporting, or approval permission
        canActivate: [PermissionGuard],
        data: {
          permissions: [
            Permission.SYSTEM_ADMIN,
            Permission.VIEW_ADMIN_FLIGHTS,
            Permission.VIEW_ADMIN_ACCOMMODATION,
            Permission.VIEW_ADMIN_VISA,
            Permission.VIEW_ADMIN_TRANSPORT,
            Permission.VIEW_ADMIN_COMBINED,
            Permission.VIEW_ADMIN_MEAL,
            Permission.MANAGE_USERS,
            Permission.GENERATE_ADMIN_REPORTS,
            Permission.EXPORT_DATA,
            Permission.VIEW_PENDING_APPROVALS,
            Permission.APPROVE_TRF,
            Permission.APPROVE_TRANSPORT,
            Permission.APPROVE_VISA,
            Permission.APPROVE_ACCOMMODATION,
            Permission.APPROVE_COMBINED
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
      },

      // Combined Request Management
      {
        path: 'combined',
        children: [
          { path: '', component: CombinedListComponent },
          { path: 'new', component: CombinedRequestWizardComponent },
          { path: 'edit/:id', component: CombinedRequestWizardComponent },
          { path: ':id', component: CombinedDetailComponent }
        ]
      },

      // Secondary Settings entry from avatar menu
      { path: 'settings', component: SystemSettingsComponent }
    ]
  },
  { 
    path: '**', 
    redirectTo: 'dashboard' 
  }
];
