"""
CERES Simplified - Customer Onboarding Workflow Integration Tests
Tests for complete customer onboarding workflow integration
"""

from decimal import Decimal
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date

from apps.customers.models import Customer, BeneficialOwner
from apps.risk.models import RiskAssessment, RiskFactor
from apps.sanctions.models import SanctionsList, SanctionsEntry, SanctionsScreening
from apps.compliance.models import ComplianceRule, ComplianceCheck
from apps.documents.models import DocumentType, Document
from apps.cases.models import Case

from apps.core.services import CustomerOnboardingOrchestrator
from apps.risk.services import RiskCalculationService
from apps.sanctions.services import SanctionsScreeningService
from apps.compliance.services import ComplianceWorkflowService


class CustomerOnboardingWorkflowTest(TransactionTestCase):
    """Integration tests for complete customer onboarding workflow"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='compliance_officer',
            email='compliance@ceres.com',
            password='testpass123'
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
        
        # Create compliance rules
        self.kyc_rule = ComplianceRule.objects.create(
            name='KYC Documentation Check',
            description='Verify all required KYC documents',
            rule_type='KYC',
            severity='CRITICAL',
            auto_check=True,
            is_active=True
        )
        
        self.aml_rule = ComplianceRule.objects.create(
            name='AML Risk Assessment',
            description='Assess customer for AML risks',
            rule_type='AML',
            severity='HIGH',
            auto_check=True,
            is_active=True
        )
        
        # Create document types
        self.passport_type = DocumentType.objects.create(
            name='Passport',
            description='Government issued passport',
            category='IDENTITY',
            is_required=True,
            is_active=True
        )
        
        # Create sanctions list
        self.sanctions_list = SanctionsList.objects.create(
            name='OFAC SDN List',
            description='OFAC Specially Designated Nationals List',
            source_url='https://www.treasury.gov/ofac/downloads/sdnlist.txt',
            is_active=True,
            last_updated=timezone.now(),
            total_entries=2
        )
        
        # Create test sanctions entries
        self.sanctions_entry = SanctionsEntry.objects.create(
            sanctions_list=self.sanctions_list,
            primary_name='JOHN TERRORIST',
            nationality='XX',
            address='Unknown Location',
            listing_date=timezone.now().date(),
            is_active=True
        )
        
        self.orchestrator = CustomerOnboardingOrchestrator()
    
    def test_complete_individual_onboarding_success(self):
        """Test complete successful onboarding for individual customer"""
        # Create customer data
        customer_data = {
            'customer_type': 'INDIVIDUAL',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'date_of_birth': date(1985, 3, 15),
            'nationality': 'US',
            'country': 'US',
            'email': 'jane.smith@example.com',
            'phone': '+1234567890',
            'address': '123 Main St',
            'city': 'New York',
            'postal_code': '10001',
            'industry': 'TECHNOLOGY',
            'expected_monthly_volume': Decimal('50000.00'),
            'source_of_funds': 'SALARY',
            'is_pep': False
        }
        
        # Execute onboarding workflow
        result = self.orchestrator.process_customer_onboarding(
            customer_data=customer_data,
            user=self.user
        )
        
        # Verify workflow result
        self.assertTrue(result['success'])
        self.assertIn('customer', result)
        self.assertIn('risk_assessment', result)
        self.assertIn('sanctions_screening', result)
        self.assertIn('compliance_checks', result)
        
        customer = result['customer']
        
        # Verify customer was created
        self.assertEqual(customer.first_name, 'Jane')
        self.assertEqual(customer.last_name, 'Smith')
        self.assertEqual(customer.email, 'jane.smith@example.com')
        
        # Verify risk assessment was performed
        risk_assessment = result['risk_assessment']
        self.assertIsInstance(risk_assessment, RiskAssessment)
        self.assertEqual(risk_assessment.customer, customer)
        self.assertTrue(risk_assessment.is_current)
        self.assertIn(risk_assessment.risk_level, ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'])
        
        # Verify sanctions screening was performed
        sanctions_screening = result['sanctions_screening']
        self.assertIsInstance(sanctions_screening, SanctionsScreening)
        self.assertEqual(sanctions_screening.customer, customer)
        self.assertEqual(sanctions_screening.screening_result, 'CLEAR')  # Should be clear
        
        # Verify compliance checks were performed
        compliance_checks = result['compliance_checks']
        self.assertGreater(len(compliance_checks), 0)
        
        # Verify customer status is appropriate
        customer.refresh_from_db()
        self.assertIn(customer.onboarding_status, ['APPROVED', 'PENDING_REVIEW'])
    
    def test_complete_corporate_onboarding_with_beneficial_owners(self):
        """Test complete onboarding for corporate customer with beneficial owners"""
        # Create corporate customer data
        customer_data = {
            'customer_type': 'LEGAL_ENTITY',
            'company_name': 'Tech Innovations Inc',
            'registration_number': 'REG123456789',
            'nationality': 'US',
            'country': 'US',
            'email': 'contact@techinnovations.com',
            'phone': '+1234567890',
            'address': '456 Business Ave',
            'city': 'San Francisco',
            'postal_code': '94105',
            'industry': 'TECHNOLOGY',
            'expected_monthly_volume': Decimal('200000.00'),
            'source_of_funds': 'BUSINESS_REVENUE'
        }
        
        # Beneficial owners data
        beneficial_owners_data = [
            {
                'first_name': 'John',
                'last_name': 'Founder',
                'date_of_birth': date(1980, 1, 1),
                'nationality': 'US',
                'ownership_percentage': Decimal('60.00'),
                'is_control_person': True,
                'relationship_type': 'SHAREHOLDER'
            },
            {
                'first_name': 'Sarah',
                'last_name': 'Partner',
                'date_of_birth': date(1985, 6, 15),
                'nationality': 'US',
                'ownership_percentage': Decimal('40.00'),
                'is_control_person': False,
                'relationship_type': 'SHAREHOLDER'
            }
        ]
        
        # Execute onboarding workflow
        result = self.orchestrator.process_customer_onboarding(
            customer_data=customer_data,
            beneficial_owners_data=beneficial_owners_data,
            user=self.user
        )
        
        # Verify workflow result
        self.assertTrue(result['success'])
        
        customer = result['customer']
        
        # Verify customer was created
        self.assertEqual(customer.company_name, 'Tech Innovations Inc')
        self.assertEqual(customer.customer_type, 'LEGAL_ENTITY')
        
        # Verify beneficial owners were created
        beneficial_owners = customer.beneficial_owners.all()
        self.assertEqual(beneficial_owners.count(), 2)
        
        # Verify beneficial owners screening
        for bo in beneficial_owners:
            bo_screenings = SanctionsScreening.objects.filter(
                customer=customer,
                screened_name__icontains=bo.first_name
            )
            self.assertGreater(bo_screenings.count(), 0)
        
        # Verify risk assessment considers beneficial owners
        risk_assessment = result['risk_assessment']
        self.assertIsInstance(risk_assessment, RiskAssessment)
    
    def test_onboarding_with_sanctions_hit(self):
        """Test onboarding workflow when sanctions hit is detected"""
        # Create customer with name similar to sanctions entry
        customer_data = {
            'customer_type': 'INDIVIDUAL',
            'first_name': 'John',
            'last_name': 'Terrorist',  # Matches sanctions entry
            'date_of_birth': date(1980, 1, 1),
            'nationality': 'XX',
            'country': 'XX',
            'email': 'john.terrorist@example.com',
            'phone': '+1234567890',
            'address': '123 Suspicious St',
            'city': 'Unknown',
            'postal_code': '00000',
            'industry': 'OTHER',
            'expected_monthly_volume': Decimal('10000.00'),
            'source_of_funds': 'OTHER'
        }
        
        # Execute onboarding workflow
        result = self.orchestrator.process_customer_onboarding(
            customer_data=customer_data,
            user=self.user
        )
        
        # Verify workflow result
        self.assertTrue(result['success'])  # Workflow completes but flags issues
        
        customer = result['customer']
        
        # Verify sanctions screening detected hit
        sanctions_screening = result['sanctions_screening']
        self.assertEqual(sanctions_screening.screening_result, 'HIT')
        self.assertGreater(sanctions_screening.match_score, 80)
        
        # Verify customer status reflects sanctions concern
        customer.refresh_from_db()
        self.assertEqual(customer.onboarding_status, 'REQUIRES_MANUAL_REVIEW')
        
        # Verify case was created for manual review
        cases = Case.objects.filter(customer=customer)
        self.assertGreater(cases.count(), 0)
        
        sanctions_case = cases.filter(case_type='SANCTIONS_REVIEW').first()
        self.assertIsNotNone(sanctions_case)
        self.assertEqual(sanctions_case.priority, 'HIGH')
    
    def test_onboarding_with_high_risk_profile(self):
        """Test onboarding workflow for high-risk customer profile"""
        # Create high-risk customer
        customer_data = {
            'customer_type': 'INDIVIDUAL',
            'first_name': 'High',
            'last_name': 'Risk',
            'date_of_birth': date(1970, 1, 1),
            'nationality': 'AF',  # High-risk country
            'country': 'AF',
            'email': 'highrisk@example.com',
            'phone': '+93234567890',
            'address': '123 High Risk St',
            'city': 'Kabul',
            'postal_code': '1001',
            'industry': 'MONEY_SERVICES',  # High-risk industry
            'expected_monthly_volume': Decimal('1000000.00'),  # High volume
            'source_of_funds': 'BUSINESS_REVENUE',
            'is_pep': True  # PEP status
        }
        
        # Execute onboarding workflow
        result = self.orchestrator.process_customer_onboarding(
            customer_data=customer_data,
            user=self.user
        )
        
        # Verify workflow result
        self.assertTrue(result['success'])
        
        customer = result['customer']
        
        # Verify high risk assessment
        risk_assessment = result['risk_assessment']
        self.assertIn(risk_assessment.risk_level, ['HIGH', 'CRITICAL'])
        self.assertGreater(risk_assessment.final_score, 70)
        
        # Verify enhanced due diligence requirements
        customer.refresh_from_db()
        self.assertEqual(customer.onboarding_status, 'REQUIRES_MANUAL_REVIEW')
        
        # Verify compliance checks flagged issues
        compliance_checks = result['compliance_checks']
        failed_checks = [check for check in compliance_checks if check.check_result == 'FAIL']
        self.assertGreater(len(failed_checks), 0)
    
    def test_onboarding_workflow_error_handling(self):
        """Test onboarding workflow error handling"""
        # Create invalid customer data (missing required fields)
        invalid_customer_data = {
            'customer_type': 'INDIVIDUAL',
            'first_name': 'Test',
            # Missing required fields
        }
        
        # Execute onboarding workflow
        result = self.orchestrator.process_customer_onboarding(
            customer_data=invalid_customer_data,
            user=self.user
        )
        
        # Verify workflow handles error gracefully
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIsNotNone(result['error'])
    
    def test_onboarding_with_document_upload(self):
        """Test onboarding workflow with document upload"""
        customer_data = {
            'customer_type': 'INDIVIDUAL',
            'first_name': 'Document',
            'last_name': 'Test',
            'date_of_birth': date(1985, 5, 15),
            'nationality': 'US',
            'country': 'US',
            'email': 'doctest@example.com',
            'phone': '+1234567890',
            'address': '123 Doc St',
            'city': 'New York',
            'postal_code': '10001',
            'industry': 'TECHNOLOGY',
            'expected_monthly_volume': Decimal('50000.00'),
            'source_of_funds': 'SALARY'
        }
        
        # Execute onboarding workflow
        result = self.orchestrator.process_customer_onboarding(
            customer_data=customer_data,
            user=self.user
        )
        
        self.assertTrue(result['success'])
        customer = result['customer']
        
        # Simulate document upload
        document = Document.objects.create(
            customer=customer,
            document_type=self.passport_type,
            file_name='passport.pdf',
            file_size=1024000,
            upload_date=timezone.now(),
            status='PENDING_REVIEW',
            uploaded_by=self.user
        )
        
        # Verify document was associated with customer
        self.assertEqual(document.customer, customer)
        self.assertEqual(document.document_type, self.passport_type)
        
        # Verify compliance check considers document
        compliance_checks = ComplianceCheck.objects.filter(customer=customer)
        kyc_checks = compliance_checks.filter(compliance_rule=self.kyc_rule)
        self.assertGreater(kyc_checks.count(), 0)


class WorkflowIntegrationTest(TestCase):
    """Integration tests for various workflow components"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.customer = Customer.objects.create(
            customer_type='INDIVIDUAL',
            first_name='Integration',
            last_name='Test',
            nationality='US',
            country='US',
            email='integration@example.com',
            phone='+1234567890',
            address='123 Integration St',
            city='New York',
            postal_code='10001',
            industry='TECHNOLOGY',
            expected_monthly_volume=Decimal('50000.00'),
            source_of_funds='SALARY'
        )
    
    def test_risk_calculation_sanctions_screening_integration(self):
        """Test integration between risk calculation and sanctions screening"""
        # Create risk calculation service
        risk_service = RiskCalculationService()
        sanctions_service = SanctionsScreeningService()
        
        # Perform risk assessment
        risk_assessment = risk_service.calculate_customer_risk(self.customer, self.user)
        
        # Perform sanctions screening
        screening_result = sanctions_service.screen_customer(self.customer)
        
        # Verify both services work together
        self.assertIsInstance(risk_assessment, RiskAssessment)
        self.assertIsInstance(screening_result, SanctionsScreening)
        
        # Verify data consistency
        self.assertEqual(risk_assessment.customer, screening_result.customer)
    
    def test_compliance_workflow_risk_assessment_integration(self):
        """Test integration between compliance workflow and risk assessment"""
        compliance_service = ComplianceWorkflowService()
        risk_service = RiskCalculationService()
        
        # Perform risk assessment first
        risk_assessment = risk_service.calculate_customer_risk(self.customer, self.user)
        
        # Run compliance workflow
        compliance_result = compliance_service.process_customer_compliance(
            self.customer, self.user
        )
        
        # Verify integration
        self.assertTrue(compliance_result['success'])
        self.assertGreater(len(compliance_result['checks']), 0)
        
        # Verify compliance considers risk level
        for check in compliance_result['checks']:
            self.assertEqual(check.customer, self.customer)
    
    def test_end_to_end_customer_lifecycle(self):
        """Test complete customer lifecycle from onboarding to monitoring"""
        orchestrator = CustomerOnboardingOrchestrator()
        
        # Step 1: Initial onboarding
        customer_data = {
            'customer_type': 'INDIVIDUAL',
            'first_name': 'Lifecycle',
            'last_name': 'Test',
            'date_of_birth': date(1985, 1, 1),
            'nationality': 'US',
            'country': 'US',
            'email': 'lifecycle@example.com',
            'phone': '+1234567890',
            'address': '123 Lifecycle St',
            'city': 'New York',
            'postal_code': '10001',
            'industry': 'TECHNOLOGY',
            'expected_monthly_volume': Decimal('50000.00'),
            'source_of_funds': 'SALARY'
        }
        
        onboarding_result = orchestrator.process_customer_onboarding(
            customer_data=customer_data,
            user=self.user
        )
        
        self.assertTrue(onboarding_result['success'])
        customer = onboarding_result['customer']
        
        # Step 2: Simulate profile change
        customer.expected_monthly_volume = Decimal('200000.00')  # Significant increase
        customer.save()
        
        # Step 3: Trigger monitoring
        from apps.risk.services import RiskMonitoringService
        monitoring_service = RiskMonitoringService()
        
        monitoring_result = monitoring_service.monitor_customer_changes(customer)
        
        # Verify monitoring detected change
        self.assertTrue(monitoring_result)
        
        # Step 4: Verify new risk assessment was triggered
        latest_assessment = RiskAssessment.objects.filter(
            customer=customer,
            is_current=True
        ).first()
        
        self.assertIsNotNone(latest_assessment)
        
        # Step 5: Verify compliance re-evaluation
        compliance_service = ComplianceWorkflowService()
        compliance_result = compliance_service.process_customer_compliance(
            customer, self.user
        )
        
        self.assertTrue(compliance_result['success'])

