"""
CERES Simplified - Fase 4: Interface de Case Management
Sistema de gestão de casos com interface customizada no Django Admin com 
visualização de casos por status, atribuição de responsáveis e acompanhamento de progresso
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from django.contrib.admin import SimpleListFilter
from django.utils import timezone
from datetime import timedelta
from django.http import HttpResponse
from django.contrib.auth.models import User
import csv

from .models import Case, CaseType


class CaseStatusFilter(SimpleListFilter):
    """Filtro customizado para status de casos"""
    title = 'Status do Caso'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return Case.Status.choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


class CasePriorityFilter(SimpleListFilter):
    """Filtro customizado para prioridade de casos"""
    title = 'Prioridade'
    parameter_name = 'priority'

    def lookups(self, request, model_admin):
        return Case.Priority.choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(priority=self.value())
        return queryset


class AssignedToFilter(SimpleListFilter):
    """Filtro por responsável atribuído"""
    title = 'Responsável'
    parameter_name = 'assigned_to'

    def lookups(self, request, model_admin):
        users = User.objects.filter(
            assigned_cases__isnull=False
        ).distinct()
        return [(user.id, user.get_full_name() or user.username) for user in users]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(assigned_to_id=self.value())
        return queryset


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    """
    Interface Avançada de Case Management - Fase 4
    Visualização de casos por status, atribuição de responsáveis e acompanhamento de progresso
    """
    
    # Configuração da lista principal
    list_display = (
        'get_case_number', 'title', 'get_status_badge', 'get_priority_badge',
        'customer', 'get_assigned_to', 'get_age', 'get_progress_bar'
    )
    
    # Filtros avançados conforme especificação
    list_filter = (
        CaseStatusFilter, CasePriorityFilter, AssignedToFilter, 
        'case_type', 'created_at', 'due_date'
    )
    
    # Busca avançada
    search_fields = (
        'case_number', 'title', 'description', 'customer__first_name',
        'customer__last_name', 'customer__company_name', 'assigned_to__username',
        'assigned_to__first_name', 'assigned_to__last_name'
    )
    
    # Ordenação padrão
    ordering = ('-created_at',)
    
    # Paginação
    list_per_page = 25
    
    # Formulários organizados conforme especificação
    fieldsets = (
        ('Informações do Caso', {
            'fields': (
                ('case_number', 'status'),
                ('title', 'priority'),
                ('case_type', 'customer'),
            ),
            'classes': ('wide',),
        }),
        ('Atribuição e Prazos', {
            'fields': (
                ('assigned_to', 'created_by'),
                ('due_date',),
            ),
            'classes': ('wide',)
        }),
        ('Descrição e Detalhes', {
            'fields': (
                'description',
                'resolution_notes',
            ),
            'classes': ('wide',)
        }),
    )
    
    # Campos somente leitura
    readonly_fields = ('case_number', 'created_at', 'updated_at')
    
    # Ações em lote conforme especificação
    actions = [
        'assign_to_me', 'mark_in_progress', 'mark_resolved', 'close_cases'
    ]
    
    def get_case_number(self, obj):
        """Número do caso com link para edição"""
        url = reverse('admin:cases_case_change', args=[obj.pk])
        return format_html(
            '<a href="{}" style="font-weight: bold; color: #3b82f6;">{}</a>',
            url, obj.case_number
        )
    get_case_number.short_description = 'Número do Caso'
    get_case_number.admin_order_field = 'case_number'
    
    def get_status_badge(self, obj):
        """Badge colorido para status do caso"""
        colors = {
            'OPEN': '#3b82f6',           # Azul
            'IN_PROGRESS': '#f59e0b',    # Amarelo
            'UNDER_REVIEW': '#8b5cf6',   # Roxo
            'RESOLVED': '#10b981',       # Verde
            'CLOSED': '#6b7280'          # Cinza
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    get_status_badge.short_description = 'Status'
    get_status_badge.admin_order_field = 'status'
    
    def get_priority_badge(self, obj):
        """Badge colorido para prioridade"""
        colors = {
            'LOW': '#10b981',      # Verde
            'MEDIUM': '#f59e0b',   # Amarelo
            'HIGH': '#ef4444',     # Vermelho
            'CRITICAL': '#7c2d12'  # Vermelho escuro
        }
        color = colors.get(obj.priority, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color, obj.get_priority_display()
        )
    get_priority_badge.short_description = 'Prioridade'
    get_priority_badge.admin_order_field = 'priority'
    
    def get_assigned_to(self, obj):
        """Responsável atribuído"""
        if obj.assigned_to:
            name = obj.assigned_to.get_full_name() or obj.assigned_to.username
            return format_html(
                '<span style="font-weight: 500;">{}</span>', name
            )
        return format_html(
            '<span style="color: #ef4444; font-style: italic;">Não atribuído</span>'
        )
    get_assigned_to.short_description = 'Responsável'
    get_assigned_to.admin_order_field = 'assigned_to'
    
    def get_age(self, obj):
        """Idade do caso"""
        age = timezone.now() - obj.created_at
        days = age.days
        
        if days == 0:
            age_text = "Hoje"
            color = "#10b981"
        elif days == 1:
            age_text = "1 dia"
            color = "#3b82f6"
        elif days <= 7:
            age_text = f"{days} dias"
            color = "#f59e0b"
        else:
            age_text = f"{days} dias"
            color = "#ef4444"
        
        return format_html(
            '<span style="color: {}; font-weight: 600;">{}</span>',
            color, age_text
        )
    get_age.short_description = 'Idade'
    get_age.admin_order_field = 'created_at'
    
    def get_progress_bar(self, obj):
        """Barra de progresso baseada no status"""
        progress_map = {
            'OPEN': 10,
            'IN_PROGRESS': 50,
            'UNDER_REVIEW': 80,
            'RESOLVED': 95,
            'CLOSED': 100
        }
        
        progress = progress_map.get(obj.status, 0)
        color = '#10b981' if progress == 100 else '#3b82f6'
        
        return format_html(
            '<div style="width: 80px; height: 8px; background: #e5e7eb; '
            'border-radius: 4px; overflow: hidden;">'
            '<div style="width: {}%; height: 100%; background: {};"></div>'
            '</div>',
            progress, color
        )
    get_progress_bar.short_description = 'Progresso'
    
    def save_model(self, request, obj, form, change):
        """Lógica de salvamento customizada"""
        if not change:
            obj.created_by = request.user
            # Auto-gerar número do caso se não existir
            if not obj.case_number:
                last_case = Case.objects.order_by('-created_at').first()
                next_number = 1
                if last_case and last_case.case_number:
                    try:
                        last_num = int(last_case.case_number.split('-')[-1])
                        next_number = last_num + 1
                    except:
                        pass
                obj.case_number = f"CASE-{next_number:06d}"
        
        # Atualizar timestamps baseado no status
        if obj.status == 'RESOLVED' and not obj.resolved_at:
            obj.resolved_at = timezone.now()
            obj.resolved_by = request.user
        elif obj.status == 'CLOSED' and not obj.closed_at:
            obj.closed_at = timezone.now()
        
        super().save_model(request, obj, form, change)
    
    # Ações em lote
    def assign_to_me(self, request, queryset):
        """Atribuir casos selecionados ao usuário atual"""
        updated = queryset.update(assigned_to=request.user)
        self.message_user(request, f'{updated} caso(s) atribuído(s) a você.')
    assign_to_me.short_description = "Atribuir a mim"
    
    def mark_in_progress(self, request, queryset):
        """Marcar casos como em progresso"""
        updated = queryset.update(status='IN_PROGRESS')
        self.message_user(request, f'{updated} caso(s) marcado(s) como em progresso.')
    mark_in_progress.short_description = "Marcar como em progresso"
    
    def mark_resolved(self, request, queryset):
        """Marcar casos como resolvidos"""
        updated = queryset.update(
            status='RESOLVED',
            resolved_at=timezone.now(),
            resolved_by=request.user
        )
        self.message_user(request, f'{updated} caso(s) marcado(s) como resolvido(s).')
    mark_resolved.short_description = "Marcar como resolvido"
    
    def close_cases(self, request, queryset):
        """Fechar casos selecionados"""
        updated = queryset.update(
            status='CLOSED',
            closed_at=timezone.now()
        )
        self.message_user(request, f'{updated} caso(s) fechado(s).')
    close_cases.short_description = "Fechar casos"


@admin.register(CaseType)
class CaseTypeAdmin(admin.ModelAdmin):
    """Admin para tipos de casos"""
    
    list_display = ('name', 'default_priority', 'auto_assign', 'sla_hours', 'is_active')
    list_filter = ('default_priority', 'auto_assign', 'is_active')
    search_fields = ('name', 'description')
    ordering = ('name',)

