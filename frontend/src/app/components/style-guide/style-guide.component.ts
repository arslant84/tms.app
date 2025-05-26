import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-style-guide',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './style-guide.component.html',
  styleUrls: ['./style-guide.component.scss']
})
export class StyleGuideComponent {
  primaryColors = [
    { name: 'Primary Teal', class: 'bg-primary-teal', rgb: 'RGB: 0, 177, 169' },
    { name: 'Primary Brown', class: 'bg-primary-brown', rgb: 'RGB: 255, 255, 255' },
    { name: 'Primary Dark Gray', class: 'bg-primary-dark-gray', rgb: 'RGB: 60, 56, 53' }
  ];

  secondaryColors = [
    { name: 'Purple Dark', class: 'bg-secondary-purple-dark', rgb: 'RGB: 64, 43, 83' },
    { name: 'Purple Medium', class: 'bg-secondary-purple-medium', rgb: 'RGB: 104, 70, 139' },
    { name: 'Blue', class: 'bg-secondary-blue', rgb: 'RGB: 97, 94, 154' },
    { name: 'Light Blue', class: 'bg-secondary-light-blue', rgb: 'RGB: 148, 189, 229' },
    { name: 'Green', class: 'bg-secondary-green', rgb: 'RGB: 58, 84, 65' },
    { name: 'Yellow', class: 'bg-secondary-yellow', rgb: 'RGB: 212, 214, 82' },
    { name: 'Orange', class: 'bg-secondary-orange', rgb: 'RGB: 242, 176, 47' }
  ];

  specialColors = [
    { name: 'Neutral Color', class: 'bg-neutral', rgb: 'RGB: 205, 182, 134' },
    { name: 'Highlight Color', class: 'bg-highlight', rgb: 'RGB: 217, 39, 44' }
  ];
}
