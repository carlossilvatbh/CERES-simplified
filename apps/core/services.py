"""
CERES Simplified - Core Automation Services
Central business logic automation and orchestration
"""

import logging
from typing import Dict, List, Optional
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import User

from apps.customers.models import Customer
from apps.risk.services import RiskCalculationService
from apps.sanctions.services import SanctionsScreeningService
from apps.compliance.services import ComplianceWorkflowService
from apps.compliance.models import ComplianceAlert

logger = logging.getLogger(__name__)


class CustomerOnboardingOrchestrator:
    """
    Orchestrates the complete customer onboarding process
    Coordinates risk assessment, sanctions screening, and compliance checks
    """
    
    def __init__(self):
        self.risk_service = RiskCalculationService()
        self.sanctions_service = SanctionsScreeningService()
        self.compliance_service = ComplianceWorkflowService()
    
    def process_customer_onboarding(self, customer: Customer, initiated_by: User = None) -> Dict:
        """
        Process complete customer onboarding workflow
        
        Args:
            customer: Customer instance to onboard
            initiated_by: User who initiated the onboarding
            
        Returns:
            Dict with onboarding results and status
        """
        logger.info(f"Starting complete onboarding for customer {customer.id}")
        
        try:
            with transaction.atomic():
                onboarding_results = {
                    'customer_id': customer.id,
                    'status': 'IN_PROGRESS',
                    'steps_completed': [],
                    'steps_failed': [],
                    'final_status': None,
                    'next_actions': []
                }
                
                # Step 1: Risk Assessment
                try:
                    risk_assessment = self.risk_service.calculate_customer_risk(customer)
                    onboarding_results['steps_completed'].append({
                        'step': 'risk_assessment',
                        'status': 'COMPLETED',
                        'result': {
                            'risk_score': risk_assessment.risk_score,
                            'risk_level': risk_assessment.risk_level
                        }
                    })
                    logger.info(f"Risk assessment completed for customer {customer.id}: {risk_assessment.risk_level}")
                    
                except Exception as e:
                    onboarding_results['steps_failed'].append({
                        'step': 'risk_assessment',
                        'error': str(e)
                    })
                    logger.error(f"Risk assessment failed for customer {customer.id}: {str(e)}")
                
                # Step 2: Sanctions Screening
                try:
                    sanctions_check = self.sanctions_service.screen_customer(customer, initiated_by)
                    onboarding_results['steps_completed'].append({
                        'step': 'sanctions_screening',
                        'status': 'COMPLETED',
                        'result': {
                            'match_status': sanctions_check.match_status,
                            'total_matches': sanctions_check.total_matches
                        }
                    })
                    logger.info(f"Sanctions screening completed for customer {customer.id}: {sanctions_check.match_status}")
                    
                except Exception as e:
                    onboarding_results['steps_failed'].append({
                        'step': 'sanctions_screening',
                        'error': str(e)
                    })
                    logger.error(f"Sanctions screening failed for customer {customer.id}: {str(e)}")
                
                # Step 3: Screen Beneficial Owners
                if customer.customer_type == 'LEGAL_ENTITY':
                    try:
                        beneficial_owners = customer.beneficial_owners.all()
                        bo_results = []
                        
                        for bo in beneficial_owners:
                            bo_sanctions = self.sanctions_service.screen_beneficial_owner(bo, initiated_by)
                            bo_results.append({
                                'beneficial_owner_id': bo.id,
                                'name': bo.full_name,
                                'match_status': bo_sanctions.match_status,
                                'total_matches': bo_sanctions.total_matches
                            })
                        
                        onboarding_results['steps_completed'].append({
                            'step': 'beneficial_owner_screening',
                            'status': 'COMPLETED',
                            'result': {
                                'beneficial_owners_screened': len(bo_results),
                                'results': bo_results
                            }
                        })
                        logger.info(f"Beneficial owner screening completed for customer {customer.id}: {len(bo_results)} owners")
                        
                    except Exception as e:
                        onboarding_results['steps_failed'].append({
                            'step': 'beneficial_owner_screening',
                            'error': str(e)
                        })
                        logger.error(f"Beneficial owner screening failed for customer {customer.id}: {str(e)}")
                
                # Step 4: Compliance Workflow
                try:
                    compliance_results = self.compliance_service.process_customer_onboarding(customer, initiated_by)
                    onboarding_results['steps_completed'].append({
                        'step': 'compliance_workflow',
                        'status': 'COMPLETED',
                        'result': compliance_results
                    })
                    logger.info(f"Compliance workflow completed for customer {customer.id}: {compliance_results['final_decision']}")
                    
                except Exception as e:
                    onboarding_results['steps_failed'].append({
                        'step': 'compliance_workflow',
                        'error': str(e)
                    })
                    logger.error(f"Compliance workflow failed for customer {customer.id}: {str(e)}")
                
                # Determine final onboarding status
                final_status = self._determine_final_onboarding_status(onboarding_results, customer)
                onboarding_results['final_status'] = final_status
                onboarding_results['status'] = 'COMPLETED'
                
                # Generate next actions
                next_actions = self._generate_next_actions(onboarding_results, customer)
                onboarding_results['next_actions'] = next_actions
                
                logger.info(f"Complete onboarding finished for customer {customer.id}: {final_status}")
                return onboarding_results
                
        except Exception as e:
            logger.error(f"Error in complete onboarding for customer {customer.id}: {str(e)}")
            raise
    
    def _determine_final_onboarding_status(self, results: Dict, customer: Customer) -> str:
        """Determine final onboarding status based on all checks"""
        
        # Check if any critical steps failed
        failed_steps = [step['step'] for step in results['steps_failed']]
        
        if 'sanctions_screening' in failed_steps:
            return 'REJECTED_SANCTIONS_FAILURE'
        
        if 'compliance_workflow' in failed_steps:
            return 'REJECTED_COMPLIANCE_FAILURE'
        
        # Check compliance decision
        compliance_step = next(
            (step for step in results['steps_completed'] if step['step'] == 'compliance_workflow'),
            None
        )
        
        if compliance_step:
            compliance_decision = compliance_step['result'].get('final_decision')
            
            if compliance_decision == 'REJECTED':
                return 'REJECTED_COMPLIANCE'
            elif compliance_decision == 'PENDING_MANUAL_REVIEW':
                return 'PENDING_MANUAL_REVIEW'
            elif compliance_decision in ['AUTO_APPROVED', 'CONDITIONALLY_APPROVED']:
                return 'APPROVED'
        
        # Check sanctions results
        sanctions_step = next(
            (step for step in results['steps_completed'] if step['step'] == 'sanctions_screening'),
            None
        )
        
        if sanctions_step:
            sanctions_status = sanctions_step['result'].get('match_status')
            if sanctions_status == 'MATCH':
                return 'PENDING_SANCTIONS_REVIEW'
            elif sanctions_status == 'POTENTIAL_MATCH':
                return 'PENDING_MANUAL_REVIEW'
        
        # Default based on risk level
        risk_step = next(
            (step for step in results['steps_completed'] if step['step'] == 'risk_assessment'),
            None
        )
        
        if risk_step:
            risk_level = risk_step['result'].get('risk_level')
            if risk_level == 'HIGH':
                return 'PENDING_MANUAL_REVIEW'
        
        return 'APPROVED'
    
    def _generate_next_actions(self, results: Dict, customer: Customer) -> List[str]:
        """Generate list of next actions based on onboarding results"""
        
        actions = []
        final_status = results['final_status']
        
        if final_status == 'APPROVED':
            actions.append('Customer approved - activate account')
            actions.append('Send welcome communication')
            actions.append('Schedule periodic review')
        
        elif final_status == 'PENDING_MANUAL_REVIEW':
            actions.append('Assign to compliance officer for manual review')
            actions.append('Gather additional documentation if needed')
            actions.append('Schedule review meeting')
        
        elif final_status == 'PENDING_SANCTIONS_REVIEW':
            actions.append('Assign to sanctions specialist for review')
            actions.append('Investigate potential sanctions matches')
            actions.append('Document review decision')
        
        elif 'REJECTED' in final_status:
            actions.append('Send rejection notification to customer')
            actions.append('Document rejection reasons')
            actions.append('Archive customer record')
        
        # Add specific actions based on failed steps
        for failed_step in results['steps_failed']:
            step_name = failed_step['step']
            if step_name == 'risk_assessment':
                actions.append('Retry risk assessment with manual review')
            elif step_name == 'sanctions_screening':
                actions.append('Perform manual sanctions screening')
            elif step_name == 'compliance_workflow':
                actions.append('Manual compliance review required')
        
        return actions


