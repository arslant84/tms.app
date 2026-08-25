import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { TrfEditLoaderService } from './trf-edit-loader.service';
import type { TrfBackendResponse } from './trf-wizard.types';

describe('TrfEditLoaderService', () => {
  let service: TrfEditLoaderService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(TrfEditLoaderService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('loadForEdit', () => {
    it('unwraps a { trf: {...} } response shape', done => {
      service.loadForEdit(42, false).subscribe(data => {
        expect(data.id).toBe(42);
        expect(data.requestor_name).toBe('Jane Doe');
        done();
      });

      const req = httpMock.expectOne(req => req.method === 'GET' && req.url.includes('42'));
      req.flush({ trf: { id: 42, requestor_name: 'Jane Doe' } });
    });

    it('passes through an already-unwrapped response', done => {
      service.loadForEdit(43, false).subscribe(data => {
        expect(data.id).toBe(43);
        done();
      });

      const req = httpMock.expectOne(req => req.method === 'GET' && req.url.includes('43'));
      req.flush({ id: 43, requestor_name: 'John Doe' });
    });
  });

  describe('canEditStatus', () => {
    it('allows Draft, Rejected, and any Pending status', () => {
      expect(service.canEditStatus('Draft')).toBe(true);
      expect(service.canEditStatus('Rejected')).toBe(true);
      expect(service.canEditStatus('Pending HOD')).toBe(true);
    });

    it('disallows Approved and other terminal statuses', () => {
      expect(service.canEditStatus('Approved')).toBe(false);
      expect(service.canEditStatus('Cancelled')).toBe(false);
    });

    it('handles undefined status without throwing', () => {
      expect(service.canEditStatus(undefined)).toBe(false);
    });
  });

  describe('buildRequestorData', () => {
    it('prefers snake_case fields over camelCase aliases', () => {
      const data: TrfBackendResponse = {
        id: 1,
        requestor_name: 'Jane Doe',
        requestorName: 'wrong',
        staff_id: 'S001',
      };
      const result = service.buildRequestorData(data);
      expect(result.fullName).toBe('Jane Doe');
      expect(result.staffId).toBe('S001');
    });
  });

  describe('buildApprovalData', () => {
    it('defaults additionalComments/selected_approvers/skipped_steps', () => {
      const result = service.buildApprovalData({ id: 1 });
      expect(result.additionalComments).toBe('');
      expect(result.selected_approvers).toEqual({});
      expect(result.skipped_steps).toEqual({});
    });
  });

  describe('buildTravelTypeData', () => {
    it('builds domesticTravelData for Domestic, leaving other fields undefined', () => {
      const data: TrfBackendResponse = {
        id: 1,
        domesticTravelDetails: {
          purpose: 'Site visit',
          itinerary: [{ segment_date: '2026-01-01', from_location: 'KUL', to_location: 'PEN' }],
        },
      };
      const result = service.buildTravelTypeData('Domestic', data);
      expect(result.domesticTravelData?.purposeOfTravel).toBe('Site visit');
      expect(result.domesticTravelData?.itinerary?.length).toBe(1);
      expect(result.overseasTravelData).toBeUndefined();
    });

    it('builds overseasTravelData for Overseas', () => {
      const data: TrfBackendResponse = {
        id: 1,
        overseasTravelDetails: { purpose: 'Conference' },
        advance_consent_accepted: true,
      };
      const result = service.buildTravelTypeData('Overseas', data);
      expect(result.overseasTravelData?.purpose).toBe('Conference');
      expect(result.overseasTravelData?.advanceConsentAccepted).toBe(true);
      expect(result.domesticTravelData).toBeUndefined();
    });

    it('builds externalPartiesData with the External Parties field mapping', () => {
      const data: TrfBackendResponse = {
        id: 1,
        externalPartiesTravelDetails: { purpose: 'Vendor visit' },
        externalPartyRequestorInfo: { externalFullName: 'John Vendor' },
      };
      const result = service.buildTravelTypeData('External Parties', data);
      expect(result.externalPartiesData?.purpose).toBe('Vendor visit');
      expect(result.externalPartiesData?.externalFullName).toBe('John Vendor');
    });

    it('returns an empty result for a null travel type', () => {
      const result = service.buildTravelTypeData(null, { id: 1 });
      expect(result).toEqual({});
    });
  });

  describe('loadLinkedAccommodation', () => {
    it('returns null when no linked request is found', done => {
      service.loadLinkedAccommodation(42).subscribe(result => {
        expect(result).toBeNull();
        done();
      });

      const req = httpMock.expectOne(req => req.url.includes('/accommodation'));
      req.flush({ results: [{ trf: 99 }] });
    });

    it('maps the linked request into AccommodationDetails when found', done => {
      service.loadLinkedAccommodation(42).subscribe(result => {
        expect(result?.required).toBe(true);
        expect(result?.location).toBe('Ashgabat');
        done();
      });

      const req = httpMock.expectOne(req => req.url.includes('/accommodation'));
      req.flush({ results: [{ trf: 42, additional_data: { location: 'Ashgabat' } }] });
    });

    it('resolves to null rather than erroring when the request fails', done => {
      service.loadLinkedAccommodation(42).subscribe(result => {
        expect(result).toBeNull();
        done();
      });

      const req = httpMock.expectOne(req => req.url.includes('/accommodation'));
      req.flush('error', { status: 500, statusText: 'Server Error' });
    });
  });

  describe('loadLinkedTransport', () => {
    it('maps the linked request into TransportDetails when found', done => {
      service.loadLinkedTransport(42).subscribe(result => {
        expect(result?.required).toBe(true);
        expect(result?.journeys.length).toBe(1);
        done();
      });

      // TransportService.getAllRequests() runs each row through
      // toFrontendFormat() (transport.model.ts) before this service ever
      // sees it, which reads the backend's raw snake_case shape (trf,
      // transport_details) - not the frontend-facing trfId/transportDetails
      // names this service's own LinkedTransportRow interface names (those
      // describe the shape *after* that transformation).
      const req = httpMock.expectOne(req => req.url.includes('/transport'));
      req.flush({
        results: [{ id: 1, trf: 42, transport_details: [{ from: 'KUL', to: 'PEN' }] }],
      });
    });
  });
});
