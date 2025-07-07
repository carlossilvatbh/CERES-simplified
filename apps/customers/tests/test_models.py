"""
CERES Simplified - Customer Models Unit Tests
Comprehensive unit tests for customer models
"""

import uuid
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from datetime import date, timedelta

from apps.customers.models import Customer, BeneficialOwner


class CustomerModelTest(TestCase):
    """Test cases for Customer model"""
    
    def setUp(self):
        """Set up test data"""
        self.valid_customer_data = {
            'customer_type': 'INDIVIDUAL',
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': date(1985, 5, 15),
            'nationality': 'US',
            'country': 'US',
            'email': 'john.doe@example.com',
            'phone': '+1234567890',
            'address': '123 Main St',
            'city': 'New York',
            'postal_code': '10001',
            'industry': 'TECHNOLOGY',
            'expected_monthly_volume': Decimal('50000.00'),
            'source_of_funds': 'SALARY',
            'is_pep': False,
            'onboarding_status': 'PENDING_REVIEW'
        }
    
    def test_create_valid_customer(self):
        """Test creating a valid customer"""
        customer = Customer.objects.create(**self.valid_customer_data)
        
        self.assertIsInstance(customer.id, uuid.UUID)
        self.assertEqual(customer.full_name, 'John Doe')
        self.assertEqual(customer.customer_type, 'INDIVIDUAL')
        self.assertEqual(customer.onboarding_status, 'PENDING_REVIEW')
        self.assertIsNotNone(customer.created_at)
        self.assertIsNotNone(customer.updated_at)
    
    def test_customer_full_name_property(self):
        """Test full_name property for different customer types"""
        # Individual customer
        individual = Customer.objects.create(**self.valid_customer_data)
        self.assertEqual(individual.full_name, 'John Doe')
        
        # Corporate customer
        corporate_data = self.valid_customer_data.copy()
        corporate_data.update({
            'customer_type': 'LEGAL_ENTITY',
            'company_name': 'Acme Corporation',
            'first_name': '',
            'last_name': '',
            'email': 'contact@acme.com'
        })
        corporate = Customer.objects.create(**corporate_data)
        self.assertEqual(corporate.full_name, 'Acme Corporation')
    
    def test_customer_age_calculation(self):
        """Test age calculation"""
        customer = Customer.objects.create(**self.valid_customer_data)
        expected_age = timezone.now().year - 1985
        
        # Account for birthday not yet passed this year
        if timezone.now().date() < date(timezone.now().year, 5, 15):
            expected_age -= 1
        
        self.assertEqual(customer.age, expected_age)
    
    def test_customer_age_none_for_no_birth_date(self):
        """Test age returns None when no birth date"""
        data = self.valid_customer_data.copy()
        data['date_of_birth'] = None
        customer = Customer.objects.create(**data)
        self.assertIsNone(customer.age)
    
    def test_customer_str_representation(self):
        """Test string representation"""
        customer = Customer.objects.create(**self.valid_customer_data)
        expected_str = f"John Doe (INDIVIDUAL)"
        self.assertEqual(str(customer), expected_str)
    
    def test_email_uniqueness(self):
        """Test email uniqueness constraint"""
        Customer.objects.create(**self.valid_customer_data)
        
        # Try to create another customer with same email
        duplicate_data = self.valid_customer_data.copy()
        duplicate_data['first_name'] = 'Jane'
        
        with self.assertRaises(IntegrityError):
            Customer.objects.create(**duplicate_data)
    
    def test_required_fields_validation(self):
        """Test required fields validation"""
        # Test missing customer_type
        data = self.valid_customer_data.copy()
        del data['customer_type']
        
        with self.assertRaises(IntegrityError):
            Customer.objects.create(**data)
    
    def test_customer_type_choices(self):
        """Test customer type choices validation"""
        data = self.valid_customer_data.copy()
        data['customer_type'] = 'INVALID_TYPE'
        
        customer = Customer(**data)
        with self.assertRaises(ValidationError):
            customer.full_clean()
    
    def test_onboarding_status_choices(self):
        """Test onboarding status choices"""
        valid_statuses = [
            'PENDING_REVIEW', 'APPROVED', 'REJECTED', 
            'REQUIRES_MANUAL_REVIEW', 'SUSPENDED'
        ]
        
        for status in valid_statuses:
            data = self.valid_customer_data.copy()
            data['onboarding_status'] = status
            data['email'] = f'test_{status.lower()}@example.com'
            
            customer = Customer.objects.create(**data)
            self.assertEqual(customer.onboarding_status, status)
    
    def test_risk_level_default(self):
        """Test default risk level"""
        customer = Customer.objects.create(**self.valid_customer_data)
        self.assertEqual(customer.risk_level, 'MEDIUM')
    
    def test_expected_monthly_volume_validation(self):
        """Test expected monthly volume validation"""
        # Test negative value
        data = self.valid_customer_data.copy()
        data['expected_monthly_volume'] = Decimal('-1000.00')
        
        customer = Customer(**data)
        with self.assertRaises(ValidationError):
            customer.full_clean()
    
    def test_next_review_date_auto_calculation(self):
        """Test next review date calculation"""
        customer = Customer.objects.create(**self.valid_customer_data)
        
        # Should be set to 1 year from creation for medium risk
        expected_date = (timezone.now() + timedelta(days=365)).date()
        self.assertEqual(customer.next_review_date, expected_date)
    
    def test_customer_meta_options(self):
        """Test model meta options"""
        customer = Customer.objects.create(**self.valid_customer_data)
        
        # Test verbose names
        self.assertEqual(Customer._meta.verbose_name, "Cliente")
        self.assertEqual(Customer._meta.verbose_name_plural, "Clientes")
        
        # Test ordering
        self.assertEqual(Customer._meta.ordering, ['-created_at'])


