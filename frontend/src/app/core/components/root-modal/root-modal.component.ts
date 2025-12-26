import { Component, ViewChild, ViewContainerRef, OnInit } from '@angular/core';
import { ModalService } from '../../services/modal.service';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-root-modal',
  template: '<ng-template #modalHost></ng-template>',
  standalone: true,
  imports: [CommonModule],
})
export class RootModalComponent implements OnInit {
  @ViewChild('modalHost', { read: ViewContainerRef, static: true }) modalHost!: ViewContainerRef;

  constructor(private modalService: ModalService) {}

  ngOnInit(): void {
    this.modalService.registerHostViewContainerRef(this.modalHost);
  }
}
