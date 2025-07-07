"""
CERES Simplified - Risk Services Unit Tests
Comprehensive unit tests for risk calculation and monitoring services
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date
from unittest.mock import patch, MagicMock

from apps.customers.models import Customer
from apps.risk.models import RiskFactor, RiskAssessment, RiskMatrix
from apps.risk.services import RiskCalculationService, RiskMonitoringService


class RiskCalculationServiceTest(TestCase):
    """Test cases for RiskCalculationService"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.customer = Customer.objects.create(
            customer_type='INDIVIDUAL',
            first_name='John',
            last_name='Doe',
            date_of_birth=date(1985, 5, 15),
            nationality='US',
            country='US',
            email='john.doe@example.com',
            phone='+1234567890',
            address='123 Main St',
            city='New York',
            postal_code='10001',
            industry='TECHNOLOGY',
            expected_monthly_volume=Decimal('50000.00'),
            source_of_funds='SALARY',
            is_pep=False
        )
        
        # Create risk factors
        self.geographic_factor = RiskFactor.objects.create(
            name='Geographic Risk',
            description='Risk based on customer location',
            factor_type='GEOGRAPHIC',
            risk_weight=10,
            is_active=True
        )
        
        self.industry_factor = RiskFactor.objects.create(
            name='Industry Risk',
            description='Risk based on customer industry',
            factor_type='INDUSTRY',
            risk_weight=15,
            is_active=True
        )
        
        self.pep_factor = RiskFactor.objects.create(
            name='PEP Risk',
            description='Risk based on PEP status',
            factor_type='OTHER',
            risk_weight=25,
            is_active=True
        )
        
        # Create risk matrix
        self.risk_matrix = RiskMatrix.objects.create(
            name='Individual Matrix',
            customer_type='INDIVIDUAL',
            description='Matrix for individual customers',
            low_risk_threshold=30,
            medium_risk_threshold=60,
            high_risk_threshold=80,
            is_active=True
        )
        
        self.service = RiskCalculationService()
    
    def test_calculate_customer_risk_basic(self):
        """Test basic risk calculation"""
        assessment = self.service.calculate_customer_risk(self.customer, self.user)
        
        self.assertIsInstance(assessment, RiskAssessment)
        self.assertEqual(assessment.customer, self.customer)
        self.assertEqual(assessment.assessed_by, self.user)
        self.assertEqual(assessment.assessment_type, 'INITIAL')
        self.assertTrue(assessment.is_current)
        self.assertGreaterEqual(assessment.final_score, 0)
        self.assertLessEqual(assessment.final_score, 100)
    
    def test_calculate_customer_risk_with_factors(self):
        """Test risk calculation with specific factors"""
        # Test with low-risk customer
        low_risk_customer = Customer.objects.create(
            customer_type='INDIVIDUAL',
            first_name='Jane',
            last_name='Smith',
            nationality='CH',  # Switzerland - low risk
            country='CH',
            email='jane@example.com',
            phone='+41234567890',
            address='123 Swiss St',
            city='Zurich',
            postal_code='8001',
            industry='BANKING',  # Regulated industry
            expected_monthly_volume=Decimal('10000.00'),  # Low volume
            source_of_funds='SALARY',
            is_pep=False
        )
        
        assessment = self.service.calculate_customer_risk(low_risk_customer, self.user)
        
        # Should be relatively low risk
        self.assertLess(assessment.final_score, 70)
        self.assertIn(assessment.risk_level, ['LOW', 'MEDIUM'])
    
    def test_calculate_customer_risk_high_risk(self):
        """Test risk calculation for high-risk customer"""
        high_risk_customer = Customer.objects.create(
            customer_type='INDIVIDUAL',
            first_name='High',
            last_name='Risk',
            nationality='AF',  # Afghanistan - high risk
            country='AF',
            email='highrisk@example.com',
            phone='+93234567890',
            address='123 High Risk St',
            city='Kabul',
            postal_code='1001',
            industry='MONEY_SERVICES',  # High-risk industry
            expected_monthly_volume=Decimal('500000.00'),  # High volume
            source_of_funds='BUSINESS_REVENUE',
            is_pep=True  # PEP status
        )
        
        assessment = self.service.calculate_customer_risk(high_risk_customer, self.user)
        
        # Should be high risk
        self.assertGreater(assessment.final_score, 60)
        self.assertIn(assessment.risk_level, ['HIGH', 'CRITICAL'])
    
    def test_get_base_risk_score(self):
        """Test base risk score calculation"""
        base_score = self.service._get_base_risk_score(self.customer)
        
        # Should return default base score
        self.assertEqual(base_score, 50)
    
    def test_apply_risk_factors(self):
        """Test risk factor application"""
        base_score = 50
        final_score = self.service._apply_risk_factors(self.customer, base_score)
        
        # Score should be modified by factors
        self.assertNotEqual(final_score, base_score)
        self.assertGreaterEqual(final_score, 0)
        self.assertLessEqual(final_score, 100)
    
    def test_get_geographic_risk_weight(self):
        """Test geographic risk weight calculation"""
        # Test low-risk country
        weight = self.service._get_geographic_risk_weight('CH')  # Switzerland
        self.assertLessEqual(weight, 0)
        
        # Test high-risk country
        weight = self.service._get_geographic_risk_weight('AF')  # Afghanistan
        self.assertGreaterEqual(weight, 15)
        
        # Test unknown country (should use default)
        weight = self.service._get_geographic_risk_weight('XX')
        self.assertEqual(weight, 0)
    
    def test_get_industry_risk_weight(self):
        """Test industry risk weight calculation"""
        # Test low-risk industry
        weight = self.service._get_industry_risk_weight('BANKING')
        self.assertLessEqual(weight, 5)
        
        # Test high-risk industry
        weight = self.service._get_industry_risk_weight('MONEY_SERVICES')
        self.assertGreaterEqual(weight, 15)
        
        # Test unknown industry (should use default)
        weight = self.service._get_industry_risk_weight('UNKNOWN')
        self.assertEqual(weight, 0)
    
    def test_get_transaction_volume_risk_weight(self):
        """Test transaction volume risk weight calculation"""
        # Test low volume
        weight = self.service._get_transaction_volume_risk_weight(Decimal('5000.00'))
        self.assertLessEqual(weight, 0)
        
        # Test medium volume
        weight = self.service._get_transaction_volume_risk_weight(Decimal('50000.00'))
        self.assertGreaterEqual(weight, 0)
        self.assertLessEqual(weight, 10)
        
        # Test high volume
        weight = self.service._get_transaction_volume_risk_weight(Decimal('500000.00'))
        self.assertGreaterEqual(weight, 10)
    
    def test_determine_risk_level(self):
        """Test risk level determination"""
        # Test low risk
        risk_level = self.service._determine_risk_level(25, self.customer.customer_type)
        self.assertEqual(risk_level, 'LOW')
        
        # Test medium risk
        risk_level = self.service._determine_risk_level(45, self.customer.customer_type)
        self.assertEqual(risk_level, 'MEDIUM')
        
        # Test high risk
        risk_level = self.service._determine_risk_level(75, self.customer.customer_type)
        self.assertEqual(risk_level, 'HIGH')
        
        # Test critical risk
        risk_level = self.service._determine_risk_level(95, self.customer.customer_type)
        self.assertEqual(risk_level, 'CRITICAL')
    
    def test_force_recalculate(self):
        """Test force recalculation of existing assessment"""
        # Create initial assessment
        initial_assessment = self.service.calculate_customer_risk(self.customer, self.user)
        initial_score = initial_assessment.final_score
        
        # Force recalculation
        new_assessment = self.service.calculate_customer_risk(
            self.customer, self.user, force_recalculate=True
        )
        
        # Should create new assessment
        self.assertNotEqual(initial_assessment.id, new_assessment.id)
        
        # Old assessment should no longer be current
        initial_assessment.refresh_from_db()
        self.assertFalse(initial_assessment.is_current)
        
        # New assessment should be current
        self.assertTrue(new_assessment.is_current)
    
    def test_assessment_justification_generation(self):
        """Test assessment justification generation"""
        assessment = self.service.calculate_customer_risk(self.customer, self.user)
        
        # Should have meaningful justification
        self.assertIsNotNone(assessment.justification)
        self.assertGreater(len(assessment.justification), 50)
        self.assertIn('risk assessment', assessment.justification.lower())


