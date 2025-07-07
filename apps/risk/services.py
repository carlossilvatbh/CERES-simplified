"""
CERES Simplified - Risk Assessment Services
Business logic for risk calculation and assessment
"""

import logging
from decimal import Decimal
from typing import Dict, List, Tuple, Optional
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import RiskAssessment, RiskFactor, RiskMatrix, RiskFactorApplication
from apps.customers.models import Customer

logger = logging.getLogger(__name__)


class RiskCalculationService:
    """Service for calculating customer risk scores"""
    
    def __init__(self):
        self.base_score = 50  # Base risk score (neutral)
        self.max_score = 100
        self.min_score = 0
    
    def calculate_customer_risk(self, customer: Customer, force_recalculate: bool = False) -> RiskAssessment:
        """
        Calculate comprehensive risk score for a customer
        
        Args:
            customer: Customer instance
            force_recalculate: Force new calculation even if recent assessment exists
            
        Returns:
            RiskAssessment instance with calculated score
        """
        logger.info(f"Calculating risk for customer {customer.id}")
        
        # Check if recent assessment exists
        if not force_recalculate:
            recent_assessment = self._get_recent_assessment(customer)
            if recent_assessment:
                logger.info(f"Using recent assessment for customer {customer.id}")
                return recent_assessment
        
        try:
            with transaction.atomic():
                # Get applicable risk factors
                risk_factors = self._get_applicable_risk_factors(customer)
                
                # Calculate base score
                calculated_score = self._calculate_base_score(customer, risk_factors)
                
                # Apply risk matrix adjustments
                final_score = self._apply_risk_matrix(customer, calculated_score)
                
                # Determine risk level
                risk_level = self._determine_risk_level(final_score)
                
                # Create assessment record
                assessment = self._create_assessment(
                    customer=customer,
                    score=final_score,
                    risk_level=risk_level,
                    risk_factors=risk_factors
                )
                
                # Update customer risk level
                customer.risk_level = risk_level
                customer.last_risk_assessment = timezone.now()
                customer.save(update_fields=['risk_level', 'last_risk_assessment'])
                
                logger.info(f"Risk calculated for customer {customer.id}: {final_score} ({risk_level})")
                return assessment
                
        except Exception as e:
            logger.error(f"Error calculating risk for customer {customer.id}: {str(e)}")
            raise ValidationError(f"Erro no cálculo de risco: {str(e)}")
    
    def _get_recent_assessment(self, customer: Customer) -> Optional[RiskAssessment]:
        """Get recent assessment if exists (within 30 days)"""
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        return RiskAssessment.objects.filter(
            customer=customer,
            is_current=True,
            assessment_date__gte=thirty_days_ago
        ).first()
    
    def _get_applicable_risk_factors(self, customer: Customer) -> List[RiskFactor]:
        """Get risk factors applicable to customer type"""
        return RiskFactor.objects.filter(
            is_active=True,
            customer_type__in=[customer.customer_type, 'ALL']
        ).order_by('weight')
    
    def _calculate_base_score(self, customer: Customer, risk_factors: List[RiskFactor]) -> int:
        """Calculate base risk score using weighted factors"""
        total_score = self.base_score
        total_weight = 0
        
        for factor in risk_factors:
            factor_score = self._evaluate_risk_factor(customer, factor)
            weighted_score = factor_score * (factor.weight / 100)
            total_score += weighted_score
            total_weight += factor.weight
            
            logger.debug(f"Factor {factor.name}: score={factor_score}, weight={factor.weight}, contribution={weighted_score}")
        
        # Normalize score
        if total_weight > 0:
            normalized_score = min(max(total_score, self.min_score), self.max_score)
        else:
            normalized_score = self.base_score
        
        return int(normalized_score)
    
    def _evaluate_risk_factor(self, customer: Customer, factor: RiskFactor) -> float:
        """Evaluate individual risk factor for customer"""
        
        if factor.factor_type == RiskFactor.FactorType.GEOGRAPHIC:
            return self._evaluate_geographic_risk(customer, factor)
        elif factor.factor_type == RiskFactor.FactorType.INDUSTRY:
            return self._evaluate_industry_risk(customer, factor)
        elif factor.factor_type == RiskFactor.FactorType.TRANSACTION_VOLUME:
            return self._evaluate_transaction_volume_risk(customer, factor)
        elif factor.factor_type == RiskFactor.FactorType.PEP_STATUS:
            return self._evaluate_pep_risk(customer, factor)
        elif factor.factor_type == RiskFactor.FactorType.DOCUMENT_QUALITY:
            return self._evaluate_document_quality_risk(customer, factor)
        elif factor.factor_type == RiskFactor.FactorType.BENEFICIAL_OWNERSHIP:
            return self._evaluate_beneficial_ownership_risk(customer, factor)
        else:
            return 0.0
    
    def _evaluate_geographic_risk(self, customer: Customer, factor: RiskFactor) -> float:
        """Evaluate geographic risk based on customer location"""
        high_risk_countries = ['AF', 'IR', 'KP', 'SY']  # Example high-risk countries
        medium_risk_countries = ['PK', 'BD', 'MM']  # Example medium-risk countries
        
        if customer.country in high_risk_countries:
            return factor.high_risk_score
        elif customer.country in medium_risk_countries:
            return factor.medium_risk_score
        else:
            return factor.low_risk_score
    
    def _evaluate_industry_risk(self, customer: Customer, factor: RiskFactor) -> float:
        """Evaluate industry risk based on customer business"""
        high_risk_industries = ['CRYPTO', 'GAMBLING', 'MONEY_SERVICES']
        medium_risk_industries = ['REAL_ESTATE', 'JEWELRY', 'ART_DEALERS']
        
        if customer.industry in high_risk_industries:
            return factor.high_risk_score
        elif customer.industry in medium_risk_industries:
            return factor.medium_risk_score
        else:
            return factor.low_risk_score
    
    def _evaluate_transaction_volume_risk(self, customer: Customer, factor: RiskFactor) -> float:
        """Evaluate risk based on expected transaction volume"""
        if not customer.expected_monthly_volume:
            return factor.medium_risk_score
        
        volume = float(customer.expected_monthly_volume)
        
        if volume > 1000000:  # > 1M
            return factor.high_risk_score
        elif volume > 100000:  # > 100K
            return factor.medium_risk_score
        else:
            return factor.low_risk_score
    
    def _evaluate_pep_risk(self, customer: Customer, factor: RiskFactor) -> float:
        """Evaluate PEP (Politically Exposed Person) risk"""
        if customer.is_pep:
            return factor.high_risk_score
        
        # Check beneficial owners for PEP status
        pep_beneficial_owners = customer.beneficial_owners.filter(is_pep=True)
        if pep_beneficial_owners.exists():
            return factor.medium_risk_score
        
        return factor.low_risk_score
    
    def _evaluate_document_quality_risk(self, customer: Customer, factor: RiskFactor) -> float:
        """Evaluate risk based on document quality and completeness"""
        from apps.documents.models import Document
        
        required_docs = Document.objects.filter(
            customer=customer,
            document_type__is_required=True
        )
        
        if not required_docs.exists():
            return factor.high_risk_score
        
        approved_docs = required_docs.filter(status='APPROVED')
        completion_rate = approved_docs.count() / required_docs.count()
        
        if completion_rate >= 0.9:
            return factor.low_risk_score
        elif completion_rate >= 0.7:
            return factor.medium_risk_score
        else:
            return factor.high_risk_score
    
    def _evaluate_beneficial_ownership_risk(self, customer: Customer, factor: RiskFactor) -> float:
        """Evaluate risk based on beneficial ownership structure"""
        beneficial_owners = customer.beneficial_owners.all()
        
        if not beneficial_owners.exists():
            return factor.high_risk_score
        
        # Check for complex ownership structures
        total_ownership = sum(bo.ownership_percentage for bo in beneficial_owners)
        
        if total_ownership < 75:  # Incomplete ownership disclosure
            return factor.high_risk_score
        elif len(beneficial_owners) > 5:  # Complex structure
            return factor.medium_risk_score
        else:
            return factor.low_risk_score
    
    def _apply_risk_matrix(self, customer: Customer, base_score: int) -> int:
        """Apply risk matrix adjustments based on customer type"""
        try:
            risk_matrix = RiskMatrix.objects.get(
                customer_type=customer.customer_type,
                is_active=True
            )
            
            # Apply matrix multiplier
            adjusted_score = base_score * risk_matrix.score_multiplier
            
            # Apply matrix adjustments
            final_score = adjusted_score + risk_matrix.score_adjustment
            
            return int(min(max(final_score, self.min_score), self.max_score))
            
        except RiskMatrix.DoesNotExist:
            logger.warning(f"No risk matrix found for customer type {customer.customer_type}")
            return base_score
    
    def _determine_risk_level(self, score: int) -> str:
        """Determine risk level based on score"""
        if score >= 80:
            return 'HIGH'
        elif score >= 60:
            return 'MEDIUM'
        elif score >= 40:
            return 'LOW'
        else:
            return 'VERY_LOW'
    
    def _create_assessment(self, customer: Customer, score: int, risk_level: str, 
                          risk_factors: List[RiskFactor]) -> RiskAssessment:
        """Create risk assessment record"""
        
        # Mark previous assessments as not current
        RiskAssessment.objects.filter(
            customer=customer,
            is_current=True
        ).update(is_current=False)
        
        # Create new assessment
        assessment = RiskAssessment.objects.create(
            customer=customer,
            risk_score=score,
            risk_level=risk_level,
            assessment_date=timezone.now(),
            is_current=True,
            methodology_version="1.0",
            notes=f"Automated assessment using {len(risk_factors)} risk factors"
        )
        
        # Create factor applications
        for factor in risk_factors:
            factor_score = self._evaluate_risk_factor(customer, factor)
            RiskFactorApplication.objects.create(
                risk_assessment=assessment,
                risk_factor=factor,
                applied_score=factor_score,
                weight_used=factor.weight
            )
        
        return assessment


