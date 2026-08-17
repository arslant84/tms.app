import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AccommodationDetailComponent } from './components/accommodation-detail/accommodation-detail.component';

// Accommodation requests are created exclusively via the Domestic TSR wizard.
// Only the read-only detail view remains routable, linked from the TRF detail page.
const routes: Routes = [
  {
    path: ':id',
    component: AccommodationDetailComponent
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class AccommodationRoutingModule { }
