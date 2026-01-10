import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { FlightListComponent } from '../admin/flights/components/flight-list.component';
import { FlightDetailComponent } from '../admin/flights/components/flight-detail.component';
import { FlightCreateComponent } from '../admin/flights/components/flight-create.component';

const routes: Routes = [
  {
    path: '',
    redirectTo: 'flights',
    pathMatch: 'full'
  },
  {
    path: 'flights',
    children: [
      {
        path: '',
        component: FlightListComponent
      },
      {
        path: 'create',
        component: FlightCreateComponent
      },
      {
        path: 'edit/:id',
        component: FlightCreateComponent
      },
      {
        path: ':id',
        component: FlightDetailComponent
      }
    ]
  }
  // Hotel bookings routes can be added here later
  // {
  //   path: 'hotels',
  //   children: [...]
  // }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class BookingsRoutingModule { }
