"""
CERES Simplified - Fase 4: Interface de Gestão de Clientes
Formulários intuitivos, filtros e busca avançada conforme especificação
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from django.contrib.admin import SimpleListFilter
from django.utils import timezone
from datetime import timedelta

from .models import Customer, BeneficialOwner


class RiskLevelFilter(SimpleListFilter):
    """Filtro customizado para nível de risco"""
    title = 'Nível de Risco'
    parameter_name = 'risk_level'

    def lookups(self, request, model_admin):
        return Customer.RISK_LEVEL_CHOICES

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(risk_level=self.value())
        return queryset


class OnboardingStatusFilter(SimpleListFilter):
    """Filtro para status de onboarding"""
    title = 'Status de Onboarding'
    parameter_name = 'onboarding_status'

    def lookups(self, request, model_admin):
        return Customer.ONBOARDING_STATUS_CHOICES

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(onboarding_status=self.value())
        return queryset


class BeneficialOwnerInline(admin.TabularInline):
    """Inline admin para beneficiários finais"""
    model = BeneficialOwner
    extra = 1
    fields = ('full_name', 'ownership_percentage', 'document_number')


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """
    Interface Avançada de Gestão de Clientes - Fase 4
    Formulários intuitivos, filtros e busca avançada
    """
    
    # Configuração da lista principal
    list_display = (
        'get_customer_name', 'customer_type', 'get_risk_badge', 
        'get_onboarding_badge', 'country', 'created_at'
    )
    
    # Filtros avançados conforme especificação
    list_filter = (
        RiskLevelFilter, OnboardingStatusFilter, 'customer_type',
        'country', 'is_pep', 'created_at'
    )
    
    # Busca avançada
    search_fields = (
        'first_name', 'last_name', 'company_name', 'email',
        'phone', 'document_number', 'tax_id'
    )
    
    # Ordenação padrão
    ordering = ('-created_at',)
    
    # Paginação
    list_per_page = 25
    
    # Formulários organizados conforme especificação
    fieldsets = (
        ('Informações Básicas', {
            'fields': (
                ('customer_type',),
                ('first_name', 'last_name'),
                ('company_name',),
                ('email', 'phone'),
            ),
            'classes': ('wide',),
        }),
        ('Documentação', {
            'fields': (
                ('document_type', 'document_number'),
                ('tax_id',),
            ),
            'classes': ('wide',)
        }),
        ('Localização', {
            'fields': (
                ('address', 'city'),
                ('state', 'country'),
                ('postal_code',),
            ),
            'classes': ('wide',)
        }),
        ('Informações de Negócio', {
            'fields': (
                ('industry', 'business_purpose'),
                ('date_of_birth',),
            ),
            'classes': ('wide',)
        }),
        ('Compliance e Risco', {
            'fields': (
                ('risk_level', 'onboarding_status'),
                ('is_pep',),
                ('next_review_date',),
            ),
            'classes': ('wide',)
        }),
    )
    
    # Campos somente leitura
    readonly_fields = ('created_at', 'updated_at')
    
    # Inlines para relacionamentos
    inlines = [BeneficialOwnerInline]
    
    # Ações em lote
    actions = ['approve_customers', 'mark_for_review', 'update_risk_high']
    
    def get_customer_name(self, obj):
        """Nome do cliente com link para edição"""
        if obj.customer_type == 'INDIVIDUAL':
            name = f"{obj.first_name} {obj.last_name}"
        else:
            name = obj.company_name or f"{obj.first_name} {obj.last_name}"
        
        url = reverse('admin:customers_customer_change', args=[obj.pk])
        return format_html(
            '<a href="{}" style="font-weight: bold; color: #3b82f6;">{}</a>',
            url, name
        )
    get_customer_name.short_description = 'Nome do Cliente'
    get_customer_name.admin_order_field = 'first_name'
    
    def get_risk_badge(self, obj):
        """Badge colorido para nível de risco"""
        colors = {
            'LOW': '#10b981',      # Verde
            'MEDIUM': '#f59e0b',   # Amarelo
            'HIGH': '#ef4444',     # Vermelho
            'CRITICAL': '#7c2d12'  # Vermelho escuro
        }
        color = colors.get(obj.risk_level, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color, obj.get_risk_level_display()
        )
    get_risk_badge.short_description = 'Risco'
    get_risk_badge.admin_order_field = 'risk_level'
    
    def get_onboarding_badge(self, obj):
        """Badge para status de onboarding"""
        colors = {
            'PENDING': '#f59e0b',                    # Amarelo
            'IN_PROGRESS': '#3b82f6',               # Azul
            'COMPLETED': '#10b981',                 # Verde
            'REQUIRES_MANUAL_REVIEW': '#8b5cf6',    # Roxo
            'REJECTED': '#ef4444'                   # Vermelho
        }
        color = colors.get(obj.onboarding_status, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color, obj.get_onboarding_status_display()
        )
    get_onboarding_badge.short_description = 'Onboarding'
    get_onboarding_badge.admin_order_field = 'onboarding_status'
    
    def get_queryset(self, request):
        """Otimização de consultas"""
        return super().get_queryset(request).prefetch_related('beneficial_owners')
    
    # Ações em lote
    def approve_customers(self, request, queryset):
        """Aprovar clientes selecionados"""
        updated = queryset.update(onboarding_status='COMPLETED')
        self.message_user(request, f'{updated} cliente(s) aprovado(s) com sucesso.')
    approve_customers.short_description = "Aprovar clientes selecionados"
    
    def mark_for_review(self, request, queryset):
        """Marcar para revisão manual"""
        updated = queryset.update(onboarding_status='REQUIRES_MANUAL_REVIEW')
        self.message_user(request, f'{updated} cliente(s) marcado(s) para revisão.')
    mark_for_review.short_description = "Marcar para revisão manual"
    
    def update_risk_high(self, request, queryset):
        """Atualizar risco para alto"""
        updated = queryset.update(risk_level='HIGH')
        self.message_user(request, f'{updated} cliente(s) marcado(s) como alto risco.')
    update_risk_high.short_description = "Marcar como alto risco"


@admin.register(BeneficialOwner)
class BeneficialOwnerAdmin(admin.ModelAdmin):
    """Admin para beneficiários finais"""
    
    list_display = (
        'full_name', 'customer', 'ownership_percentage', 'created_at'
    )
    
    list_filter = ('created_at',)
    
    search_fields = (
        'full_name', 'customer__first_name', 
        'customer__last_name', 'customer__company_name'
    )
    
    ordering = ('-created_at',)

