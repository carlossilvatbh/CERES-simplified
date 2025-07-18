# Generated by Django 5.1.4 on 2025-07-07 10:02

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('customers', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='RiskFactor',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200, verbose_name='Nome')),
                ('description', models.TextField(verbose_name='Descrição')),
                ('factor_type', models.CharField(choices=[('GEOGRAPHIC', 'Geográfico'), ('INDUSTRY', 'Setor'), ('PRODUCT', 'Produto'), ('CUSTOMER_TYPE', 'Tipo de Cliente'), ('TRANSACTION', 'Transacional'), ('OTHER', 'Outro')], max_length=20, verbose_name='Tipo de Fator')),
                ('risk_weight', models.IntegerField(default=0, help_text='Valor entre -50 e 50 que será adicionado ao score', validators=[django.core.validators.MinValueValidator(-50), django.core.validators.MaxValueValidator(50)], verbose_name='Peso do Risco')),
                ('is_active', models.BooleanField(default=True, verbose_name='Ativo')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
            ],
            options={
                'verbose_name': 'Fator de Risco',
                'verbose_name_plural': 'Fatores de Risco',
                'ordering': ['factor_type', 'name'],
            },
        ),
        migrations.CreateModel(
            name='RiskAssessment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('assessment_type', models.CharField(choices=[('INITIAL', 'Inicial'), ('PERIODIC', 'Periódica'), ('TRIGGERED', 'Disparada por Evento'), ('MANUAL', 'Manual')], default='INITIAL', max_length=20, verbose_name='Tipo de Avaliação')),
                ('base_score', models.IntegerField(default=50, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name='Score Base')),
                ('final_score', models.IntegerField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name='Score Final')),
                ('risk_level', models.CharField(choices=[('LOW', 'Baixo Risco'), ('MEDIUM', 'Médio Risco'), ('HIGH', 'Alto Risco'), ('CRITICAL', 'Risco Crítico')], max_length=10, verbose_name='Nível de Risco')),
                ('methodology', models.CharField(default='CERES Simplified', max_length=100, verbose_name='Metodologia')),
                ('justification', models.TextField(help_text='Explicação detalhada da avaliação de risco', verbose_name='Justificativa')),
                ('assessment_date', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Data da Avaliação')),
                ('valid_until', models.DateTimeField(blank=True, null=True, verbose_name='Válida até')),
                ('is_current', models.BooleanField(default=True, verbose_name='Avaliação Atual')),
                ('requires_approval', models.BooleanField(default=False, verbose_name='Requer Aprovação')),
                ('is_approved', models.BooleanField(default=False, verbose_name='Aprovada')),
                ('approved_at', models.DateTimeField(blank=True, null=True, verbose_name='Aprovada em')),
                ('notes', models.TextField(blank=True, verbose_name='Observações')),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_risk_assessments', to=settings.AUTH_USER_MODEL, verbose_name='Aprovada por')),
                ('assessed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='Avaliado por')),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='risk_assessments', to='customers.customer', verbose_name='Cliente')),
            ],
            options={
                'verbose_name': 'Avaliação de Risco',
                'verbose_name_plural': 'Avaliações de Risco',
                'ordering': ['-assessment_date'],
            },
        ),
        migrations.CreateModel(
            name='RiskFactorApplication',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('applied_weight', models.IntegerField(help_text='Peso efetivamente aplicado (pode diferir do peso padrão)', verbose_name='Peso Aplicado')),
                ('justification', models.TextField(blank=True, help_text='Justificativa para aplicação deste fator', verbose_name='Justificativa')),
                ('applied_at', models.DateTimeField(auto_now_add=True, verbose_name='Aplicado em')),
                ('applied_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='Aplicado por')),
                ('factor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='risk.riskfactor', verbose_name='Fator de Risco')),
                ('risk_assessment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='risk.riskassessment', verbose_name='Avaliação de Risco')),
            ],
            options={
                'verbose_name': 'Aplicação de Fator de Risco',
                'verbose_name_plural': 'Aplicações de Fatores de Risco',
                'unique_together': {('risk_assessment', 'factor')},
            },
        ),
        migrations.AddField(
            model_name='riskassessment',
            name='applied_factors',
            field=models.ManyToManyField(through='risk.RiskFactorApplication', to='risk.riskfactor', verbose_name='Fatores Aplicados'),
        ),
        migrations.CreateModel(
            name='RiskMatrix',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200, verbose_name='Nome')),
                ('description', models.TextField(verbose_name='Descrição')),
                ('customer_type', models.CharField(choices=[('INDIVIDUAL', 'Pessoa Física'), ('CORPORATE', 'Pessoa Jurídica'), ('PARTNERSHIP', 'Sociedade'), ('TRUST', 'Trust'), ('FOUNDATION', 'Fundação'), ('OTHER', 'Outro')], max_length=20, verbose_name='Tipo de Cliente')),
                ('low_risk_threshold', models.IntegerField(default=30, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name='Limite Baixo Risco')),
                ('medium_risk_threshold', models.IntegerField(default=60, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name='Limite Médio Risco')),
                ('high_risk_threshold', models.IntegerField(default=80, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name='Limite Alto Risco')),
                ('is_active', models.BooleanField(default=True, verbose_name='Ativa')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Criada em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Atualizada em')),
                ('default_factors', models.ManyToManyField(blank=True, to='risk.riskfactor', verbose_name='Fatores Padrão')),
            ],
            options={
                'verbose_name': 'Matriz de Risco',
                'verbose_name_plural': 'Matrizes de Risco',
                'ordering': ['customer_type', 'name'],
            },
        ),
        migrations.AddIndex(
            model_name='riskassessment',
            index=models.Index(fields=['customer', 'is_current'], name='risk_riskas_custome_a886e9_idx'),
        ),
        migrations.AddIndex(
            model_name='riskassessment',
            index=models.Index(fields=['risk_level'], name='risk_riskas_risk_le_d8da9f_idx'),
        ),
        migrations.AddIndex(
            model_name='riskassessment',
            index=models.Index(fields=['assessment_date'], name='risk_riskas_assessm_58c18e_idx'),
        ),
    ]
