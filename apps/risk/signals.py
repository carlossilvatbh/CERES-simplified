"""
CERES Simplified - Risk Assessment Signals
Automated risk calculation triggers
"""

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone

from apps.customers.models import Customer, BeneficialOwner
from apps.documents.models import Document
from apps.sanctions.models import SanctionsCheck
from .models import RiskAssessment
from .services import RiskCalculationService, RiskMonitoringService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Customer)
def customer_updated_risk_trigger(sender, instance, created, **kwargs):
    """
    Trigger risk assessment when customer is created or updated
    """
    if created:
        logger.info(f"New customer created: {instance.id}, scheduling risk assessment")
        # Schedule risk assessment for new customer
        _schedule_risk_assessment(instance, reason="New customer")
    else:
        # Check if significant fields changed
        if _customer_risk_fields_changed(instance):
            logger.info(f"Customer {instance.id} risk-relevant fields changed, scheduling reassessment")
            _schedule_risk_assessment(instance, reason="Customer data updated")


@receiver(post_save, sender=BeneficialOwner)
def beneficial_owner_updated_risk_trigger(sender, instance, created, **kwargs):
    """
    Trigger risk assessment when beneficial owner is added or updated
    """
    customer = instance.customer
    reason = "Beneficial owner added" if created else "Beneficial owner updated"
    
    logger.info(f"Beneficial owner changed for customer {customer.id}: {reason}")
    _schedule_risk_assessment(customer, reason=reason)


@receiver(post_delete, sender=BeneficialOwner)
def beneficial_owner_deleted_risk_trigger(sender, instance, **kwargs):
    """
    Trigger risk assessment when beneficial owner is deleted
    """
    customer = instance.customer
    logger.info(f"Beneficial owner deleted for customer {customer.id}")
    _schedule_risk_assessment(customer, reason="Beneficial owner removed")


@receiver(post_save, sender=Document)
def document_updated_risk_trigger(sender, instance, created, **kwargs):
    """
    Trigger risk assessment when document status changes
    """
    if not created and instance.status in ['APPROVED', 'REJECTED']:
        customer = instance.customer
        logger.info(f"Document status changed for customer {customer.id}: {instance.status}")
        _schedule_risk_assessment(customer, reason=f"Document {instance.status.lower()}")


@receiver(post_save, sender=SanctionsCheck)
def sanctions_check_risk_trigger(sender, instance, created, **kwargs):
    """
    Trigger risk assessment when sanctions check is completed
    """
    if not created and instance.match_status in ['MATCH', 'POTENTIAL_MATCH']:
        if instance.customer:
            customer = instance.customer
            logger.info(f"Sanctions match found for customer {customer.id}")
            _schedule_risk_assessment(customer, reason="Sanctions match detected", priority=True)
        
        if instance.beneficial_owner:
            customer = instance.beneficial_owner.customer
            logger.info(f"Sanctions match found for beneficial owner of customer {customer.id}")
            _schedule_risk_assessment(customer, reason="Beneficial owner sanctions match", priority=True)


def _customer_risk_fields_changed(customer):
    """
    Check if risk-relevant fields have changed
    """
    # This is a simplified check - in production, you'd track field changes
    risk_relevant_fields = [
        'customer_type', 'country', 'industry', 'is_pep', 
        'expected_monthly_volume', 'onboarding_status'
    ]
    
    # For now, we'll assume any save indicates potential risk change
    # In production, you'd use django-model-utils or similar to track changes
    return True


def _schedule_risk_assessment(customer, reason="Manual trigger", priority=False):
    """
    Schedule or immediately perform risk assessment
    """
    try:
        # For simplicity, we'll perform assessment immediately
        # In production, you might use Celery for async processing
        
        risk_service = RiskCalculationService()
        monitoring_service = RiskMonitoringService()
        
        # Check if reassessment is needed
        if monitoring_service.monitor_customer_changes(customer) or priority:
            assessment = risk_service.calculate_customer_risk(
                customer=customer, 
                force_recalculate=priority
            )
            
            logger.info(f"Risk assessment completed for customer {customer.id}: "
                       f"Score={assessment.risk_score}, Level={assessment.risk_level}, "
                       f"Reason={reason}")
            
            # Create alert if high risk
            if assessment.risk_level == 'HIGH':
                _create_high_risk_alert(customer, assessment, reason)
                
        else:
            logger.info(f"Risk assessment not needed for customer {customer.id}")
            
    except Exception as e:
        logger.error(f"Error in risk assessment for customer {customer.id}: {str(e)}")


