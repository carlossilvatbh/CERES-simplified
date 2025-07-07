"""
CERES Simplified - Risk Models Unit Tests
Comprehensive unit tests for risk assessment models
"""

import uuid
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date

from apps.customers.models import Customer
from apps.risk.models import (
    RiskFactor, RiskAssessment, RiskFactorApplication, 
    RiskMatrix, RiskMonitoring
)


class RiskFactorModelTest(TestCase):
    """Test cases for RiskFactor model"""
    
    def setUp(self):
        """Set up test data"""
        self.valid_factor_data = {
            'name': 'Geographic Risk',
            'description': 'Risk based on customer geographic location',
            'factor_type': 'GEOGRAPHIC',
            'risk_weight': 20,
            'is_active': True
        }
    
    def test_create_valid_risk_factor(self):
        """Test creating a valid risk factor"""
        factor = RiskFactor.objects.create(**self.valid_factor_data)
        
        self.assertIsInstance(factor.id, uuid.UUID)
        self.assertEqual(factor.name, 'Geographic Risk')
        self.assertEqual(factor.factor_type, 'GEOGRAPHIC')
        self.assertEqual(factor.risk_weight, 20)
        self.assertTrue(factor.is_active)
    
    def test_risk_factor_str_representation(self):
        """Test string representation"""
        factor = RiskFactor.objects.create(**self.valid_factor_data)
        expected_str = "Geographic Risk (Geográfico)"
        self.assertEqual(str(factor), expected_str)
    
    def test_factor_type_choices(self):
        """Test factor type choices validation"""
        valid_types = ['GEOGRAPHIC', 'INDUSTRY', 'PRODUCT', 'CUSTOMER_TYPE', 'TRANSACTION', 'OTHER']
        
        for factor_type in valid_types:
            data = self.valid_factor_data.copy()
            data['factor_type'] = factor_type
            data['name'] = f'Test {factor_type}'
            
            factor = RiskFactor.objects.create(**data)
            self.assertEqual(factor.factor_type, factor_type)
    
    def test_risk_weight_validation(self):
        """Test risk weight validation"""
        # Test weight within valid range
        data = self.valid_factor_data.copy()
        data['risk_weight'] = 25
        factor = RiskFactor.objects.create(**data)
        self.assertEqual(factor.risk_weight, 25)
        
        # Test weight at boundaries
        data['risk_weight'] = -50
        data['name'] = 'Negative Weight Test'
        factor = RiskFactor.objects.create(**data)
        self.assertEqual(factor.risk_weight, -50)
        
        data['risk_weight'] = 50
        data['name'] = 'Max Weight Test'
        factor = RiskFactor.objects.create(**data)
        self.assertEqual(factor.risk_weight, 50)
        
        # Test weight outside valid range
        data['risk_weight'] = 60
        factor = RiskFactor(**data)
        with self.assertRaises(ValidationError):
            factor.full_clean()
    
    def test_risk_factor_meta_options(self):
        """Test model meta options"""
        factor = RiskFactor.objects.create(**self.valid_factor_data)
        
        self.assertEqual(RiskFactor._meta.verbose_name, "Fator de Risco")
        self.assertEqual(RiskFactor._meta.verbose_name_plural, "Fatores de Risco")
        self.assertEqual(RiskFactor._meta.ordering, ['factor_type', 'name'])