class RiskMonitoringService:
    """Service for ongoing risk monitoring"""
    
    def monitor_customer_changes(self, customer: Customer) -> bool:
        """
        Monitor customer for changes that require risk reassessment
        
        Returns:
            True if reassessment is needed
        """
        logger.info(f"Monitoring customer {customer.id} for risk changes")
        
        # Check if customer data has changed significantly
        changes_detected = self._detect_significant_changes(customer)
        
        if changes_detected:
            logger.info(f"Significant changes detected for customer {customer.id}")
            return True
        
        # Check if assessment is outdated
        if self._is_assessment_outdated(customer):
            logger.info(f"Assessment outdated for customer {customer.id}")
            return True
        
        return False
    
    def _detect_significant_changes(self, customer: Customer) -> bool:
        """Detect significant changes in customer profile"""
        # This would typically compare current data with last assessment
        # For simplicity, we'll check basic indicators
        
        last_assessment = customer.risk_assessments.filter(is_current=True).first()
        if not last_assessment:
            return True
        
        # Check for changes in key risk factors
        changes = []
        
        # Check PEP status change
        if customer.is_pep != getattr(last_assessment, 'customer_was_pep', False):
            changes.append('PEP status changed')
        
        # Check transaction volume changes (if available)
        # This would require historical data tracking
        
        return len(changes) > 0
    
    def _is_assessment_outdated(self, customer: Customer) -> bool:
        """Check if current assessment is outdated"""
        if not customer.last_risk_assessment:
            return True
        
        # Assessments older than 90 days are considered outdated
        ninety_days_ago = timezone.now() - timezone.timedelta(days=90)
        return customer.last_risk_assessment < ninety_days_ago


