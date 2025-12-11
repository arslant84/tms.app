import { TestBed } from '@angular/core/testing';

import { TrfService } from './trf.service';

describe('TrfService', () => {
  let service: TrfService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(TrfService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
