import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { TrfListComponent } from './components/trf-list/trf-list.component';
import { TrfWizardComponent } from './components/trf-wizard/trf-wizard.component';
import { TrfDetailComponent } from './components/trf-detail/trf-detail.component';
import { TrfTypeSelectionComponent } from './components/trf-type-selection/trf-type-selection.component';

const routes: Routes = [
  {
    path: '',
    component: TrfListComponent,
  },
  {
    path: 'create',
    component: TrfTypeSelectionComponent,
  },
  {
    path: 'create/domestic',
    component: TrfWizardComponent,
  },
  {
    path: 'create/overseas',
    component: TrfWizardComponent,
  },
  {
    path: 'create/external-parties',
    component: TrfWizardComponent,
  },
  {
    path: 'edit/:id',
    component: TrfWizardComponent,
  },
  {
    path: ':id',
    component: TrfDetailComponent,
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class TrfManagementRoutingModule {}