class RiskReportingService:
    """Service for risk reporting and analytics"""
    
    def generate_risk_summary(self, date_from=None, date_to=None) -> Dict:
        """Generate risk assessment summary"""
        
        if not date_from:
            date_from = timezone.now() - timezone.timedelta(days=30)
        if not date_to:
            date_to = timezone.now()
        
        assessments = RiskAssessment.objects.filter(
            assessment_date__range=[date_from, date_to]
        )
        
        summary = {
            'total_assessments': assessments.count(),
            'risk_distribution': {},
            'average_score': 0,
            'high_risk_customers': 0,
            'trends': {}
        }
        
        # Calculate risk distribution
        for level in ['VERY_LOW', 'LOW', 'MEDIUM', 'HIGH']:
            count = assessments.filter(risk_level=level).count()
            summary['risk_distribution'][level] = count
        
        # Calculate average score
        if assessments.exists():
            avg_score = assessments.aggregate(
                avg_score=models.Avg('risk_score')
            )['avg_score']
            summary['average_score'] = round(avg_score, 2) if avg_score else 0
        
        # Count high risk customers
        summary['high_risk_customers'] = assessments.filter(
            risk_level='HIGH'
        ).count()
        
        return summary
    
    def get_customer_risk_history(self, customer: Customer) -> List[Dict]:
        """Get risk assessment history for customer"""
        
        assessments = customer.risk_assessments.order_by('-assessment_date')[:10]
        
        history = []
        for assessment in assessments:
            history.append({
                'date': assessment.assessment_date,
                'score': assessment.risk_score,
                'level': assessment.risk_level,
                'methodology': assessment.methodology_version,
                'notes': assessment.notes
            })
        
        return history

