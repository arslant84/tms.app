import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';

import { TransportRoutingModule } from './transport-routing.module';
import { TransportListComponent } from './components/transport-list/transport-list.component';
import { TransportDetailComponent } from './components/transport-detail/transport-detail.component';
import { TransportCreateComponent } from './components/transport-create/transport-create.component';

@NgModule({
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    TransportRoutingModule,
    TransportListComponent,
    TransportDetailComponent,
    TransportCreateComponent
  ]
})
export class TransportModule { }
