from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import Jurisdiction, IssuingAuthority, Vocabulary, VocabularyTerm, Language, Scheme
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
    verbose_name = "موضوع"
    verbose_name_plural = "📚 موضوعات"
    list_display = ('name', 'code', 'scheme', 'lang', 'created_at')
    search_fields = ('name', 'code', 'scheme', 'lang')
    list_filter = ('scheme', 'lang', 'created_at')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('name',)
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('name', 'code')
        }),
        ('طبقه‌بندی', {
            'fields': ('scheme', 'lang')
        }),
        ('اطلاعات سیستم', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class VocabularyTermInline(admin.TabularInline):
    model = VocabularyTerm
    extra = 1
    readonly_fields = ('id', 'created_at', 'updated_at')


class VocabularyTermAdmin(SimpleHistoryAdmin):
    verbose_name = "واژه"
    verbose_name_plural = "📝 واژگان"
    list_display = ('term', 'vocabulary', 'code', 'is_active', 'created_at')
    list_filter = ('is_active', 'vocabulary', 'created_at')
    search_fields = ('term', 'code', 'description', 'vocabulary__name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('vocabulary__name', 'term')


# Add inline to Vocabulary admin
VocabularyAdmin.inlines = [VocabularyTermInline]

class LanguageAdmin(SimpleHistoryAdmin):
    verbose_name = "زبان"
    verbose_name_plural = "🌐 زبان‌ها"
    list_display = ('name', 'code', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'code')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('name',)


class SchemeAdmin(SimpleHistoryAdmin):
    verbose_name = "طرح کلی"
    verbose_name_plural = "📋 طرح‌های کلی"
    list_display = ('name', 'code', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'code', 'description')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('name',)


# Register models with custom admin site
admin_site.register(Jurisdiction, JurisdictionAdmin)
admin_site.register(IssuingAuthority, IssuingAuthorityAdmin)
admin_site.register(Language, LanguageAdmin)
admin_site.register(Scheme, SchemeAdmin)
admin_site.register(Vocabulary, VocabularyAdmin)
admin_site.register(VocabularyTerm, VocabularyTermAdmin)
