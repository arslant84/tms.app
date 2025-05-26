import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { InsightsDashboardComponent } from './components/insights-dashboard/insights-dashboard.component';

const routes: Routes = [
  {
    path: '',
    component: InsightsDashboardComponent
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class TravelInsightsRoutingModule { }
