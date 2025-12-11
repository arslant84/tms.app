import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AccommodationListComponent } from './components/accommodation-list/accommodation-list.component';
import { AccommodationDetailComponent } from './components/accommodation-detail/accommodation-detail.component';
import { AccommodationCreateComponent } from './components/accommodation-create/accommodation-create.component';

const routes: Routes = [
  {
    path: '',
    component: AccommodationListComponent
  },
  {
    path: 'create',
    component: AccommodationCreateComponent
  },
  {
    path: 'edit/:id',
    component: AccommodationCreateComponent
  },
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
