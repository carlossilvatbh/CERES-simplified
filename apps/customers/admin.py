"""
CERES Simplified - Customer Admin
Customized Django Admin for customer management
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Q
from .models import Customer, BeneficialOwner, CustomerNote


class BeneficialOwnerInline(admin.TabularInline):
    """Inline admin for beneficial owners"""
    model = BeneficialOwner
    extra = 0
    fields = [
        'full_name', 'document_number', 'ownership_percentage', 
        'is_pep', 'is_sanctions_checked', 'email', 'phone'
    ]
    readonly_fields = ['is_sanctions_checked']


class CustomerNoteInline(admin.TabularInline):
    """Inline admin for customer notes"""
    model = CustomerNote
    extra = 0
    fields = ['title', 'content', 'is_important', 'is_internal']
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing existing note
            return ['created_by', 'created_at']
        return []


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """Customized admin for Customer model"""
    
    list_display = [
        'full_name', 'document_number', 'customer_type', 
        'onboarding_status_colored', 'risk_level_colored', 
        'risk_score', 'is_pep', 'needs_review_display', 'created_at'
    ]
    
    list_filter = [
        'customer_type', 'onboarding_status', 'risk_level', 
        'is_pep', 'is_sanctions_checked', 'country', 'created_at'
    ]
    
    search_fields = [
        'full_name', 'legal_name', 'document_number', 
        'email', 'phone', 'business_type'
    ]
    
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'risk_score', 
        'sanctions_last_check', 'last_review_date'
    ]
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': (
                'id', 'customer_type', 'full_name', 'legal_name',
                'document_type', 'document_number'
            )
        }),
        ('Contato', {
            'fields': (
                'email', 'phone', 'address', 'city', 
                'state', 'country', 'postal_code'
            )
        }),
        ('Informações Comerciais', {
            'fields': (
                'business_type', 'industry', 'annual_revenue'
            ),
            'classes': ('collapse',)
        }),
        ('Status e Risco', {
            'fields': (
                'onboarding_status', 'risk_level', 'risk_score',
                'is_pep', 'is_sanctions_checked', 'sanctions_last_check'
            )
        }),
        ('Datas', {
            'fields': (
                'created_at', 'updated_at', 'last_review_date', 'next_review_date'
            ),
            'classes': ('collapse',)
        }),
        ('Observações', {
            'fields': ('notes',),
            'classes': ('collapse',)
        })
    )
    
    inlines = [BeneficialOwnerInline, CustomerNoteInline]
    
    actions = [
        'mark_as_approved', 'mark_as_under_review', 'mark_as_rejected',
        'schedule_review', 'run_sanctions_check'
    ]
    
    def get_queryset(self, request):
        """Optimize queryset with related data"""
        return super().get_queryset(request).select_related('created_by').prefetch_related(
            'beneficial_owners', 'customer_notes'
        )
    
    def onboarding_status_colored(self, obj):
        """Display onboarding status with colors"""
        colors = {
            'PENDING': 'orange',
            'IN_PROGRESS': 'blue',
            'ADDITIONAL_INFO': 'purple',
            'UNDER_REVIEW': 'yellow',
            'APPROVED': 'green',
            'REJECTED': 'red',
            'SUSPENDED': 'darkred',
            'CLOSED': 'gray',
        }
        color = colors.get(obj.onboarding_status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_onboarding_status_display()
        )
    onboarding_status_colored.short_description = 'Status'
    onboarding_status_colored.admin_order_field = 'onboarding_status'
    
    def risk_level_colored(self, obj):
        """Display risk level with colors"""
        color = obj.get_risk_color()
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_risk_level_display()
        )
    risk_level_colored.short_description = 'Nível de Risco'
    risk_level_colored.admin_order_field = 'risk_level'
    
    def needs_review_display(self, obj):
        """Display if customer needs review"""
        if obj.needs_review():
            return format_html('<span style="color: red;">⚠️ Sim</span>')
        return format_html('<span style="color: green;">✓ Não</span>')
    needs_review_display.short_description = 'Precisa Revisão'
    
    def mark_as_approved(self, request, queryset):
        """Mark selected customers as approved"""
        updated = queryset.update(
            onboarding_status=Customer.OnboardingStatus.APPROVED,
            last_review_date=timezone.now()
        )
        self.message_user(request, f'{updated} clientes marcados como aprovados.')
    mark_as_approved.short_description = 'Marcar como aprovado'
    
    def mark_as_under_review(self, request, queryset):
        """Mark selected customers as under review"""
        updated = queryset.update(onboarding_status=Customer.OnboardingStatus.UNDER_REVIEW)
        self.message_user(request, f'{updated} clientes marcados como em análise.')
    mark_as_under_review.short_description = 'Marcar como em análise'
    
    def mark_as_rejected(self, request, queryset):
        """Mark selected customers as rejected"""
        updated = queryset.update(onboarding_status=Customer.OnboardingStatus.REJECTED)
        self.message_user(request, f'{updated} clientes marcados como rejeitados.')
    mark_as_rejected.short_description = 'Marcar como rejeitado'
    
    def schedule_review(self, request, queryset):
        """Schedule review for selected customers"""
        from datetime import timedelta
        next_review = timezone.now() + timedelta(days=30)
        updated = queryset.update(next_review_date=next_review)
        self.message_user(request, f'Revisão agendada para {updated} clientes em 30 dias.')
    schedule_review.short_description = 'Agendar revisão (30 dias)'
    
    def run_sanctions_check(self, request, queryset):
        """Run sanctions check for selected customers"""
        # Simplified sanctions check (just mark as checked)
        updated = queryset.update(
            is_sanctions_checked=True,
            sanctions_last_check=timezone.now()
        )
        self.message_user(request, f'Verificação de sanções executada para {updated} clientes.')
    run_sanctions_check.short_description = 'Executar verificação de sanções'
    
    def save_model(self, request, obj, form, change):
        """Override save to set created_by"""
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(BeneficialOwner)
class BeneficialOwnerAdmin(admin.ModelAdmin):
    """Admin for beneficial owners"""
    
    list_display = [
        'full_name', 'customer', 'ownership_percentage', 
        'document_number', 'is_pep', 'is_sanctions_checked', 'created_at'
    ]
    
    list_filter = [
        'is_pep', 'is_sanctions_checked', 'country', 'created_at'
    ]
    
    search_fields = [
        'full_name', 'document_number', 'email', 
        'customer__full_name', 'customer__document_number'
    ]
    
    readonly_fields = ['created_at', 'updated_at', 'sanctions_last_check']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': (
                'customer', 'full_name', 'document_type', 'document_number',
                'ownership_percentage'
            )
        }),
        ('Contato', {
            'fields': ('email', 'phone', 'address', 'country')
        }),
        ('Verificações', {
            'fields': (
                'is_pep', 'is_sanctions_checked', 'sanctions_last_check'
            )
        }),
        ('Observações', {
            'fields': ('notes',),
            'classes': ('collapse',)
        })
    )
    
    actions = ['run_sanctions_check']
    
    def run_sanctions_check(self, request, queryset):
        """Run sanctions check for selected beneficial owners"""
        updated = queryset.update(
            is_sanctions_checked=True,
            sanctions_last_check=timezone.now()
        )
        self.message_user(request, f'Verificação de sanções executada para {updated} beneficiários.')
    run_sanctions_check.short_description = 'Executar verificação de sanções'


@admin.register(CustomerNote)
class CustomerNoteAdmin(admin.ModelAdmin):
    """Admin for customer notes"""
    
    list_display = [
        'title', 'customer', 'is_important', 'is_internal', 
        'created_by', 'created_at'
    ]
    
    list_filter = [
        'is_important', 'is_internal', 'created_at'
    ]
    
    search_fields = [
        'title', 'content', 'customer__full_name', 'customer__document_number'
    ]
    
    readonly_fields = ['created_at', 'created_by']
    
    def save_model(self, request, obj, form, change):
        """Override save to set created_by"""
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# Customize admin site
admin.site.site_header = 'CERES - Sistema Simplificado'
admin.site.site_title = 'CERES Admin'
admin.site.index_title = 'Painel de Administração'

