import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-trf-stepper',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './trf-stepper.component.html',
  styleUrls: ['./trf-stepper.component.scss']
})
export class TrfStepperComponent {
  @Input() currentStep = 1;
  @Input() steps: string[] = [];
  @Input() completedSteps: boolean[] = [];
  @Output() stepClick = new EventEmitter<number>();

  onStepClick(step: number): void {
    this.stepClick.emit(step);
  }

  isStepClickable(stepNumber: number): boolean {
    return stepNumber <= this.currentStep || (this.completedSteps && this.completedSteps[stepNumber - 1]);
  }

  isStepActive(stepNumber: number): boolean {
    return this.currentStep === stepNumber;
  }

  isStepCompleted(stepNumber: number): boolean {
    const index = stepNumber - 1;
    return this.completedSteps ? this.completedSteps[index] : stepNumber < this.currentStep;
  }
}
