from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    UserViewSet, LoginView, LogoutView, TokenRefreshView, PasswordChangeView,
    PasswordResetRequestView, PasswordResetConfirmView,
    RoleViewSet, PermissionViewSet, DepartmentViewSet, ApplicationSettingViewSet, AdminActionLogViewSet
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'roles', RoleViewSet)
router.register(r'permissions', PermissionViewSet)
router.register(r'departments', DepartmentViewSet)
router.register(r'settings', ApplicationSettingViewSet, basename='applicationsetting')
router.register(r'audit-logs', AdminActionLogViewSet, basename='auditlog')

urlpatterns = [
    path('', include(router.urls)),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('password/change/', PasswordChangeView.as_view(), name='password_change'),
    path('password/reset/request/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password/reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
]
