import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { FlightSearchComponent } from './components/flight-search/flight-search.component';
import { HotelSearchComponent } from './components/hotel-search/hotel-search.component';
import { BookingDetailComponent } from './components/booking-detail/booking-detail.component';

const routes: Routes = [
  {
    path: '',
    redirectTo: 'flights',
    pathMatch: 'full'
  },
  {
    path: 'flights',
    component: FlightSearchComponent
  },
  {
    path: 'hotels',
    component: HotelSearchComponent
  },
  {
    path: 'detail/:id',
    component: BookingDetailComponent
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class BookingPortalRoutingModule { }
