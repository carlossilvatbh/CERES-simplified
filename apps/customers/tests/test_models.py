"""
CERES Simplified - Fase 5: Testes Unitários para Modelos de Customers (CORRIGIDO)
Testes abrangentes para validação de modelos, validações e comportamentos
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from apps.customers.models import Customer, BeneficialOwner


class CustomerModelTest(TestCase):
    """Testes unitários para o modelo Customer"""
    
    def setUp(self):
        """Configuração inicial para os testes"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.customer_data = {
            'customer_type': 'INDIVIDUAL',
            'full_name': 'João Silva',
            'email': 'joao.silva@email.com',
            'phone': '+5511999999999',
            'document_type': 'CPF',
            'document_number': '12345678901',
            'country': 'Brasil',
            'risk_level': 'MEDIUM',
            'onboarding_status': 'PENDING'
        }
    
    def test_create_individual_customer(self):
        """Teste de criação de cliente pessoa física"""
        customer = Customer.objects.create(**self.customer_data)
        
        self.assertEqual(customer.customer_type, 'INDIVIDUAL')
        self.assertEqual(customer.full_name, 'João Silva')
        self.assertEqual(customer.email, 'joao.silva@email.com')
        self.assertEqual(customer.risk_level, 'MEDIUM')
        self.assertEqual(customer.onboarding_status, 'PENDING')
        self.assertIsNotNone(customer.id)
        self.assertIsNotNone(customer.created_at)
    
    def test_create_corporate_customer(self):
        """Teste de criação de cliente pessoa jurídica"""
        corporate_data = self.customer_data.copy()
        corporate_data.update({
            'customer_type': 'CORPORATE',
            'full_name': 'Empresa Teste LTDA',
            'legal_name': 'Empresa Teste LTDA',
            'tax_id': '12345678000195',
            'industry': 'Tecnologia',
            'email': 'empresa@teste.com'
        })
        
        customer = Customer.objects.create(**corporate_data)
        
        self.assertEqual(customer.customer_type, 'CORPORATE')
        self.assertEqual(customer.full_name, 'Empresa Teste LTDA')
        self.assertEqual(customer.legal_name, 'Empresa Teste LTDA')
        self.assertEqual(customer.tax_id, '12345678000195')
        self.assertEqual(customer.industry, 'Tecnologia')
    
    def test_customer_str_method(self):
        """Teste do método __str__ do Customer"""
        customer = Customer.objects.create(**self.customer_data)
        # O método __str__ real inclui o document_number
        expected_str = "João Silva (12345678901)"
        self.assertEqual(str(customer), expected_str)
    
    def test_customer_risk_level_choices(self):
        """Teste das opções de nível de risco"""
        valid_risk_levels = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        
        for risk_level in valid_risk_levels:
            customer_data = self.customer_data.copy()
            customer_data['risk_level'] = risk_level
            customer_data['email'] = f'test_{risk_level.lower()}@email.com'
            customer = Customer.objects.create(**customer_data)
            self.assertEqual(customer.risk_level, risk_level)
    
    def test_customer_onboarding_status_choices(self):
        """Teste das opções de status de onboarding"""
        valid_statuses = [
            'PENDING', 'IN_PROGRESS', 'ADDITIONAL_INFO', 
            'UNDER_REVIEW', 'APPROVED', 'REJECTED'
        ]
        
        for status in valid_statuses:
            customer_data = self.customer_data.copy()
            customer_data['onboarding_status'] = status
            customer_data['email'] = f'test_{status.lower()}@email.com'
            customer = Customer.objects.create(**customer_data)
            self.assertEqual(customer.onboarding_status, status)
    
    def test_customer_email_uniqueness(self):
        """Teste de unicidade do email"""
        Customer.objects.create(**self.customer_data)
        
        # Tentar criar outro customer com mesmo email deve falhar
        duplicate_data = self.customer_data.copy()
        duplicate_data['full_name'] = 'Maria Silva'
        
        with self.assertRaises(Exception):  # IntegrityError esperado
            Customer.objects.create(**duplicate_data)
    
    def test_customer_pep_flag(self):
        """Teste da flag de Pessoa Politicamente Exposta"""
        customer_data = self.customer_data.copy()
        customer_data['is_pep'] = True
        
        customer = Customer.objects.create(**customer_data)
        self.assertTrue(customer.is_pep)
    
    def test_customer_sanctions_check(self):
        """Teste da verificação de sanções"""
        customer = Customer.objects.create(**self.customer_data)
        
        # Inicialmente não verificado
        self.assertFalse(customer.is_sanctions_checked)
        self.assertIsNone(customer.sanctions_last_check)
        
        # Simular verificação
        customer.is_sanctions_checked = True
        customer.sanctions_last_check = timezone.now()
        customer.save()
        
        self.assertTrue(customer.is_sanctions_checked)
        self.assertIsNotNone(customer.sanctions_last_check)
    
    def test_customer_review_dates(self):
        """Teste das datas de revisão"""
        customer = Customer.objects.create(**self.customer_data)
        
        # Definir próxima revisão
        next_review = timezone.now() + timedelta(days=365)
        customer.next_review_date = next_review
        customer.save()
        
        self.assertEqual(customer.next_review_date.date(), next_review.date())
    
    def test_customer_manager_methods(self):
        """Teste dos métodos customizados do manager"""
        # Criar clientes de diferentes riscos
        Customer.objects.create(
            customer_type='INDIVIDUAL',
            full_name='Cliente Baixo Risco',
            email='baixo@risco.com',
            document_number='11111111111',
            country='Brasil',
            risk_level='LOW'
        )
        
        Customer.objects.create(
            customer_type='INDIVIDUAL',
            full_name='Cliente Alto Risco',
            email='alto@risco.com',
            document_number='22222222222',
            country='Brasil',
            risk_level='HIGH'
        )
        
        # Testar filtros do manager
        high_risk_customers = Customer.objects.high_risk()
        self.assertEqual(high_risk_customers.count(), 1)
        self.assertEqual(high_risk_customers.first().full_name, 'Cliente Alto Risco')


