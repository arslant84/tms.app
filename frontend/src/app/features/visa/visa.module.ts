import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';

import { VisaRoutingModule } from './visa-routing.module';
import { VisaListComponent } from './components/visa-list/visa-list.component';
import { VisaDetailComponent } from './components/visa-detail/visa-detail.component';
import { VisaFormComponent } from './components/visa-form/visa-form.component';

@NgModule({
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    VisaRoutingModule,
    VisaListComponent,
    VisaDetailComponent,
    VisaFormComponent
  ]
})
export class VisaModule { }
