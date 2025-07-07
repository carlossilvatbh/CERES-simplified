# CERES Simplified - Makefile
# Comandos úteis para desenvolvimento

.PHONY: help install migrate superuser run test clean

help:
	@echo "CERES Simplified - Comandos Disponíveis:"
	@echo ""
	@echo "  install     - Instalar dependências"
	@echo "  migrate     - Executar migrações do banco"
	@echo "  superuser   - Criar superusuário"
	@echo "  run         - Executar servidor de desenvolvimento"
	@echo "  test        - Executar testes"
	@echo "  clean       - Limpar arquivos temporários"
	@echo "  setup       - Setup completo (install + migrate + superuser)"
	@echo ""

install:
	pip install -r requirements.txt

migrate:
	python manage.py makemigrations
	python manage.py migrate

superuser:
	python manage.py createsuperuser

run:
	python manage.py runserver

test:
	python manage.py test

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -f db.sqlite3

setup: install migrate
	@echo "Setup básico concluído!"
	@echo "Execute 'make superuser' para criar um usuário admin"
	@echo "Execute 'make run' para iniciar o servidor"

