import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';

import { NotificationsRoutingModule } from './notifications-routing.module';
import { NotificationListComponent } from './components/notification-list/notification-list.component';
import { NotificationPreferencesComponent } from './components/notification-preferences/notification-preferences.component';

@NgModule({
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    NotificationsRoutingModule,
    NotificationListComponent,
    NotificationPreferencesComponent
  ]
})
export class NotificationsModule { }
