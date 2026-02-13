import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { ActivatedRoute } from '@angular/router';
import { of } from 'rxjs';

import { VisaFormComponent } from './visa-form.component';

describe('VisaFormComponent', () => {
  let component: VisaFormComponent;
  let fixture: ComponentFixture<VisaFormComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [VisaFormComponent],
      providers: [
        provideHttpClient(),
        {
          provide: ActivatedRoute,
          useValue: {
            params: of({}),
            snapshot: { params: {} }
          }
        }
      ]
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
