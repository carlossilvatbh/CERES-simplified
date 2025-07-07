"""
CERES Simplified - Fase 5: Testes Unitários para Serviços de Sanctions
Testes abrangentes para validação de screening de sanções e matching
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from unittest.mock import patch, MagicMock
from decimal import Decimal

from apps.customers.models import Customer, BeneficialOwner
from apps.sanctions.models import SanctionsList, SanctionsEntry, SanctionsCheck
from apps.sanctions.services import SanctionsScreeningService


class SanctionsScreeningServiceTest(TestCase):
    """Testes unitários para SanctionsScreeningService"""
    
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
            country='Brasil'
        )
        
        # Criar lista de sanções para teste
        self.sanctions_list = SanctionsList.objects.create(
            name='OFAC SDN List',
            description='Office of Foreign Assets Control - Specially Designated Nationals',
            source_url='https://www.treasury.gov/ofac/downloads/sdn.xml',
            is_active=True
        )
        
        # Criar entradas de sanções para teste
        self.sanctions_entries = [
            SanctionsEntry.objects.create(
                sanctions_list=self.sanctions_list,
                name='SILVA, João',
                aliases='João Silva;J. Silva',
                document_number='12345678901',
                country='Brasil',
                entry_type='INDIVIDUAL',
                is_active=True
            ),
            SanctionsEntry.objects.create(
                sanctions_list=self.sanctions_list,
                name='SANTOS, Maria',
                aliases='Maria Santos;M. Santos',
                document_number='98765432100',
                country='Brasil',
                entry_type='INDIVIDUAL',
                is_active=True
            ),
            SanctionsEntry.objects.create(
                sanctions_list=self.sanctions_list,
                name='Empresa Sancionada LTDA',
                aliases='Empresa Sancionada;ES LTDA',
                document_number='12345678000195',
                country='Brasil',
                entry_type='ENTITY',
                is_active=True
            )
        ]
        
        self.service = SanctionsScreeningService()
    
    def test_exact_name_match(self):
        """Teste de match exato por nome"""
        matches = self.service._find_name_matches('João Silva')
        
        # Deve encontrar match exato
        self.assertGreater(len(matches), 0)
        
        # Verificar se o match tem score alto
        best_match = max(matches, key=lambda x: x['score'])
        self.assertGreaterEqual(best_match['score'], 90)
    
    def test_fuzzy_name_match(self):
        """Teste de match fuzzy por nome"""
        # Teste com nome similar mas não exato
        matches = self.service._find_name_matches('Joao Silva')  # Sem acento
        
        # Deve encontrar match com score menor
        self.assertGreater(len(matches), 0)
        best_match = max(matches, key=lambda x: x['score'])
        self.assertGreater(best_match['score'], 70)
        self.assertLess(best_match['score'], 100)
    
    def test_alias_match(self):
        """Teste de match por alias"""
        matches = self.service._find_name_matches('J. Silva')
        
        # Deve encontrar match através do alias
        self.assertGreater(len(matches), 0)
        best_match = max(matches, key=lambda x: x['score'])
        self.assertGreater(best_match['score'], 80)
    
    def test_document_number_match(self):
        """Teste de match por número de documento"""
        matches = self.service._find_document_matches('12345678901')
        
        # Deve encontrar match exato por documento
        self.assertGreater(len(matches), 0)
        
        # Match por documento deve ter score máximo
        best_match = max(matches, key=lambda x: x['score'])
        self.assertEqual(best_match['score'], 100)
    
    def test_no_match_scenario(self):
        """Teste de cenário sem matches"""
        # Nome que não existe nas sanções
        name_matches = self.service._find_name_matches('Carlos Oliveira')
        doc_matches = self.service._find_document_matches('99999999999')
        
        # Não deve encontrar matches
        self.assertEqual(len(name_matches), 0)
        self.assertEqual(len(doc_matches), 0)
    
    def test_screen_customer_no_matches(self):
        """Teste de screening de cliente sem matches"""
        # Cliente com dados que não estão nas sanções
        clean_customer = Customer.objects.create(
            customer_type='INDIVIDUAL',
            first_name='Carlos',
            last_name='Oliveira',
            email='carlos@email.com',
            phone='+5511888888888',
            document_type='CPF',
            document_number='99999999999',
            country='Brasil'
        )
        
        result = self.service.screen_customer(clean_customer, self.user)
        
        # Verificar resultado
        self.assertEqual(result['status'], 'CLEAR')
        self.assertEqual(len(result['matches']), 0)
        self.assertIsNotNone(result['check_id'])
    
    def test_screen_customer_with_matches(self):
        """Teste de screening de cliente com matches"""
        result = self.service.screen_customer(self.customer, self.user)
        
        # Verificar resultado
        self.assertEqual(result['status'], 'POTENTIAL_MATCH')
        self.assertGreater(len(result['matches']), 0)
        self.assertIsNotNone(result['check_id'])
        
        # Verificar se o check foi salvo no banco
        check = SanctionsCheck.objects.get(id=result['check_id'])
        self.assertEqual(check.customer, self.customer)
        self.assertEqual(check.checked_by, self.user)
    
    def test_screen_beneficial_owners(self):
        """Teste de screening de beneficiários finais"""
        # Criar beneficiário que está nas sanções
        beneficial_owner = BeneficialOwner.objects.create(
            customer=self.customer,
            full_name='Maria Santos',
            document_number='98765432100',
            document_type='CPF',
            ownership_percentage=Decimal('25.00'),
            country='Brasil'
        )
        
        result = self.service.screen_beneficial_owners(self.customer, self.user)
        
        # Verificar resultado
        self.assertEqual(result['status'], 'POTENTIAL_MATCH')
        self.assertGreater(len(result['matches']), 0)
        
        # Verificar se o match é do beneficiário correto
        match = result['matches'][0]
        self.assertIn('Maria Santos', match['matched_name'])
    
    def test_comprehensive_screening(self):
        """Teste de screening abrangente (cliente + beneficiários)"""
        # Criar beneficiário
        BeneficialOwner.objects.create(
            customer=self.customer,
            full_name='Carlos Limpo',  # Nome não sancionado
            document_number='11111111111',
            document_type='CPF',
            ownership_percentage=Decimal('50.00'),
            country='Brasil'
        )
        
        result = self.service.comprehensive_screening(self.customer, self.user)
        
        # Verificar resultado
        self.assertIn('customer_result', result)
        self.assertIn('beneficial_owners_result', result)
        self.assertIn('overall_status', result)
        
        # Status geral deve ser POTENTIAL_MATCH devido ao cliente principal
        self.assertEqual(result['overall_status'], 'POTENTIAL_MATCH')
    
    def test_match_scoring_algorithm(self):
        """Teste do algoritmo de scoring de matches"""
        test_cases = [
            ('João Silva', 'João Silva', 100),  # Match exato
            ('João Silva', 'Joao Silva', 95),   # Sem acento
            ('João Silva', 'J. Silva', 85),     # Abreviação
            ('João Silva', 'João Santos', 70),  # Nome parcial
            ('João Silva', 'Maria Santos', 30)  # Nomes diferentes
        ]
        
        for name1, name2, expected_min_score in test_cases:
            score = self.service._calculate_name_similarity(name1, name2)
            self.assertGreaterEqual(score, expected_min_score - 10,
                                  f"Score para '{name1}' vs '{name2}' muito baixo")
    
    def test_false_positive_handling(self):
        """Teste de tratamento de falsos positivos"""
        # Criar entrada com nome comum que pode gerar falsos positivos
        common_name_entry = SanctionsEntry.objects.create(
            sanctions_list=self.sanctions_list,
            name='Silva, João',
            aliases='João Silva',
            document_number='00000000000',  # Documento diferente
            country='Venezuela',  # País diferente
            entry_type='INDIVIDUAL',
            is_active=True
        )
        
        result = self.service.screen_customer(self.customer, self.user)
        
        # Deve encontrar match mas com score menor devido às diferenças
        matches = result['matches']
        if matches:
            best_match = max(matches, key=lambda x: x['score'])
            # Score deve ser menor devido ao país e documento diferentes
            self.assertLess(best_match['score'], 90)
    
    def test_inactive_sanctions_exclusion(self):
        """Teste de exclusão de sanções inativas"""
        # Desativar entrada de sanção
        self.sanctions_entries[0].is_active = False
        self.sanctions_entries[0].save()
        
        result = self.service.screen_customer(self.customer, self.user)
        
        # Não deve encontrar a entrada inativa
        for match in result['matches']:
            self.assertNotEqual(match['sanctions_entry_id'], self.sanctions_entries[0].id)
    
    def test_multiple_sanctions_lists(self):
        """Teste com múltiplas listas de sanções"""
        # Criar segunda lista de sanções
        second_list = SanctionsList.objects.create(
            name='UN Sanctions List',
            description='United Nations Sanctions List',
            source_url='https://www.un.org/sanctions',
            is_active=True
        )
        
        # Criar entrada na segunda lista
        SanctionsEntry.objects.create(
            sanctions_list=second_list,
            name='Silva, João',
            aliases='João Silva',
            document_number='12345678901',
            country='Brasil',
            entry_type='INDIVIDUAL',
            is_active=True
        )
        
        result = self.service.screen_customer(self.customer, self.user)
        
        # Deve encontrar matches de ambas as listas
        list_sources = set(match['list_name'] for match in result['matches'])
        self.assertGreaterEqual(len(list_sources), 1)
    
    def test_screening_performance(self):
        """Teste de performance do screening"""
        import time
        
        start_time = time.time()
        
        # Executar múltiplos screenings
        for _ in range(5):
            self.service.screen_customer(self.customer, self.user)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Verificar se execução é rápida (menos de 2 segundos para 5 screenings)
        self.assertLess(execution_time, 2.0)
    
    def test_screening_audit_trail(self):
        """Teste de trilha de auditoria do screening"""
        result = self.service.screen_customer(self.customer, self.user)
        
        # Verificar se o check foi registrado
        check = SanctionsCheck.objects.get(id=result['check_id'])
        self.assertEqual(check.customer, self.customer)
        self.assertEqual(check.checked_by, self.user)
        self.assertIsNotNone(check.check_date)
        self.assertIsNotNone(check.result_summary)
    
    def test_match_details_structure(self):
        """Teste da estrutura dos detalhes do match"""
        result = self.service.screen_customer(self.customer, self.user)
        
        if result['matches']:
            match = result['matches'][0]
            
            # Verificar campos obrigatórios
            required_fields = [
                'sanctions_entry_id', 'matched_name', 'score', 
                'match_type', 'list_name', 'entry_type'
            ]
            
            for field in required_fields:
                self.assertIn(field, match)
    
    @patch('apps.sanctions.services.SanctionsScreeningService._find_name_matches')
    def test_service_with_mocked_name_search(self, mock_name_search):
        """Teste com mock da busca por nome"""
        mock_name_search.return_value = [
            {
                'sanctions_entry_id': 1,
                'matched_name': 'João Silva',
                'score': 95,
                'match_type': 'NAME',
                'list_name': 'OFAC SDN',
                'entry_type': 'INDIVIDUAL'
            }
        ]
        
        result = self.service.screen_customer(self.customer, self.user)
        
        # Verificar se o mock foi chamado
        mock_name_search.assert_called()
        self.assertEqual(result['status'], 'POTENTIAL_MATCH')
    
    def test_error_handling_invalid_customer(self):
        """Teste de tratamento de erro com cliente inválido"""
        with self.assertRaises(ValueError):
            self.service.screen_customer(None, self.user)
    
    def test_bulk_screening(self):
        """Teste de screening em lote"""
        # Criar múltiplos clientes
        customers = []
        for i in range(3):
            customer = Customer.objects.create(
                customer_type='INDIVIDUAL',
                first_name=f'Cliente{i}',
                last_name='Teste',
                email=f'cliente{i}@email.com',
                phone=f'+551199999999{i}',
                document_type='CPF',
                document_number=f'1234567890{i}',
                country='Brasil'
            )
            customers.append(customer)
        
        results = self.service.bulk_screening(customers, self.user)
        
        # Verificar resultados
        self.assertEqual(len(results), 3)
        for result in results:
            self.assertIn('customer_id', result)
            self.assertIn('status', result)
            self.assertIn('matches', result)


class SanctionsModelTest(TestCase):
    """Testes unitários para modelos de sanctions"""
    
    def setUp(self):
        """Configuração inicial"""
        self.sanctions_list = SanctionsList.objects.create(
            name='Test List',
            description='Lista de teste',
            source_url='https://test.com',
            is_active=True
        )
    
    def test_sanctions_entry_creation(self):
        """Teste de criação de entrada de sanção"""
        entry = SanctionsEntry.objects.create(
            sanctions_list=self.sanctions_list,
            name='Teste, João',
            aliases='João Teste;J. Teste',
            document_number='12345678901',
            country='Brasil',
            entry_type='INDIVIDUAL',
            is_active=True
        )
        
        self.assertEqual(entry.name, 'Teste, João')
        self.assertEqual(entry.country, 'Brasil')
        self.assertTrue(entry.is_active)
    
    def test_sanctions_entry_str_method(self):
        """Teste do método __str__ da entrada de sanção"""
        entry = SanctionsEntry.objects.create(
            sanctions_list=self.sanctions_list,
            name='Teste, João',
            entry_type='INDIVIDUAL',
            is_active=True
        )
        
        expected_str = "Teste, João (Test List)"
        self.assertEqual(str(entry), expected_str)

