# Contributing to CERES Simplified

Obrigado por seu interesse em contribuir com o CERES Simplified! Este documento fornece diretrizes para contribuições.

## 🚀 Como Contribuir

### 1. Fork e Clone
```bash
# Fork o repositório no GitHub
# Clone seu fork
git clone https://github.com/SEU_USERNAME/CERES-simplified.git
cd CERES-simplified
```

### 2. Configurar Ambiente
```bash
# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt

# Executar migrações
python manage.py migrate

# Criar superusuário
python manage.py createsuperuser
```

### 3. Criar Branch
```bash
# Criar branch para sua feature/fix
git checkout -b feature/nome-da-feature
# ou
git checkout -b fix/nome-do-fix
```

### 4. Fazer Alterações
- Siga as convenções de código Python (PEP 8)
- Mantenha a simplicidade como princípio
- Adicione testes quando apropriado
- Atualize documentação se necessário

### 5. Commit e Push
```bash
# Adicionar alterações
git add .

# Commit com mensagem descritiva
git commit -m "feat: adicionar nova funcionalidade X"

# Push para seu fork
git push origin feature/nome-da-feature
```

### 6. Pull Request
- Abra um Pull Request no repositório original
- Descreva claramente as alterações
- Referencie issues relacionadas

## 📝 Convenções de Commit

Usamos [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` nova funcionalidade
- `fix:` correção de bug
- `docs:` alterações na documentação
- `style:` formatação, sem mudança de código
- `refactor:` refatoração de código
- `test:` adição ou correção de testes
- `chore:` tarefas de manutenção

## 🏗️ Estrutura do Projeto

```
ceres-simple/
├── apps/                   # Apps Django
│   ├── customers/         # Gestão de clientes
│   ├── risk/             # Avaliação de risco
│   ├── sanctions/        # Verificação de sanções
│   ├── cases/            # Gestão de casos
│   ├── documents/        # Gestão de documentos
│   └── compliance/       # Compliance
├── ceres/                # Configurações Django
├── static/               # Arquivos estáticos
├── media/                # Uploads de arquivos
├── templates/            # Templates HTML
└── requirements.txt      # Dependências
```

## 🧪 Testes

```bash
# Executar testes
python manage.py test

# Verificar cobertura
coverage run --source='.' manage.py test
coverage report
```

## 📋 Checklist para Pull Request

- [ ] Código segue PEP 8
- [ ] Testes passam
- [ ] Documentação atualizada
- [ ] Commit messages seguem convenção
- [ ] Não quebra funcionalidades existentes
- [ ] Mantém simplicidade do projeto

## 🐛 Reportar Bugs

Ao reportar bugs, inclua:

1. **Descrição clara** do problema
2. **Passos para reproduzir**
3. **Comportamento esperado**
4. **Comportamento atual**
5. **Ambiente** (OS, Python version, etc.)
6. **Screenshots** se aplicável

## 💡 Sugerir Funcionalidades

Para sugerir novas funcionalidades:

1. **Verifique** se já não existe issue similar
2. **Descreva** o problema que resolve
3. **Proponha** uma solução
4. **Considere** o impacto na simplicidade

## 📞 Contato

- Abra uma [Issue](https://github.com/carlossilvatbh/CERES-simplified/issues)
- Discussões no [GitHub Discussions](https://github.com/carlossilvatbh/CERES-simplified/discussions)

## 📄 Licença

Ao contribuir, você concorda que suas contribuições serão licenciadas sob a mesma licença do projeto.

---

**Obrigado por contribuir! 🙏**