class RiskAssessmentModelTest(TestCase):
    """Test cases for RiskAssessment model"""
    
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
            source_of_funds='SALARY'
        )
        
        self.valid_assessment_data = {
            'customer': self.customer,
            'assessment_type': 'INITIAL',
            'base_score': 50,
            'final_score': 65,
            'risk_level': 'MEDIUM',
            'methodology': 'CERES Simplified',
            'justification': 'Standard risk assessment based on customer profile',
            'assessed_by': self.user,
            'is_current': True
        }
    
    def test_create_valid_risk_assessment(self):
        """Test creating a valid risk assessment"""
        assessment = RiskAssessment.objects.create(**self.valid_assessment_data)
        
        self.assertIsInstance(assessment.id, uuid.UUID)
        self.assertEqual(assessment.customer, self.customer)
        self.assertEqual(assessment.final_score, 65)
        self.assertEqual(assessment.risk_level, 'MEDIUM')
        self.assertTrue(assessment.is_current)
    
    def test_risk_assessment_str_representation(self):
        """Test string representation"""
        assessment = RiskAssessment.objects.create(**self.valid_assessment_data)
        expected_str = f"John Doe - MEDIUM (65)"
        self.assertEqual(str(assessment), expected_str)
    
    def test_assessment_type_choices(self):
        """Test assessment type choices"""
        valid_types = ['INITIAL', 'PERIODIC', 'TRIGGERED', 'MANUAL']
        
        for assessment_type in valid_types:
            data = self.valid_assessment_data.copy()
            data['assessment_type'] = assessment_type
            data['is_current'] = False  # Avoid unique constraint
            
            assessment = RiskAssessment.objects.create(**data)
            self.assertEqual(assessment.assessment_type, assessment_type)
    
    def test_risk_level_choices(self):
        """Test risk level choices"""
        valid_levels = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        
        for risk_level in valid_levels:
            data = self.valid_assessment_data.copy()
            data['risk_level'] = risk_level
            data['is_current'] = False  # Avoid unique constraint
            
            assessment = RiskAssessment.objects.create(**data)
            self.assertEqual(assessment.risk_level, risk_level)
    
    def test_score_validation(self):
        """Test score validation"""
        # Test valid scores
        data = self.valid_assessment_data.copy()
        data['base_score'] = 0
        data['final_score'] = 100
        data['is_current'] = False
        
        assessment = RiskAssessment.objects.create(**data)
        self.assertEqual(assessment.base_score, 0)
        self.assertEqual(assessment.final_score, 100)
        
        # Test invalid scores
        data['base_score'] = -10
        assessment = RiskAssessment(**data)
        with self.assertRaises(ValidationError):
            assessment.full_clean()
        
        data['base_score'] = 50
        data['final_score'] = 150
        assessment = RiskAssessment(**data)
        with self.assertRaises(ValidationError):
            assessment.full_clean()
    
    def test_current_assessment_uniqueness(self):
        """Test that only one current assessment per customer"""
        # Create first current assessment
        RiskAssessment.objects.create(**self.valid_assessment_data)
        
        # Try to create another current assessment for same customer
        data = self.valid_assessment_data.copy()
        data['final_score'] = 70
        
        with self.assertRaises(Exception):  # Should raise integrity error
            RiskAssessment.objects.create(**data)
    
    def test_customer_relationship(self):
        """Test customer foreign key relationship"""
        assessment = RiskAssessment.objects.create(**self.valid_assessment_data)
        
        # Test relationship from customer side
        self.assertIn(assessment, self.customer.risk_assessments.all())
        
        # Test cascade delete
        customer_id = self.customer.id
        self.customer.delete()
        
        # Assessment should be deleted too
        self.assertFalse(RiskAssessment.objects.filter(customer_id=customer_id).exists())


class RiskMatrixModelTest(TestCase):
    """Test cases for RiskMatrix model"""
    
    def setUp(self):
        """Set up test data"""
        self.valid_matrix_data = {
            'name': 'Individual Customer Matrix',
            'description': 'Standard risk matrix for individual customers',
            'customer_type': 'INDIVIDUAL',
            'low_risk_threshold': 30,
            'medium_risk_threshold': 60,
            'high_risk_threshold': 80,
            'is_active': True
        }
    
    def test_create_valid_risk_matrix(self):
        """Test creating a valid risk matrix"""
        matrix = RiskMatrix.objects.create(**self.valid_matrix_data)
        
        self.assertIsInstance(matrix.id, uuid.UUID)
        self.assertEqual(matrix.name, 'Individual Customer Matrix')
        self.assertEqual(matrix.customer_type, 'INDIVIDUAL')
        self.assertEqual(matrix.low_risk_threshold, 30)
        self.assertTrue(matrix.is_active)
    
    def test_risk_matrix_str_representation(self):
        """Test string representation"""
        matrix = RiskMatrix.objects.create(**self.valid_matrix_data)
        expected_str = "Individual Customer Matrix (Pessoa Física)"
        self.assertEqual(str(matrix), expected_str)
    
    def test_customer_type_choices(self):
        """Test customer type choices"""
        valid_types = ['INDIVIDUAL', 'CORPORATE', 'PARTNERSHIP', 'TRUST', 'FOUNDATION', 'OTHER']
        
        for customer_type in valid_types:
            data = self.valid_matrix_data.copy()
            data['customer_type'] = customer_type
            data['name'] = f'{customer_type} Matrix'
            
            matrix = RiskMatrix.objects.create(**data)
            self.assertEqual(matrix.customer_type, customer_type)
    
    def test_threshold_validation(self):
        """Test threshold validation"""
        # Test valid thresholds
        data = self.valid_matrix_data.copy()
        data['low_risk_threshold'] = 25
        data['medium_risk_threshold'] = 55
        data['high_risk_threshold'] = 85
        
        matrix = RiskMatrix.objects.create(**data)
        self.assertEqual(matrix.low_risk_threshold, 25)
        
        # Test invalid thresholds (outside 0-100 range)
        data['low_risk_threshold'] = -10
        matrix = RiskMatrix(**data)
        with self.assertRaises(ValidationError):
            matrix.full_clean()
        
        data['low_risk_threshold'] = 30
        data['high_risk_threshold'] = 150
        matrix = RiskMatrix(**data)
        with self.assertRaises(ValidationError):
            matrix.full_clean()


