"""
CERES Simplified - Initial Data Setup
Management command for setting up initial system data
"""

import logging
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.risk.models import RiskFactor
from apps.compliance.models import ComplianceRule
from apps.sanctions.models import SanctionsList
from apps.documents.models import DocumentType

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Setup initial data for CERES system'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up initial CERES data...'))
        
        try:
            # Setup basic risk factors
            risk_factor, created = RiskFactor.objects.get_or_create(
                name='Geographic Risk',
                defaults={
                    'description': 'Risk based on customer geographic location',
                    'factor_type': 'GEOGRAPHIC',
                    'risk_weight': 20,
                    'is_active': True
                }
            )
            if created:
                self.stdout.write('Created Geographic Risk factor')
            
            # Setup basic compliance rule
            compliance_rule, created = ComplianceRule.objects.get_or_create(
                name='KYC Documentation Check',
                defaults={
                    'description': 'Verify all required KYC documents are provided',
                    'rule_type': 'KYC',
                    'severity': 'CRITICAL',
                    'auto_check': True,
                    'is_active': True
                }
            )
            if created:
                self.stdout.write('Created KYC compliance rule')
            
            # Setup basic document type
            doc_type, created = DocumentType.objects.get_or_create(
                name='Passport',
                defaults={
                    'description': 'Government issued passport',
                    'category': 'IDENTITY',
                    'is_required': True,
                    'is_active': True
                }
            )
            if created:
                self.stdout.write('Created Passport document type')
            
            # Setup basic sanctions list
            sanctions_list, created = SanctionsList.objects.get_or_create(
                name='OFAC SDN List (Sample)',
                defaults={
                    'description': 'Sample OFAC Specially Designated Nationals List',
                    'source_url': 'https://www.treasury.gov/ofac/downloads/sdnlist.txt',
                    'is_active': True,
                    'last_updated': timezone.now(),
                    'list_type': 'OFAC'
                }
            )
            if created:
                self.stdout.write('Created sample sanctions list')
            
            self.stdout.write(self.style.SUCCESS('Initial data setup completed successfully'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error in initial data setup: {str(e)}'))
            logger.error(f'Error in initial data setup: {str(e)}')
            raise

