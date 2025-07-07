"""
CERES Simplified - Sanctions and Compliance Integration Tests
Tests for integration between sanctions screening and compliance workflows
"""

from decimal import Decimal
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date

from apps.customers.models import Customer, BeneficialOwner
from apps.sanctions.models import SanctionsList, SanctionsEntry, SanctionsScreening
from apps.compliance.models import ComplianceRule, ComplianceCheck
from apps.cases.models import Case
from apps.risk.models import RiskAssessment

from apps.sanctions.services import SanctionsScreeningService
from apps.compliance.services import ComplianceWorkflowService
from apps.core.services import AlertManagementService


class SanctionsComplianceIntegrationTest(TransactionTestCase):
    """Integration tests for sanctions screening and compliance workflows"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='compliance_officer',
            email='compliance@ceres.com',
            password='testpass123'
        )
        
        # Create sanctions list and entries
        self.sanctions_list = SanctionsList.objects.create(
            name='OFAC SDN List',
            description='OFAC Specially Designated Nationals List',
            source_url='https://www.treasury.gov/ofac/downloads/sdnlist.txt',
            is_active=True,
            last_updated=timezone.now(),
            total_entries=3
        )
        
        # Create various sanctions entries for testing
        self.terrorist_entry = SanctionsEntry.objects.create(
            sanctions_list=self.sanctions_list,
            primary_name='JOHN TERRORIST',
            nationality='XX',
            address='Unknown Location',
            listing_date=timezone.now().date(),
            is_active=True
        )
        
        self.drug_dealer_entry = SanctionsEntry.objects.create(
            sanctions_list=self.sanctions_list,
            primary_name='MARIA DRUGDEALER',
            nationality='CO',
            address='Bogota, Colombia',
            listing_date=timezone.now().date(),
            is_active=True
        )
        
        self.money_launderer_entry = SanctionsEntry.objects.create(
            sanctions_list=self.sanctions_list,
            primary_name='ROBERT MONEYLAUNDERING',
            nationality='RU',
            address='Moscow, Russia',
            listing_date=timezone.now().date(),
            is_active=True
        )
        
        # Create compliance rules
        self.sanctions_rule = ComplianceRule.objects.create(
            name='Sanctions Screening',
            description='Screen customer against sanctions lists',
            rule_type='SANCTIONS',
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
        
        self.enhanced_dd_rule = ComplianceRule.objects.create(
            name='Enhanced Due Diligence',
            description='Enhanced due diligence for high-risk customers',
            rule_type='EDD',
            severity='HIGH',
            auto_check=False,
            is_active=True
        )
        
        # Initialize services
        self.sanctions_service = SanctionsScreeningService()
        self.compliance_service = ComplianceWorkflowService()
        self.alert_service = AlertManagementService()
    
    def test_sanctions_hit_triggers_compliance_workflow(self):
        """Test that sanctions hit triggers appropriate compliance workflow"""
        # Create customer with name matching sanctions entry
        customer = Customer.objects.create(
            customer_type='INDIVIDUAL',
            first_name='John',
            last_name='Terrorist',
            date_of_birth=date(1980, 1, 1),
            nationality='XX',
            country='XX',
            email='john.terrorist@example.com',
            phone='+1234567890',
            address='123 Suspicious St',
            city='Unknown',
            postal_code='00000',
            industry='OTHER',
            expected_monthly_volume=Decimal('10000.00'),
            source_of_funds='OTHER'
        )
        
        # Perform sanctions screening
        screening_result = self.sanctions_service.screen_customer(customer)
        
        # Verify sanctions hit detected
        self.assertEqual(screening_result.screening_result, 'HIT')
        self.assertGreater(screening_result.match_score, 80)
        
        # Run compliance workflow
        compliance_result = self.compliance_service.process_customer_compliance(
            customer, self.user
        )
        
        # Verify compliance workflow was triggered
        self.assertTrue(compliance_result['success'])
        
        # Verify sanctions compliance check failed
        sanctions_checks = ComplianceCheck.objects.filter(
            customer=customer,
            compliance_rule=self.sanctions_rule
        )
        self.assertGreater(sanctions_checks.count(), 0)
        
        sanctions_check = sanctions_checks.first()
        self.assertEqual(sanctions_check.check_result, 'FAIL')
        self.assertIn('sanctions hit', sanctions_check.check_details.lower())
        
        # Verify case was created for manual review
        cases = Case.objects.filter(customer=customer)
        self.assertGreater(cases.count(), 0)
        
        sanctions_case = cases.filter(case_type='SANCTIONS_REVIEW').first()
        self.assertIsNotNone(sanctions_case)
        self.assertEqual(sanctions_case.priority, 'HIGH')
        self.assertEqual(sanctions_case.status, 'OPEN')
    
    def test_beneficial_owner_sanctions_hit_workflow(self):
        """Test sanctions hit on beneficial owner triggers compliance workflow"""
        # Create corporate customer
        customer = Customer.objects.create(
            customer_type='LEGAL_ENTITY',
            company_name='Suspicious Corp',
            nationality='US',
            country='US',
            email='contact@suspicious.com',
            phone='+1234567890',
            address='456 Business Ave',
            city='New York',
            postal_code='10001',
            industry='TECHNOLOGY',
            expected_monthly_volume=Decimal('100000.00'),
            source_of_funds='BUSINESS_REVENUE'
        )
        
        # Create beneficial owner with sanctions hit
        beneficial_owner = BeneficialOwner.objects.create(
            customer=customer,
            first_name='Maria',
            last_name='Drugdealer',
            date_of_birth=date(1975, 5, 10),
            nationality='CO',
            ownership_percentage=Decimal('51.00'),
            is_control_person=True,
            relationship_type='SHAREHOLDER'
        )
        
        # Perform sanctions screening (should include beneficial owners)
        screening_result = self.sanctions_service.screen_customer(customer)
        
        # Verify beneficial owner screening detected hit
        bo_screenings = SanctionsScreening.objects.filter(
            customer=customer,
            screened_name__icontains='Maria'
        )
        self.assertGreater(bo_screenings.count(), 0)
        
        bo_screening = bo_screenings.first()
        self.assertEqual(bo_screening.screening_result, 'HIT')
        
        # Run compliance workflow
        compliance_result = self.compliance_service.process_customer_compliance(
            customer, self.user
        )
        
        # Verify enhanced due diligence triggered
        edd_checks = ComplianceCheck.objects.filter(
            customer=customer,
            compliance_rule=self.enhanced_dd_rule
        )
        self.assertGreater(edd_checks.count(), 0)
        
        # Verify customer status updated
        customer.refresh_from_db()
        self.assertEqual(customer.onboarding_status, 'REQUIRES_MANUAL_REVIEW')
    
    def test_multiple_sanctions_hits_escalation(self):
        """Test escalation when multiple sanctions hits detected"""
        # Create customer with multiple potential matches
        customer = Customer.objects.create(
            customer_type='INDIVIDUAL',
            first_name='Robert',
            last_name='Moneylaundering',
            date_of_birth=date(1970, 12, 25),
            nationality='RU',
            country='RU',
            email='robert.ml@example.com',
            phone='+7234567890',
            address='123 Moscow St',
            city='Moscow',
            postal_code='101000',
            industry='MONEY_SERVICES',
            expected_monthly_volume=Decimal('1000000.00'),
            source_of_funds='BUSINESS_REVENUE'
        )
        
        # Perform sanctions screening
        screening_result = self.sanctions_service.screen_customer(customer)
        
        # Verify high-confidence hit
        self.assertEqual(screening_result.screening_result, 'HIT')
        self.assertGreater(screening_result.match_score, 90)
        
        # Run compliance workflow
        compliance_result = self.compliance_service.process_customer_compliance(
            customer, self.user
        )
        
        # Verify multiple compliance checks failed
        failed_checks = ComplianceCheck.objects.filter(
            customer=customer,
            check_result='FAIL'
        )
        self.assertGreater(failed_checks.count(), 1)
        
        # Verify high-priority case created
        cases = Case.objects.filter(customer=customer)
        high_priority_cases = cases.filter(priority='CRITICAL')
        self.assertGreater(high_priority_cases.count(), 0)
        
        # Verify customer immediately suspended
        customer.refresh_from_db()
        self.assertEqual(customer.onboarding_status, 'REJECTED')
    
    def test_false_positive_sanctions_handling(self):
        """Test handling of false positive sanctions matches"""
        # Create customer with similar but not exact match
        customer = Customer.objects.create(
            customer_type='INDIVIDUAL',
            first_name='John',
            last_name='Terror',  # Similar but not exact match
            date_of_birth=date(1990, 6, 15),  # Different age
            nationality='US',  # Different nationality
            country='US',
            email='john.terror@example.com',
            phone='+1234567890',
            address='123 Normal St',
            city='New York',
            postal_code='10001',
            industry='TECHNOLOGY',
            expected_monthly_volume=Decimal('50000.00'),
            source_of_funds='SALARY'
        )
        
        # Perform sanctions screening
        screening_result = self.sanctions_service.screen_customer(customer)
        
        # Should detect potential match but with lower confidence
        if screening_result.screening_result == 'HIT':
            self.assertLess(screening_result.match_score, 80)
        else:
            self.assertEqual(screening_result.screening_result, 'CLEAR')
        
        # Run compliance workflow
        compliance_result = self.compliance_service.process_customer_compliance(
            customer, self.user
        )
        
        # Should pass or require manual review, not automatic rejection
        customer.refresh_from_db()
        self.assertIn(customer.onboarding_status, [
            'APPROVED', 'PENDING_REVIEW', 'REQUIRES_MANUAL_REVIEW'
        ])
        self.assertNotEqual(customer.onboarding_status, 'REJECTED')
    
    def test_sanctions_screening_with_risk_assessment_integration(self):
        """Test integration between sanctions screening and risk assessment"""
        # Create medium-risk customer
        customer = Customer.objects.create(
            customer_type='INDIVIDUAL',
            first_name='Medium',
            last_name='Risk',
            date_of_birth=date(1985, 3, 15),
            nationality='US',
            country='US',
            email='medium.risk@example.com',
            phone='+1234567890',
            address='123 Medium St',
            city='New York',
            postal_code='10001',
            industry='TECHNOLOGY',
            expected_monthly_volume=Decimal('75000.00'),
            source_of_funds='SALARY'
        )
        
        # Create risk assessment
        risk_assessment = RiskAssessment.objects.create(
            customer=customer,
            assessment_type='INITIAL',
            base_score=50,
            final_score=65,
            risk_level='MEDIUM',
            methodology='CERES Simplified',
            justification='Medium risk customer',
            assessed_by=self.user,
            is_current=True
        )
        
        # Perform sanctions screening
        screening_result = self.sanctions_service.screen_customer(customer)
        
        # Should be clear
        self.assertEqual(screening_result.screening_result, 'CLEAR')
        
        # Run compliance workflow
        compliance_result = self.compliance_service.process_customer_compliance(
            customer, self.user
        )
        
        # Verify compliance considers risk level
        compliance_checks = compliance_result['checks']
        
        # Medium risk should trigger standard checks
        sanctions_checks = [c for c in compliance_checks if c.compliance_rule == self.sanctions_rule]
        self.assertGreater(len(sanctions_checks), 0)
        
        sanctions_check = sanctions_checks[0]
        self.assertEqual(sanctions_check.check_result, 'PASS')
    
    def test_ongoing_sanctions_monitoring(self):
        """Test ongoing sanctions monitoring for existing customers"""
        # Create approved customer
        customer = Customer.objects.create(
            customer_type='INDIVIDUAL',
            first_name='Approved',
            last_name='Customer',
            date_of_birth=date(1985, 1, 1),
            nationality='US',
            country='US',
            email='approved@example.com',
            phone='+1234567890',
            address='123 Approved St',
            city='New York',
            postal_code='10001',
            industry='TECHNOLOGY',
            expected_monthly_volume=Decimal('50000.00'),
            source_of_funds='SALARY',
            onboarding_status='APPROVED'
        )
        
        # Initial screening (should be clear)
        initial_screening = self.sanctions_service.screen_customer(customer)
        self.assertEqual(initial_screening.screening_result, 'CLEAR')
        
        # Simulate new sanctions entry added that matches customer
        new_sanctions_entry = SanctionsEntry.objects.create(
            sanctions_list=self.sanctions_list,
            primary_name='APPROVED CUSTOMER',
            nationality='US',
            address='123 Approved St, New York',
            listing_date=timezone.now().date(),
            is_active=True
        )
        
        # Update sanctions list count
        self.sanctions_list.total_entries += 1
        self.sanctions_list.save()
        
        # Perform re-screening
        rescreening_result = self.sanctions_service.screen_customer(customer)
        
        # Should now detect hit
        self.assertEqual(rescreening_result.screening_result, 'HIT')
        
        # Run compliance workflow for existing customer
        compliance_result = self.compliance_service.process_customer_compliance(
            customer, self.user
        )
        
        # Verify customer status updated
        customer.refresh_from_db()
        self.assertEqual(customer.onboarding_status, 'SUSPENDED')
        
        # Verify case created for investigation
        investigation_cases = Case.objects.filter(
            customer=customer,
            case_type='SANCTIONS_REVIEW'
        )
        self.assertGreater(investigation_cases.count(), 0)
    
    def test_compliance_workflow_with_alert_management(self):
        """Test integration between compliance workflow and alert management"""
        # Create high-risk customer with sanctions concerns
        customer = Customer.objects.create(
            customer_type='INDIVIDUAL',
            first_name='Alert',
            last_name='Test',
            date_of_birth=date(1980, 1, 1),
            nationality='AF',  # High-risk country
            country='AF',
            email='alert.test@example.com',
            phone='+93234567890',
            address='123 Alert St',
            city='Kabul',
            postal_code='1001',
            industry='MONEY_SERVICES',
            expected_monthly_volume=Decimal('500000.00'),
            source_of_funds='BUSINESS_REVENUE',
            is_pep=True
        )
        
        # Perform sanctions screening
        screening_result = self.sanctions_service.screen_customer(customer)
        
        # Run compliance workflow
        compliance_result = self.compliance_service.process_customer_compliance(
            customer, self.user
        )
        
        # Process alerts
        alert_result = self.alert_service.process_customer_alerts(customer)
        
        # Verify alerts were generated
        self.assertTrue(alert_result['alerts_processed'])
        self.assertGreater(alert_result['total_alerts'], 0)
        
        # Verify high-priority alerts for compliance issues
        high_priority_alerts = [
            alert for alert in alert_result['alerts'] 
            if alert.get('priority') == 'HIGH'
        ]
        self.assertGreater(len(high_priority_alerts), 0)
    
    def test_bulk_sanctions_screening_performance(self):
        """Test performance of bulk sanctions screening"""
        # Create multiple customers for bulk screening
        customers = []
        for i in range(10):
            customer = Customer.objects.create(
                customer_type='INDIVIDUAL',
                first_name=f'Bulk{i}',
                last_name='Test',
                date_of_birth=date(1980 + i, 1, 1),
                nationality='US',
                country='US',
                email=f'bulk{i}@example.com',
                phone=f'+123456789{i}',
                address=f'123 Bulk{i} St',
                city='New York',
                postal_code='10001',
                industry='TECHNOLOGY',
                expected_monthly_volume=Decimal('50000.00'),
                source_of_funds='SALARY'
            )
            customers.append(customer)
        
        # Perform bulk screening
        import time
        start_time = time.time()
        
        screening_results = []
        for customer in customers:
            result = self.sanctions_service.screen_customer(customer)
            screening_results.append(result)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify all screenings completed
        self.assertEqual(len(screening_results), 10)
        
        # Verify reasonable performance (should complete in under 10 seconds)
        self.assertLess(processing_time, 10.0)
        
        # Verify all results are valid
        for result in screening_results:
            self.assertIsInstance(result, SanctionsScreening)
            self.assertIn(result.screening_result, ['CLEAR', 'HIT', 'POTENTIAL_MATCH'])

