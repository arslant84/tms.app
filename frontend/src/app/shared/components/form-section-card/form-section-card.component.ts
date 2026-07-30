import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-form-section-card',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './form-section-card.component.html',
  styleUrls: ['./form-section-card.component.scss']
})
export class FormSectionCardComponent {
  /** Bootstrap icon class, e.g. "bi-cup-hot" (without the leading "bi "). */
  @Input() icon = '';
  @Input() title = '';
}
