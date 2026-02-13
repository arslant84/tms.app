import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';

import { VisaService } from './visa.service';

describe('VisaService', () => {
  let service: VisaService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient()]
    });
    service = TestBed.inject(VisaService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
