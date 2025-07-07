"""
CERES Simplified - Daily Automated Tasks
Management command for running daily business logic automation
"""

import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta

from apps.customers.models import Customer
from apps.risk.services import RiskCalculationService, RiskMonitoringService
from apps.sanctions.services import SanctionsScreeningService
from apps.compliance.services import ComplianceWorkflowService
from apps.compliance.models import ComplianceAlert

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run daily automated tasks for CERES system'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run in dry-run mode without making changes',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output',
        )
    
    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.verbose = options['verbose']
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING('Running in DRY-RUN mode'))
        
        self.stdout.write(self.style.SUCCESS('Starting daily automated tasks...'))
        
        try:
            # Task 1: Check overdue risk assessments
            self._check_overdue_risk_assessments()
            
            # Task 2: Run periodic sanctions screening
            self._run_periodic_sanctions_screening()
            
            # Task 3: Process compliance reviews
            self._process_compliance_reviews()
            
            # Task 4: Clean up old alerts
            self._cleanup_old_alerts()
            
            # Task 5: Generate daily metrics
            self._generate_daily_metrics()
            
            self.stdout.write(self.style.SUCCESS('Daily automated tasks completed successfully'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error in daily tasks: {str(e)}'))
            logger.error(f'Error in daily automated tasks: {str(e)}')
            raise
    
    def _check_overdue_risk_assessments(self):
        """Check for customers with overdue risk assessments"""
        
        self.stdout.write('Checking overdue risk assessments...')
        
        # Find customers with overdue assessments
        ninety_days_ago = timezone.now() - timedelta(days=90)
        
        overdue_customers = Customer.objects.filter(
            Q(next_review_date__lt=timezone.now()) |
            Q(last_risk_assessment__lt=ninety_days_ago) |
            Q(last_risk_assessment__isnull=True)
        ).filter(
            onboarding_status__in=['APPROVED', 'ACTIVE']
        )
        
        if self.verbose:
            self.stdout.write(f'Found {overdue_customers.count()} customers with overdue assessments')
        
        if not self.dry_run:
            risk_service = RiskCalculationService()
            monitoring_service = RiskMonitoringService()
            
            processed = 0
            errors = 0
            
            for customer in overdue_customers:
                try:
                    if monitoring_service.monitor_customer_changes(customer):
                        risk_service.calculate_customer_risk(customer, force_recalculate=True)
                        processed += 1
                        
                        if self.verbose:
                            self.stdout.write(f'  - Updated risk for customer {customer.id}')
                            
                except Exception as e:
                    errors += 1
                    logger.error(f'Error updating risk for customer {customer.id}: {str(e)}')
            
            self.stdout.write(f'Risk assessments: {processed} updated, {errors} errors')
        else:
            self.stdout.write(f'Would update {overdue_customers.count()} risk assessments')
    
    def _run_periodic_sanctions_screening(self):
        """Run periodic sanctions screening for active customers"""
        
        self.stdout.write('Running periodic sanctions screening...')
        
        # Find customers that need sanctions re-screening (older than 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        customers_to_screen = Customer.objects.filter(
            onboarding_status__in=['APPROVED', 'ACTIVE']
        ).filter(
            Q(sanctions_checks__check_date__lt=thirty_days_ago) |
            Q(sanctions_checks__isnull=True)
        ).distinct()
        
        if self.verbose:
            self.stdout.write(f'Found {customers_to_screen.count()} customers needing sanctions screening')
        
        if not self.dry_run:
            sanctions_service = SanctionsScreeningService()
            
            processed = 0
            errors = 0
            
            for customer in customers_to_screen[:50]:  # Limit to 50 per day
                try:
                    sanctions_service.screen_customer(customer)
                    processed += 1
                    
                    if self.verbose:
                        self.stdout.write(f'  - Screened customer {customer.id}')
                        
                except Exception as e:
                    errors += 1
                    logger.error(f'Error screening customer {customer.id}: {str(e)}')
            
            self.stdout.write(f'Sanctions screening: {processed} completed, {errors} errors')
        else:
            self.stdout.write(f'Would screen {min(customers_to_screen.count(), 50)} customers')
    
    def _process_compliance_reviews(self):
        """Process pending compliance reviews"""
        
        self.stdout.write('Processing compliance reviews...')
        
        # Find customers requiring manual review
        customers_for_review = Customer.objects.filter(
            onboarding_status='REQUIRES_MANUAL_REVIEW'
        )
        
        if self.verbose:
            self.stdout.write(f'Found {customers_for_review.count()} customers requiring manual review')
        
        # For now, just log the count - manual reviews require human intervention
        # In a full implementation, this might trigger notifications or escalations
        
        if customers_for_review.exists() and not self.dry_run:
            # Create alerts for pending reviews
            for customer in customers_for_review:
                existing_alert = ComplianceAlert.objects.filter(
                    customer=customer,
                    alert_type='REVIEW_DUE',
                    status='OPEN'
                ).exists()
                
                if not existing_alert:
                    ComplianceAlert.objects.create(
                        alert_type='REVIEW_DUE',
                        severity='WARNING',
                        title=f'Manual Review Pending: {customer.full_name}',
                        message=f'Customer {customer.full_name} has been pending manual review',
                        customer=customer,
                        status='OPEN'
                    )
        
        self.stdout.write(f'Compliance reviews: {customers_for_review.count()} pending')
    
    def _cleanup_old_alerts(self):
        """Clean up old resolved alerts"""
        
        self.stdout.write('Cleaning up old alerts...')
        
        # Delete resolved alerts older than 90 days
        ninety_days_ago = timezone.now() - timedelta(days=90)
        
        old_alerts = ComplianceAlert.objects.filter(
            status__in=['RESOLVED', 'CLOSED'],
            updated_at__lt=ninety_days_ago
        )
        
        count = old_alerts.count()
        
        if self.verbose:
            self.stdout.write(f'Found {count} old alerts to clean up')
        
        if not self.dry_run and count > 0:
            old_alerts.delete()
            self.stdout.write(f'Cleaned up {count} old alerts')
        else:
            self.stdout.write(f'Would clean up {count} old alerts')
    
    def _generate_daily_metrics(self):
        """Generate daily system metrics"""
        
        self.stdout.write('Generating daily metrics...')
        
        if not self.dry_run:
            from apps.compliance.models import ComplianceMetric
            
            today = timezone.now().date()
            
            # Customer metrics
            total_customers = Customer.objects.count()
            active_customers = Customer.objects.filter(onboarding_status='APPROVED').count()
            pending_customers = Customer.objects.filter(onboarding_status='PENDING_REVIEW').count()
            
            # Risk metrics
            high_risk_customers = Customer.objects.filter(risk_level='HIGH').count()
            
            # Compliance metrics
            open_alerts = ComplianceAlert.objects.filter(status='OPEN').count()
            
            # Create or update daily metric
            metric, created = ComplianceMetric.objects.update_or_create(
                metric_date=today,
                defaults={
                    'total_customers': total_customers,
                    'active_customers': active_customers,
                    'pending_customers': pending_customers,
                    'high_risk_customers': high_risk_customers,
                    'open_alerts': open_alerts,
                    'calculated_at': timezone.now()
                }
            )
            
            action = 'Created' if created else 'Updated'
            self.stdout.write(f'{action} daily metrics for {today}')
            
            if self.verbose:
                self.stdout.write(f'  - Total customers: {total_customers}')
                self.stdout.write(f'  - Active customers: {active_customers}')
                self.stdout.write(f'  - High risk customers: {high_risk_customers}')
                self.stdout.write(f'  - Open alerts: {open_alerts}')
        else:
            self.stdout.write('Would generate daily metrics')