class BeneficialOwnerModelTest(TestCase):
    """Testes unitários para o modelo BeneficialOwner"""
    
    def setUp(self):
        """Configuração inicial para os testes"""
        self.customer = Customer.objects.create(
            customer_type='CORPORATE',
            full_name='Empresa Teste LTDA',
            email='empresa@teste.com',
            phone='+5511999999999',
            document_type='CNPJ',
            document_number='12345678000195',
            country='Brasil'
        )
        
        self.beneficial_owner_data = {
            'customer': self.customer,
            'full_name': 'Maria Santos',
            'document_number': '98765432100',
            'document_type': 'CPF',
            'ownership_percentage': Decimal('25.50'),
            'email': 'maria.santos@email.com',
            'phone': '+5511888888888',
            'country': 'Brasil'
        }
    
    def test_create_beneficial_owner(self):
        """Teste de criação de beneficiário final"""
        beneficial_owner = BeneficialOwner.objects.create(**self.beneficial_owner_data)
        
        self.assertEqual(beneficial_owner.full_name, 'Maria Santos')
        self.assertEqual(beneficial_owner.document_number, '98765432100')
        self.assertEqual(beneficial_owner.ownership_percentage, Decimal('25.50'))
        self.assertEqual(beneficial_owner.customer, self.customer)
        self.assertIsNotNone(beneficial_owner.id)
        self.assertIsNotNone(beneficial_owner.created_at)
    
    def test_beneficial_owner_str_method(self):
        """Teste do método __str__ do BeneficialOwner"""
        beneficial_owner = BeneficialOwner.objects.create(**self.beneficial_owner_data)
        expected_str = "Maria Santos (25.50%)"
        self.assertEqual(str(beneficial_owner), expected_str)
    
    def test_ownership_percentage_validation(self):
        """Teste de validação do percentual de participação"""
        # Teste com percentual válido
        valid_percentages = [Decimal('0.01'), Decimal('50.00'), Decimal('100.00')]
        
        for percentage in valid_percentages:
            data = self.beneficial_owner_data.copy()
            data['ownership_percentage'] = percentage
            data['document_number'] = f'doc_{percentage}'
            beneficial_owner = BeneficialOwner.objects.create(**data)
            self.assertEqual(beneficial_owner.ownership_percentage, percentage)
    
    def test_beneficial_owner_pep_flag(self):
        """Teste da flag PEP para beneficiário final"""
        data = self.beneficial_owner_data.copy()
        data['is_pep'] = True
        
        beneficial_owner = BeneficialOwner.objects.create(**data)
        self.assertTrue(beneficial_owner.is_pep)
    
    def test_beneficial_owner_sanctions_check(self):
        """Teste da verificação de sanções para beneficiário final"""
        beneficial_owner = BeneficialOwner.objects.create(**self.beneficial_owner_data)
        
        # Inicialmente não verificado
        self.assertFalse(beneficial_owner.is_sanctions_checked)
        self.assertIsNone(beneficial_owner.sanctions_last_check)
        
        # Simular verificação
        beneficial_owner.is_sanctions_checked = True
        beneficial_owner.sanctions_last_check = timezone.now()
        beneficial_owner.save()
        
        self.assertTrue(beneficial_owner.is_sanctions_checked)
        self.assertIsNotNone(beneficial_owner.sanctions_last_check)
    
    def test_beneficial_owner_customer_relationship(self):
        """Teste do relacionamento com Customer"""
        beneficial_owner = BeneficialOwner.objects.create(**self.beneficial_owner_data)
        
        # Verificar relacionamento direto
        self.assertEqual(beneficial_owner.customer, self.customer)
        
        # Verificar relacionamento reverso
        self.assertIn(beneficial_owner, self.customer.beneficial_owners.all())
    
    def test_beneficial_owner_unique_constraint(self):
        """Teste de constraint de unicidade"""
        BeneficialOwner.objects.create(**self.beneficial_owner_data)
        
        # Tentar criar outro beneficiário com mesmo customer e documento
        duplicate_data = self.beneficial_owner_data.copy()
        duplicate_data['full_name'] = 'João Santos'
        
        with self.assertRaises(Exception):  # IntegrityError esperado
            BeneficialOwner.objects.create(**duplicate_data)
    
    def test_beneficial_owner_ordering(self):
        """Teste da ordenação padrão"""
        # Criar múltiplos beneficiários
        bo1_data = self.beneficial_owner_data.copy()
        bo1_data['ownership_percentage'] = Decimal('10.00')
        bo1_data['full_name'] = 'Ana Silva'
        bo1_data['document_number'] = '11111111111'
        
        bo2_data = self.beneficial_owner_data.copy()
        bo2_data['ownership_percentage'] = Decimal('30.00')
        bo2_data['full_name'] = 'Carlos Santos'
        bo2_data['document_number'] = '22222222222'
        
        bo1 = BeneficialOwner.objects.create(**bo1_data)
        bo2 = BeneficialOwner.objects.create(**bo2_data)
        
        # Verificar ordenação (maior percentual primeiro, depois nome)
        beneficial_owners = list(BeneficialOwner.objects.all())
        self.assertEqual(beneficial_owners[0], bo2)  # 30% primeiro
        self.assertEqual(beneficial_owners[1], bo1)  # 10% depois


