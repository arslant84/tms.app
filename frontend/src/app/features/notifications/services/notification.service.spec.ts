import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { BehaviorSubject } from 'rxjs';

import { NotificationService } from './notification.service';
import { AuthService } from '../../../core/services/auth.service';
import { environment } from '../../../../environments/environment';

// Regression coverage for the bug where the notification bell badge showed
// 0 for up to a full minute after every login/page load, no matter how many
// notifications were actually unread. startPolling() called
// refreshNotifications() (populates the list) immediately on login, but left
// refreshUnreadCount() (the only thing that updates unreadCount$, which
// drives the header badge) to the interval(60000) timer - and RxJS's
// interval() does not emit an initial tick, its first emission is 60s out.
// So unreadCount$ sat at its BehaviorSubject seed value (0) until that first
// tick fired.
describe('NotificationService - initial unread count on login', () => {
  let service: NotificationService;
  let httpMock: HttpTestingController;
  let currentUser$: BehaviorSubject<{ id: number } | null>;

  beforeEach(() => {
    currentUser$ = new BehaviorSubject<{ id: number } | null>(null);

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: AuthService,
          useValue: { currentUser$, getCurrentUser: () => currentUser$.value },
        },
      ],
    });

    service = TestBed.inject(NotificationService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('fetches the unread count immediately on login, without waiting for the 60s poll tick', () => {
    let latestCount: number | undefined;
    service.unreadCount$.subscribe(count => (latestCount = count));

    currentUser$.next({ id: 1 });

    const unreadReq = httpMock.expectOne(`${environment.apiUrl}/notifications/unread_count/`);
    unreadReq.flush({ success: true, data: { count: 16 } });

    // The notifications list refresh is a separate, expected request -
    // drain it so it doesn't trip httpMock.verify().
    const listReq = httpMock.expectOne(req => req.url === `${environment.apiUrl}/notifications/`);
    listReq.flush({ results: [] });

    expect(latestCount).toBe(16);
  });
});
