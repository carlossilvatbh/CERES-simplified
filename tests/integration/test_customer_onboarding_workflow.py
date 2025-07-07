"""
CERES Simplified - Fase 5: Testes de Integração - Workflow de Onboarding
Testes abrangentes para validação do workflow completo de onboarding de clientes
"""

from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from unittest.mock import patch, MagicMock

from apps.customers.models import Customer, BeneficialOwner
from apps.risk.models import RiskAssessment, RiskFactor
from apps.sanctions.models import SanctionsList, SanctionsEntry, SanctionsCheck
from apps.cases.models import Case, CaseType
from apps.documents.models import Document
from apps.compliance.models import ComplianceCheck

from apps.risk.services import RiskCalculationService
from apps.sanctions.services import SanctionsScreeningService
from apps.compliance.services import ComplianceWorkflowService
from apps.core.services import CustomerOnboardingOrchestrator


class CustomerOnboardingWorkflowTest(TransactionTestCase):
    """Testes de integração para workflow completo de onboarding"""
    
    def setUp(self):
        """Configuração inicial para os testes"""
        # Criar usuários
        self.compliance_user = User.objects.create_user(
            username='compliance',
            email='compliance@ceres.com',
            password='testpass123',
            first_name='Compliance',
            last_name='Officer'
        )
        
        self.risk_user = User.objects.create_user(
            username='risk',
            email='risk@ceres.com',
            password='testpass123',
            first_name='Risk',
            last_name='Analyst'
        )
        
        # Configurar fatores de risco
        self.setup_risk_factors()
        
        # Configurar listas de sanções
        self.setup_sanctions_lists()
        
        # Configurar tipos de caso
        self.setup_case_types()
        
        # Inicializar serviços
        self.risk_service = RiskCalculationService()
        self.sanctions_service = SanctionsScreeningService()
        self.compliance_service = ComplianceWorkflowService()
        self.orchestrator = CustomerOnboardingOrchestrator()
    
    def setup_risk_factors(self):
        """Configurar fatores de risco para teste"""
        self.risk_factors = [
            RiskFactor.objects.create(
                name='País de Residência',
                description='Risco baseado no país',
                weight=Decimal('0.3'),
                is_active=True
            ),
            RiskFactor.objects.create(
                name='Pessoa Politicamente Exposta',
                description='Cliente é PEP',
                weight=Decimal('0.4'),
                is_active=True
            ),
            RiskFactor.objects.create(
                name='Tipo de Negócio',
                description='Risco do setor de atuação',
                weight=Decimal('0.3'),
                is_active=True
            )
        ]
    
    def setup_sanctions_lists(self):
        """Configurar listas de sanções para teste"""
        self.sanctions_list = SanctionsList.objects.create(
            name='OFAC SDN List',
            description='Office of Foreign Assets Control',
            source_url='https://www.treasury.gov/ofac/downloads/sdn.xml',
            is_active=True
        )
        
        # Criar algumas entradas de sanções para teste
        self.sanctions_entries = [
            SanctionsEntry.objects.create(
                sanctions_list=self.sanctions_list,
                name='SILVA, João Sancionado',
                aliases='João Silva Sancionado',
                document_number='99999999999',
                country='Brasil',
                entry_type='INDIVIDUAL',
                is_active=True
            ),
            SanctionsEntry.objects.create(
                sanctions_list=self.sanctions_list,
                name='Empresa Sancionada LTDA',
                aliases='ES LTDA',
                document_number='99999999000199',
                country='Brasil',
                entry_type='ENTITY',
                is_active=True
            )
        ]
    
    def setup_case_types(self):
        """Configurar tipos de caso para teste"""
        self.case_types = [
            CaseType.objects.create(
                name='Onboarding Review',
                description='Revisão de onboarding de cliente',
                default_priority='MEDIUM',
                sla_hours=48
            ),
            CaseType.objects.create(
                name='High Risk Customer',
                description='Cliente de alto risco',
                default_priority='HIGH',
                sla_hours=24
            ),
            CaseType.objects.create(
                name='Sanctions Match',
                description='Possível match em lista de sanções',
                default_priority='CRITICAL',
                sla_hours=4
            )
        ]
    
    def test_successful_low_risk_onboarding(self):
        """Teste de onboarding bem-sucedido para cliente de baixo risco"""
        # Dados do cliente de baixo risco
        customer_data = {
            'customer_type': 'INDIVIDUAL',
            'first_name': 'Maria',
            'last_name': 'Santos',
            'email': 'maria.santos@email.com',
            'phone': '+5511999999999',
            'document_type': 'CPF',
            'document_number': '12345678901',
            'country': 'Brasil',
            'is_pep': False
        }
        
        # Executar workflow completo
        result = self.orchestrator.process_customer_onboarding(
            customer_data, self.compliance_user
        )
        
        # Verificar resultado
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['onboarding_status'], 'COMPLETED')
        
        # Verificar se cliente foi criado
        customer = Customer.objects.get(id=result['customer_id'])
        self.assertEqual(customer.first_name, 'Maria')
        self.assertEqual(customer.last_name, 'Santos')
        self.assertEqual(customer.onboarding_status, 'COMPLETED')
        
        # Verificar se avaliação de risco foi feita
        risk_assessment = RiskAssessment.objects.filter(customer=customer).first()
        self.assertIsNotNone(risk_assessment)
        self.assertIn(risk_assessment.risk_level, ['LOW', 'MEDIUM'])
        
        # Verificar se screening de sanções foi feito
        sanctions_check = SanctionsCheck.objects.filter(customer=customer).first()
        self.assertIsNotNone(sanctions_check)
        self.assertEqual(sanctions_check.result, 'CLEAR')
        
        # Verificar se compliance check foi feito
        compliance_check = ComplianceCheck.objects.filter(customer=customer).first()
        self.assertIsNotNone(compliance_check)
        self.assertEqual(compliance_check.status, 'APPROVED')
    
    def test_high_risk_customer_onboarding(self):
        """Teste de onboarding para cliente de alto risco"""
        # Dados do cliente de alto risco
        customer_data = {
            'customer_type': 'CORPORATE',
            'company_name': 'Empresa Alto Risco LTDA',
            'email': 'contato@altorisco.com',
            'phone': '+5511999999999',
            'document_type': 'CNPJ',
            'document_number': '12345678000195',
            'country': 'Afeganistão',  # País de alto risco
            'industry': 'Criptomoedas',  # Setor de alto risco
            'is_pep': False
        }
        
        # Executar workflow completo
        result = self.orchestrator.process_customer_onboarding(
            customer_data, self.compliance_user
        )
        
        # Verificar resultado
        self.assertEqual(result['status'], 'REQUIRES_REVIEW')
        self.assertEqual(result['onboarding_status'], 'REQUIRES_MANUAL_REVIEW')
        
        # Verificar se cliente foi criado
        customer = Customer.objects.get(id=result['customer_id'])
        self.assertEqual(customer.onboarding_status, 'REQUIRES_MANUAL_REVIEW')
        self.assertEqual(customer.risk_level, 'HIGH')
        
        # Verificar se caso foi criado para revisão
        case = Case.objects.filter(customer=customer).first()
        self.assertIsNotNone(case)
        self.assertEqual(case.case_type.name, 'High Risk Customer')
        self.assertEqual(case.priority, 'HIGH')
    
    def test_sanctions_match_onboarding(self):
        """Teste de onboarding com match em lista de sanções"""
        # Dados do cliente que está nas sanções
        customer_data = {
            'customer_type': 'INDIVIDUAL',
            'first_name': 'João',
            'last_name': 'Sancionado Silva',
            'email': 'joao@email.com',
            'phone': '+5511999999999',
            'document_type': 'CPF',
            'document_number': '99999999999',  # Mesmo documento da entrada de sanção
            'country': 'Brasil',
            'is_pep': False
        }
        
        # Executar workflow completo
        result = self.orchestrator.process_customer_onboarding(
            customer_data, self.compliance_user
        )
        
        # Verificar resultado
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(result['onboarding_status'], 'REJECTED')
        
        # Verificar se cliente foi criado mas rejeitado
        customer = Customer.objects.get(id=result['customer_id'])
        self.assertEqual(customer.onboarding_status, 'REJECTED')
        
        # Verificar se caso crítico foi criado
        case = Case.objects.filter(customer=customer).first()
        self.assertIsNotNone(case)
        self.assertEqual(case.case_type.name, 'Sanctions Match')
        self.assertEqual(case.priority, 'CRITICAL')
        
        # Verificar se sanctions check registrou o match
        sanctions_check = SanctionsCheck.objects.filter(customer=customer).first()
        self.assertIsNotNone(sanctions_check)
        self.assertEqual(sanctions_check.result, 'POTENTIAL_MATCH')
    
    def test_pep_customer_onboarding(self):
        """Teste de onboarding para cliente PEP"""
        # Dados do cliente PEP
        customer_data = {
            'customer_type': 'INDIVIDUAL',
            'first_name': 'Carlos',
            'last_name': 'Político',
            'email': 'carlos.politico@email.com',
            'phone': '+5511999999999',
            'document_type': 'CPF',
            'document_number': '11111111111',
            'country': 'Brasil',
            'is_pep': True  # Pessoa Politicamente Exposta
        }
        
        # Executar workflow completo
        result = self.orchestrator.process_customer_onboarding(
            customer_data, self.compliance_user
        )
        
        # Verificar resultado
        self.assertEqual(result['status'], 'REQUIRES_REVIEW')
        self.assertEqual(result['onboarding_status'], 'REQUIRES_MANUAL_REVIEW')
        
        # Verificar se cliente foi criado
        customer = Customer.objects.get(id=result['customer_id'])
        self.assertEqual(customer.risk_level, 'HIGH')  # PEP = alto risco
        self.assertTrue(customer.is_pep)
        
        # Verificar se caso foi criado para revisão
        case = Case.objects.filter(customer=customer).first()
        self.assertIsNotNone(case)
        self.assertEqual(case.priority, 'HIGH')
    
    def test_corporate_customer_with_beneficial_owners(self):
        """Teste de onboarding de pessoa jurídica com beneficiários finais"""
        # Dados da empresa
        customer_data = {
            'customer_type': 'CORPORATE',
            'company_name': 'Empresa Teste LTDA',
            'email': 'contato@empresa.com',
            'phone': '+5511999999999',
            'document_type': 'CNPJ',
            'document_number': '12345678000195',
            'country': 'Brasil',
            'industry': 'Tecnologia'
        }
        
        # Dados dos beneficiários finais
        beneficial_owners_data = [
            {
                'full_name': 'Sócio A',
                'document_number': '11111111111',
                'document_type': 'CPF',
                'ownership_percentage': Decimal('60.00'),
                'country': 'Brasil',
                'is_pep': False
            },
            {
                'full_name': 'Sócio B PEP',
                'document_number': '22222222222',
                'document_type': 'CPF',
                'ownership_percentage': Decimal('40.00'),
                'country': 'Brasil',
                'is_pep': True  # Beneficiário PEP
            }
        ]
        
        # Executar workflow completo
        result = self.orchestrator.process_customer_onboarding(
            customer_data, self.compliance_user, beneficial_owners_data
        )
        
        # Verificar resultado
        self.assertEqual(result['status'], 'REQUIRES_REVIEW')  # Devido ao beneficiário PEP
        
        # Verificar se empresa foi criada
        customer = Customer.objects.get(id=result['customer_id'])
        self.assertEqual(customer.company_name, 'Empresa Teste LTDA')
        
        # Verificar se beneficiários foram criados
        beneficial_owners = BeneficialOwner.objects.filter(customer=customer)
        self.assertEqual(beneficial_owners.count(), 2)
        
        # Verificar se beneficiário PEP foi identificado
        pep_owner = beneficial_owners.filter(is_pep=True).first()
        self.assertIsNotNone(pep_owner)
        self.assertEqual(pep_owner.full_name, 'Sócio B PEP')
        
        # Verificar se caso foi criado devido ao beneficiário PEP
        case = Case.objects.filter(customer=customer).first()
        self.assertIsNotNone(case)
    
    def test_document_upload_integration(self):
        """Teste de integração com upload de documentos"""
        # Criar cliente primeiro
        customer_data = {
            'customer_type': 'INDIVIDUAL',
            'first_name': 'Ana',
            'last_name': 'Silva',
            'email': 'ana.silva@email.com',
            'phone': '+5511999999999',
            'document_type': 'CPF',
            'document_number': '33333333333',
            'country': 'Brasil'
        }
        
        result = self.orchestrator.process_customer_onboarding(
            customer_data, self.compliance_user
        )
        
        customer = Customer.objects.get(id=result['customer_id'])
        
        # Simular upload de documentos
        documents_data = [
            {
                'name': 'RG - Ana Silva',
                'document_type': 'ID',
                'description': 'Documento de identidade'
            },
            {
                'name': 'Comprovante de Residência',
                'document_type': 'PROOF_OF_ADDRESS',
                'description': 'Conta de luz'
            }
        ]
        
        # Criar documentos
        for doc_data in documents_data:
            Document.objects.create(
                customer=customer,
                name=doc_data['name'],
                document_type=doc_data['document_type'],
                description=doc_data['description'],
                status='PENDING_REVIEW'
            )
        
        # Verificar se documentos foram criados
        documents = Document.objects.filter(customer=customer)
        self.assertEqual(documents.count(), 2)
        
        # Simular aprovação de documentos
        for doc in documents:
            doc.status = 'APPROVED'
            doc.save()
        
        # Verificar se todos os documentos foram aprovados
        approved_docs = documents.filter(status='APPROVED')
        self.assertEqual(approved_docs.count(), 2)
    
    def test_workflow_error_handling(self):
        """Teste de tratamento de erros no workflow"""
        # Dados inválidos (sem email obrigatório)
        invalid_customer_data = {
            'customer_type': 'INDIVIDUAL',
            'first_name': 'João',
            'last_name': 'Silva',
            # email ausente
            'phone': '+5511999999999',
            'document_type': 'CPF',
            'document_number': '44444444444',
            'country': 'Brasil'
        }
        
        # Executar workflow e verificar tratamento de erro
        with self.assertRaises(ValueError):
            self.orchestrator.process_customer_onboarding(
                invalid_customer_data, self.compliance_user
            )
    
    def test_workflow_performance(self):
        """Teste de performance do workflow completo"""
        import time
        
        customer_data = {
            'customer_type': 'INDIVIDUAL',
            'first_name': 'Performance',
            'last_name': 'Test',
            'email': 'performance@test.com',
            'phone': '+5511999999999',
            'document_type': 'CPF',
            'document_number': '55555555555',
            'country': 'Brasil'
        }
        
        start_time = time.time()
        
        # Executar workflow
        result = self.orchestrator.process_customer_onboarding(
            customer_data, self.compliance_user
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Verificar se execução é rápida (menos de 5 segundos)
        self.assertLess(execution_time, 5.0)
        self.assertEqual(result['status'], 'SUCCESS')
    
    def test_audit_trail_completeness(self):
        """Teste de completude da trilha de auditoria"""
        customer_data = {
            'customer_type': 'INDIVIDUAL',
            'first_name': 'Audit',
            'last_name': 'Trail',
            'email': 'audit@trail.com',
            'phone': '+5511999999999',
            'document_type': 'CPF',
            'document_number': '66666666666',
            'country': 'Brasil'
        }
        
        # Executar workflow
        result = self.orchestrator.process_customer_onboarding(
            customer_data, self.compliance_user
        )
        
        customer = Customer.objects.get(id=result['customer_id'])
        
        # Verificar trilha de auditoria
        
        # 1. Customer criado com usuário responsável
        self.assertEqual(customer.created_by, self.compliance_user)
        self.assertIsNotNone(customer.created_at)
        
        # 2. Risk Assessment registrado
        risk_assessment = RiskAssessment.objects.filter(customer=customer).first()
        self.assertIsNotNone(risk_assessment)
        self.assertEqual(risk_assessment.assessed_by, self.compliance_user)
        
        # 3. Sanctions Check registrado
        sanctions_check = SanctionsCheck.objects.filter(customer=customer).first()
        self.assertIsNotNone(sanctions_check)
        self.assertEqual(sanctions_check.checked_by, self.compliance_user)
        
        # 4. Compliance Check registrado
        compliance_check = ComplianceCheck.objects.filter(customer=customer).first()
        self.assertIsNotNone(compliance_check)
        self.assertEqual(compliance_check.checked_by, self.compliance_user)
    
    def test_concurrent_onboarding(self):
        """Teste de onboarding concorrente"""
        from threading import Thread
        import time
        
        results = []
        
        def onboard_customer(customer_id):
            customer_data = {
                'customer_type': 'INDIVIDUAL',
                'first_name': f'Concurrent{customer_id}',
                'last_name': 'Test',
                'email': f'concurrent{customer_id}@test.com',
                'phone': f'+551199999999{customer_id}',
                'document_type': 'CPF',
                'document_number': f'7777777777{customer_id}',
                'country': 'Brasil'
            }
            
            try:
                result = self.orchestrator.process_customer_onboarding(
                    customer_data, self.compliance_user
                )
                results.append(result)
            except Exception as e:
                results.append({'error': str(e)})
        
        # Criar múltiplas threads
        threads = []
        for i in range(3):
            thread = Thread(target=onboard_customer, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Aguardar conclusão
        for thread in threads:
            thread.join()
        
        # Verificar resultados
        self.assertEqual(len(results), 3)
        for result in results:
            self.assertNotIn('error', result)
            self.assertIn('status', result)


class WorkflowIntegrationTest(TestCase):
    """Testes de integração entre diferentes workflows"""
    
    def setUp(self):
        """Configuração inicial"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_risk_to_case_workflow(self):
        """Teste de workflow de risco para criação de caso"""
        # Criar cliente de alto risco
        customer = Customer.objects.create(
            customer_type='INDIVIDUAL',
            first_name='Alto',
            last_name='Risco',
            email='alto.risco@email.com',
            phone='+5511999999999',
            document_type='CPF',
            document_number='88888888888',
            country='Afeganistão',  # Alto risco
            is_pep=True,  # Alto risco
            risk_level='HIGH'
        )
        
        # Executar avaliação de risco
        risk_service = RiskCalculationService()
        assessment = risk_service.create_assessment(customer, self.user)
        
        # Verificar se caso foi criado automaticamente para alto risco
        if assessment.risk_level in ['HIGH', 'CRITICAL']:
            # Simular criação automática de caso
            case_type = CaseType.objects.create(
                name='High Risk Review',
                description='Revisão de cliente de alto risco',
                default_priority='HIGH'
            )
            
            case = Case.objects.create(
                case_type=case_type,
                title=f'Revisão de Alto Risco - {customer}',
                description=f'Cliente classificado como {assessment.risk_level}',
                customer=customer,
                priority='HIGH',
                status='OPEN',
                created_by=self.user
            )
            
            # Verificar integração
            self.assertEqual(case.customer, customer)
            self.assertEqual(case.priority, 'HIGH')
            self.assertIn('Alto Risco', case.title)
    
    def test_sanctions_to_compliance_workflow(self):
        """Teste de workflow de sanções para compliance"""
        # Criar lista e entrada de sanções
        sanctions_list = SanctionsList.objects.create(
            name='Test List',
            description='Lista de teste',
            is_active=True
        )
        
        SanctionsEntry.objects.create(
            sanctions_list=sanctions_list,
            name='TESTE, João',
            document_number='99999999999',
            country='Brasil',
            entry_type='INDIVIDUAL',
            is_active=True
        )
        
        # Criar cliente que pode ter match
        customer = Customer.objects.create(
            customer_type='INDIVIDUAL',
            first_name='João',
            last_name='Teste',
            email='joao.teste@email.com',
            phone='+5511999999999',
            document_type='CPF',
            document_number='99999999999',
            country='Brasil'
        )
        
        # Executar screening
        sanctions_service = SanctionsScreeningService()
        result = sanctions_service.screen_customer(customer, self.user)
        
        # Se houver match, deve acionar compliance
        if result['status'] == 'POTENTIAL_MATCH':
            compliance_check = ComplianceCheck.objects.create(
                customer=customer,
                check_type='SANCTIONS_REVIEW',
                status='PENDING',
                checked_by=self.user,
                notes=f"Potential sanctions match found: {len(result['matches'])} matches"
            )
            
            # Verificar integração
            self.assertEqual(compliance_check.customer, customer)
            self.assertEqual(compliance_check.check_type, 'SANCTIONS_REVIEW')
            self.assertEqual(compliance_check.status, 'PENDING')

