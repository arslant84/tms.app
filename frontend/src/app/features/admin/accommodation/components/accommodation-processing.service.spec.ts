import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { environment } from '../../../../../environments/environment';

import { AccommodationProcessingService } from './accommodation-processing.service';
import type { BookedAccommodation } from './accommodation-processing.mapper';

describe('AccommodationProcessingService', () => {
  let service: AccommodationProcessingService;
  let httpMock: HttpTestingController;
  const apiUrl = `${environment.apiUrl}/accommodation`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(AccommodationProcessingService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  function makeBooking(overrides: Partial<BookedAccommodation> = {}): BookedAccommodation {
    return {
      id: 1,
      trf: 42,
      requestNumber: 'ACC-1',
      requestorName: 'Jane Doe',
      staffId: 'S001',
      staffHouseName: 'House A',
      roomName: 'Room 1',
      location: 'Ashgabat',
      checkInDate: '2026-01-01',
      checkOutDate: '2026-01-05',
      status: 'Confirmed',
      ...overrides,
    };
  }

  describe('loadRequests', () => {
    it('splits requests into pending and booked by status', done => {
      service.loadRequests().subscribe(result => {
        expect(result.pending.length).toBe(1);
        expect(result.pending[0].id).toBe(1);
        expect(result.booked.length).toBe(1);
        expect(result.booked[0].id).toBe(2);
        done();
      });

      const req = httpMock.expectOne(
        r => r.url === `${apiUrl}/requests/` && r.params.get('admin_view') === 'true'
      );
      req.flush([
        { id: 1, status: 'Approved', requestor_name: 'A' },
        { id: 2, status: 'Accommodation Assigned', requestor_name: 'B' },
        { id: 3, status: 'Draft', requestor_name: 'C' },
      ]);
    });

    it('handles a paginated {results: []} response shape', done => {
      service.loadRequests().subscribe(result => {
        expect(result.pending.length).toBe(1);
        done();
      });

      const req = httpMock.expectOne(r => r.url === `${apiUrl}/requests/`);
      req.flush({ results: [{ id: 1, status: 'Approved' }] });
    });
  });

  describe('fetchBookings', () => {
    it('maps raw bookings into BookingData rows', done => {
      service.fetchBookings().subscribe(bookings => {
        expect(bookings).toEqual([
          {
            id: 1,
            staff_house_id: 2,
            room_id: 3,
            date: '2026-01-01',
            status: 'Confirmed',
            guest_name: 'Jane Doe',
            trf_id: 42,
            notes: undefined,
          },
        ]);
        done();
      });

      const req = httpMock.expectOne(r => r.url === `${apiUrl}/bookings/`);
      req.flush([
        {
          id: 1,
          staff_house: 2,
          room: 3,
          date: '2026-01-01',
          status: 'Confirmed',
          staff_name: 'Jane Doe',
          trf: 42,
        },
      ]);
    });
  });

  describe('assignRoom', () => {
    it('POSTs to the assign endpoint for the given request', done => {
      service
        .assignRoom(7, {
          staff_house: 1,
          room: 2,
          start_date: '2026-01-01',
          end_date: '2026-01-05',
          assigned_room_info: 'House A - Room 1',
        })
        .subscribe(response => {
          expect(response.message).toBe('Assigned');
          done();
        });

      const req = httpMock.expectOne(`${apiUrl}/requests/7/assign/`);
      expect(req.request.method).toBe('POST');
      req.flush({ message: 'Assigned' });
    });
  });

  describe('rejectNoRoomsAvailable', () => {
    it('POSTs the canned no-rooms-available reason', done => {
      service.rejectNoRoomsAvailable(9).subscribe(() => done());

      const req = httpMock.expectOne(`${apiUrl}/requests/9/reject/`);
      expect(req.request.body.reason).toContain('No rooms available');
      req.flush({});
    });
  });

  describe('fetchRelatedBookings', () => {
    it('filters confirmed bookings by matching trf id', async () => {
      const promise = service.fetchRelatedBookings(makeBooking({ trf: 42 }));

      const req = httpMock.expectOne(
        r => r.url === `${apiUrl}/bookings/` && r.params.get('status') === 'Confirmed'
      );
      req.flush([
        { id: 1, staff_house: 1, room: 1, date: '2026-01-01', status: 'Confirmed', trf: 42 },
        { id: 2, staff_house: 1, room: 2, date: '2026-01-01', status: 'Confirmed', trf: 99 },
      ]);

      const related = await promise;
      expect(related.length).toBe(1);
      expect(related[0].id).toBe(1);
    });

    it('returns nothing when the booking has no trf', async () => {
      const promise = service.fetchRelatedBookings(makeBooking({ trf: null }));

      const req = httpMock.expectOne(r => r.url === `${apiUrl}/bookings/`);
      req.flush([
        { id: 1, staff_house: 1, room: 1, date: '2026-01-01', status: 'Confirmed', trf: null },
      ]);

      const related = await promise;
      expect(related.length).toBe(0);
    });
  });

  describe('deleteBookings', () => {
    it('sends one DELETE per booking', async () => {
      const promise = service.deleteBookings([
        { id: 1, staff_house: 1, room: 1, date: '2026-01-01', status: 'Confirmed' },
        { id: 2, staff_house: 1, room: 1, date: '2026-01-02', status: 'Confirmed' },
      ] as never);

      const reqs = httpMock.match(r => r.method === 'DELETE');
      expect(reqs.length).toBe(2);
      reqs.forEach(r => r.flush(null));

      await promise;
    });
  });

  describe('restoreApprovedStatus', () => {
    it('PATCHes the request back to Approved', async () => {
      const promise = service.restoreApprovedStatus(makeBooking({ id: 3 }));

      const req = httpMock.expectOne(`${apiUrl}/requests/3/`);
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body.status).toBe('Approved');
      req.flush({});

      await promise;
    });
  });
});