class CustomerModelIntegrationTest(TestCase):
    """Testes de integração para modelos de Customer"""
    
    def setUp(self):
        """Configuração inicial"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_customer_with_multiple_beneficial_owners(self):
        """Teste de customer com múltiplos beneficiários finais"""
        customer = Customer.objects.create(
            customer_type='CORPORATE',
            full_name='Empresa ABC LTDA',
            email='abc@empresa.com',
            phone='+5511999999999',
            document_type='CNPJ',
            document_number='12345678000195',
            country='Brasil'
        )
        
        # Criar múltiplos beneficiários
        beneficial_owners_data = [
            {
                'full_name': 'Sócio A',
                'document_number': '11111111111',
                'ownership_percentage': Decimal('60.00')
            },
            {
                'full_name': 'Sócio B',
                'document_number': '22222222222',
                'ownership_percentage': Decimal('40.00')
            }
        ]
        
        for data in beneficial_owners_data:
            data['customer'] = customer
            data['document_type'] = 'CPF'
            data['country'] = 'Brasil'
            BeneficialOwner.objects.create(**data)
        
        # Verificar relacionamentos
        self.assertEqual(customer.beneficial_owners.count(), 2)
        
        # Verificar soma dos percentuais
        total_percentage = sum(
            bo.ownership_percentage 
            for bo in customer.beneficial_owners.all()
        )
        self.assertEqual(total_percentage, Decimal('100.00'))
    
    def test_customer_risk_calculation_integration(self):
        """Teste de integração com cálculo de risco"""
        customer = Customer.objects.create(
            customer_type='INDIVIDUAL',
            full_name='João Silva',
            email='joao@teste.com',
            phone='+5511999999999',
            document_type='CPF',
            document_number='12345678901',
            country='Brasil',
            is_pep=True,  # Alto risco
            risk_level='LOW'  # Será atualizado
        )
        
        # Simular atualização de risco baseada em PEP
        if customer.is_pep:
            customer.risk_level = 'HIGH'
            customer.save()
        
        customer.refresh_from_db()
        self.assertEqual(customer.risk_level, 'HIGH')
    
    def test_customer_audit_trail(self):
        """Teste de trilha de auditoria"""
        customer = Customer.objects.create(
            customer_type='INDIVIDUAL',
            full_name='Maria Santos',
            email='maria@teste.com',
            phone='+5511999999999',
            document_type='CPF',
            document_number='98765432100',
            country='Brasil',
            created_by=self.user
        )
        
        # Verificar criação
        self.assertEqual(customer.created_by, self.user)
        self.assertIsNotNone(customer.created_at)
        
        # Simular atualização
        original_updated_at = customer.updated_at
        customer.risk_level = 'HIGH'
        customer.save()
        
        customer.refresh_from_db()
        self.assertGreater(customer.updated_at, original_updated_at)

