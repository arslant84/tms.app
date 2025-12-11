import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { UserProfileComponent } from './components/user-profile/user-profile.component';
import { UserAdminComponent } from './components/user-admin/user-admin.component';
import { AuthGuard } from '../../core/guards/auth.guard';
import { UserRole } from '../../core/models/user.model';

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
    canActivate: [AuthGuard],
    data: { roles: ['admin'] }
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class UserManagementRoutingModule { }
