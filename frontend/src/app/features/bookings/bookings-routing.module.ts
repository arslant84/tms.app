import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { FlightListComponent } from '../admin/flight-list/flight-list.component';
import { FlightDetailComponent } from '../admin/flight-detail/flight-detail.component';
import { FlightCreateComponent } from '../admin/flight-create/flight-create.component';

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
