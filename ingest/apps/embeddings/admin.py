from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import Embedding


@admin.register(Embedding)
class EmbeddingAdmin(SimpleHistoryAdmin):
    list_display = ('content_object', 'model_name', 'created_at')
    list_filter = ('model_name', 'content_type', 'created_at')
    search_fields = ('text_content', 'model_name')
    readonly_fields = ('id', 'vector', 'created_at', 'updated_at')
    
    def has_add_permission(self, request):
        return False  # Embeddings are created automatically
    
    def has_change_permission(self, request, obj=None):
        return False  # Embeddings are read-only
