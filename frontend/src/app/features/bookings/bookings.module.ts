import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';

import { BookingsRoutingModule } from './bookings-routing.module';
import { FlightListComponent } from '../admin/flight-list/flight-list.component';
import { FlightDetailComponent } from '../admin/flight-detail/flight-detail.component';
import { FlightCreateComponent } from '../admin/flight-create/flight-create.component';

@NgModule({
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    BookingsRoutingModule,
    FlightListComponent,
    FlightDetailComponent,
    FlightCreateComponent
  ]
})
export class BookingsModule { }
