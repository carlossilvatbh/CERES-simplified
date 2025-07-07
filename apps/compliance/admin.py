"""
CERES Simplified - Compliance Admin
Admin interface for compliance management
"""

from django.contrib import admin

from .models import ComplianceRule, ComplianceCheck, ComplianceReport


@admin.register(ComplianceRule)
class ComplianceRuleAdmin(admin.ModelAdmin):
    """Admin for compliance rules"""
    list_display = ('name', 'rule_type', 'severity', 'auto_check', 'is_active')
    list_filter = ('rule_type', 'severity', 'auto_check', 'is_active')
    search_fields = ('name', 'description')
    ordering = ('name',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'rule_type')
        }),
        ('Configuration', {
            'fields': ('severity', 'auto_check', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ComplianceCheck)
class ComplianceCheckAdmin(admin.ModelAdmin):
    """Admin for compliance checks"""
    list_display = (
        'customer', 'rule', 'check_status', 'risk_score', 'check_date'
    )
    list_filter = ('check_status', 'rule__rule_type')
    search_fields = (
        'customer__first_name', 'customer__last_name', 'rule__name'
    )
    ordering = ('-check_date',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('customer', 'rule', 'check_status', 'risk_score')
        }),
        ('Results', {
            'fields': ('result_details',)
        }),
        ('Dates', {
            'fields': ('check_date', 'completed_date', 'next_check_date')
        }),
        ('User Tracking', {
            'fields': ('initiated_by', 'reviewed_by'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('check_date',)


@admin.register(ComplianceReport)
class ComplianceReportAdmin(admin.ModelAdmin):
    """Admin for compliance reports"""
    list_display = ('title', 'report_type', 'customer', 'status', 'created_at')
    list_filter = ('report_type', 'status', 'created_at')
    search_fields = (
        'title', 'description', 'customer__first_name', 'customer__last_name'
    )
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'report_type')
        }),
        ('Scope', {
            'fields': ('customer', 'period_start', 'period_end')
        }),
        ('Content', {
            'fields': ('content', 'summary', 'recommendations')
        }),
        ('Status', {
            'fields': ('status', 'approved_by', 'approved_at')
        }),
        ('Metadata', {
            'fields': ('created_at', 'created_by', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'approved_at')
