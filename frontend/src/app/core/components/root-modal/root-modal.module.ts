import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RootModalComponent } from './root-modal.component';

@NgModule({
  imports: [CommonModule, RootModalComponent],
  exports: [RootModalComponent],
})
export class RootModalModule {}
