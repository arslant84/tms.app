import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';

import { BookingsRoutingModule } from './bookings-routing.module';
import { FlightListComponent } from './components/flight-list/flight-list.component';
import { FlightDetailComponent } from './components/flight-detail/flight-detail.component';
import { FlightCreateComponent } from './components/flight-create/flight-create.component';

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
