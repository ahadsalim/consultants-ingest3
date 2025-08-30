import factory
from django.contrib.auth.models import User
from factory.django import DjangoModelFactory

from ingest.apps.masterdata.models import Jurisdiction, IssuingAuthority, Vocabulary, VocabularyTerm
from ingest.apps.documents.models import LegalDocument, LegalUnit, QAEntry, FileAsset
from ingest.apps.documents.enums import DocumentType, DocumentStatus, UnitType, QAStatus


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@test.com")
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')


class JurisdictionFactory(DjangoModelFactory):
    class Meta:
        model = Jurisdiction

    name = factory.Faker('country')
    code = factory.Sequence(lambda n: f"JUR{n:03d}")
    description = factory.Faker('text', max_nb_chars=200)
    is_active = True


class IssuingAuthorityFactory(DjangoModelFactory):
    class Meta:
        model = IssuingAuthority

    name = factory.Faker('company')
    code = factory.Sequence(lambda n: f"AUTH{n:03d}")
    jurisdiction = factory.SubFactory(JurisdictionFactory)
    description = factory.Faker('text', max_nb_chars=200)
    is_active = True


class VocabularyFactory(DjangoModelFactory):
    class Meta:
        model = Vocabulary

    name = factory.Faker('word')
    code = factory.Sequence(lambda n: f"VOCAB{n:03d}")
    description = factory.Faker('text', max_nb_chars=200)


class VocabularyTermFactory(DjangoModelFactory):
    class Meta:
        model = VocabularyTerm

    vocabulary = factory.SubFactory(VocabularyFactory)
    term = factory.Faker('word')
    code = factory.Sequence(lambda n: f"TERM{n:03d}")
    description = factory.Faker('text', max_nb_chars=200)
    is_active = True


class LegalDocumentFactory(DjangoModelFactory):
    class Meta:
        model = LegalDocument

    title = factory.Faker('sentence', nb_words=6)
    reference_no = factory.Sequence(lambda n: f"DOC-{n:04d}")
    doc_type = DocumentType.LAW
    jurisdiction = factory.SubFactory(JurisdictionFactory)
    authority = factory.SubFactory(IssuingAuthorityFactory)
    status = DocumentStatus.DRAFT
    created_by = factory.SubFactory(UserFactory)


class LegalUnitFactory(DjangoModelFactory):
    class Meta:
        model = LegalUnit

    document = factory.SubFactory(LegalDocumentFactory)
    unit_type = UnitType.ARTICLE
    label = factory.Sequence(lambda n: f"ماده {n}")
    number = factory.Sequence(lambda n: str(n))
    order_index = factory.Sequence(lambda n: n)
    content = factory.Faker('text', max_nb_chars=500)


class QAEntryFactory(DjangoModelFactory):
    class Meta:
        model = QAEntry

    question = factory.Faker('sentence', nb_words=10, variable_nb_words=True)
    answer = factory.Faker('text', max_nb_chars=300)
    status = QAStatus.DRAFT
    created_by = factory.SubFactory(UserFactory)


class FileAssetFactory(DjangoModelFactory):
    class Meta:
        model = FileAsset

    document = factory.SubFactory(LegalDocumentFactory)
    bucket = "test-bucket"
    object_key = factory.Sequence(lambda n: f"test/file_{n}.pdf")
    original_filename = factory.Sequence(lambda n: f"document_{n}.pdf")
    content_type = "application/pdf"
    size_bytes = factory.Faker('random_int', min=1000, max=1000000)
    sha256 = factory.Faker('sha256')
    uploaded_by = factory.SubFactory(UserFactory)
