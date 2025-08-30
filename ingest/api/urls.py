from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from .views import HealthCheckView, PresignURLView
from .masterdata import views as masterdata_views
from .documents import views as documents_views
from .syncbridge import views as syncbridge_views

# Create router and register viewsets
router = DefaultRouter()

# Masterdata endpoints
router.register(r'masterdata/jurisdictions', masterdata_views.JurisdictionViewSet)
router.register(r'masterdata/authorities', masterdata_views.IssuingAuthorityViewSet)
router.register(r'masterdata/vocabularies', masterdata_views.VocabularyViewSet)
router.register(r'masterdata/vocabulary-terms', masterdata_views.VocabularyTermViewSet)

# Documents endpoints
router.register(r'documents', documents_views.LegalDocumentViewSet)
router.register(r'units', documents_views.LegalUnitViewSet)
router.register(r'files', documents_views.FileAssetViewSet)
router.register(r'qa', documents_views.QAEntryViewSet)

# Sync endpoints
router.register(r'sync/jobs', syncbridge_views.SyncJobViewSet)

urlpatterns = [
    # Authentication
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # API Documentation
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Utility endpoints
    path('health/', HealthCheckView.as_view(), name='health'),
    path('presign/', PresignURLView.as_view(), name='presign'),
    
    # Router URLs
    path('', include(router.urls)),
]
