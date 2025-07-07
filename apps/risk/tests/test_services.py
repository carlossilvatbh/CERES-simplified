"""
CERES Simplified - Fase 5: Testes Unitários para Serviços de Risk Assessment
Testes abrangentes para validação de cálculos de risco e lógica de negócio
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from unittest.mock import patch, MagicMock

from apps.customers.models import Customer, BeneficialOwner
from apps.risk.models import RiskAssessment, RiskFactor, RiskMatrix
from apps.risk.services import RiskCalculationService


class RiskCalculationServiceTest(TestCase):
    """Testes unitários para RiskCalculationService"""
    
    def setUp(self):
        """Configuração inicial para os testes"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.customer = Customer.objects.create(
            customer_type='INDIVIDUAL',
            first_name='João',
            last_name='Silva',
            email='joao.silva@email.com',
            phone='+5511999999999',
            document_type='CPF',
            document_number='12345678901',
            country='Brasil',
            risk_level='MEDIUM'
        )
        
        # Criar fatores de risco para teste
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
                name='Volume de Transações',
                description='Volume esperado de transações',
                weight=Decimal('0.3'),
                is_active=True
            )
        ]
        
        self.service = RiskCalculationService()
    
    def test_calculate_country_risk_low(self):
        """Teste de cálculo de risco por país - baixo risco"""
        # Países de baixo risco
        low_risk_countries = ['Brasil', 'Estados Unidos', 'Alemanha', 'Reino Unido']
        
        for country in low_risk_countries:
            self.customer.country = country
            risk_score = self.service._calculate_country_risk(self.customer)
            self.assertLessEqual(risk_score, 30, f"País {country} deveria ter risco baixo")
    
    def test_calculate_country_risk_medium(self):
        """Teste de cálculo de risco por país - médio risco"""
        # Países de médio risco
        medium_risk_countries = ['Argentina', 'México', 'Turquia', 'Índia']
        
        for country in medium_risk_countries:
            self.customer.country = country
            risk_score = self.service._calculate_country_risk(self.customer)
            self.assertGreater(risk_score, 30)
            self.assertLessEqual(risk_score, 70, f"País {country} deveria ter risco médio")
    
    def test_calculate_country_risk_high(self):
        """Teste de cálculo de risco por país - alto risco"""
        # Países de alto risco
        high_risk_countries = ['Afeganistão', 'Coreia do Norte', 'Irã', 'Síria']
        
        for country in high_risk_countries:
            self.customer.country = country
            risk_score = self.service._calculate_country_risk(self.customer)
            self.assertGreater(risk_score, 70, f"País {country} deveria ter risco alto")
    
    def test_calculate_pep_risk(self):
        """Teste de cálculo de risco PEP"""
        # Cliente não PEP
        self.customer.is_pep = False
        risk_score = self.service._calculate_pep_risk(self.customer)
        self.assertEqual(risk_score, 0)
        
        # Cliente PEP
        self.customer.is_pep = True
        risk_score = self.service._calculate_pep_risk(self.customer)
        self.assertEqual(risk_score, 80)
    
    def test_calculate_business_risk_individual(self):
        """Teste de cálculo de risco de negócio - pessoa física"""
        self.customer.customer_type = 'INDIVIDUAL'
        risk_score = self.service._calculate_business_risk(self.customer)
        self.assertEqual(risk_score, 20)  # Pessoa física = baixo risco
    
    def test_calculate_business_risk_corporate(self):
        """Teste de cálculo de risco de negócio - pessoa jurídica"""
        self.customer.customer_type = 'CORPORATE'
        
        # Indústrias de baixo risco
        low_risk_industries = ['Tecnologia', 'Educação', 'Saúde']
        for industry in low_risk_industries:
            self.customer.industry = industry
            risk_score = self.service._calculate_business_risk(self.customer)
            self.assertLessEqual(risk_score, 40)
        
        # Indústrias de alto risco
        high_risk_industries = ['Jogos', 'Criptomoedas', 'Câmbio']
        for industry in high_risk_industries:
            self.customer.industry = industry
            risk_score = self.service._calculate_business_risk(self.customer)
            self.assertGreaterEqual(risk_score, 70)
    
    def test_calculate_sanctions_risk(self):
        """Teste de cálculo de risco de sanções"""
        # Cliente não verificado
        self.customer.is_sanctions_checked = False
        risk_score = self.service._calculate_sanctions_risk(self.customer)
        self.assertEqual(risk_score, 50)  # Risco médio por não ter verificado
        
        # Cliente verificado sem matches
        self.customer.is_sanctions_checked = True
        risk_score = self.service._calculate_sanctions_risk(self.customer)
        self.assertEqual(risk_score, 0)  # Sem risco
    
    def test_calculate_overall_risk_score(self):
        """Teste de cálculo de score geral de risco"""
        # Configurar cliente de baixo risco
        self.customer.country = 'Brasil'
        self.customer.is_pep = False
        self.customer.customer_type = 'INDIVIDUAL'
        self.customer.is_sanctions_checked = True
        
        risk_score = self.service.calculate_risk_score(self.customer)
        
        # Verificar se o score está dentro do range esperado
        self.assertGreaterEqual(risk_score, 0)
        self.assertLessEqual(risk_score, 100)
        self.assertIsInstance(risk_score, int)
    
    def test_calculate_high_risk_customer(self):
        """Teste de cliente de alto risco"""
        # Configurar cliente de alto risco
        self.customer.country = 'Afeganistão'
        self.customer.is_pep = True
        self.customer.customer_type = 'CORPORATE'
        self.customer.industry = 'Criptomoedas'
        self.customer.is_sanctions_checked = False
        
        risk_score = self.service.calculate_risk_score(self.customer)
        
        # Cliente de alto risco deve ter score elevado
        self.assertGreaterEqual(risk_score, 70)
    
    def test_determine_risk_level_from_score(self):
        """Teste de determinação do nível de risco baseado no score"""
        test_cases = [
            (10, 'LOW'),
            (25, 'LOW'),
            (35, 'MEDIUM'),
            (50, 'MEDIUM'),
            (75, 'HIGH'),
            (90, 'CRITICAL'),
            (95, 'CRITICAL')
        ]
        
        for score, expected_level in test_cases:
            level = self.service._determine_risk_level(score)
            self.assertEqual(level, expected_level, 
                           f"Score {score} deveria resultar em nível {expected_level}")
    
    def test_create_risk_assessment(self):
        """Teste de criação de avaliação de risco"""
        assessment = self.service.create_assessment(self.customer, self.user)
        
        # Verificar se a avaliação foi criada
        self.assertIsNotNone(assessment)
        self.assertEqual(assessment.customer, self.customer)
        self.assertEqual(assessment.assessed_by, self.user)
        self.assertIsNotNone(assessment.risk_score)
        self.assertIsNotNone(assessment.risk_level)
        self.assertIsNotNone(assessment.assessment_date)
        
        # Verificar se o customer foi atualizado
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.risk_level, assessment.risk_level)
        self.assertEqual(self.customer.risk_score, assessment.risk_score)
    
    def test_risk_assessment_with_beneficial_owners(self):
        """Teste de avaliação de risco considerando beneficiários finais"""
        # Criar beneficiário final PEP
        BeneficialOwner.objects.create(
            customer=self.customer,
            full_name='Maria Santos PEP',
            document_number='98765432100',
            document_type='CPF',
            ownership_percentage=Decimal('60.00'),
            is_pep=True,
            country='Brasil'
        )
        
        risk_score = self.service.calculate_risk_score(self.customer)
        
        # Score deve ser maior devido ao beneficiário PEP
        self.assertGreater(risk_score, 30)
    
    def test_risk_factors_weighting(self):
        """Teste de ponderação dos fatores de risco"""
        # Simular cálculo com fatores específicos
        factors_scores = {
            'country': 20,
            'pep': 80,
            'business': 30,
            'sanctions': 0,
            'beneficial_owners': 40
        }
        
        weighted_score = self.service._calculate_weighted_score(factors_scores)
        
        # Verificar se o score ponderado está correto
        self.assertGreaterEqual(weighted_score, 0)
        self.assertLessEqual(weighted_score, 100)
    
    def test_risk_assessment_history(self):
        """Teste de histórico de avaliações de risco"""
        # Criar múltiplas avaliações
        assessment1 = self.service.create_assessment(self.customer, self.user)
        
        # Alterar dados do cliente
        self.customer.is_pep = True
        self.customer.save()
        
        assessment2 = self.service.create_assessment(self.customer, self.user)
        
        # Verificar histórico
        assessments = RiskAssessment.objects.filter(customer=self.customer).order_by('-assessment_date')
        self.assertEqual(assessments.count(), 2)
        self.assertGreater(assessment2.risk_score, assessment1.risk_score)
    
    def test_risk_matrix_application(self):
        """Teste de aplicação da matriz de risco"""
        # Criar matriz de risco
        matrix = RiskMatrix.objects.create(
            min_score=0,
            max_score=30,
            risk_level='LOW',
            description='Baixo risco',
            required_actions='Monitoramento padrão'
        )
        
        # Testar aplicação
        risk_level = self.service._apply_risk_matrix(25)
        self.assertEqual(risk_level, 'LOW')
    
    @patch('apps.risk.services.RiskCalculationService._calculate_country_risk')
    def test_service_with_mocked_country_risk(self, mock_country_risk):
        """Teste com mock do cálculo de risco por país"""
        mock_country_risk.return_value = 50
        
        risk_score = self.service.calculate_risk_score(self.customer)
        
        # Verificar se o mock foi chamado
        mock_country_risk.assert_called_once_with(self.customer)
        self.assertIsInstance(risk_score, int)
    
    def test_error_handling_invalid_customer(self):
        """Teste de tratamento de erro com cliente inválido"""
        with self.assertRaises(ValueError):
            self.service.calculate_risk_score(None)
    
    def test_risk_calculation_performance(self):
        """Teste de performance do cálculo de risco"""
        import time
        
        start_time = time.time()
        
        # Executar múltiplos cálculos
        for _ in range(10):
            self.service.calculate_risk_score(self.customer)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Verificar se execução é rápida (menos de 1 segundo para 10 cálculos)
        self.assertLess(execution_time, 1.0)
    
    def test_risk_factors_configuration(self):
        """Teste de configuração de fatores de risco"""
        # Verificar se fatores foram criados
        self.assertEqual(RiskFactor.objects.filter(is_active=True).count(), 3)
        
        # Verificar soma dos pesos
        total_weight = sum(
            factor.weight for factor in RiskFactor.objects.filter(is_active=True)
        )
        self.assertEqual(total_weight, Decimal('1.0'))
    
    def test_risk_assessment_validation(self):
        """Teste de validação de avaliação de risco"""
        assessment = RiskAssessment.objects.create(
            customer=self.customer,
            risk_score=85,
            risk_level='HIGH',
            assessed_by=self.user,
            assessment_date=timezone.now()
        )
        
        # Verificar validações
        self.assertGreaterEqual(assessment.risk_score, 0)
        self.assertLessEqual(assessment.risk_score, 100)
        self.assertIn(assessment.risk_level, ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'])


class RiskServiceIntegrationTest(TestCase):
    """Testes de integração para serviços de risco"""
    
    def setUp(self):
        """Configuração inicial"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.service = RiskCalculationService()
    
    def test_end_to_end_risk_assessment(self):
        """Teste end-to-end de avaliação de risco"""
        # Criar cliente
        customer = Customer.objects.create(
            customer_type='CORPORATE',
            company_name='Empresa Teste LTDA',
            email='empresa@teste.com',
            phone='+5511999999999',
            document_type='CNPJ',
            document_number='12345678000195',
            country='Brasil',
            industry='Tecnologia'
        )
        
        # Criar beneficiário final
        BeneficialOwner.objects.create(
            customer=customer,
            full_name='João Silva',
            document_number='12345678901',
            document_type='CPF',
            ownership_percentage=Decimal('100.00'),
            country='Brasil'
        )
        
        # Executar avaliação completa
        assessment = self.service.create_assessment(customer, self.user)
        
        # Verificar resultado
        self.assertIsNotNone(assessment)
        self.assertEqual(assessment.customer, customer)
        self.assertIn(assessment.risk_level, ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'])
        
        # Verificar se customer foi atualizado
        customer.refresh_from_db()
        self.assertEqual(customer.risk_level, assessment.risk_level)
        self.assertEqual(customer.risk_score, assessment.risk_score)

