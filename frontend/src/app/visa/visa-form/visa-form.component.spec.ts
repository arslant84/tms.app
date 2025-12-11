import { ComponentFixture, TestBed } from '@angular/core/testing';

import { VisaFormComponent } from './visa-form.component';

describe('VisaFormComponent', () => {
  let component: VisaFormComponent;
  let fixture: ComponentFixture<VisaFormComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [VisaFormComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(VisaFormComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