class AlertManagementService:
    """Service for managing and processing compliance alerts"""
    
    def process_high_priority_alerts(self) -> Dict:
        """Process high priority alerts that require immediate attention"""
        
        logger.info("Processing high priority alerts")
        
        # Get critical and high severity open alerts
        high_priority_alerts = ComplianceAlert.objects.filter(
            status='OPEN',
            severity__in=['CRITICAL', 'ERROR']
        ).order_by('created_at')
        
        results = {
            'total_processed': 0,
            'auto_resolved': 0,
            'escalated': 0,
            'errors': 0
        }
        
        for alert in high_priority_alerts:
            try:
                action_taken = self._process_individual_alert(alert)
                
                if action_taken == 'AUTO_RESOLVED':
                    results['auto_resolved'] += 1
                elif action_taken == 'ESCALATED':
                    results['escalated'] += 1
                
                results['total_processed'] += 1
                
            except Exception as e:
                logger.error(f"Error processing alert {alert.id}: {str(e)}")
                results['errors'] += 1
        
        logger.info(f"High priority alerts processed: {results}")
        return results
    
    def _process_individual_alert(self, alert: ComplianceAlert) -> str:
        """Process individual alert and determine action"""
        
        # Auto-resolution logic based on alert type
        if alert.alert_type == 'HIGH_RISK_ACTIVITY':
            # Check if customer risk has been manually reviewed
            if alert.customer and alert.customer.onboarding_status == 'APPROVED':
                alert.status = 'RESOLVED'
                alert.resolution_notes = 'Customer approved after manual review'
                alert.resolved_at = timezone.now()
                alert.save()
                return 'AUTO_RESOLVED'
        
        elif alert.alert_type == 'RULE_VIOLATION':
            # Check if compliance issues have been addressed
            if alert.customer:
                recent_checks = alert.customer.compliance_checks.filter(
                    check_date__gte=alert.created_at,
                    check_status='PASSED'
                )
                if recent_checks.exists():
                    alert.status = 'RESOLVED'
                    alert.resolution_notes = 'Compliance issues resolved'
                    alert.resolved_at = timezone.now()
                    alert.save()
                    return 'AUTO_RESOLVED'
        
        # If not auto-resolvable, escalate
        if alert.severity == 'CRITICAL':
            # Create escalation (in a real system, this might send notifications)
            logger.warning(f"Critical alert {alert.id} escalated: {alert.title}")
            return 'ESCALATED'
        
        return 'NO_ACTION'


