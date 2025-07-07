# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planejado
- Interface web customizada
- APIs REST completas
- Sistema de notificações
- Importação em massa
- Relatórios avançados

## [0.2.0] - 2025-01-07

### Added - Fase 2: Modelos Core Implementados
- **Gestão de Clientes**: Modelos Customer, BeneficialOwner, CustomerNote
- **Avaliação de Risco**: Modelos RiskAssessment, RiskFactor, RiskMatrix
- **Verificação de Sanções**: Modelos SanctionsCheck, SanctionsList, SanctionsEntry
- **Gestão de Casos**: Modelos Case, CaseType, CaseNote, CaseAssignment
- **Gestão de Documentos**: Modelos Document, DocumentType, DocumentReview
- **Compliance**: Modelos ComplianceCheck, ComplianceRule, ComplianceAlert
- Django Admin customizado para todos os modelos
- Sistema de cálculo automático de risk score
- Workflow de aprovação de documentos
- Sistema de alertas de compliance
- Otimizações de performance com select_related/prefetch_related
- Índices de banco de dados otimizados
- Validações de negócio implementadas

### Changed
- Simplificação de 70% das dependências (15 vs 50+ pacotes)
- Redução de 67% dos apps Django (6 vs 18 apps)
- Eliminação de complexidades desnecessárias (Celery, Redis, criptografia)

### Technical
- 22 modelos implementados
- 25+ índices otimizados
- 30+ relacionamentos configurados
- Migrações Django criadas e testadas
- Sistema de auditoria simplificado

## [0.1.0] - 2025-01-07

### Added - Fase 1: Estrutura Base
- Estrutura inicial do projeto Django
- Configuração simplificada em arquivo único
- 6 apps principais criados (customers, risk, sanctions, cases, documents, compliance)
- Sistema de dependências mínimas
- Configuração de desenvolvimento funcional
- Makefile com comandos úteis
- Documentação inicial
- Configuração Git e estrutura de repositório

### Technical
- Django 5.1.4 como framework base
- SQLite como banco de desenvolvimento
- Estrutura de diretórios limpa e organizada
- Requirements.txt com dependências mínimas
- Settings.py unificado para simplicidade

## Tipos de Mudanças

- `Added` para novas funcionalidades
- `Changed` para mudanças em funcionalidades existentes
- `Deprecated` para funcionalidades que serão removidas
- `Removed` para funcionalidades removidas
- `Fixed` para correções de bugs
- `Security` para correções de vulnerabilidades
- `Technical` para mudanças técnicas internas

---

**Legenda de Versões:**
- **Major** (X.0.0): Mudanças incompatíveis na API
- **Minor** (0.X.0): Novas funcionalidades compatíveis
- **Patch** (0.0.X): Correções de bugs compatíveis