class RiskMonitoringServiceTest(TestCase):
    """Test cases for RiskMonitoringService"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.customer = Customer.objects.create(
            customer_type='INDIVIDUAL',
            first_name='John',
            last_name='Doe',
            nationality='US',
            country='US',
            email='john.doe@example.com',
            phone='+1234567890',
            address='123 Main St',
            city='New York',
            postal_code='10001',
            industry='TECHNOLOGY',
            expected_monthly_volume=Decimal('50000.00'),
            source_of_funds='SALARY'
        )
        
        # Create initial risk assessment
        self.initial_assessment = RiskAssessment.objects.create(
            customer=self.customer,
            assessment_type='INITIAL',
            base_score=50,
            final_score=55,
            risk_level='MEDIUM',
            methodology='CERES Simplified',
            justification='Initial assessment',
            assessed_by=self.user,
            is_current=True
        )
        
        self.service = RiskMonitoringService()
    
    def test_monitor_customer_changes_no_change(self):
        """Test monitoring when no significant changes"""
        result = self.service.monitor_customer_changes(self.customer)
        
        # Should return False (no significant change)
        self.assertFalse(result)
    
    def test_monitor_customer_changes_significant_change(self):
        """Test monitoring when significant changes detected"""
        # Modify customer to trigger change
        self.customer.expected_monthly_volume = Decimal('200000.00')  # Significant increase
        self.customer.save()
        
        result = self.service.monitor_customer_changes(self.customer)
        
        # Should return True (significant change detected)
        self.assertTrue(result)
    
    def test_check_transaction_volume_change(self):
        """Test transaction volume change detection"""
        # Test no significant change
        result = self.service._check_transaction_volume_change(
            self.customer, Decimal('50000.00'), Decimal('55000.00')
        )
        self.assertFalse(result)
        
        # Test significant increase
        result = self.service._check_transaction_volume_change(
            self.customer, Decimal('50000.00'), Decimal('150000.00')
        )
        self.assertTrue(result)
        
        # Test significant decrease
        result = self.service._check_transaction_volume_change(
            self.customer, Decimal('100000.00'), Decimal('30000.00')
        )
        self.assertTrue(result)
    
    def test_check_profile_changes(self):
        """Test profile change detection"""
        # Test no changes
        changes = {
            'country': 'US',
            'industry': 'TECHNOLOGY',
            'is_pep': False
        }
        result = self.service._check_profile_changes(self.customer, changes)
        self.assertFalse(result)
        
        # Test country change
        changes['country'] = 'AF'  # High-risk country
        result = self.service._check_profile_changes(self.customer, changes)
        self.assertTrue(result)
        
        # Test PEP status change
        changes = {'country': 'US', 'industry': 'TECHNOLOGY', 'is_pep': True}
        result = self.service._check_profile_changes(self.customer, changes)
        self.assertTrue(result)
    
    def test_create_monitoring_record(self):
        """Test monitoring record creation"""
        monitoring_record = self.service._create_monitoring_record(
            customer=self.customer,
            monitoring_type='TRIGGERED',
            trigger_event='PROFILE_CHANGE',
            previous_risk_level='MEDIUM',
            current_risk_level='HIGH',
            risk_change_reason='Country change to high-risk jurisdiction'
        )
        
        self.assertEqual(monitoring_record.customer, self.customer)
        self.assertEqual(monitoring_record.monitoring_type, 'TRIGGERED')
        self.assertEqual(monitoring_record.trigger_event, 'PROFILE_CHANGE')
        self.assertEqual(monitoring_record.previous_risk_level, 'MEDIUM')
        self.assertEqual(monitoring_record.current_risk_level, 'HIGH')
        self.assertTrue(monitoring_record.action_required)
    
    def test_should_trigger_reassessment(self):
        """Test reassessment trigger logic"""
        # Test no trigger needed
        result = self.service._should_trigger_reassessment(
            previous_level='MEDIUM',
            current_level='MEDIUM',
            score_change=5
        )
        self.assertFalse(result)
        
        # Test risk level change
        result = self.service._should_trigger_reassessment(
            previous_level='MEDIUM',
            current_level='HIGH',
            score_change=15
        )
        self.assertTrue(result)
        
        # Test significant score change
        result = self.service._should_trigger_reassessment(
            previous_level='MEDIUM',
            current_level='MEDIUM',
            score_change=25
        )
        self.assertTrue(result)
    
    @patch('apps.risk.services.RiskCalculationService.calculate_customer_risk')
    def test_trigger_risk_reassessment(self, mock_calculate):
        """Test risk reassessment triggering"""
        # Mock the risk calculation
        mock_assessment = MagicMock()
        mock_assessment.risk_level = 'HIGH'
        mock_assessment.final_score = 75
        mock_calculate.return_value = mock_assessment
        
        result = self.service.trigger_risk_reassessment(
            customer=self.customer,
            trigger_event='PROFILE_CHANGE',
            reason='Customer moved to high-risk country'
        )
        
        # Should call risk calculation
        mock_calculate.assert_called_once()
        
        # Should return the new assessment
        self.assertEqual(result, mock_assessment)
    
    def test_get_risk_change_threshold(self):
        """Test risk change threshold calculation"""
        # Test different risk levels
        threshold = self.service._get_risk_change_threshold('LOW')
        self.assertEqual(threshold, 15)
        
        threshold = self.service._get_risk_change_threshold('MEDIUM')
        self.assertEqual(threshold, 20)
        
        threshold = self.service._get_risk_change_threshold('HIGH')
        self.assertEqual(threshold, 10)
        
        threshold = self.service._get_risk_change_threshold('CRITICAL')
        self.assertEqual(threshold, 5)
    
    def test_periodic_monitoring_check(self):
        """Test periodic monitoring check"""
        # Mock overdue review
        self.customer.next_review_date = timezone.now().date() - timezone.timedelta(days=1)
        self.customer.save()
        
        result = self.service.check_periodic_monitoring_due(self.customer)
        self.assertTrue(result)
        
        # Test not due
        self.customer.next_review_date = timezone.now().date() + timezone.timedelta(days=30)
        self.customer.save()
        
        result = self.service.check_periodic_monitoring_due(self.customer)
        self.assertFalse(result)

