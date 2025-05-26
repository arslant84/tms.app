import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { ExpenseListComponent } from './components/expense-list/expense-list.component';
import { ExpenseCreateComponent } from './components/expense-create/expense-create.component';

const routes: Routes = [
  {
    path: '',
    component: ExpenseListComponent
  },
  {
    path: 'create',
    component: ExpenseCreateComponent
  },
  {
    path: ':id',
    component: ExpenseCreateComponent
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class ExpenseClaimsRoutingModule { }
