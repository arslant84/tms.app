import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { NotificationListComponent } from './components/notification-list/notification-list.component';
import { NotificationPreferencesComponent } from './components/notification-preferences/notification-preferences.component';

const routes: Routes = [
  {
    path: '',
    component: NotificationListComponent
  },
  {
    path: 'preferences',
    component: NotificationPreferencesComponent
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class NotificationsRoutingModule { }
