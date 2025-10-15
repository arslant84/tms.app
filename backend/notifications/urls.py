from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    NotificationEventTypeViewSet,
    NotificationTemplateViewSet,
    UserNotificationPreferenceViewSet,
    UserNotificationSubscriptionViewSet,
    UserNotificationViewSet,
    NotificationBatchViewSet
)

router = DefaultRouter()
router.register(r'event-types', NotificationEventTypeViewSet, basename='notification-event-type')
router.register(r'templates', NotificationTemplateViewSet, basename='notification-template')
router.register(r'preferences', UserNotificationPreferenceViewSet, basename='notification-preference')
router.register(r'subscriptions', UserNotificationSubscriptionViewSet, basename='notification-subscription')
router.register(r'notifications', UserNotificationViewSet, basename='user-notification')
router.register(r'batches', NotificationBatchViewSet, basename='notification-batch')

urlpatterns = [
    path('', include(router.urls)),
]
