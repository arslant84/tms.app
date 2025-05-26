import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { TrfListComponent } from './components/trf-list/trf-list.component';
import { TrfCreateComponent } from './components/trf-create/trf-create.component';
import { TrfDetailComponent } from './components/trf-detail/trf-detail.component';

const routes: Routes = [
  {
    path: '',
    component: TrfListComponent
  },
  {
    path: 'create',
    component: TrfCreateComponent
  },
  {
    path: ':id',
    component: TrfDetailComponent
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class TrfManagementRoutingModule { }