class RiskFactorApplicationModelTest(TestCase):
    """Test cases for RiskFactorApplication model"""
    
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
        
        self.risk_factor = RiskFactor.objects.create(
            name='Geographic Risk',
            description='Risk based on customer location',
            factor_type='GEOGRAPHIC',
            risk_weight=20,
            is_active=True
        )
        
        self.risk_assessment = RiskAssessment.objects.create(
            customer=self.customer,
            assessment_type='INITIAL',
            base_score=50,
            final_score=65,
            risk_level='MEDIUM',
            methodology='CERES Simplified',
            justification='Test assessment',
            assessed_by=self.user,
            is_current=True
        )
        
        self.valid_application_data = {
            'assessment': self.risk_assessment,
            'risk_factor': self.risk_factor,
            'applied_weight': 15,
            'justification': 'Customer located in low-risk jurisdiction'
        }
    
    def test_create_valid_factor_application(self):
        """Test creating a valid factor application"""
        application = RiskFactorApplication.objects.create(**self.valid_application_data)
        
        self.assertIsInstance(application.id, uuid.UUID)
        self.assertEqual(application.assessment, self.risk_assessment)
        self.assertEqual(application.risk_factor, self.risk_factor)
        self.assertEqual(application.applied_weight, 15)
    
    def test_factor_application_str_representation(self):
        """Test string representation"""
        application = RiskFactorApplication.objects.create(**self.valid_application_data)
        expected_str = f"Geographic Risk applied to John Doe assessment (weight: 15)"
        self.assertEqual(str(application), expected_str)
    
    def test_applied_weight_validation(self):
        """Test applied weight validation"""
        # Test valid weight
        data = self.valid_application_data.copy()
        data['applied_weight'] = -25
        
        application = RiskFactorApplication.objects.create(**data)
        self.assertEqual(application.applied_weight, -25)
        
        # Test weight outside valid range
        data['applied_weight'] = 60
        application = RiskFactorApplication(**data)
        with self.assertRaises(ValidationError):
            application.full_clean()
    
    def test_unique_factor_per_assessment(self):
        """Test that same factor can't be applied twice to same assessment"""
        # Create first application
        RiskFactorApplication.objects.create(**self.valid_application_data)
        
        # Try to create duplicate application
        with self.assertRaises(Exception):  # Should raise integrity error
            RiskFactorApplication.objects.create(**self.valid_application_data)


class RiskMonitoringModelTest(TestCase):
    """Test cases for RiskMonitoring model"""
    
    def setUp(self):
        """Set up test data"""
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
        
        self.valid_monitoring_data = {
            'customer': self.customer,
            'monitoring_type': 'PERIODIC',
            'trigger_event': 'SCHEDULED_REVIEW',
            'previous_risk_level': 'MEDIUM',
            'current_risk_level': 'HIGH',
            'risk_change_reason': 'Increased transaction volume',
            'action_required': True,
            'action_description': 'Enhanced due diligence required'
        }
    
    def test_create_valid_risk_monitoring(self):
        """Test creating a valid risk monitoring record"""
        monitoring = RiskMonitoring.objects.create(**self.valid_monitoring_data)
        
        self.assertIsInstance(monitoring.id, uuid.UUID)
        self.assertEqual(monitoring.customer, self.customer)
        self.assertEqual(monitoring.monitoring_type, 'PERIODIC')
        self.assertEqual(monitoring.previous_risk_level, 'MEDIUM')
        self.assertEqual(monitoring.current_risk_level, 'HIGH')
        self.assertTrue(monitoring.action_required)
    
    def test_risk_monitoring_str_representation(self):
        """Test string representation"""
        monitoring = RiskMonitoring.objects.create(**self.valid_monitoring_data)
        expected_str = f"John Doe - MEDIUM → HIGH (PERIODIC)"
        self.assertEqual(str(monitoring), expected_str)
    
    def test_monitoring_type_choices(self):
        """Test monitoring type choices"""
        valid_types = ['PERIODIC', 'TRIGGERED', 'MANUAL', 'SYSTEM_ALERT']
        
        for monitoring_type in valid_types:
            data = self.valid_monitoring_data.copy()
            data['monitoring_type'] = monitoring_type
            
            monitoring = RiskMonitoring.objects.create(**data)
            self.assertEqual(monitoring.monitoring_type, monitoring_type)
    
    def test_trigger_event_choices(self):
        """Test trigger event choices"""
        valid_events = [
            'SCHEDULED_REVIEW', 'TRANSACTION_THRESHOLD', 'PROFILE_CHANGE',
            'SANCTIONS_HIT', 'ADVERSE_MEDIA', 'MANUAL_TRIGGER'
        ]
        
        for trigger_event in valid_events:
            data = self.valid_monitoring_data.copy()
            data['trigger_event'] = trigger_event
            
            monitoring = RiskMonitoring.objects.create(**data)
            self.assertEqual(monitoring.trigger_event, trigger_event)

