import pytest
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User

from ingest.apps.documents.models import LegalDocument, LegalUnit, QAEntry, FileAsset
from ingest.apps.documents.enums import DocumentStatus, QAStatus
from tests.factories import (
    UserFactory, LegalDocumentFactory, LegalUnitFactory, 
    QAEntryFactory, FileAssetFactory
)


@pytest.mark.django_db
class TestLegalDocument:
    def test_create_document(self):
        """Test creating a legal document."""
        document = LegalDocumentFactory()
        assert document.title
        assert document.created_by
        assert document.status == DocumentStatus.DRAFT
        assert document.is_editable
        assert not document.is_approved

    def test_document_approval_workflow(self):
        """Test document approval workflow."""
        document = LegalDocumentFactory()
        reviewer = UserFactory()
        
        # Initially editable
        assert document.is_editable
        
        # Approve document
        document.status = DocumentStatus.APPROVED
        document.approved_by = reviewer
        document.save()
        
        # No longer editable after approval
        assert not document.is_editable
        assert document.is_approved


@pytest.mark.django_db
class TestLegalUnit:
    def test_create_unit(self):
        """Test creating a legal unit."""
        unit = LegalUnitFactory()
        assert unit.document
        assert unit.label
        assert unit.content
        assert unit.path_label == unit.label  # No parent

    def test_unit_hierarchy(self):
        """Test legal unit hierarchy."""
        document = LegalDocumentFactory()
        parent_unit = LegalUnitFactory(document=document, label="فصل ۱")
        child_unit = LegalUnitFactory(
            document=document, 
            parent=parent_unit, 
            label="ماده ۱"
        )
        
        assert child_unit.parent == parent_unit
        assert child_unit.path_label == "فصل ۱ > ماده ۱"
        assert parent_unit in child_unit.get_ancestors()


@pytest.mark.django_db
class TestQAEntry:
    def test_create_qa_entry(self):
        """Test creating a QA entry."""
        qa = QAEntryFactory()
        assert qa.question
        assert qa.answer
        assert qa.status == QAStatus.DRAFT
        assert qa.is_editable
        assert not qa.is_approved

    def test_qa_approval_workflow(self):
        """Test QA entry approval workflow."""
        qa = QAEntryFactory()
        reviewer = UserFactory()
        
        # Initially editable
        assert qa.is_editable
        
        # Approve QA entry
        qa.status = QAStatus.APPROVED
        qa.approved_by = reviewer
        qa.save()
        
        # No longer editable after approval
        assert not qa.is_editable
        assert qa.is_approved


@pytest.mark.django_db
class TestFileAsset:
    def test_create_file_asset(self):
        """Test creating a file asset."""
        file_asset = FileAssetFactory()
        assert file_asset.document
        assert file_asset.original_filename
        assert file_asset.content_type
        assert file_asset.size_bytes > 0

    def test_file_asset_validation(self):
        """Test file asset validation."""
        # File must be attached to either document or unit, not both
        document = LegalDocumentFactory()
        unit = LegalUnitFactory()
        
        with pytest.raises(ValidationError):
            file_asset = FileAsset(
                document=document,
                legal_unit=unit,  # Can't have both
                bucket="test",
                object_key="test/file.pdf",
                original_filename="file.pdf",
                content_type="application/pdf",
                size_bytes=1000,
                sha256="test_hash",
                uploaded_by=UserFactory()
            )
            file_asset.full_clean()