def _create_high_risk_alert(customer, assessment, reason):
    """
    Create compliance alert for high risk customers
    """
    try:
        from apps.compliance.models import ComplianceAlert
        
        ComplianceAlert.objects.create(
            alert_type='HIGH_RISK_ACTIVITY',
            severity='ERROR',
            title=f'Cliente de Alto Risco Detectado: {customer.full_name}',
            message=f'Cliente {customer.full_name} foi classificado como ALTO RISCO '
                   f'(Score: {assessment.risk_score}). Motivo: {reason}. '
                   f'Revisão manual necessária.',
            customer=customer,
            status='OPEN'
        )
        
        logger.info(f"High risk alert created for customer {customer.id}")
        
    except Exception as e:
        logger.error(f"Error creating high risk alert for customer {customer.id}: {str(e)}")


# Risk Assessment Automation
@receiver(post_save, sender=RiskAssessment)
def risk_assessment_completed(sender, instance, created, **kwargs):
    """
    Handle actions after risk assessment is completed
    """
    if created:
        customer = instance.customer
        
        # Update customer onboarding status based on risk
        if customer.onboarding_status == 'PENDING_REVIEW':
            if instance.risk_level in ['VERY_LOW', 'LOW']:
                customer.onboarding_status = 'APPROVED'
                customer.save(update_fields=['onboarding_status'])
                logger.info(f"Customer {customer.id} auto-approved based on low risk")
            elif instance.risk_level == 'HIGH':
                customer.onboarding_status = 'REQUIRES_MANUAL_REVIEW'
                customer.save(update_fields=['onboarding_status'])
                logger.info(f"Customer {customer.id} flagged for manual review due to high risk")
        
        # Schedule periodic review
        _schedule_periodic_review(customer, instance)


def _schedule_periodic_review(customer, assessment):
    """
    Schedule periodic risk review based on risk level
    """
    from datetime import timedelta
    
    # Determine review frequency based on risk level
    review_intervals = {
        'HIGH': timedelta(days=30),      # Monthly for high risk
        'MEDIUM': timedelta(days=90),    # Quarterly for medium risk
        'LOW': timedelta(days=180),      # Semi-annually for low risk
        'VERY_LOW': timedelta(days=365)  # Annually for very low risk
    }
    
    interval = review_intervals.get(assessment.risk_level, timedelta(days=90))
    next_review_date = timezone.now() + interval
    
    # Update customer next review date
    customer.next_review_date = next_review_date
    customer.save(update_fields=['next_review_date'])
    
    logger.info(f"Next review scheduled for customer {customer.id} on {next_review_date}")


# Periodic Risk Monitoring
def check_overdue_assessments():
    """
    Check for customers with overdue risk assessments
    This would typically be called by a scheduled task
    """
    from django.db.models import Q
    
    overdue_customers = Customer.objects.filter(
        Q(next_review_date__lt=timezone.now()) |
        Q(last_risk_assessment__lt=timezone.now() - timedelta(days=90)) |
        Q(last_risk_assessment__isnull=True)
    ).filter(
        onboarding_status__in=['APPROVED', 'ACTIVE']
    )
    
    logger.info(f"Found {overdue_customers.count()} customers with overdue assessments")
    
    for customer in overdue_customers:
        _schedule_risk_assessment(customer, reason="Overdue assessment", priority=False)


def bulk_risk_assessment():
    """
    Perform bulk risk assessment for all customers
    This would typically be used for initial setup or major methodology changes
    """
    customers = Customer.objects.filter(
        onboarding_status__in=['PENDING_REVIEW', 'APPROVED', 'ACTIVE']
    )
    
    logger.info(f"Starting bulk risk assessment for {customers.count()} customers")
    
    risk_service = RiskCalculationService()
    success_count = 0
    error_count = 0
    
    for customer in customers:
        try:
            risk_service.calculate_customer_risk(customer, force_recalculate=True)
            success_count += 1
        except Exception as e:
            logger.error(f"Error in bulk assessment for customer {customer.id}: {str(e)}")
            error_count += 1
    
    logger.info(f"Bulk risk assessment completed: {success_count} successful, {error_count} errors")

