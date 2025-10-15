from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ExpenseClaimViewSet, ExpenseItemViewSet, ClaimsApprovalStepViewSet

# Create router and register all viewsets
router = DefaultRouter()
router.register(r'claims', ExpenseClaimViewSet, basename='expense-claim')
router.register(r'items', ExpenseItemViewSet, basename='expense-item')
router.register(r'approval-steps', ClaimsApprovalStepViewSet, basename='claims-approval-step')

app_name = 'expenses'

urlpatterns = [
    path('', include(router.urls)),
]
