import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';

interface RequestType {
  id: string;
  title: string;
  icon: string;
  description: string;
  route: string;
}

@Component({
  selector: 'app-request-type-selection',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './request-type-selection.component.html',
  styleUrl: './request-type-selection.component.scss',
})
export class RequestTypeSelectionComponent {
  requestTypes: RequestType[] = [
    {
      id: 'domestic',
      title: 'Domestic Business Trip',
      icon: 'bi bi-airplane',
      description: 'For business travel within the country.',
      route: '/requests/travel/domestic',
    },
    {
      id: 'overseas',
      title: 'Overseas Business Trip',
      icon: 'bi bi-globe',
      description: 'For international business travel.',
      route: '/requests/travel/international',
    },
    {
      id: 'home-leave',
      title: 'Home Leave Passage',
      icon: 'bi bi-house',
      description: 'For expatriate staff entitled to travel to their home country.',
      route: '/requests/travel/home-leave',
    },
    {
      id: 'external',
      title: 'Business Travel Request for External Parties',
      icon: 'bi bi-person',
      description: 'For non-employees traveling on behalf of the company.',
      route: '/requests/travel/external',
    },
  ];

  constructor(private router: Router) {}

  selectRequestType(requestType: RequestType): void {
    this.router.navigate([requestType.route]);
  }
}
