import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';

import { AccommodationRoutingModule } from './accommodation-routing.module';
import { AccommodationListComponent } from './components/accommodation-list/accommodation-list.component';
import { AccommodationDetailComponent } from './components/accommodation-detail/accommodation-detail.component';
import { AccommodationCreateComponent } from './components/accommodation-create/accommodation-create.component';

@NgModule({
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    AccommodationRoutingModule,
    AccommodationListComponent,
    AccommodationDetailComponent,
    AccommodationCreateComponent
  ]
})
export class AccommodationModule { }
