"""
CERES Simplified - Risk Assessment Admin
Customized Django Admin for risk assessment management
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import RiskFactor, RiskAssessment, RiskFactorApplication, RiskMatrix


class RiskFactorApplicationInline(admin.TabularInline):
    """Inline admin for risk factor applications"""
    model = RiskFactorApplication
    extra = 0
    fields = ['factor', 'applied_weight', 'justification']
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing existing
            return ['applied_by', 'applied_at']
        return []


@admin.register(RiskFactor)
class RiskFactorAdmin(admin.ModelAdmin):
    """Admin for risk factors"""
    
    list_display = [
        'name', 'factor_type', 'risk_weight_colored', 
        'is_active', 'created_at'
    ]
    
    list_filter = ['factor_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('name', 'description', 'factor_type')
        }),
        ('Configuração de Risco', {
            'fields': ('risk_weight', 'is_active')
        }),
    )
    
    def risk_weight_colored(self, obj):
        """Display risk weight with colors"""
        if obj.risk_weight > 0:
            color = 'red'
            symbol = '+'
        elif obj.risk_weight < 0:
            color = 'green'
            symbol = ''
        else:
            color = 'gray'
            symbol = ''
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}{}</span>',
            color, symbol, obj.risk_weight
        )
    risk_weight_colored.short_description = 'Peso do Risco'
    risk_weight_colored.admin_order_field = 'risk_weight'


@admin.register(RiskAssessment)
class RiskAssessmentAdmin(admin.ModelAdmin):
    """Admin for risk assessments"""
    
    list_display = [
        'customer', 'assessment_type', 'risk_level_colored',
        'final_score', 'is_current', 'is_approved', 'assessment_date'
    ]
    
    list_filter = [
        'assessment_type', 'risk_level', 'is_current', 
        'is_approved', 'requires_approval', 'assessment_date'
    ]
    
    search_fields = [
        'customer__full_name', 'customer__document_number',
        'justification', 'notes'
    ]
    
    readonly_fields = [
        'risk_level', 'assessment_date', 'approved_at'
    ]
    
    fieldsets = (
        ('Cliente e Tipo', {
            'fields': ('customer', 'assessment_type')
        }),
        ('Avaliação de Risco', {
            'fields': (
                'base_score', 'final_score', 'risk_level',
                'methodology', 'justification'
            )
        }),
        ('Validade', {
            'fields': ('assessment_date', 'valid_until', 'is_current')
        }),
        ('Aprovação', {
            'fields': (
                'requires_approval', 'is_approved', 
                'approved_by', 'approved_at'
            ),
            'classes': ('collapse',)
        }),
        ('Observações', {
            'fields': ('notes',),
            'classes': ('collapse',)
        })
    )
    
    inlines = [RiskFactorApplicationInline]
    
    actions = ['approve_assessments', 'mark_as_current']
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related(
            'customer', 'assessed_by', 'approved_by'
        ).prefetch_related('applied_factors')
    
    def risk_level_colored(self, obj):
        """Display risk level with colors"""
        color = obj.get_risk_color()
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_risk_level_display()
        )
    risk_level_colored.short_description = 'Nível de Risco'
    risk_level_colored.admin_order_field = 'risk_level'
    
    def approve_assessments(self, request, queryset):
        """Approve selected assessments"""
        updated = queryset.update(
            is_approved=True,
            approved_by=request.user,
            approved_at=timezone.now()
        )
        self.message_user(request, f'{updated} avaliações aprovadas.')
    approve_assessments.short_description = 'Aprovar avaliações selecionadas'
    
    def mark_as_current(self, request, queryset):
        """Mark selected assessments as current"""
        for assessment in queryset:
            # Mark others as not current for the same customer
            RiskAssessment.objects.filter(
                customer=assessment.customer,
                is_current=True
            ).update(is_current=False)
            
            # Mark this one as current
            assessment.is_current = True
            assessment.save()
        
        self.message_user(request, f'{queryset.count()} avaliações marcadas como atuais.')
    mark_as_current.short_description = 'Marcar como avaliação atual'
    
    def save_model(self, request, obj, form, change):
        """Override save to set assessed_by"""
        if not change:  # New object
            obj.assessed_by = request.user
        
        # Calculate final score if not set
        if not obj.final_score:
            obj.final_score = obj.base_score
        
        super().save_model(request, obj, form, change)


@admin.register(RiskFactorApplication)
class RiskFactorApplicationAdmin(admin.ModelAdmin):
    """Admin for risk factor applications"""
    
    list_display = [
        'risk_assessment', 'factor', 'applied_weight',
        'applied_by', 'applied_at'
    ]
    
    list_filter = ['factor__factor_type', 'applied_at']
    
    search_fields = [
        'risk_assessment__customer__full_name',
        'factor__name', 'justification'
    ]
    
    readonly_fields = ['applied_at']
    
    def save_model(self, request, obj, form, change):
        """Override save to set applied_by"""
        if not change:  # New object
            obj.applied_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(RiskMatrix)
class RiskMatrixAdmin(admin.ModelAdmin):
    """Admin for risk matrices"""
    
    list_display = [
        'name', 'customer_type', 'low_risk_threshold',
        'medium_risk_threshold', 'high_risk_threshold', 'is_active'
    ]
    
    list_filter = ['customer_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('name', 'description', 'customer_type')
        }),
        ('Limites de Risco', {
            'fields': (
                'low_risk_threshold', 'medium_risk_threshold', 
                'high_risk_threshold'
            )
        }),
        ('Configuração', {
            'fields': ('default_factors', 'is_active')
        })
    )
    
    filter_horizontal = ['default_factors']

