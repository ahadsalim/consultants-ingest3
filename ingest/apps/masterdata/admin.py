from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import Jurisdiction, IssuingAuthority, Vocabulary, VocabularyTerm
from ingest.admin import admin_site


class JurisdictionAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'code', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'code', 'description')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('name',)


class IssuingAuthorityAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'code', 'jurisdiction', 'is_active', 'created_at')
    list_filter = ('is_active', 'jurisdiction', 'created_at')
    search_fields = ('name', 'code', 'description')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('name',)


class VocabularyAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'code', 'created_at')
    search_fields = ('name', 'code', 'description')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('name',)


class VocabularyTermInline(admin.TabularInline):
    model = VocabularyTerm
    extra = 1
    readonly_fields = ('id', 'created_at', 'updated_at')


class VocabularyTermAdmin(SimpleHistoryAdmin):
    list_display = ('term', 'vocabulary', 'code', 'is_active', 'created_at')
    list_filter = ('is_active', 'vocabulary', 'created_at')
    search_fields = ('term', 'code', 'description', 'vocabulary__name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('vocabulary__name', 'term')


# Add inline to Vocabulary admin
VocabularyAdmin.inlines = [VocabularyTermInline]

# Register models with custom admin site
admin_site.register(Jurisdiction, JurisdictionAdmin)
admin_site.register(IssuingAuthority, IssuingAuthorityAdmin)
admin_site.register(Vocabulary, VocabularyAdmin)
admin_site.register(VocabularyTerm, VocabularyTermAdmin)
