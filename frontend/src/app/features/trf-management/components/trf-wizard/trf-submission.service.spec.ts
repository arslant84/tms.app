import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { TrfSubmissionService, type PrepareTrfDataParams } from './trf-submission.service';

describe('TrfSubmissionService', () => {
  let service: TrfSubmissionService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(TrfSubmissionService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  function baseParams(overrides: Partial<PrepareTrfDataParams> = {}): PrepareTrfDataParams {
    return {
      selectedTravelType: 'Domestic',
      requestorData: { fullName: 'Jane Doe', staffId: 'S001', department: 'IT' },
      domesticTravelData: {},
      overseasTravelData: {},
      homeLeaveData: {},
      externalPartiesData: {},
      additionalComments: '',
      ...overrides,
    };
  }

  describe('prepareTrfData', () => {
    it('builds mainTrf from requestor data regardless of travel type', () => {
      const result = service.prepareTrfData(baseParams());
      expect(result.mainTrf['requestor_name']).toBe('Jane Doe');
      expect(result.mainTrf['staff_id']).toBe('S001');
      expect(result.mainTrf['travel_type']).toBe('Domestic');
      expect(result.mainTrf['status']).toBe('Draft');
    });

    it('carries Domestic itinerary/meals/accommodation/transport through', () => {
      const result = service.prepareTrfData(
        baseParams({
          domesticTravelData: {
            purposeOfTravel: 'Site visit',
            itinerary: [
              {
                date: new Date(2026, 0, 1),
                day: '',
                from: 'KUL',
                to: 'PEN',
                etd: '',
                eta: '',
                flightNumber: '',
              },
            ],
            mealProvisions: { dailySelections: [] },
            accommodation: {
              required: true,
              gender: '',
              location: '',
              checkInDate: '',
              checkInTime: '',
              checkOutDate: '',
              checkOutTime: '',
              roomType: '',
              specialRequests: '',
            },
          },
        })
      );
      expect(result.mainTrf['purpose']).toBe('Site visit');
      expect(result.itinerarySegments.length).toBe(1);
      expect(result.accommodation?.required).toBe(true);
    });

    it('sets advance_consent_accepted for Overseas', () => {
      const result = service.prepareTrfData(
        baseParams({
          selectedTravelType: 'Overseas',
          overseasTravelData: { purpose: 'Conference', advanceConsentAccepted: true },
        })
      );
      expect(result.mainTrf['advance_consent_accepted']).toBe(true);
      expect(result.mainTrf['purpose']).toBe('Conference');
    });

    it('maps External Parties fields onto mainTrf with the corrected field names', () => {
      const result = service.prepareTrfData(
        baseParams({
          selectedTravelType: 'External Parties',
          externalPartiesData: {
            purpose: 'Vendor visit',
            externalFullName: 'John Vendor',
            externalOrganization: 'Acme Corp',
          },
        })
      );
      expect(result.mainTrf['external_full_name']).toBe('John Vendor');
      expect(result.mainTrf['external_organization']).toBe('Acme Corp');
    });

    it('falls back to an empty PreparedTrfData when no travel type is selected', () => {
      const result = service.prepareTrfData(baseParams({ selectedTravelType: null }));
      expect(result.itinerarySegments).toEqual([]);
      expect(result.mealSelections).toEqual([]);
      expect(result.passportDetails).toBeNull();
    });
  });

  describe('createNestedResources', () => {
    it('rejects an invalid trfId', async () => {
      await expectAsync(
        service.createNestedResources(
          0,
          {
            mainTrf: {},
            itinerarySegments: [],
            mealSelections: [],
            passportDetails: null,
            bankDetails: null,
            advanceAmounts: [],
          },
          false,
          false,
          {},
          null
        )
      ).toBeRejectedWithError(/Invalid TRF ID/);
    });

    it('skips itinerary segments missing a required field and creates no request for them', async () => {
      // httpMock.verify() in afterEach fails if any unexpected request was
      // made - the missing from/to segment must be skipped entirely.
      const promise = service.createNestedResources(
        123,
        {
          mainTrf: {},
          itinerarySegments: [{ date: '2026-01-01' }], // missing from/to
          mealSelections: [],
          passportDetails: null,
          bankDetails: null,
          advanceAmounts: [],
        },
        false,
        false,
        {},
        null
      );

      await expectAsync(promise).toBeResolvedTo(true);
    });

    it('creates a linked accommodation request only when not a draft and not in edit mode', async () => {
      const promise = service.createNestedResources(
        123,
        {
          mainTrf: {},
          itinerarySegments: [],
          mealSelections: [],
          passportDetails: null,
          bankDetails: null,
          advanceAmounts: [],
          accommodation: {
            required: true,
            gender: '',
            location: '',
            checkInDate: '',
            checkInTime: '',
            checkOutDate: '',
            checkOutTime: '',
            roomType: '',
            specialRequests: '',
          },
        },
        false, // not a draft
        false, // not edit mode
        { fullName: 'Jane Doe' },
        null
      );

      const createReq = httpMock.expectOne(
        req => req.method === 'POST' && req.url.includes('/accommodation')
      );
      createReq.flush({ id: 999 });
      // Let the .then() chaining to submitRequest() run before looking for
      // its request - flush() resolves the create call on a microtask.
      await Promise.resolve();
      await Promise.resolve();

      const submitReq = httpMock.expectOne(req => req.url.includes('999'));
      submitReq.flush({});

      await expectAsync(promise).toBeResolvedTo(true);
    });

    it('does not create a linked accommodation request when saving as a draft', async () => {
      const promise = service.createNestedResources(
        123,
        {
          mainTrf: {},
          itinerarySegments: [],
          mealSelections: [],
          passportDetails: null,
          bankDetails: null,
          advanceAmounts: [],
          accommodation: {
            required: true,
            gender: '',
            location: '',
            checkInDate: '',
            checkInTime: '',
            checkOutDate: '',
            checkOutTime: '',
            roomType: '',
            specialRequests: '',
          },
        },
        true, // isDraft
        false,
        { fullName: 'Jane Doe' },
        null
      );

      httpMock.expectNone(req => req.url.includes('/accommodation'));
      await expectAsync(promise).toBeResolvedTo(true);
    });
  });
});
