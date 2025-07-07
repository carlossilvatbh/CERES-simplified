"""
CERES Simplified - Fase 4: Dashboard de Risk Assessment
Dashboard simples que mostre distribuição de clientes por nível de risco, 
casos pendentes, documentos aguardando aprovação e outras métricas básicas
"""

from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import path
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from django.contrib.admin import AdminSite
from django.shortcuts import render

from apps.customers.models import Customer
from apps.cases.models import Case
from apps.documents.models import Document
from apps.risk.models import RiskAssessment


class CERESAdminSite(AdminSite):
    """
    Site Admin customizado com Dashboard de Risk Assessment - Fase 4
    """
    site_header = "CERES Simplified - Sistema de Compliance"
    site_title = "CERES Admin"
    index_title = "Dashboard de Risk Assessment e Compliance"
    
    def get_urls(self):
        """URLs customizadas incluindo dashboard"""
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_view(self.dashboard_view), name='dashboard'),
            path('risk-metrics/', self.admin_view(self.risk_metrics_view), name='risk_metrics'),
        ]
        return custom_urls + urls
    
    def index(self, request, extra_context=None):
        """
        Página inicial customizada com Dashboard de Risk Assessment
        Conforme especificação da Fase 4
        """
        extra_context = extra_context or {}
        
        # Métricas de clientes por nível de risco
        risk_distribution = Customer.objects.values('risk_level').annotate(
            count=Count('id')
        ).order_by('risk_level')
        
        # Casos pendentes por status
        case_stats = Case.objects.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        # Documentos aguardando aprovação
        pending_documents = Document.objects.filter(
            status='PENDING_APPROVAL'
        ).count()
        
        # Clientes que requerem revisão manual
        manual_review_customers = Customer.objects.filter(
            onboarding_status='REQUIRES_MANUAL_REVIEW'
        ).count()
        
        # Clientes de alto risco
        high_risk_customers = Customer.objects.filter(
            risk_level__in=['HIGH', 'CRITICAL']
        ).count()
        
        # Avaliações de risco recentes (últimos 7 dias)
        week_ago = timezone.now() - timedelta(days=7)
        recent_assessments = RiskAssessment.objects.filter(
            assessment_date__gte=week_ago
        ).count()
        
        # Clientes criados hoje
        today_customers = Customer.objects.filter(
            created_at__date=timezone.now().date()
        ).count()
        
        # Clientes criados esta semana
        week_customers = Customer.objects.filter(
            created_at__gte=week_ago
        ).count()
        
        # Clientes PEP (Pessoas Politicamente Expostas)
        pep_customers = Customer.objects.filter(is_pep=True).count()
        
        # Próximas revisões (próximos 30 dias)
        next_month = timezone.now() + timedelta(days=30)
        upcoming_reviews = Customer.objects.filter(
            next_review_date__lte=next_month,
            next_review_date__gte=timezone.now()
        ).count()
        
        # Preparar dados para gráficos
        risk_chart_data = {
            'labels': [],
            'data': [],
            'colors': []
        }
        
        risk_colors = {
            'LOW': '#10b981',
            'MEDIUM': '#f59e0b', 
            'HIGH': '#ef4444',
            'CRITICAL': '#7c2d12'
        }
        
        for item in risk_distribution:
            risk_level = item['risk_level']
            risk_chart_data['labels'].append(
                dict(Customer.RISK_LEVEL_CHOICES).get(risk_level, risk_level)
            )
            risk_chart_data['data'].append(item['count'])
            risk_chart_data['colors'].append(risk_colors.get(risk_level, '#6b7280'))
        
        # Dados para gráfico de casos
        case_chart_data = {
            'labels': [],
            'data': [],
            'colors': []
        }
        
        case_colors = {
            'OPEN': '#3b82f6',
            'IN_PROGRESS': '#f59e0b',
            'PENDING_REVIEW': '#8b5cf6',
            'RESOLVED': '#10b981',
            'CLOSED': '#6b7280'
        }
        
        for item in case_stats:
            status = item['status']
            case_chart_data['labels'].append(
                dict(Case.STATUS_CHOICES).get(status, status)
            )
            case_chart_data['data'].append(item['count'])
            case_chart_data['colors'].append(case_colors.get(status, '#6b7280'))
        
        # Alertas e notificações
        alerts = []
        
        if high_risk_customers > 0:
            alerts.append({
                'type': 'warning',
                'message': f'{high_risk_customers} cliente(s) de alto risco requerem atenção',
                'action_url': '/admin/customers/customer/?risk_level__in=HIGH%2CCRITICAL',
                'action_text': 'Ver Clientes'
            })
        
        if manual_review_customers > 0:
            alerts.append({
                'type': 'info',
                'message': f'{manual_review_customers} cliente(s) aguardando revisão manual',
                'action_url': '/admin/customers/customer/?onboarding_status__exact=REQUIRES_MANUAL_REVIEW',
                'action_text': 'Revisar'
            })
        
        if pending_documents > 0:
            alerts.append({
                'type': 'info',
                'message': f'{pending_documents} documento(s) aguardando aprovação',
                'action_url': '/admin/documents/document/?status__exact=PENDING_APPROVAL',
                'action_text': 'Aprovar'
            })
        
        if upcoming_reviews > 0:
            alerts.append({
                'type': 'info',
                'message': f'{upcoming_reviews} cliente(s) com revisão agendada nos próximos 30 dias',
                'action_url': '/admin/customers/customer/?next_review_date__lte=' + next_month.strftime('%Y-%m-%d'),
                'action_text': 'Ver Agenda'
            })
        
        # Estatísticas resumidas
        stats_cards = [
            {
                'title': 'Total de Clientes',
                'value': Customer.objects.count(),
                'description': f'{today_customers} novos hoje',
                'color': '#3b82f6',
                'icon': '👥'
            },
            {
                'title': 'Alto Risco',
                'value': high_risk_customers,
                'description': 'Clientes críticos',
                'color': '#ef4444',
                'icon': '⚠️'
            },
            {
                'title': 'Casos Ativos',
                'value': Case.objects.filter(status__in=['OPEN', 'IN_PROGRESS']).count(),
                'description': 'Requerem ação',
                'color': '#f59e0b',
                'icon': '📋'
            },
            {
                'title': 'Docs Pendentes',
                'value': pending_documents,
                'description': 'Aguardando aprovação',
                'color': '#8b5cf6',
                'icon': '📄'
            },
            {
                'title': 'Avaliações (7d)',
                'value': recent_assessments,
                'description': 'Última semana',
                'color': '#10b981',
                'icon': '🔍'
            },
            {
                'title': 'Clientes PEP',
                'value': pep_customers,
                'description': 'Politicamente expostos',
                'color': '#dc2626',
                'icon': '🏛️'
            }
        ]
        
        extra_context.update({
            'stats_cards': stats_cards,
            'risk_chart_data': risk_chart_data,
            'case_chart_data': case_chart_data,
            'alerts': alerts,
            'manual_review_customers': manual_review_customers,
            'pending_documents': pending_documents,
            'high_risk_customers': high_risk_customers,
            'recent_assessments': recent_assessments,
            'today_customers': today_customers,
            'week_customers': week_customers,
            'upcoming_reviews': upcoming_reviews,
            'pep_customers': pep_customers,
        })
        
        return super().index(request, extra_context)
    
    def dashboard_view(self, request):
        """
        View detalhada do dashboard com métricas avançadas
        """
        # Tendências dos últimos 30 dias
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # Clientes por dia (últimos 30 dias)
        daily_customers = []
        for i in range(30):
            date = timezone.now() - timedelta(days=i)
            count = Customer.objects.filter(
                created_at__date=date.date()
            ).count()
            daily_customers.append({
                'date': date.strftime('%d/%m'),
                'count': count
            })
        daily_customers.reverse()
        
        # Distribuição por país (top 10)
        country_distribution = Customer.objects.values('country').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # Distribuição por indústria (top 10)
        industry_distribution = Customer.objects.values('industry').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # Performance de onboarding
        onboarding_stats = Customer.objects.values('onboarding_status').annotate(
            count=Count('id')
        ).order_by('onboarding_status')
        
        context = {
            'title': 'Dashboard Detalhado de Risk Assessment',
            'daily_customers': daily_customers,
            'country_distribution': country_distribution,
            'industry_distribution': industry_distribution,
            'onboarding_stats': onboarding_stats,
        }
        
        return TemplateResponse(request, 'admin/dashboard_detailed.html', context)
    
    def risk_metrics_view(self, request):
        """
        View específica para métricas de risco
        """
        # Distribuição detalhada de risco
        risk_metrics = {}
        
        for level, display in Customer.RISK_LEVEL_CHOICES:
            customers = Customer.objects.filter(risk_level=level)
            risk_metrics[level] = {
                'display': display,
                'count': customers.count(),
                'percentage': round(customers.count() / Customer.objects.count() * 100, 1) if Customer.objects.count() > 0 else 0,
                'recent': customers.filter(
                    created_at__gte=timezone.now() - timedelta(days=7)
                ).count()
            }
        
        # Avaliações de risco por período
        assessment_trends = []
        for i in range(12):  # Últimos 12 meses
            date = timezone.now() - timedelta(days=30*i)
            count = RiskAssessment.objects.filter(
                assessment_date__year=date.year,
                assessment_date__month=date.month
            ).count()
            assessment_trends.append({
                'month': date.strftime('%m/%Y'),
                'count': count
            })
        assessment_trends.reverse()
        
        context = {
            'title': 'Métricas Detalhadas de Risco',
            'risk_metrics': risk_metrics,
            'assessment_trends': assessment_trends,
        }
        
        return TemplateResponse(request, 'admin/risk_metrics.html', context)


# Instância customizada do admin site
admin_site = CERESAdminSite(name='ceres_admin')

# Registrar modelos no site customizado
from apps.customers.admin import CustomerAdmin, BeneficialOwnerAdmin
from apps.customers.models import Customer, BeneficialOwner

admin_site.register(Customer, CustomerAdmin)
admin_site.register(BeneficialOwner, BeneficialOwnerAdmin)

