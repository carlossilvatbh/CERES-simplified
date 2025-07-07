# CERES Simplified

<div align="center">

![CERES Logo](https://img.shields.io/badge/CERES-Simplified-blue?style=for-the-badge)
[![Django](https://img.shields.io/badge/Django-5.1.4-green?style=flat-square&logo=django)](https://djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)](https://python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square)](CONTRIBUTING.md)

**Sistema de Compliance e Gestão de Risco Simplificado**

*Mantendo a funcionalidade essencial, eliminando a complexidade desnecessária*

[🚀 Quick Start](#-quick-start) • [📋 Funcionalidades](#-funcionalidades) • [📚 Documentação](#-documentação) • [🤝 Contribuir](#-contribuir)

</div>

---

## 🎯 Sobre o Projeto

O **CERES Simplified** é uma versão simplificada do sistema CERES original, projetada para manter todas as funcionalidades essenciais de compliance e gestão de risco, mas com **70% menos complexidade**.

### ✨ Por que CERES Simplified?

- 🎯 **Foco na Essência**: Mantém apenas o que realmente importa
- ⚡ **Setup Rápido**: De 3 horas para 15 minutos
- 🔧 **Manutenção Simples**: Código limpo e bem documentado
- 💰 **Custo Reduzido**: Menos infraestrutura, menos dependências
- 🚀 **Deploy Fácil**: Sem Docker complexo, Redis ou Celery

## 🚀 Quick Start

```bash
# 1. Clone o repositório
git clone https://github.com/carlossilvatbh/CERES-simplified.git
cd CERES-simplified

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar banco de dados
python manage.py migrate

# 4. Criar superusuário
python manage.py createsuperuser

# 5. Executar servidor
python manage.py runserver
```

🎉 **Pronto!** Acesse http://localhost:8000/admin/

## 📋 Funcionalidades

<table>
<tr>
<td width="50%">

### 👥 **Gestão de Clientes**
- Cadastro de clientes (PF/PJ)
- Beneficiários finais
- Cálculo automático de risco
- Histórico completo

### ⚖️ **Avaliação de Risco**
- Scoring automático (0-100)
- Fatores configuráveis
- Matrizes por tipo de cliente
- Workflow de aprovação

### 🛡️ **Verificação de Sanções**
- Screening contra listas internacionais
- OFAC, UN, EU, UK
- Sistema de matching inteligente
- Gestão de falsos positivos

</td>
<td width="50%">

### 📁 **Gestão de Casos**
- Workflow completo de investigação
- Sistema de SLA
- Atribuição automática
- Histórico de status

### 📄 **Gestão de Documentos**
- Upload seguro
- Versionamento
- Workflow de aprovação
- Controle de expiração

### ✅ **Compliance**
- Regras configuráveis
- Alertas automáticos
- Relatórios regulatórios
- Dashboard de métricas

</td>
</tr>
</table>

## 🏗️ Arquitetura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Django Admin  │    │   REST API      │    │   Frontend      │
│   (Atual)       │    │   (Planejado)   │    │   (Futuro)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
         ┌─────────────────────────────────────────────────┐
         │              Django Backend                     │
         │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐│
         │  │Customer │ │  Risk   │ │Sanctions│ │ Cases  ││
         │  │   App   │ │   App   │ │   App   │ │  App   ││
         │  └─────────┘ └─────────┘ └─────────┘ └────────┘│
         │  ┌─────────┐ ┌─────────┐                       │
         │  │Document │ │Complian-│                       │
         │  │   App   │ │ ce App  │                       │
         │  └─────────┘ └─────────┘                       │
         └─────────────────────────────────────────────────┘
                                 │
         ┌─────────────────────────────────────────────────┐
         │              Database Layer                     │
         │        SQLite (Dev) / PostgreSQL (Prod)        │
         └─────────────────────────────────────────────────┘
```

## 📊 Comparação com Sistema Original

| 📈 Métrica | 🔴 Original | 🟢 Simplificado | 📉 Redução |
|------------|-------------|------------------|------------|
| **Apps Django** | 18 apps | 6 apps | **67%** |
| **Dependências** | 50+ pacotes | 15 pacotes | **70%** |
| **Modelos** | 80+ modelos | 22 modelos | **72%** |
| **Tempo de Setup** | 2-3 horas | 15 minutos | **90%** |
| **Linhas de Código** | 15,000+ | 4,500 | **70%** |
| **Complexidade Deploy** | Alto | Baixo | **80%** |

## 🛠️ Desenvolvimento

### Comandos Úteis

```bash
# Desenvolvimento
make dev          # Executar servidor de desenvolvimento
make test         # Executar testes
make check        # Verificar código
make migrations   # Criar migrações
make migrate      # Aplicar migrações

# Produção
make deploy       # Deploy para produção
make backup       # Backup do banco
make restore      # Restaurar backup
```

### Estrutura do Projeto

```
ceres-simple/
├── 📁 apps/                    # Apps Django
│   ├── 👥 customers/          # Gestão de clientes
│   ├── ⚖️ risk/               # Avaliação de risco
│   ├── 🛡️ sanctions/          # Verificação de sanções
│   ├── 📁 cases/              # Gestão de casos
│   ├── 📄 documents/          # Gestão de documentos
│   └── ✅ compliance/         # Compliance
├── ⚙️ ceres/                  # Configurações Django
├── 🎨 static/                 # Arquivos estáticos
├── 📁 media/                  # Uploads
├── 📄 templates/              # Templates HTML
└── 📋 requirements.txt        # Dependências
```

## 📚 Documentação

| 📖 Documento | 📝 Descrição |
|--------------|--------------|
| [📊 Relatório Fase 2](FASE2_RELATORIO.md) | Detalhes técnicos da implementação |
| [🤝 Como Contribuir](CONTRIBUTING.md) | Guia para contribuidores |
| [📋 Changelog](CHANGELOG.md) | Histórico de mudanças |
| [⚖️ Licença](LICENSE) | Termos de uso |

## 🤝 Contribuir

Contribuições são muito bem-vindas! 🎉

1. 🍴 **Fork** o projeto
2. 🌿 **Crie** uma branch (`git checkout -b feature/AmazingFeature`)
3. 💾 **Commit** suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. 📤 **Push** para a branch (`git push origin feature/AmazingFeature`)
5. 🔄 **Abra** um Pull Request

Veja [CONTRIBUTING.md](CONTRIBUTING.md) para mais detalhes.

## 🗺️ Roadmap

### ✅ Fase 1 - Estrutura Base (Concluída)
- [x] Configuração Django simplificada
- [x] Estrutura de apps
- [x] Dependências mínimas

### ✅ Fase 2 - Modelos Core (Concluída)
- [x] Modelos de negócio implementados
- [x] Django Admin customizado
- [x] Migrações e banco de dados

### 🚧 Fase 3 - Interface e APIs (Em Planejamento)
- [ ] Interface web customizada
- [ ] APIs REST completas
- [ ] Dashboard executivo
- [ ] Relatórios visuais

### 🔮 Fase 4 - Funcionalidades Avançadas (Futuro)
- [ ] Notificações por email
- [ ] Importação em massa
- [ ] Integração com APIs externas
- [ ] Mobile app

## 📞 Suporte

- 🐛 **Bugs**: [Abrir Issue](https://github.com/carlossilvatbh/CERES-simplified/issues/new?template=bug_report.md)
- 💡 **Features**: [Sugerir Feature](https://github.com/carlossilvatbh/CERES-simplified/issues/new?template=feature_request.md)
- 💬 **Discussões**: [GitHub Discussions](https://github.com/carlossilvatbh/CERES-simplified/discussions)

## 📄 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

---

<div align="center">

**Feito com ❤️ pela equipe CERES**

[⭐ Star no GitHub](https://github.com/carlossilvatbh/CERES-simplified) • [🐛 Reportar Bug](https://github.com/carlossilvatbh/CERES-simplified/issues) • [💡 Sugerir Feature](https://github.com/carlossilvatbh/CERES-simplified/issues)

</div>

