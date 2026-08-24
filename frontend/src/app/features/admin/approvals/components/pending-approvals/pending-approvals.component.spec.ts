import { fakeAsync, TestBed, tick } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { BehaviorSubject, of } from 'rxjs';

import { PendingApprovalsComponent } from './pending-approvals.component';
import { NotificationService } from '../../../../notifications/services/notification.service';

// Regression coverage for the query-param-clear bug: after a notification
// link opens /admin/approvals?type=X&id=Y&action=approve and auto-opens the
// approve dialog, the component tried to clear those params with
// `queryParamsHandling: 'merge'` + an empty queryParams object. Merging an
// empty object into existing params is a documented Angular no-op, so the
// params never actually cleared. That left the URL parked at
// ?type=X&id=Y&action=approve indefinitely - clicking a second notification
// that resolved to the exact same URL then hit Angular's default
// onSameUrlNavigation: 'ignore' and silently did nothing, which looked like
// "the second notification doesn't open" until navigating elsewhere first
// changed the URL. The fix drops queryParamsHandling so the navigate call
// replaces the query string with the given (empty) object instead.
describe('PendingApprovalsComponent - notification-link query param clearing', () => {
  let httpMock: HttpTestingController;
  let router: Router;
  let queryParams$: BehaviorSubject<Record<string, string>>;

  function flushPendingApprovalsRequests(): void {
    httpMock
      .match(() => true)
      .forEach(req => {
        req.flush({ data: [], meta: { pagination: { total_count: 0, total_pages: 1 } } });
      });
  }

  beforeEach(async () => {
    queryParams$ = new BehaviorSubject<Record<string, string>>({
      id: '5',
      type: 'trf',
      action: 'approve',
    });

    const notificationServiceSpy = jasmine.createSpyObj<NotificationService>(
      'NotificationService',
      [],
      { notifications$: of([]), unreadCount$: of(0) }
    );

    await TestBed.configureTestingModule({
      imports: [PendingApprovalsComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: NotificationService, useValue: notificationServiceSpy },
        {
          provide: ActivatedRoute,
          useValue: { queryParams: queryParams$, snapshot: { queryParams: {} } },
        },
      ],
    }).compileComponents();

    httpMock = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
  });

  it('clears query params with a plain replace, not a no-op merge', fakeAsync(() => {
    const fixture = TestBed.createComponent(PendingApprovalsComponent);
    fixture.detectChanges();
    // AppSettingsService (unrelated to this component's own data fetch)
    // also issues a request off the same HttpClient - drain everything
    // outstanding rather than asserting on unrelated app-wide traffic.
    flushPendingApprovalsRequests();

    tick(1000);
    flushPendingApprovalsRequests();

    expect(router.navigate).toHaveBeenCalledWith([], {
      relativeTo: jasmine.any(Object),
      queryParams: {},
    });

    const call = (router.navigate as jasmine.Spy).calls.mostRecent();
    expect(call.args[1].queryParamsHandling).toBeUndefined();
  }));
});
