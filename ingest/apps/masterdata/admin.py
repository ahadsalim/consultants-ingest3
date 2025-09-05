from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import Jurisdiction, IssuingAuthority, Vocabulary, VocabularyTerm, Language, Scheme
from ingest.admin import admin_site


class JurisdictionAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'code', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'code')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('name',)
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('name', 'code', 'is_active')
        }),
        ('اطلاعات سیستم', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['name'].help_text = 'نام کامل حوزه قضایی را وارد کنید. مثال: جمهوری اسلامی ایران'
        form.base_fields['code'].help_text = 'کد کوتاه حوزه قضایی را وارد کنید. مثال: IRN'
        form.base_fields['is_active'].help_text = 'آیا این حوزه قضایی فعال است؟'
        return form


class IssuingAuthorityAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'short_name', 'jurisdiction', 'is_active', 'created_at')
    list_filter = ('is_active', 'jurisdiction', 'created_at')
    search_fields = ('name', 'short_name', 'uri')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('name',)
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('name', 'short_name', 'jurisdiction', 'is_active')
        }),
        ('شناسه‌های یکتا', {
            'fields': ('uri',),
            'classes': ('collapse',)
        }),
        ('اطلاعات سیستم', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['name'].help_text = 'نام کامل مرجع صادرکننده را وارد کنید. مثال: قوه قضاییه جمهوری اسلامی ایران'
        form.base_fields['short_name'].help_text = 'نام کوتاه مرجع صادرکننده را وارد کنید. مثال: قوه قضاییه'
        form.base_fields['jurisdiction'].help_text = 'حوزه قضایی مرتبط با این مرجع را انتخاب کنید.'
        form.base_fields['is_active'].help_text = 'آیا این مرجع فعال است؟'
        form.base_fields['uri'].help_text = 'شناسه یکتای منبع (URI) را وارد کنید. مثال: https://example.org/authority/judiciary'
        return form


class VocabularyAdmin(SimpleHistoryAdmin):
    verbose_name = "موضوع"
    verbose_name_plural = "📚 موضوعات"
    list_display = ('name', 'code', 'scheme', 'lang', 'created_at')
    search_fields = ('name', 'code', 'scheme__name', 'lang__name')
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
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['name'].help_text = 'نام کامل موضوع را وارد کنید. مثال: حقوق مدنی'
        form.base_fields['code'].help_text = 'کد کوتاه موضوع را وارد کنید. مثال: civil_law'
        form.base_fields['scheme'].help_text = 'طرح کلی مرتبط با این موضوع را انتخاب کنید.'
        form.base_fields['lang'].help_text = 'زبان این موضوع را انتخاب کنید.'
        return form


class VocabularyTermInline(admin.StackedInline):
    model = VocabularyTerm
    extra = 1
    readonly_fields = ('id', 'created_at', 'updated_at')
    fields = ('term', 'code', 'is_active', 'description')
    
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        form = formset.form
        form.base_fields['term'].help_text = 'واژه یا عبارت را وارد کنید'
        form.base_fields['code'].help_text = 'کد شناسایی یکتا برای این واژه'
        form.base_fields['is_active'].help_text = 'آیا این واژه فعال است؟'
        form.base_fields['description'].help_text = 'توضیحات تکمیلی (اختیاری)'
        return formset


class VocabularyTermAdmin(SimpleHistoryAdmin):
    verbose_name = "واژه"
    verbose_name_plural = "📝 واژگان"
    list_display = ('term', 'vocabulary', 'code', 'is_active', 'created_at')
    list_filter = ('is_active', 'vocabulary', 'created_at')
    search_fields = ('term', 'code', 'vocabulary__name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('vocabulary__name', 'term')
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('term', 'code', 'vocabulary', 'is_active')
        }),
        ('توضیحات', {
            'fields': ('description',),
            'classes': ('collapse',)
        }),
        ('اطلاعات سیستم', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['term'].help_text = 'واژه یا عبارت را به فارسی وارد کنید. مثال: قرارداد'
        form.base_fields['code'].help_text = 'کد شناسایی یکتا برای این واژه. مثال: contract'
        form.base_fields['vocabulary'].help_text = 'موضوع مرتبط با این واژه را انتخاب کنید.'
        form.base_fields['is_active'].help_text = 'آیا این واژه فعال است؟'
        form.base_fields['description'].help_text = 'توضیحات تکمیلی درباره این واژه (اختیاری)'
        return form


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
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('name', 'code', 'is_active')
        }),
        ('اطلاعات سیستم', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['name'].help_text = 'نام کامل زبان را به فارسی وارد کنید. مثال: فارسی'
        form.base_fields['code'].help_text = 'کد دو حرفی زبان را وارد کنید. مثال: fa'
        form.base_fields['is_active'].help_text = 'آیا این زبان در سیستم فعال است؟'
        return form


class SchemeAdmin(SimpleHistoryAdmin):
    verbose_name = "طرح کلی"
    verbose_name_plural = "📋 طرح‌های کلی"
    list_display = ('name', 'code', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'code')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('name',)
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('name', 'code', 'is_active')
        }),
        ('اطلاعات سیستم', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['name'].help_text = 'نام طرح کلی را وارد کنید. مثال: موضوعات حقوقی'
        form.base_fields['code'].help_text = 'کد کوتاه طرح کلی را وارد کنید. مثال: legal_subjects'
        form.base_fields['is_active'].help_text = 'آیا این طرح کلی فعال است؟'
        return form


# Register models with custom admin site
admin_site.register(Jurisdiction, JurisdictionAdmin)
admin_site.register(IssuingAuthority, IssuingAuthorityAdmin)
admin_site.register(Language, LanguageAdmin)
admin_site.register(Scheme, SchemeAdmin)
admin_site.register(Vocabulary, VocabularyAdmin)
admin_site.register(VocabularyTerm, VocabularyTermAdmin)
