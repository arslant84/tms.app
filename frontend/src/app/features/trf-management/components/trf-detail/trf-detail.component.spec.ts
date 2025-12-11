import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TrfDetailComponent } from './trf-detail.component';

describe('TrfDetailComponent', () => {
  let component: TrfDetailComponent;
  let fixture: ComponentFixture<TrfDetailComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TrfDetailComponent]
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
