"""
CERES Simplified - Fase 4: Gestão de Documentos Simplificada
Interface para upload, visualização e aprovação de documentos
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from django.contrib.admin import SimpleListFilter
from django.utils import timezone

from .models import Document


class DocumentStatusFilter(SimpleListFilter):
    """Filtro customizado para status de documentos"""
    title = 'Status do Documento'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return Document.STATUS_CHOICES

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


class DocumentTypeFilter(SimpleListFilter):
    """Filtro customizado para tipos de documento"""
    title = 'Tipo de Documento'
    parameter_name = 'document_type'

    def lookups(self, request, model_admin):
        return Document.DOCUMENT_TYPE_CHOICES

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(document_type=self.value())
        return queryset


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """
    Interface de Gestão de Documentos - Fase 4
    Upload, visualização e aprovação de documentos
    """
    
    # Configuração da lista principal
    list_display = (
        'get_document_name', 'document_type', 'get_status_badge', 
        'customer', 'get_file_info', 'created_at'
    )
    
    # Filtros avançados
    list_filter = (
        DocumentStatusFilter, DocumentTypeFilter, 'created_at'
    )
    
    # Busca avançada
    search_fields = (
        'name', 'description', 'customer__first_name', 'customer__last_name',
        'customer__company_name'
    )
    
    # Ordenação padrão
    ordering = ('-created_at',)
    
    # Paginação
    list_per_page = 25
    
    # Formulários organizados
    fieldsets = (
        ('Informações do Documento', {
            'fields': (
                ('name', 'document_type'),
                ('customer', 'status'),
                'description',
            ),
            'classes': ('wide',),
        }),
        ('Arquivo', {
            'fields': (
                'file',
                'expiry_date',
            ),
            'classes': ('wide',)
        }),
    )
    
    # Campos somente leitura
    readonly_fields = ('created_at', 'updated_at')
    
    # Ações em lote
    actions = ['approve_documents', 'reject_documents', 'mark_for_review']
    
    def get_document_name(self, obj):
        """Nome do documento com ícone de tipo"""
        icons = {
            'ID': '🆔',
            'PASSPORT': '📘',
            'DRIVER_LICENSE': '🚗',
            'PROOF_OF_ADDRESS': '🏠',
            'BANK_STATEMENT': '🏦',
            'INCOME_PROOF': '💰',
            'BUSINESS_LICENSE': '📋',
            'ARTICLES_OF_INCORPORATION': '📄',
            'OTHER': '📎'
        }
        
        icon = icons.get(obj.document_type, '📎')
        url = reverse('admin:documents_document_change', args=[obj.pk])
        
        return format_html(
            '{} <a href="{}" style="font-weight: bold; color: #3b82f6;">{}</a>',
            icon, url, obj.name
        )
    get_document_name.short_description = 'Nome do Documento'
    get_document_name.admin_order_field = 'name'
    
    def get_status_badge(self, obj):
        """Badge colorido para status do documento"""
        colors = {
            'PENDING_REVIEW': '#f59e0b',     # Amarelo
            'PENDING_APPROVAL': '#8b5cf6',   # Roxo
            'APPROVED': '#10b981',           # Verde
            'REJECTED': '#ef4444',           # Vermelho
            'EXPIRED': '#7c2d12'             # Vermelho escuro
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    get_status_badge.short_description = 'Status'
    get_status_badge.admin_order_field = 'status'
    
    def get_file_info(self, obj):
        """Informações do arquivo"""
        if obj.file:
            return format_html(
                '<a href="{}" style="color: #3b82f6; text-decoration: none;" '
                'title="Download">📥 Download</a>',
                obj.file.url
            )
        return format_html('<span style="color: #ef4444;">Sem arquivo</span>')
    get_file_info.short_description = 'Arquivo'
    
    # Ações em lote
    def approve_documents(self, request, queryset):
        """Aprovar documentos selecionados"""
        updated = queryset.update(status='APPROVED')
        self.message_user(request, f'{updated} documento(s) aprovado(s) com sucesso.')
    approve_documents.short_description = "Aprovar documentos selecionados"
    
    def reject_documents(self, request, queryset):
        """Rejeitar documentos selecionados"""
        updated = queryset.update(status='REJECTED')
        self.message_user(request, f'{updated} documento(s) rejeitado(s).')
    reject_documents.short_description = "Rejeitar documentos selecionados"
    
    def mark_for_review(self, request, queryset):
        """Marcar para revisão"""
        updated = queryset.update(status='PENDING_REVIEW')
        self.message_user(request, f'{updated} documento(s) marcado(s) para revisão.')
    mark_for_review.short_description = "Marcar para revisão"

