import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TrfListComponent } from './trf-list.component';

describe('TrfListComponent', () => {
  let component: TrfListComponent;
  let fixture: ComponentFixture<TrfListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TrfListComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(TrfListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
