import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TrfCreateComponent } from './trf-create.component';

describe('TrfCreateComponent', () => {
  let component: TrfCreateComponent;
  let fixture: ComponentFixture<TrfCreateComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TrfCreateComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(TrfCreateComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
