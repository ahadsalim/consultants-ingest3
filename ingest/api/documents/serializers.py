from rest_framework import serializers
from ingest.apps.documents.models import LegalUnit, FileAsset, QAEntry
from ingest.apps.masterdata.models import VocabularyTerm


class FileAssetSerializer(serializers.ModelSerializer):
    uploaded_by_username = serializers.CharField(source='uploaded_by.username', read_only=True)
    size_mb = serializers.SerializerMethodField()
    
    class Meta:
        model = FileAsset
        fields = [
            'id', 'legal_unit', 'manifestation', 'bucket', 'object_key', 
            'original_filename', 'content_type', 'size_bytes', 'size_mb',
            'sha256', 'uploaded_by', 'uploaded_by_username', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'bucket', 'object_key', 'sha256', 'size_bytes', 
            'uploaded_by', 'uploaded_by_username', 'created_at', 'updated_at'
        ]
    
    def get_size_mb(self, obj):
        return round(obj.size_bytes / (1024 * 1024), 2)


class LegalUnitSerializer(serializers.ModelSerializer):
    files = FileAssetSerializer(many=True, read_only=True)
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = LegalUnit
        fields = [
            'id', 'parent', 'unit_type', 'label', 'number', 
            'order_index', 'path_label', 'content', 'work', 'expr', 'manifestation', 'files', 'children',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'path_label', 'created_at', 'updated_at']
    
    def get_children(self, obj):
        children = obj.get_children()
        return LegalUnitSerializer(children, many=True, context=self.context).data


"""Removed LegalDocument and DocumentRelation serializers."""


class QAEntrySerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    reviewed_by_username = serializers.CharField(source='reviewed_by.username', read_only=True)
    approved_by_username = serializers.CharField(source='approved_by.username', read_only=True)
    
    source_unit_label = serializers.CharField(source='source_unit.label', read_only=True)
    
    tags_display = serializers.SerializerMethodField()
    
    class Meta:
        model = QAEntry
        fields = [
            'id', 'question', 'answer', 'tags', 'tags_display', 'source_unit', 'source_unit_label', 'status',
            'created_by', 'created_by_username', 'reviewed_by', 'reviewed_by_username',
            'approved_by', 'approved_by_username', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_by_username', 'reviewed_by_username', 'approved_by_username',
            'source_unit_label', 'tags_display',
            'created_at', 'updated_at'
        ]
    
    def get_tags_display(self, obj):
        return [
            {
                'id': str(tag.id),
                'term': tag.term,
                'vocabulary': tag.vocabulary.name
            }
            for tag in obj.tags.all()
        ]
