import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { ActivatedRoute, Router } from '@angular/router';
import { of } from 'rxjs';

import { NotificationListComponent } from './notification-list.component';
import { NotificationService, type UserNotification } from '../../services/notification.service';

describe('NotificationListComponent', () => {
  let component: NotificationListComponent;
  let fixture: ComponentFixture<NotificationListComponent>;
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
      imports: [NotificationListComponent],
      providers: [
        provideHttpClient(),
        { provide: NotificationService, useValue: notificationServiceSpy },
        {
          provide: ActivatedRoute,
          useValue: { params: of({}), snapshot: { params: {} } },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(NotificationListComponent);
    component = fixture.componentInstance;
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  // Same regression coverage as header.component.spec.ts's
  // 'onNotificationClick navigation' block - this component had its own,
  // independently-broken-and-fixed copy of the same navigation logic (see
  // commit 49b73586). Kept as a parallel suite rather than a shared helper
  // so a future edit to either component's buildNavigation() that
  // re-introduces drift between the two gets caught here too.
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
        sent_via_push: false,
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
      component.onNotificationClick(notification({ action_url: '/visa/8', is_read: true }));
      expect(router.navigate).toHaveBeenCalledWith(['/visa/8'], undefined);
    });

    it('does not navigate when action_url is absent', () => {
      component.onNotificationClick(notification({ action_url: undefined, is_read: true }));
      expect(router.navigate).not.toHaveBeenCalled();
    });

    it('routes an approval-required notification to admin approvals with query params, not the entity page', () => {
      component.onNotificationClick(
        notification({
          title: 'New Approval Required: Manager Approval',
          action_url: 'http://localhost:4200/accommodation/12',
          is_read: true,
        })
      );
      expect(router.navigate).toHaveBeenCalledWith(['/admin/approvals'], {
        queryParams: { type: 'accommodation', id: '12', action: 'approve' },
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
