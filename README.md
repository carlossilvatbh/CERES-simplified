# CERES Simplified
## Sistema Simplificado de Avaliação de Risco e Compliance

Esta é uma versão simplificada do sistema CERES, focada em testar funcionalidade e lógica de negócio sem as complexidades de segurança, auditoria e escalabilidade do sistema original.

## 🚀 Início Rápido

### Pré-requisitos
- Python 3.11+
- pip

### Instalação

1. **Clone o repositório**
```bash
git clone <repository-url>
cd ceres-simple
```

2. **Crie um ambiente virtual**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

3. **Instale as dependências**
```bash
pip install -r requirements.txt
```

4. **Configure as variáveis de ambiente**
```bash
cp .env.example .env
# Edite o arquivo .env conforme necessário
```

5. **Execute as migrações**
```bash
python manage.py migrate
```

6. **Crie um superusuário**
```bash
python manage.py createsuperuser
```

7. **Execute o servidor**
```bash
python manage.py runserver
```

8. **Acesse o sistema**
- Admin: http://localhost:8000/admin/
- API: http://localhost:8000/api/

## 📋 Funcionalidades

### Core
- ✅ Cadastro de Clientes
- ✅ Avaliação de Risco Simplificada
- ✅ Verificação de Sanções Básica
- ✅ Gestão de Casos
- ✅ Upload de Documentos
- ✅ Interface Django Admin Customizada

### Removido da Versão Original
- ❌ Microserviços complexos
- ❌ Celery + Redis
- ❌ Frontend Vue.js/React
- ❌ Criptografia de campos
- ❌ Auditoria completa
- ❌ Multi-tenant
- ❌ OAuth/JWT complexo
- ❌ Machine Learning avançado

## 🏗️ Arquitetura

```
ceres-simple/
├── manage.py
├── requirements.txt
├── ceres/                 # Configurações Django
├── apps/
│   ├── customers/         # Gestão de clientes
│   ├── risk/             # Avaliação de risco
│   ├── sanctions/        # Verificação de sanções
│   ├── cases/            # Gestão de casos
│   ├── documents/        # Gestão de documentos
│   └── compliance/       # Regras de compliance
├── static/               # Arquivos estáticos
├── media/                # Uploads
└── templates/            # Templates Django
```

## 🔧 Comandos Úteis

```bash
# Executar servidor de desenvolvimento
python manage.py runserver

# Criar migrações
python manage.py makemigrations

# Aplicar migrações
python manage.py migrate

# Criar superusuário
python manage.py createsuperuser

# Coletar arquivos estáticos
python manage.py collectstatic

# Shell Django
python manage.py shell

# Executar testes
python manage.py test
```

## 📊 Banco de Dados

Por padrão, o sistema usa SQLite para desenvolvimento. Para usar PostgreSQL:

1. Instale o PostgreSQL
2. Crie um banco de dados
3. Configure as variáveis no arquivo `.env`:
```
USE_SQLITE=False
DB_NAME=ceres_simple
DB_USER=seu_usuario
DB_PASSWORD=sua_senha
DB_HOST=localhost
DB_PORT=5432
```

## 🎯 Objetivo

Esta versão simplificada foi criada para:
- Testar lógica de negócio sem complexidades técnicas
- Facilitar desenvolvimento e debugging
- Permitir foco na funcionalidade core
- Reduzir tempo de setup e configuração

## 📝 Notas

- Esta é uma versão de teste/desenvolvimento
- Não deve ser usada em produção
- Funcionalidades de segurança foram simplificadas
- Para produção, use o sistema CERES completo

## 🤝 Contribuição

1. Faça um fork do projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT.