class BeneficialOwnerModelTest(TestCase):
    """Test cases for BeneficialOwner model"""
    
    def setUp(self):
        """Set up test data"""
        self.customer = Customer.objects.create(
            customer_type='LEGAL_ENTITY',
            company_name='Test Corp',
            nationality='US',
            country='US',
            email='test@corp.com',
            phone='+1234567890',
            address='123 Business St',
            city='New York',
            postal_code='10001',
            industry='TECHNOLOGY',
            expected_monthly_volume=Decimal('100000.00'),
            source_of_funds='BUSINESS_REVENUE'
        )
        
        self.valid_bo_data = {
            'customer': self.customer,
            'first_name': 'Jane',
            'last_name': 'Smith',
            'date_of_birth': date(1980, 3, 20),
            'nationality': 'US',
            'ownership_percentage': Decimal('25.50'),
            'is_control_person': True,
            'relationship_type': 'SHAREHOLDER'
        }
    
    def test_create_valid_beneficial_owner(self):
        """Test creating a valid beneficial owner"""
        bo = BeneficialOwner.objects.create(**self.valid_bo_data)
        
        self.assertIsInstance(bo.id, uuid.UUID)
        self.assertEqual(bo.full_name, 'Jane Smith')
        self.assertEqual(bo.ownership_percentage, Decimal('25.50'))
        self.assertTrue(bo.is_control_person)
        self.assertEqual(bo.customer, self.customer)
    
    def test_beneficial_owner_full_name(self):
        """Test full_name property"""
        bo = BeneficialOwner.objects.create(**self.valid_bo_data)
        self.assertEqual(bo.full_name, 'Jane Smith')
    
    def test_beneficial_owner_str_representation(self):
        """Test string representation"""
        bo = BeneficialOwner.objects.create(**self.valid_bo_data)
        expected_str = f"Jane Smith (25.50% of Test Corp)"
        self.assertEqual(str(bo), expected_str)
    
    def test_ownership_percentage_validation(self):
        """Test ownership percentage validation"""
        # Test percentage over 100
        data = self.valid_bo_data.copy()
        data['ownership_percentage'] = Decimal('150.00')
        
        bo = BeneficialOwner(**data)
        with self.assertRaises(ValidationError):
            bo.full_clean()
        
        # Test negative percentage
        data['ownership_percentage'] = Decimal('-5.00')
        bo = BeneficialOwner(**data)
        with self.assertRaises(ValidationError):
            bo.full_clean()
    
    def test_relationship_type_choices(self):
        """Test relationship type choices"""
        valid_types = ['SHAREHOLDER', 'DIRECTOR', 'OFFICER', 'TRUSTEE', 'OTHER']
        
        for rel_type in valid_types:
            data = self.valid_bo_data.copy()
            data['relationship_type'] = rel_type
            data['first_name'] = f'Test_{rel_type}'
            
            bo = BeneficialOwner.objects.create(**data)
            self.assertEqual(bo.relationship_type, rel_type)
    
    def test_customer_relationship(self):
        """Test customer foreign key relationship"""
        bo = BeneficialOwner.objects.create(**self.valid_bo_data)
        
        # Test relationship from customer side
        self.assertIn(bo, self.customer.beneficial_owners.all())
        
        # Test cascade delete
        customer_id = self.customer.id
        self.customer.delete()
        
        # Beneficial owner should be deleted too
        self.assertFalse(BeneficialOwner.objects.filter(customer_id=customer_id).exists())
    
    def test_beneficial_owner_meta_options(self):
        """Test model meta options"""
        bo = BeneficialOwner.objects.create(**self.valid_bo_data)
        
        # Test verbose names
        self.assertEqual(BeneficialOwner._meta.verbose_name, "Beneficiário Final")
        self.assertEqual(BeneficialOwner._meta.verbose_name_plural, "Beneficiários Finais")
        
        # Test ordering
        self.assertEqual(BeneficialOwner._meta.ordering, ['-ownership_percentage', 'last_name'])
    
    def test_multiple_beneficial_owners_per_customer(self):
        """Test multiple beneficial owners for one customer"""
        # Create first beneficial owner
        bo1 = BeneficialOwner.objects.create(**self.valid_bo_data)
        
        # Create second beneficial owner
        bo2_data = self.valid_bo_data.copy()
        bo2_data.update({
            'first_name': 'Bob',
            'last_name': 'Johnson',
            'ownership_percentage': Decimal('30.00'),
            'is_control_person': False
        })
        bo2 = BeneficialOwner.objects.create(**bo2_data)
        
        # Test both are associated with customer
        self.assertEqual(self.customer.beneficial_owners.count(), 2)
        self.assertIn(bo1, self.customer.beneficial_owners.all())
        self.assertIn(bo2, self.customer.beneficial_owners.all())
    
    def test_beneficial_owner_age_calculation(self):
        """Test age calculation for beneficial owner"""
        bo = BeneficialOwner.objects.create(**self.valid_bo_data)
        expected_age = timezone.now().year - 1980
        
        # Account for birthday not yet passed this year
        if timezone.now().date() < date(timezone.now().year, 3, 20):
            expected_age -= 1
        
        self.assertEqual(bo.age, expected_age)

