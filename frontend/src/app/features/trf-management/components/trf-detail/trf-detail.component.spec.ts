import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { ActivatedRoute } from '@angular/router';
import { of } from 'rxjs';

import { TrfDetailComponent } from './trf-detail.component';

describe('TrfDetailComponent', () => {
  let component: TrfDetailComponent;
  let fixture: ComponentFixture<TrfDetailComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TrfDetailComponent],
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

    fixture = TestBed.createComponent(TrfDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
