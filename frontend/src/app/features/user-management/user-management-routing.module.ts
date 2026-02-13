import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { UserProfileComponent } from './components/user-profile/user-profile.component';
import { UserAdminComponent } from './components/user-admin/user-admin.component';
import { PermissionGuard } from '../../core/guards/permission.guard';
import { Permission } from '../../core/models/permission.models';

const routes: Routes = [
  {
    path: '',
    redirectTo: 'profile',
    pathMatch: 'full'
  },
  {
    path: 'profile',
    component: UserProfileComponent
  },
  {
    path: 'admin',
    component: UserAdminComponent,
    canActivate: [PermissionGuard],
    data: {
      permissions: [Permission.MANAGE_USERS, Permission.SYSTEM_ADMIN],
      requireAll: false
    }
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class UserManagementRoutingModule { }
