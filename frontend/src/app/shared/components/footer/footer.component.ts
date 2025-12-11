import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AppSettingsService } from '../../../core/services/app-settings.service';
import { Observable, map } from 'rxjs';

@Component({
  selector: 'app-footer',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './footer.component.html',
  styleUrls: ['./footer.component.scss']
})
export class FooterComponent implements OnInit {
  currentYear: number = new Date().getFullYear();
  applicationName$: Observable<string>;
  supportEmail$: Observable<string>;

  constructor(private appSettingsService: AppSettingsService) {
    this.applicationName$ = this.appSettingsService.settings$.pipe(
      map(settings => settings.application_name || 'TMS')
    );
    this.supportEmail$ = this.appSettingsService.settings$.pipe(
      map(settings => settings.support_email || 'support@example.com')
    );
  }

  ngOnInit(): void {}
}
