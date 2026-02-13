import { Injectable, ViewContainerRef, createComponent, ComponentRef, Type } from '@angular/core';
import { Subject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ModalService {
  private hostViewContainerRef!: ViewContainerRef;
  private componentRef?: ComponentRef<any>;
  private readonly _afterClosed = new Subject<any>();
  public readonly afterClosed = this._afterClosed.asObservable();

  constructor() {}

  registerHostViewContainerRef(vcr: ViewContainerRef): void {
    this.hostViewContainerRef = vcr;
  }

  open<T>(component: Type<T>, inputs?: Record<string, any>): void {
    if (!this.hostViewContainerRef) {
      console.error('Modal host container not registered!');
      return;
    }

    // Clear any existing modal
    this.hostViewContainerRef.clear();

    // Create the component
    this.componentRef = this.hostViewContainerRef.createComponent(component);

    // Pass inputs to the component instance
    if (inputs) {
      for (const key in inputs) {
        if (inputs.hasOwnProperty(key)) {
          this.componentRef.instance[key] = inputs[key];
        }
      }
    }

    // Subscribe to a close event if the modal component has one
    if (this.componentRef.instance.close) {
      this.componentRef.instance.close.subscribe(() => {
        this.close();
      });
    }

    document.body.classList.add('modal-open');
  }

  close(data?: any): void {
    if (this.componentRef) {
      this.componentRef.destroy();
      this.componentRef = undefined;
      this.hostViewContainerRef.clear();
      this._afterClosed.next(data);
    }
    document.body.classList.remove('modal-open');
  }
}

