import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { ActivatedRoute } from '@angular/router';
import { of } from 'rxjs';

import { VisaDetailComponent } from './visa-detail.component';

describe('VisaDetailComponent', () => {
  let component: VisaDetailComponent;
  let fixture: ComponentFixture<VisaDetailComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [VisaDetailComponent],
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

    fixture = TestBed.createComponent(VisaDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
