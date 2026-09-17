import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { ActivatedRoute, Router } from '@angular/router';
import { of } from 'rxjs';

import { HeaderComponent } from './header.component';
import {
  NotificationService,
  type UserNotification,
} from '../../../features/notifications/services/notification.service';

describe('HeaderComponent', () => {
  let component: HeaderComponent;
  let fixture: ComponentFixture<HeaderComponent>;
  let router: Router;
  let notificationServiceSpy: jasmine.SpyObj<NotificationService>;

  beforeEach(async () => {
    notificationServiceSpy = jasmine.createSpyObj<NotificationService>(
      'NotificationService',
      ['markAsRead'],
      {
        notifications$: of([]),
        unreadCount$: of(0),
      }
    );
    notificationServiceSpy.markAsRead.and.returnValue(of({} as UserNotification));

    await TestBed.configureTestingModule({
      imports: [HeaderComponent],
      providers: [
        provideHttpClient(),
        { provide: NotificationService, useValue: notificationServiceSpy },
        {
          provide: ActivatedRoute,
          useValue: {
            params: of({}),
            snapshot: { params: {} },
          },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(HeaderComponent);
    component = fixture.componentInstance;
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  // Regression coverage for the 2026-08-23 fix (commit 49b73586): the
  // backend's action_url changed shape from a bare relative path with the
  // wrong raw entity_type segment (e.g. /travelrequest/123) to an absolute
  // URL with the real Angular route segment already correct
  // (http://host/trf/123). The old client-side remapping logic looked for
  // the stale segment names, found nothing to replace, and passed the
  // whole absolute URL string to router.navigate() as one invalid path
  // segment - which matches no route and silently falls through to the
  // wildcard route. This locks in that an absolute action_url now resolves
  // to the correct bare path.
  describe('onNotificationClick navigation', () => {
    function notification(overrides: Partial<UserNotification>): UserNotification {
      return {
        id: 1,
        user: 1,
        title: 'Some notification',
        message: 'Some message',
        action_text: 'View',
        priority: 'normal',
        is_read: true,
        sent_via_email: false,
        created_at: new Date().toISOString(),
        ...overrides,
      } as UserNotification;
    }

    it('navigates to the bare path for an absolute action_url', () => {
      component.onNotificationClick(
        notification({ action_url: 'http://localhost:4200/trf/123', is_read: true })
      );
      expect(router.navigate).toHaveBeenCalledWith(['/trf/123'], undefined);
    });

    it('navigates correctly for an already-bare action_url (older notifications)', () => {
      component.onNotificationClick(notification({ action_url: '/transport/45', is_read: true }));
      expect(router.navigate).toHaveBeenCalledWith(['/transport/45'], undefined);
    });

    it('does not navigate when action_url is absent', () => {
      component.onNotificationClick(notification({ action_url: undefined, is_read: true }));
      expect(router.navigate).not.toHaveBeenCalled();
    });

    it('routes an approval-required notification to admin approvals with query params, not the entity page', () => {
      component.onNotificationClick(
        notification({
          title: 'New Approval Required: Manager Approval',
          action_url: 'http://localhost:4200/trf/77',
          is_read: true,
        })
      );
      expect(router.navigate).toHaveBeenCalledWith(['/admin/approvals'], {
        queryParams: { type: 'trf', id: '77', action: 'approve' },
      });
    });

    it('marks unread notifications as read before navigating', () => {
      component.onNotificationClick(
        notification({ action_url: 'http://localhost:4200/trf/9', is_read: false, id: 9 })
      );
      expect(notificationServiceSpy.markAsRead).toHaveBeenCalledWith(9);
      expect(router.navigate).toHaveBeenCalledWith(['/trf/9'], undefined);
    });
  });
});
