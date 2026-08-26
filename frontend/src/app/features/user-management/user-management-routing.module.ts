import { NgModule } from '@angular/core';
import { RouterModule, type Routes } from '@angular/router';
import { PermissionGuard } from '../../core/guards/permission.guard';
import { Permission } from '../../core/models/permission.models';
import { UserAdminComponent } from './components/user-admin/user-admin.component';
import { UserProfileComponent } from './components/user-profile/user-profile.component';

const routes: Routes = [
  {
    path: '',
    redirectTo: 'profile',
    pathMatch: 'full',
  },
  {
    path: 'profile',
    component: UserProfileComponent,
  },
  {
    path: 'admin',
    component: UserAdminComponent,
    canActivate: [PermissionGuard],
    data: {
      permissions: [Permission.MANAGE_USERS, Permission.SYSTEM_ADMIN],
      requireAll: false,
    },
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class UserManagementRoutingModule {}
