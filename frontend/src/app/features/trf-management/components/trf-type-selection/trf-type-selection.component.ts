import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';

interface TravelTypeOption {
  id: string;
  title: string;
  description: string;
  icon: string;
  route: string;
}

@Component({
  selector: 'app-trf-type-selection',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './trf-type-selection.component.html',
  styleUrls: ['./trf-type-selection.component.scss']
})
export class TrfTypeSelectionComponent {
  travelTypeOptions: TravelTypeOption[] = [
    {
      id: 'domestic',
      title: 'Domestic Business Trip',
      description: 'For business travel within the country.',
      icon: 'bi-house-door',
      route: '/trf/create/domestic'
    },
    {
      id: 'overseas',
      title: 'Overseas Business Trip',
      description: 'For international business travel.',
      icon: 'bi-globe',
      route: '/trf/create/overseas'
    },
    {
      id: 'home-leave',
      title: 'Home Leave Passage',
      description: 'For expatriate staff entitled to travel to their home country.',
      icon: 'bi-file-earmark-text',
      route: '/trf/create/home-leave'
    },
    {
      id: 'external-parties',
      title: 'Business Travel Request for External Parties',
      description: 'For non-employees traveling on behalf of the company.',
      icon: 'bi-people',
      route: '/trf/create/external-parties'
    }
  ];

  constructor(private router: Router) {}

  navigateToTravelType(route: string): void {
    this.router.navigate([route]);
  }
}
