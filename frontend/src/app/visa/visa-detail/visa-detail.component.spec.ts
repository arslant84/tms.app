import { ComponentFixture, TestBed } from '@angular/core/testing';

import { VisaDetailComponent } from './visa-detail.component';

describe('VisaDetailComponent', () => {
  let component: VisaDetailComponent;
  let fixture: ComponentFixture<VisaDetailComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [VisaDetailComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(VisaDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
