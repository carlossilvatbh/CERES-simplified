"""
CERES Simplified - Compliance Workflow Services
Business logic for compliance checks and approval workflows
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import (
    ComplianceRule, ComplianceCheck, ComplianceAlert, 
    ComplianceReport, ComplianceMetric
)
from apps.customers.models import Customer
from apps.risk.models import RiskAssessment
from apps.sanctions.models import SanctionsCheck
from apps.documents.models import Document

logger = logging.getLogger(__name__)


class ComplianceWorkflowService:
    """Service for managing compliance workflows and approvals"""
    
    def __init__(self):
        self.auto_approval_threshold = 40  # Risk score threshold for auto-approval
        self.manual_review_threshold = 60  # Risk score threshold for manual review
    
    def process_customer_onboarding(self, customer: Customer, initiated_by: User = None) -> Dict:
        """
        Process complete customer onboarding compliance workflow
        
        Args:
            customer: Customer instance
            initiated_by: User who initiated the process
            
        Returns:
            Dict with workflow results and next steps
        """
        logger.info(f"Starting compliance workflow for customer {customer.id}")
        
        try:
            with transaction.atomic():
                # Initialize workflow tracking
                workflow_results = {
                    'customer_id': customer.id,
                    'status': 'IN_PROGRESS',
                    'checks_completed': [],
                    'checks_failed': [],
                    'next_steps': [],
                    'final_decision': None,
                    'requires_manual_review': False
                }
                
                # Step 1: Run all applicable compliance checks
                compliance_results = self._run_compliance_checks(customer, initiated_by)
                workflow_results['checks_completed'] = compliance_results['passed']
                workflow_results['checks_failed'] = compliance_results['failed']
                
                # Step 2: Evaluate overall compliance status
                overall_status = self._evaluate_compliance_status(compliance_results)
                
                # Step 3: Make approval decision
                decision = self._make_approval_decision(customer, overall_status)
                workflow_results.update(decision)
                
                # Step 4: Update customer status
                self._update_customer_status(customer, decision)
                
                # Step 5: Generate alerts if needed
                self._generate_compliance_alerts(customer, workflow_results)
                
                # Step 6: Schedule follow-up actions
                self._schedule_follow_up_actions(customer, decision)
                
                logger.info(f"Compliance workflow completed for customer {customer.id}: {decision['final_decision']}")
                return workflow_results
                
        except Exception as e:
            logger.error(f"Error in compliance workflow for customer {customer.id}: {str(e)}")
            raise ValidationError(f"Erro no workflow de compliance: {str(e)}")
    
    def _run_compliance_checks(self, customer: Customer, initiated_by: User = None) -> Dict:
        """Run all applicable compliance checks for customer"""
        
        # Get active compliance rules
        applicable_rules = ComplianceRule.objects.filter(
            is_active=True,
            auto_check=True
        )
        
        results = {
            'passed': [],
            'failed': [],
            'requires_review': [],
            'total_score': 0,
            'max_score': 0
        }
        
        for rule in applicable_rules:
            try:
                check_result = self._execute_compliance_check(customer, rule, initiated_by)
                
                if check_result['status'] == 'PASSED':
                    results['passed'].append(check_result)
                elif check_result['status'] == 'FAILED':
                    results['failed'].append(check_result)
                else:
                    results['requires_review'].append(check_result)
                
                results['total_score'] += check_result.get('score', 0)
                results['max_score'] += rule.severity == 'CRITICAL' and 25 or rule.severity == 'HIGH' and 15 or 10
                
            except Exception as e:
                logger.error(f"Error executing compliance check {rule.id} for customer {customer.id}: {str(e)}")
                results['failed'].append({
                    'rule_id': rule.id,
                    'rule_name': rule.name,
                    'status': 'FAILED',
                    'error': str(e)
                })
        
        return results
    
    def _execute_compliance_check(self, customer: Customer, rule: ComplianceRule, initiated_by: User = None) -> Dict:
        """Execute individual compliance check"""
        
        logger.debug(f"Executing compliance check {rule.name} for customer {customer.id}")
        
        # Create compliance check record
        compliance_check = ComplianceCheck.objects.create(
            customer=customer,
            rule=rule,
            check_status='IN_PROGRESS',
            initiated_by=initiated_by,
            check_date=timezone.now()
        )
        
        try:
            # Execute check based on rule type
            if rule.rule_type == 'KYC':
                result = self._check_kyc_compliance(customer, rule)
            elif rule.rule_type == 'AML':
                result = self._check_aml_compliance(customer, rule)
            elif rule.rule_type == 'SANCTIONS':
                result = self._check_sanctions_compliance(customer, rule)
            elif rule.rule_type == 'PEP':
                result = self._check_pep_compliance(customer, rule)
            elif rule.rule_type == 'FATCA':
                result = self._check_fatca_compliance(customer, rule)
            elif rule.rule_type == 'CRS':
                result = self._check_crs_compliance(customer, rule)
            else:
                result = self._check_generic_compliance(customer, rule)
            
            # Update compliance check with results
            compliance_check.check_status = result['status']
            compliance_check.result_details = result.get('details', '')
            compliance_check.risk_score = result.get('score', 0)
            compliance_check.completed_date = timezone.now()
            compliance_check.save()
            
            result['check_id'] = compliance_check.id
            result['rule_id'] = rule.id
            result['rule_name'] = rule.name
            
            return result
            
        except Exception as e:
            compliance_check.check_status = 'FAILED'
            compliance_check.result_details = f"Error: {str(e)}"
            compliance_check.save()
            raise
    
    def _check_kyc_compliance(self, customer: Customer, rule: ComplianceRule) -> Dict:
        """Check KYC (Know Your Customer) compliance"""
        
        issues = []
        score = 0
        
        # Check required documents
        required_docs = Document.objects.filter(
            customer=customer,
            document_type__is_required=True
        )
        
        if not required_docs.exists():
            issues.append("No required documents found")
            score += 20
        else:
            approved_docs = required_docs.filter(status='APPROVED')
            completion_rate = approved_docs.count() / required_docs.count()
            
            if completion_rate < 0.8:
                issues.append(f"Document completion rate too low: {completion_rate:.1%}")
                score += 15
            elif completion_rate < 1.0:
                issues.append(f"Some documents pending approval: {completion_rate:.1%}")
                score += 5
        
        # Check customer data completeness
        required_fields = ['full_name', 'document_number', 'country', 'date_of_birth']
        missing_fields = []
        
        for field in required_fields:
            if not getattr(customer, field, None):
                missing_fields.append(field)
        
        if missing_fields:
            issues.append(f"Missing required fields: {', '.join(missing_fields)}")
            score += len(missing_fields) * 5
        
        # Check beneficial ownership (for legal entities)
        if customer.customer_type == 'LEGAL_ENTITY':
            beneficial_owners = customer.beneficial_owners.all()
            if not beneficial_owners.exists():
                issues.append("No beneficial owners declared")
                score += 25
            else:
                total_ownership = sum(bo.ownership_percentage for bo in beneficial_owners)
                if total_ownership < 75:
                    issues.append(f"Incomplete ownership disclosure: {total_ownership}%")
                    score += 15
        
        # Determine status
        if score == 0:
            status = 'PASSED'
        elif score <= 10:
            status = 'REQUIRES_REVIEW'
        else:
            status = 'FAILED'
        
        return {
            'status': status,
            'score': score,
            'details': '; '.join(issues) if issues else 'All KYC requirements met',
            'issues': issues
        }
    
    def _check_aml_compliance(self, customer: Customer, rule: ComplianceRule) -> Dict:
        """Check AML (Anti-Money Laundering) compliance"""
        
        issues = []
        score = 0
        
        # Check risk assessment
        risk_assessment = customer.risk_assessments.filter(is_current=True).first()
        if not risk_assessment:
            issues.append("No current risk assessment")
            score += 20
        elif risk_assessment.risk_level == 'HIGH':
            issues.append("High risk customer requires enhanced due diligence")
            score += 15
        
        # Check transaction volume vs declared business
        if customer.expected_monthly_volume:
            volume = float(customer.expected_monthly_volume)
            if volume > 1000000:  # > 1M
                issues.append("High transaction volume requires enhanced monitoring")
                score += 10
        
        # Check geographic risk
        high_risk_countries = ['AF', 'IR', 'KP', 'SY']  # Example
        if customer.country in high_risk_countries:
            issues.append(f"Customer from high-risk jurisdiction: {customer.country}")
            score += 20
        
        # Check industry risk
        high_risk_industries = ['CRYPTO', 'GAMBLING', 'MONEY_SERVICES']
        if customer.industry in high_risk_industries:
            issues.append(f"High-risk industry: {customer.industry}")
            score += 15
        
        # Determine status
        if score == 0:
            status = 'PASSED'
        elif score <= 15:
            status = 'REQUIRES_REVIEW'
        else:
            status = 'FAILED'
        
        return {
            'status': status,
            'score': score,
            'details': '; '.join(issues) if issues else 'AML requirements met',
            'issues': issues
        }
    
    def _check_sanctions_compliance(self, customer: Customer, rule: ComplianceRule) -> Dict:
        """Check sanctions screening compliance"""
        
        issues = []
        score = 0
        
        # Check customer sanctions screening
        customer_sanctions = SanctionsCheck.objects.filter(
            customer=customer
        ).order_by('-check_date').first()
        
        if not customer_sanctions:
            issues.append("No sanctions screening performed")
            score += 25
        elif customer_sanctions.match_status == 'MATCH':
            issues.append("Customer matches sanctions list")
            score += 50  # Critical issue
        elif customer_sanctions.match_status == 'POTENTIAL_MATCH':
            issues.append("Potential sanctions match requires review")
            score += 20
        elif customer_sanctions.check_date < timezone.now() - timedelta(days=30):
            issues.append("Sanctions screening outdated")
            score += 10
        
        # Check beneficial owners sanctions screening
        for bo in customer.beneficial_owners.all():
            bo_sanctions = SanctionsCheck.objects.filter(
                beneficial_owner=bo
            ).order_by('-check_date').first()
            
            if not bo_sanctions:
                issues.append(f"No sanctions screening for beneficial owner: {bo.full_name}")
                score += 15
            elif bo_sanctions.match_status == 'MATCH':
                issues.append(f"Beneficial owner matches sanctions list: {bo.full_name}")
                score += 50
            elif bo_sanctions.match_status == 'POTENTIAL_MATCH':
                issues.append(f"Potential sanctions match for beneficial owner: {bo.full_name}")
                score += 20
        
        # Determine status
        if score == 0:
            status = 'PASSED'
        elif score <= 20:
            status = 'REQUIRES_REVIEW'
        else:
            status = 'FAILED'
        
        return {
            'status': status,
            'score': score,
            'details': '; '.join(issues) if issues else 'Sanctions screening clear',
            'issues': issues
        }
    
    def _check_pep_compliance(self, customer: Customer, rule: ComplianceRule) -> Dict:
        """Check PEP (Politically Exposed Person) compliance"""
        
        issues = []
        score = 0
        
        # Check customer PEP status
        if customer.is_pep:
            issues.append("Customer is a Politically Exposed Person")
            score += 15  # Requires enhanced due diligence, not necessarily failure
        
        # Check beneficial owners PEP status
        pep_beneficial_owners = customer.beneficial_owners.filter(is_pep=True)
        for bo in pep_beneficial_owners:
            issues.append(f"Beneficial owner is PEP: {bo.full_name}")
            score += 10
        
        # If PEP detected, check for enhanced due diligence
        if customer.is_pep or pep_beneficial_owners.exists():
            # Check for enhanced documentation
            enhanced_docs = Document.objects.filter(
                customer=customer,
                document_type__name__icontains='enhanced'
            )
            if not enhanced_docs.exists():
                issues.append("PEP requires enhanced due diligence documentation")
                score += 20
        
        # Determine status
        if score == 0:
            status = 'PASSED'
        elif score <= 25:
            status = 'REQUIRES_REVIEW'
        else:
            status = 'FAILED'
        
        return {
            'status': status,
            'score': score,
            'details': '; '.join(issues) if issues else 'PEP screening clear',
            'issues': issues
        }
    
    def _check_fatca_compliance(self, customer: Customer, rule: ComplianceRule) -> Dict:
        """Check FATCA compliance"""
        
        issues = []
        score = 0
        
        # Check if customer is US person or has US connections
        us_indicators = [
            customer.country == 'US',
            customer.nationality == 'US',
            # Add more US indicators as needed
        ]
        
        if any(us_indicators):
            # Check for FATCA documentation
            fatca_docs = Document.objects.filter(
                customer=customer,
                document_type__name__icontains='fatca'
            )
            if not fatca_docs.exists():
                issues.append("US person requires FATCA documentation")
                score += 20
        
        # Determine status
        if score == 0:
            status = 'PASSED'
        elif score <= 10:
            status = 'REQUIRES_REVIEW'
        else:
            status = 'FAILED'
        
        return {
            'status': status,
            'score': score,
            'details': '; '.join(issues) if issues else 'FATCA requirements met',
            'issues': issues
        }
    
    def _check_crs_compliance(self, customer: Customer, rule: ComplianceRule) -> Dict:
        """Check CRS (Common Reporting Standard) compliance"""
        
        issues = []
        score = 0
        
        # Check for CRS reporting requirements
        crs_countries = ['US', 'GB', 'DE', 'FR', 'IT', 'ES']  # Example CRS countries
        
        if customer.country in crs_countries or customer.nationality in crs_countries:
            # Check for CRS documentation
            crs_docs = Document.objects.filter(
                customer=customer,
                document_type__name__icontains='crs'
            )
            if not crs_docs.exists():
                issues.append("CRS reporting jurisdiction requires additional documentation")
                score += 15
        
        # Determine status
        if score == 0:
            status = 'PASSED'
        elif score <= 10:
            status = 'REQUIRES_REVIEW'
        else:
            status = 'FAILED'
        
        return {
            'status': status,
            'score': score,
            'details': '; '.join(issues) if issues else 'CRS requirements met',
            'issues': issues
        }
    
    def _check_generic_compliance(self, customer: Customer, rule: ComplianceRule) -> Dict:
        """Check generic compliance rule"""
        
        # For generic rules, we'll do basic checks
        issues = []
        score = 0
        
        # Basic completeness check
        if not customer.full_name or not customer.document_number:
            issues.append("Basic customer information incomplete")
            score += 10
        
        # Determine status
        if score == 0:
            status = 'PASSED'
        else:
            status = 'REQUIRES_REVIEW'
        
        return {
            'status': status,
            'score': score,
            'details': '; '.join(issues) if issues else 'Generic compliance check passed',
            'issues': issues
        }
    
    def _evaluate_compliance_status(self, compliance_results: Dict) -> str:
        """Evaluate overall compliance status"""
        
        failed_checks = len(compliance_results['failed'])
        review_checks = len(compliance_results['requires_review'])
        total_checks = failed_checks + review_checks + len(compliance_results['passed'])
        
        if failed_checks > 0:
            return 'FAILED'
        elif review_checks > 0:
            return 'REQUIRES_REVIEW'
        elif total_checks == 0:
            return 'NO_CHECKS'
        else:
            return 'PASSED'
    
    def _make_approval_decision(self, customer: Customer, compliance_status: str) -> Dict:
        """Make final approval decision based on compliance and risk"""
        
        decision = {
            'final_decision': None,
            'requires_manual_review': False,
            'next_steps': [],
            'approval_conditions': []
        }
        
        # Get current risk assessment
        risk_assessment = customer.risk_assessments.filter(is_current=True).first()
        risk_score = risk_assessment.risk_score if risk_assessment else 50
        
        # Decision logic
        if compliance_status == 'FAILED':
            decision['final_decision'] = 'REJECTED'
            decision['next_steps'].append('Address compliance failures')
            
        elif compliance_status == 'REQUIRES_REVIEW' or risk_score >= self.manual_review_threshold:
            decision['final_decision'] = 'PENDING_MANUAL_REVIEW'
            decision['requires_manual_review'] = True
            decision['next_steps'].append('Manual review required')
            
        elif risk_score <= self.auto_approval_threshold:
            decision['final_decision'] = 'AUTO_APPROVED'
            decision['next_steps'].append('Customer onboarded successfully')
            
        else:
            decision['final_decision'] = 'CONDITIONALLY_APPROVED'
            decision['approval_conditions'].append('Enhanced monitoring required')
            decision['next_steps'].append('Approve with conditions')
        
        return decision
    
    def _update_customer_status(self, customer: Customer, decision: Dict):
        """Update customer onboarding status based on decision"""
        
        status_mapping = {
            'AUTO_APPROVED': 'APPROVED',
            'CONDITIONALLY_APPROVED': 'APPROVED',
            'PENDING_MANUAL_REVIEW': 'REQUIRES_MANUAL_REVIEW',
            'REJECTED': 'REJECTED'
        }
        
        new_status = status_mapping.get(decision['final_decision'])
        if new_status:
            customer.onboarding_status = new_status
            customer.save(update_fields=['onboarding_status'])
    
    def _generate_compliance_alerts(self, customer: Customer, workflow_results: Dict):
        """Generate compliance alerts based on workflow results"""
        
        if workflow_results['checks_failed']:
            ComplianceAlert.objects.create(
                alert_type='RULE_VIOLATION',
                severity='ERROR',
                title=f'Compliance Failures: {customer.full_name}',
                message=f'Customer {customer.full_name} failed {len(workflow_results["checks_failed"])} compliance checks',
                customer=customer,
                status='OPEN'
            )
        
        if workflow_results['requires_manual_review']:
            ComplianceAlert.objects.create(
                alert_type='REVIEW_DUE',
                severity='WARNING',
                title=f'Manual Review Required: {customer.full_name}',
                message=f'Customer {customer.full_name} requires manual compliance review',
                customer=customer,
                status='OPEN'
            )
    
    def _schedule_follow_up_actions(self, customer: Customer, decision: Dict):
        """Schedule follow-up actions based on decision"""
        
        if decision['final_decision'] in ['AUTO_APPROVED', 'CONDITIONALLY_APPROVED']:
            # Schedule periodic review
            if customer.risk_level == 'HIGH':
                next_review = timezone.now() + timedelta(days=30)
            elif customer.risk_level == 'MEDIUM':
                next_review = timezone.now() + timedelta(days=90)
            else:
                next_review = timezone.now() + timedelta(days=180)
            
            customer.next_review_date = next_review
            customer.save(update_fields=['next_review_date'])


class ComplianceReportingService:
    """Service for compliance reporting and metrics"""
    
    def generate_compliance_dashboard_data(self, date_from=None, date_to=None) -> Dict:
        """Generate data for compliance dashboard"""
        
        if not date_from:
            date_from = timezone.now() - timedelta(days=30)
        if not date_to:
            date_to = timezone.now()
        
        # Get compliance checks in period
        checks = ComplianceCheck.objects.filter(
            check_date__range=[date_from, date_to]
        )
        
        # Calculate metrics
        total_checks = checks.count()
        passed_checks = checks.filter(check_status='PASSED').count()
        failed_checks = checks.filter(check_status='FAILED').count()
        review_checks = checks.filter(check_status='REQUIRES_REVIEW').count()
        
        # Calculate rates
        pass_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0
        fail_rate = (failed_checks / total_checks * 100) if total_checks > 0 else 0
        
        # Get alerts
        alerts = ComplianceAlert.objects.filter(
            created_at__range=[date_from, date_to]
        )
        
        open_alerts = alerts.filter(status='OPEN').count()
        critical_alerts = alerts.filter(severity='CRITICAL').count()
        
        return {
            'period': {
                'from': date_from,
                'to': date_to
            },
            'checks': {
                'total': total_checks,
                'passed': passed_checks,
                'failed': failed_checks,
                'review': review_checks,
                'pass_rate': round(pass_rate, 1),
                'fail_rate': round(fail_rate, 1)
            },
            'alerts': {
                'total': alerts.count(),
                'open': open_alerts,
                'critical': critical_alerts
            },
            'trends': self._calculate_compliance_trends(date_from, date_to)
        }
    
    def _calculate_compliance_trends(self, date_from, date_to) -> Dict:
        """Calculate compliance trends over time"""
        
        # This would typically calculate week-over-week or month-over-month trends
        # For simplicity, we'll return basic trend indicators
        
        current_period_checks = ComplianceCheck.objects.filter(
            check_date__range=[date_from, date_to]
        )
        
        previous_period_start = date_from - (date_to - date_from)
        previous_period_checks = ComplianceCheck.objects.filter(
            check_date__range=[previous_period_start, date_from]
        )
        
        current_pass_rate = current_period_checks.filter(check_status='PASSED').count()
        previous_pass_rate = previous_period_checks.filter(check_status='PASSED').count()
        
        trend = 'stable'
        if current_pass_rate > previous_pass_rate:
            trend = 'improving'
        elif current_pass_rate < previous_pass_rate:
            trend = 'declining'
        
        return {
            'overall_trend': trend,
            'current_period_checks': current_period_checks.count(),
            'previous_period_checks': previous_period_checks.count()
        }

