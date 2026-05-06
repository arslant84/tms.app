from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    UserViewSet, LoginView, LogoutView, TokenRefreshView, PasswordChangeView,
    PasswordResetRequestView, PasswordResetConfirmView, RegisterView,
    RoleViewSet, PermissionViewSet, DepartmentViewSet, ApplicationSettingViewSet, AdminActionLogViewSet,
    MFASetupView, MFAConfirmView, MFAVerifyView, MFADisableView, MFAStatusView,
    PrivacyPolicyView,
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
    path('register/', RegisterView.as_view(), name='register'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('password/change/', PasswordChangeView.as_view(), name='password_change'),
    path('password/reset/request/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password/reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    # MFA endpoints — CTRL-0000001024 / CTRL-0000001063
    path('mfa/status/', MFAStatusView.as_view(), name='mfa_status'),
    path('mfa/setup/', MFASetupView.as_view(), name='mfa_setup'),
    path('mfa/confirm/', MFAConfirmView.as_view(), name='mfa_confirm'),
    path('mfa/verify/', MFAVerifyView.as_view(), name='mfa_verify'),
    path('mfa/disable/', MFADisableView.as_view(), name='mfa_disable'),
    # Privacy policy — CTRL-0000001000 / CTRL-0000001001 / CTRL-0000001003
    path('privacy-policy/', PrivacyPolicyView.as_view(), name='privacy_policy'),
]