class SystemHealthMonitor:
    """Service for monitoring system health and performance"""
    
    def check_system_health(self) -> Dict:
        """Perform comprehensive system health check"""
        
        logger.info("Performing system health check")
        
        health_status = {
            'overall_status': 'HEALTHY',
            'checks': {},
            'warnings': [],
            'errors': [],
            'timestamp': timezone.now()
        }
        
        # Check database connectivity
        try:
            Customer.objects.count()
            health_status['checks']['database'] = 'HEALTHY'
        except Exception as e:
            health_status['checks']['database'] = 'ERROR'
            health_status['errors'].append(f"Database connectivity: {str(e)}")
            health_status['overall_status'] = 'UNHEALTHY'
        
        # Check for stale data
        try:
            stale_assessments = self._check_stale_risk_assessments()
            if stale_assessments > 10:
                health_status['warnings'].append(f"{stale_assessments} customers have stale risk assessments")
                health_status['checks']['risk_assessments'] = 'WARNING'
            else:
                health_status['checks']['risk_assessments'] = 'HEALTHY'
        except Exception as e:
            health_status['checks']['risk_assessments'] = 'ERROR'
            health_status['errors'].append(f"Risk assessment check: {str(e)}")
        
        # Check alert backlog
        try:
            open_alerts = ComplianceAlert.objects.filter(status='OPEN').count()
            if open_alerts > 50:
                health_status['warnings'].append(f"{open_alerts} open compliance alerts")
                health_status['checks']['alert_backlog'] = 'WARNING'
            else:
                health_status['checks']['alert_backlog'] = 'HEALTHY'
        except Exception as e:
            health_status['checks']['alert_backlog'] = 'ERROR'
            health_status['errors'].append(f"Alert backlog check: {str(e)}")
        
        # Check pending reviews
        try:
            pending_reviews = Customer.objects.filter(
                onboarding_status='REQUIRES_MANUAL_REVIEW'
            ).count()
            if pending_reviews > 20:
                health_status['warnings'].append(f"{pending_reviews} customers pending manual review")
                health_status['checks']['pending_reviews'] = 'WARNING'
            else:
                health_status['checks']['pending_reviews'] = 'HEALTHY'
        except Exception as e:
            health_status['checks']['pending_reviews'] = 'ERROR'
            health_status['errors'].append(f"Pending reviews check: {str(e)}")
        
        # Determine overall status
        if health_status['errors']:
            health_status['overall_status'] = 'UNHEALTHY'
        elif health_status['warnings']:
            health_status['overall_status'] = 'WARNING'
        
        logger.info(f"System health check completed: {health_status['overall_status']}")
        return health_status
    
    def _check_stale_risk_assessments(self) -> int:
        """Check for customers with stale risk assessments"""
        
        ninety_days_ago = timezone.now() - timezone.timedelta(days=90)
        
        stale_customers = Customer.objects.filter(
            onboarding_status__in=['APPROVED', 'ACTIVE']
        ).filter(
            models.Q(last_risk_assessment__lt=ninety_days_ago) |
            models.Q(last_risk_assessment__isnull=True)
        ).count()
        
        return stale_customers


