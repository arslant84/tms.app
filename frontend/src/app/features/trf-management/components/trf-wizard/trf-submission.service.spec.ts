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

    it('creates a linked accommodation request when not a draft and no accommodation is linked yet', async () => {
      const promise = service.createNestedResources(
        123,
        {
          mainTrf: {},
          itinerarySegments: [],
          mealSelections: [],
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

    it('still creates a linked accommodation request in edit mode when finishing a Draft that has none yet', async () => {
      // Regression test: this is the isEditMode=true, hasLinkedAccommodation=false
      // case - e.g. a TRF saved as a Draft, reopened later, "Requires
      // Accommodation" ticked, then submitted. Previously the `!isEditMode`
      // guard alone skipped creation here, silently dropping the accommodation
      // request with no error shown anywhere.
      const promise = service.createNestedResources(
        123,
        {
          mainTrf: {},
          itinerarySegments: [],
          mealSelections: [],
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
        true, // edit mode
        { fullName: 'Jane Doe' },
        null,
        false, // hasLinkedAccommodation - none yet
        false
      );

      const createReq = httpMock.expectOne(
        req => req.method === 'POST' && req.url.includes('/accommodation')
      );
      createReq.flush({ id: 999 });
      await Promise.resolve();
      await Promise.resolve();

      const submitReq = httpMock.expectOne(req => req.url.includes('999'));
      submitReq.flush({});

      await expectAsync(promise).toBeResolvedTo(true);
    });

    it('does not re-create a linked accommodation request when one is already linked', async () => {
      const promise = service.createNestedResources(
        123,
        {
          mainTrf: {},
          itinerarySegments: [],
          mealSelections: [],
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
        true, // edit mode
        { fullName: 'Jane Doe' },
        null,
        true, // hasLinkedAccommodation - already exists
        false
      );

      httpMock.expectNone(req => req.url.includes('/accommodation'));
      await expectAsync(promise).toBeResolvedTo(true);
    });

    it('creates a linked transport request when not a draft and no transport is linked yet', async () => {
      const promise = service.createNestedResources(
        123,
        {
          mainTrf: { purpose: 'Business trip' },
          itinerarySegments: [],
          mealSelections: [],
          bankDetails: null,
          advanceAmounts: [],
          transport: {
            required: true,
            journeys: [
              {
                date: '2026-01-01',
                day: '',
                from: 'KUL',
                to: 'PEN',
                departureTime: '09:00',
                numberOfPassengers: 1,
              },
            ],
          },
        },
        false, // not a draft
        false, // not edit mode
        { fullName: 'Jane Doe' },
        null
      );

      const createReq = httpMock.expectOne(
        req => req.method === 'POST' && req.url.includes('/transport')
      );
      createReq.flush({ id: 888 });

      await expectAsync(promise).toBeResolvedTo(true);
    });

    it('still creates a linked transport request in edit mode when finishing a Draft that has none yet', async () => {
      // Regression test mirroring the accommodation one above - this is the
      // exact bug reported for TSR-20260826-0956-TURKM-YUN7: a Draft TSR with
      // "Requires Transport" checked, reopened and submitted later, ended up
      // with zero linked transport because the old `!isEditMode` guard skipped
      // creation on every edit, not just re-edits of an already-submitted one.
      const promise = service.createNestedResources(
        123,
        {
          mainTrf: { purpose: 'Business trip' },
          itinerarySegments: [],
          mealSelections: [],
          bankDetails: null,
          advanceAmounts: [],
          transport: {
            required: true,
            journeys: [
              {
                date: '2026-01-01',
                day: '',
                from: 'KUL',
                to: 'PEN',
                departureTime: '09:00',
                numberOfPassengers: 1,
              },
            ],
          },
        },
        false, // not a draft
        true, // edit mode
        { fullName: 'Jane Doe' },
        null,
        false,
        false // hasLinkedTransport - none yet
      );

      const createReq = httpMock.expectOne(
        req => req.method === 'POST' && req.url.includes('/transport')
      );
      createReq.flush({ id: 888 });

      await expectAsync(promise).toBeResolvedTo(true);
    });

    it('does not re-create a linked transport request when one is already linked', async () => {
      const promise = service.createNestedResources(
        123,
        {
          mainTrf: { purpose: 'Business trip' },
          itinerarySegments: [],
          mealSelections: [],
          bankDetails: null,
          advanceAmounts: [],
          transport: {
            required: true,
            journeys: [
              {
                date: '2026-01-01',
                day: '',
                from: 'KUL',
                to: 'PEN',
                departureTime: '09:00',
                numberOfPassengers: 1,
              },
            ],
          },
        },
        false, // not a draft
        true, // edit mode
        { fullName: 'Jane Doe' },
        null,
        false,
        true // hasLinkedTransport - already exists
      );

      httpMock.expectNone(req => req.url.includes('/transport'));
      await expectAsync(promise).toBeResolvedTo(true);
    });
  });
});
