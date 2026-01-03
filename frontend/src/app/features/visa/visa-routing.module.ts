import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { VisaListComponent } from './components/visa-list/visa-list.component';
import { VisaDetailComponent } from './components/visa-detail/visa-detail.component';
import { VisaFormComponent } from './components/visa-form/visa-form.component';

const routes: Routes = [
  {
    path: '',
    component: VisaListComponent
  },
  {
    path: 'new',
    component: VisaFormComponent
  },
  {
    path: ':id',
    component: VisaDetailComponent
  },
  {
    path: ':id/edit',
    component: VisaFormComponent
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class VisaRoutingModule { }
