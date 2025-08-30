import pytest
from django.urls import reverse
from rest_framework import status

from tests.factories import (
    UserFactory, LegalDocumentFactory, LegalUnitFactory, 
    QAEntryFactory, JurisdictionFactory
)


@pytest.mark.django_db
class TestHealthAPI:
    def test_health_check(self, api_client):
        """Test health check endpoint."""
        url = reverse('health')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] in ['healthy', 'unhealthy']


@pytest.mark.django_db
class TestLegalDocumentAPI:
    def test_list_documents(self, authenticated_client, user_operator):
        """Test listing legal documents."""
        # Create documents for the authenticated user
        LegalDocumentFactory.create_batch(3, created_by=user_operator)
        
        url = reverse('legaldocument-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 3

    def test_create_document(self, authenticated_client):
        """Test creating a legal document."""
        jurisdiction = JurisdictionFactory()
        authority = jurisdiction.authorities.create(
            name="Test Authority",
            code="TEST_AUTH"
        )
        
        data = {
            'title': 'Test Document',
            'reference_no': 'TEST-001',
            'doc_type': 'law',
            'jurisdiction': str(jurisdiction.id),
            'authority': str(authority.id),
            'status': 'draft'
        }
        
        url = reverse('legaldocument-list')
        response = authenticated_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == 'Test Document'

    def test_unauthorized_access(self, api_client):
        """Test unauthorized access to documents."""
        url = reverse('legaldocument-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestPresignAPI:
    def test_generate_presigned_url(self, authenticated_client):
        """Test generating presigned URLs."""
        data = {
            'filename': 'test.pdf',
            'content_type': 'application/pdf'
        }
        
        url = reverse('presign')
        response = authenticated_client.post(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'upload_url' in response.data
        assert 'download_url' in response.data
        assert 'object_key' in response.data

    def test_presign_missing_data(self, authenticated_client):
        """Test presigned URL generation with missing data."""
        data = {'filename': 'test.pdf'}  # Missing content_type
        
        url = reverse('presign')
        response = authenticated_client.post(url, data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
