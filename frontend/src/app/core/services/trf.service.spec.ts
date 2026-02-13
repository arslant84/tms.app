import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';

import { TrfService } from './trf.service';

describe('TrfService', () => {
  let service: TrfService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient()]
    });
    service = TestBed.inject(TrfService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
