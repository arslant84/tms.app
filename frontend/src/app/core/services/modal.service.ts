import { type ComponentRef, Injectable, type Type, type ViewContainerRef } from '@angular/core';
import { Subject } from 'rxjs';

/** Minimal shape a component hosted by ModalService may implement to emit
 *  a close event back to ModalService.close(). */
interface CloseEmitter {
  subscribe: (next: (data?: unknown) => void) => void;
}

@Injectable({
  providedIn: 'root',
})
export class ModalService {
  private hostViewContainerRef!: ViewContainerRef;
  private componentRef?: ComponentRef<unknown>;
  private readonly _afterClosed = new Subject<unknown>();
  public readonly afterClosed = this._afterClosed.asObservable();

  registerHostViewContainerRef(vcr: ViewContainerRef): void {
    this.hostViewContainerRef = vcr;
  }

  open<T>(component: Type<T>, inputs?: Record<string, unknown>): void {
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
      const instance = this.componentRef.instance as Record<string, unknown>;
      for (const key in inputs) {
        if (Object.hasOwn(inputs, key)) {
          instance[key] = inputs[key];
        }
      }
    }

    // Subscribe to a close event if the modal component has one
    const closeEmitter = (this.componentRef.instance as { close?: CloseEmitter }).close;
    if (closeEmitter) {
      closeEmitter.subscribe((data?: unknown) => {
        this.close(data);
      });
    }

    document.body.classList.add('modal-open');
  }

  close(data?: unknown): void {
    if (this.componentRef) {
      this.componentRef.destroy();
      this.componentRef = undefined;
      this.hostViewContainerRef.clear();
      this._afterClosed.next(data);
    }
    document.body.classList.remove('modal-open');
  }
}
