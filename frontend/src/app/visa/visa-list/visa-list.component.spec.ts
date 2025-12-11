import { ComponentFixture, TestBed } from '@angular/core/testing';

import { VisaListComponent } from './visa-list.component';

describe('VisaListComponent', () => {
  let component: VisaListComponent;
  let fixture: ComponentFixture<VisaListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [VisaListComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(VisaListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
