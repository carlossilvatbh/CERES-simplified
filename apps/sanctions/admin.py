"""
CERES Simplified - Sanctions Screening Admin
Customized Django Admin for sanctions screening management
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Count
from .models import SanctionsList, SanctionsEntry, SanctionsCheck, SanctionsMatch


class SanctionsEntryInline(admin.TabularInline):
    """Inline admin for sanctions entries"""
    model = SanctionsEntry
    extra = 0
    fields = ['primary_name', 'entry_type', 'nationality', 'is_active']
    readonly_fields = ['created_at']


class SanctionsMatchInline(admin.TabularInline):
    """Inline admin for sanctions matches"""
    model = SanctionsMatch
    extra = 0
    fields = [
        'sanctions_entry', 'match_type', 'match_score', 
        'review_status', 'matched_value'
    ]
    readonly_fields = ['created_at']


@admin.register(SanctionsList)
class SanctionsListAdmin(admin.ModelAdmin):
    """Admin for sanctions lists"""
    
    list_display = [
        'name', 'list_type', 'entries_count', 'is_active',
        'last_updated', 'needs_update_display'
    ]
    
    list_filter = ['list_type', 'is_active', 'auto_update', 'last_updated']
    search_fields = ['name', 'description']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('name', 'description', 'list_type')
        }),
        ('Configuração', {
            'fields': ('source_url', 'is_active', 'auto_update')
        }),
        ('Atualização', {
            'fields': ('last_updated', 'update_frequency_days')
        })
    )
    
    readonly_fields = ['last_updated']
    inlines = [SanctionsEntryInline]
    
    actions = ['mark_as_updated', 'activate_lists', 'deactivate_lists']
    
    def get_queryset(self, request):
        """Optimize queryset with entry count"""
        return super().get_queryset(request).annotate(
            entries_count=Count('entries')
        )
    
    def entries_count(self, obj):
        """Display number of entries"""
        return obj.entries_count
    entries_count.short_description = 'Entradas'
    entries_count.admin_order_field = 'entries_count'
    
    def needs_update_display(self, obj):
        """Display if list needs update"""
        if obj.needs_update():
            return format_html('<span style="color: red;">⚠️ Sim</span>')
        return format_html('<span style="color: green;">✓ Não</span>')
    needs_update_display.short_description = 'Precisa Atualizar'
    
    def mark_as_updated(self, request, queryset):
        """Mark selected lists as updated"""
        updated = queryset.update(last_updated=timezone.now())
        self.message_user(request, f'{updated} listas marcadas como atualizadas.')
    mark_as_updated.short_description = 'Marcar como atualizada'
    
    def activate_lists(self, request, queryset):
        """Activate selected lists"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} listas ativadas.')
    activate_lists.short_description = 'Ativar listas'
    
    def deactivate_lists(self, request, queryset):
        """Deactivate selected lists"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} listas desativadas.')
    deactivate_lists.short_description = 'Desativar listas'


@admin.register(SanctionsEntry)
class SanctionsEntryAdmin(admin.ModelAdmin):
    """Admin for sanctions entries"""
    
    list_display = [
        'primary_name', 'entry_type', 'sanctions_list',
        'nationality', 'listing_date', 'is_active'
    ]
    
    list_filter = [
        'entry_type', 'sanctions_list', 'nationality',
        'is_active', 'listing_date'
    ]
    
    search_fields = [
        'primary_name', 'alternative_names', 'passport_number',
        'national_id', 'external_id'
    ]
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': (
                'sanctions_list', 'entry_type', 'primary_name',
                'alternative_names'
            )
        }),
        ('Identificação', {
            'fields': (
                'date_of_birth', 'place_of_birth', 'nationality',
                'passport_number', 'national_id'
            )
        }),
        ('Endereço', {
            'fields': ('address',),
            'classes': ('collapse',)
        }),
        ('Sanções', {
            'fields': (
                'sanctions_program', 'listing_date', 'external_id'
            )
        }),
        ('Status', {
            'fields': ('is_active',)
        })
    )
    
    actions = ['activate_entries', 'deactivate_entries']
    
    def activate_entries(self, request, queryset):
        """Activate selected entries"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} entradas ativadas.')
    activate_entries.short_description = 'Ativar entradas'
    
    def deactivate_entries(self, request, queryset):
        """Deactivate selected entries"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} entradas desativadas.')
    deactivate_entries.short_description = 'Desativar entradas'


@admin.register(SanctionsCheck)
class SanctionsCheckAdmin(admin.ModelAdmin):
    """Admin for sanctions checks"""
    
    list_display = [
        'get_target_name', 'check_type', 'match_status_colored',
        'total_matches', 'check_status', 'check_date'
    ]
    
    list_filter = [
        'check_type', 'check_status', 'match_status',
        'check_date'
    ]
    
    search_fields = [
        'search_name', 'search_document',
        'customer__full_name', 'beneficial_owner__full_name'
    ]
    
    readonly_fields = ['check_date', 'completed_date', 'total_matches']
    
    fieldsets = (
        ('Alvo da Verificação', {
            'fields': (
                'check_type', 'customer', 'beneficial_owner'
            )
        }),
        ('Parâmetros de Busca', {
            'fields': (
                'search_name', 'search_document', 'search_date_of_birth'
            )
        }),
        ('Status', {
            'fields': (
                'check_status', 'match_status', 'total_matches'
            )
        }),
        ('Listas Verificadas', {
            'fields': ('lists_checked',)
        }),
        ('Datas', {
            'fields': ('check_date', 'completed_date'),
            'classes': ('collapse',)
        }),
        ('Observações', {
            'fields': ('notes',),
            'classes': ('collapse',)
        })
    )
    
    filter_horizontal = ['lists_checked']
    inlines = [SanctionsMatchInline]
    
    actions = [
        'mark_as_completed', 'mark_as_no_match', 
        'mark_as_false_positive'
    ]
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related(
            'customer', 'beneficial_owner', 'initiated_by', 'reviewed_by'
        ).prefetch_related('lists_checked', 'matches')
    
    def match_status_colored(self, obj):
        """Display match status with colors"""
        colors = {
            'NO_MATCH': 'green',
            'POTENTIAL_MATCH': 'orange',
            'CONFIRMED_MATCH': 'red',
            'FALSE_POSITIVE': 'gray',
        }
        color = colors.get(obj.match_status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_match_status_display()
        )
    match_status_colored.short_description = 'Status da Correspondência'
    match_status_colored.admin_order_field = 'match_status'
    
    def mark_as_completed(self, request, queryset):
        """Mark selected checks as completed"""
        updated = queryset.update(
            check_status=SanctionsCheck.CheckStatus.COMPLETED,
            completed_date=timezone.now()
        )
        self.message_user(request, f'{updated} verificações marcadas como concluídas.')
    mark_as_completed.short_description = 'Marcar como concluída'
    
    def mark_as_no_match(self, request, queryset):
        """Mark selected checks as no match"""
        updated = queryset.update(
            match_status=SanctionsCheck.MatchStatus.NO_MATCH,
            check_status=SanctionsCheck.CheckStatus.COMPLETED,
            completed_date=timezone.now()
        )
        self.message_user(request, f'{updated} verificações marcadas como sem correspondência.')
    mark_as_no_match.short_description = 'Marcar como sem correspondência'
    
    def mark_as_false_positive(self, request, queryset):
        """Mark selected checks as false positive"""
        updated = queryset.update(
            match_status=SanctionsCheck.MatchStatus.FALSE_POSITIVE,
            reviewed_by=request.user
        )
        self.message_user(request, f'{updated} verificações marcadas como falso positivo.')
    mark_as_false_positive.short_description = 'Marcar como falso positivo'
    
    def save_model(self, request, obj, form, change):
        """Override save to set initiated_by"""
        if not change:  # New object
            obj.initiated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(SanctionsMatch)
class SanctionsMatchAdmin(admin.ModelAdmin):
    """Admin for sanctions matches"""
    
    list_display = [
        'sanctions_check', 'sanctions_entry', 'match_type',
        'match_score_colored', 'review_status_colored', 'created_at'
    ]
    
    list_filter = [
        'match_type', 'review_status', 'match_score', 'created_at'
    ]
    
    search_fields = [
        'matched_value', 'sanctions_entry__primary_name',
        'sanctions_check__search_name', 'review_notes'
    ]
    
    readonly_fields = ['created_at', 'reviewed_at']
    
    fieldsets = (
        ('Correspondência', {
            'fields': (
                'sanctions_check', 'sanctions_entry', 'match_type',
                'match_score', 'matched_field', 'matched_value'
            )
        }),
        ('Revisão', {
            'fields': (
                'review_status', 'review_notes', 'reviewed_by', 'reviewed_at'
            )
        })
    )
    
    actions = [
        'confirm_matches', 'mark_as_false_positive', 
        'mark_needs_investigation'
    ]
    
    def match_score_colored(self, obj):
        """Display match score with colors"""
        if obj.match_score >= 80:
            color = 'red'
        elif obj.match_score >= 60:
            color = 'orange'
        else:
            color = 'green'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}%</span>',
            color, obj.match_score
        )
    match_score_colored.short_description = 'Score'
    match_score_colored.admin_order_field = 'match_score'
    
    def review_status_colored(self, obj):
        """Display review status with colors"""
        colors = {
            'PENDING': 'orange',
            'CONFIRMED': 'red',
            'FALSE_POSITIVE': 'green',
            'NEEDS_INVESTIGATION': 'purple',
        }
        color = colors.get(obj.review_status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_review_status_display()
        )
    review_status_colored.short_description = 'Status da Revisão'
    review_status_colored.admin_order_field = 'review_status'
    
    def confirm_matches(self, request, queryset):
        """Confirm selected matches"""
        updated = queryset.update(
            review_status=SanctionsMatch.ReviewStatus.CONFIRMED,
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'{updated} correspondências confirmadas.')
    confirm_matches.short_description = 'Confirmar correspondências'
    
    def mark_as_false_positive(self, request, queryset):
        """Mark selected matches as false positive"""
        updated = queryset.update(
            review_status=SanctionsMatch.ReviewStatus.FALSE_POSITIVE,
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'{updated} correspondências marcadas como falso positivo.')
    mark_as_false_positive.short_description = 'Marcar como falso positivo'
    
    def mark_needs_investigation(self, request, queryset):
        """Mark selected matches as needing investigation"""
        updated = queryset.update(
            review_status=SanctionsMatch.ReviewStatus.NEEDS_INVESTIGATION,
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'{updated} correspondências marcadas para investigação.')
    mark_needs_investigation.short_description = 'Marcar para investigação'

