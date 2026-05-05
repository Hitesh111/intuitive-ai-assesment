from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from vm_lifecycle.health import liveness, readiness
from vm_lifecycle.views import VMInstanceViewSet

router = DefaultRouter()
router.register(r'v1/vms', VMInstanceViewSet, basename='vm-instance')

urlpatterns = [
    path('', TemplateView.as_view(template_name='dashboard.html'), name='dashboard'),
    path('admin/', admin.site.urls),

    # Health probes (no auth required)
    path('healthz/', liveness, name='healthz'),
    path('readyz/', readiness, name='readyz'),

    # JWT auth endpoints
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # VM lifecycle endpoints
    path('api/', include(router.urls)),
]