class BusinessRulesEngine:
    """Engine for executing configurable business rules"""
    
    def __init__(self):
        self.rules = self._load_business_rules()
    
    def _load_business_rules(self) -> Dict:
        """Load business rules configuration"""
        
        # In a production system, these would be loaded from database or config files
        return {
            'auto_approval_rules': {
                'max_risk_score': 40,
                'required_documents': ['passport', 'proof_of_address'],
                'max_transaction_volume': 100000,
                'excluded_countries': ['AF', 'IR', 'KP', 'SY'],
                'excluded_industries': ['CRYPTO', 'GAMBLING']
            },
            'enhanced_due_diligence_rules': {
                'min_risk_score': 60,
                'pep_status': True,
                'high_risk_countries': ['PK', 'BD', 'MM'],
                'high_risk_industries': ['MONEY_SERVICES', 'REAL_ESTATE'],
                'min_transaction_volume': 500000
            },
            'rejection_rules': {
                'sanctions_match': True,
                'max_risk_score': 90,
                'missing_critical_documents': True,
                'prohibited_countries': ['AF', 'IR', 'KP', 'SY'],
                'prohibited_industries': []
            }
        }
    
    def evaluate_customer_against_rules(self, customer: Customer, rule_set: str) -> Dict:
        """Evaluate customer against specific rule set"""
        
        if rule_set not in self.rules:
            raise ValueError(f"Unknown rule set: {rule_set}")
        
        rules = self.rules[rule_set]
        evaluation_result = {
            'rule_set': rule_set,
            'customer_id': customer.id,
            'passed': True,
            'failed_rules': [],
            'score': 0
        }
        
        # Evaluate each rule
        for rule_name, rule_value in rules.items():
            rule_result = self._evaluate_individual_rule(customer, rule_name, rule_value)
            
            if not rule_result['passed']:
                evaluation_result['passed'] = False
                evaluation_result['failed_rules'].append(rule_result)
        
        return evaluation_result
    
    def _evaluate_individual_rule(self, customer: Customer, rule_name: str, rule_value) -> Dict:
        """Evaluate individual business rule"""
        
        result = {
            'rule_name': rule_name,
            'passed': True,
            'message': ''
        }
        
        try:
            if rule_name == 'max_risk_score':
                risk_assessment = customer.risk_assessments.filter(is_current=True).first()
                if risk_assessment and risk_assessment.risk_score > rule_value:
                    result['passed'] = False
                    result['message'] = f"Risk score {risk_assessment.risk_score} exceeds maximum {rule_value}"
            
            elif rule_name == 'excluded_countries':
                if customer.country in rule_value:
                    result['passed'] = False
                    result['message'] = f"Customer from excluded country: {customer.country}"
            
            elif rule_name == 'excluded_industries':
                if customer.industry in rule_value:
                    result['passed'] = False
                    result['message'] = f"Customer from excluded industry: {customer.industry}"
            
            elif rule_name == 'pep_status':
                if rule_value and customer.is_pep:
                    result['passed'] = False
                    result['message'] = "Customer is a Politically Exposed Person"
            
            elif rule_name == 'sanctions_match':
                if rule_value:
                    sanctions_matches = customer.sanctions_checks.filter(
                        match_status='MATCH'
                    ).exists()
                    if sanctions_matches:
                        result['passed'] = False
                        result['message'] = "Customer has sanctions matches"
            
            # Add more rule evaluations as needed
            
        except Exception as e:
            result['passed'] = False
            result['message'] = f"Error evaluating rule: {str(e)}"
        
        return result

