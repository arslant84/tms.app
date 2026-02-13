import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { TransportListComponent } from './components/transport-list/transport-list.component';
import { TransportDetailComponent } from './components/transport-detail/transport-detail.component';
import { TransportCreateComponent } from './components/transport-create/transport-create.component';

const routes: Routes = [
  {
    path: '',
    component: TransportListComponent
  },
  {
    path: 'create',
    component: TransportCreateComponent
  },
  {
    path: 'edit/:id',
    component: TransportCreateComponent
  },
  {
    path: ':id',
    component: TransportDetailComponent
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class TransportRoutingModule { }
