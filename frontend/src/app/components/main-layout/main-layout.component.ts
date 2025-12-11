import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { SidebarComponent } from '../../shared/components/sidebar/sidebar.component';
import { HeaderComponent } from '../../shared/components/header/header.component';
import { FooterComponent } from '../../shared/components/footer/footer.component';
import { RightPanelComponent } from '../../shared/components/right-panel/right-panel.component';

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [CommonModule, RouterModule, SidebarComponent, HeaderComponent, FooterComponent, RightPanelComponent],
  templateUrl: './main-layout.component.html',
  styleUrl: './main-layout.component.scss'
})
export class MainLayoutComponent {
  isSidebarCollapsed: boolean = false;
  showRightPanel: boolean = false;
  selectedRequestId: number = 0;
  selectedRequestType: string = '';
  logoPath: string = 'img/pet-logo-without-text.png';  // Using the public directory as configured in angular.json
  
  toggleSidebar(): void {
    this.isSidebarCollapsed = !this.isSidebarCollapsed;
  }
  
  openRightPanel(requestId: number, requestType: string): void {
    this.selectedRequestId = requestId;
    this.selectedRequestType = requestType;
    this.showRightPanel = true;
  }
  
  closeRightPanel(): void {
    this.showRightPanel = false;
  }
}
