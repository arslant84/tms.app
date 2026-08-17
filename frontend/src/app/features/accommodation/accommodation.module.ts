import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';

import { AccommodationRoutingModule } from './accommodation-routing.module';
import { AccommodationDetailComponent } from './components/accommodation-detail/accommodation-detail.component';

@NgModule({
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    AccommodationRoutingModule,
    AccommodationDetailComponent
  ]
})
export class AccommodationModule { }
