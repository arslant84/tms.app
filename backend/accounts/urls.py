from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import UserViewSet, LoginView, LogoutView, TokenRefreshView, PasswordChangeView, RoleViewSet, PermissionViewSet, ApplicationSettingViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'roles', RoleViewSet)
router.register(r'permissions', PermissionViewSet)
router.register(r'settings', ApplicationSettingViewSet, basename='applicationsetting')

urlpatterns = [
    path('', include(router.urls)),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('password/change/', PasswordChangeView.as_view(), name='password_change'),
]
