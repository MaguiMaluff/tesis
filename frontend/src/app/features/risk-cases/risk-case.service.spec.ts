import { TestBed } from '@angular/core/testing';

import { RiskCaseService } from './risk-case.service';

describe('RiskCaseService', () => {
  let service: RiskCaseService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(RiskCaseService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
