import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { ActivatedRoute } from '@angular/router';
import { of } from 'rxjs';

import { VisaListComponent } from './visa-list.component';

describe('VisaListComponent', () => {
  let component: VisaListComponent;
  let fixture: ComponentFixture<VisaListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [VisaListComponent],
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

    fixture = TestBed.createComponent(VisaListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
