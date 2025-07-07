"""
CERES Simplified - Risk Assessment Models
Simplified risk assessment models maintaining core business logic
"""

import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal


class RiskFactor(models.Model):
    """Risk factors used in assessment"""
    
    class FactorType(models.TextChoices):
        GEOGRAPHIC = "GEOGRAPHIC", "Geográfico"
        INDUSTRY = "INDUSTRY", "Setor"
        PRODUCT = "PRODUCT", "Produto"
        CUSTOMER_TYPE = "CUSTOMER_TYPE", "Tipo de Cliente"
        TRANSACTION = "TRANSACTION", "Transacional"
        OTHER = "OTHER", "Outro"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name="Nome")
    description = models.TextField(verbose_name="Descrição")
    factor_type = models.CharField(
        max_length=20,
        choices=FactorType.choices,
        verbose_name="Tipo de Fator"
    )
    
    # Risk scoring
    risk_weight = models.IntegerField(
        validators=[MinValueValidator(-50), MaxValueValidator(50)],
        default=0,
        verbose_name="Peso do Risco",
        help_text="Valor entre -50 e 50 que será adicionado ao score"
    )
    
    # Metadata
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    
    class Meta:
        verbose_name = "Fator de Risco"
        verbose_name_plural = "Fatores de Risco"
        ordering = ['factor_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_factor_type_display()})"


class RiskAssessment(models.Model):
    """Risk assessment for customers"""
    
    class AssessmentType(models.TextChoices):
        INITIAL = "INITIAL", "Inicial"
        PERIODIC = "PERIODIC", "Periódica"
        TRIGGERED = "TRIGGERED", "Disparada por Evento"
        MANUAL = "MANUAL", "Manual"
    
    class RiskLevel(models.TextChoices):
        LOW = "LOW", "Baixo Risco"
        MEDIUM = "MEDIUM", "Médio Risco"
        HIGH = "HIGH", "Alto Risco"
        CRITICAL = "CRITICAL", "Risco Crítico"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.CASCADE,
        related_name='risk_assessments',
        verbose_name="Cliente"
    )
    
    # Assessment details
    assessment_type = models.CharField(
        max_length=20,
        choices=AssessmentType.choices,
        default=AssessmentType.INITIAL,
        verbose_name="Tipo de Avaliação"
    )
    
    # Risk scoring
    base_score = models.IntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Score Base"
    )
    final_score = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Score Final"
    )
    risk_level = models.CharField(
        max_length=10,
        choices=RiskLevel.choices,
        verbose_name="Nível de Risco"
    )
    
    # Applied factors
    applied_factors = models.ManyToManyField(
        RiskFactor,
        through='RiskFactorApplication',
        verbose_name="Fatores Aplicados"
    )
    
    # Assessment details
    methodology = models.CharField(
        max_length=100,
        default="CERES Simplified",
        verbose_name="Metodologia"
    )
    justification = models.TextField(
        verbose_name="Justificativa",
        help_text="Explicação detalhada da avaliação de risco"
    )
    
    # Dates
    assessment_date = models.DateTimeField(
        default=timezone.now,
        verbose_name="Data da Avaliação"
    )
    valid_until = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Válida até"
    )
    
    # User tracking
    assessed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Avaliado por"
    )
    
    # Flags
    is_current = models.BooleanField(
        default=True,
        verbose_name="Avaliação Atual"
    )
    requires_approval = models.BooleanField(
        default=False,
        verbose_name="Requer Aprovação"
    )
    is_approved = models.BooleanField(
        default=False,
        verbose_name="Aprovada"
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_risk_assessments',
        verbose_name="Aprovada por"
    )
    approved_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Aprovada em"
    )
    
    # Notes
    notes = models.TextField(blank=True, verbose_name="Observações")
    
    class Meta:
        verbose_name = "Avaliação de Risco"
        verbose_name_plural = "Avaliações de Risco"
        ordering = ['-assessment_date']
        indexes = [
            models.Index(fields=['customer', 'is_current']),
            models.Index(fields=['risk_level']),
            models.Index(fields=['assessment_date']),
        ]
    
    def __str__(self):
        return f"Avaliação {self.customer.full_name} - {self.risk_level} ({self.assessment_date.date()})"
    
    def save(self, *args, **kwargs):
        """Override save to calculate risk level and manage current assessment"""
        # Calculate risk level based on score
        if self.final_score >= 80:
            self.risk_level = self.RiskLevel.CRITICAL
        elif self.final_score >= 60:
            self.risk_level = self.RiskLevel.HIGH
        elif self.final_score >= 30:
            self.risk_level = self.RiskLevel.MEDIUM
        else:
            self.risk_level = self.RiskLevel.LOW
        
        # Set validity period (1 year for low/medium, 6 months for high/critical)
        if not self.valid_until:
            from datetime import timedelta
            if self.risk_level in [self.RiskLevel.HIGH, self.RiskLevel.CRITICAL]:
                self.valid_until = self.assessment_date + timedelta(days=180)  # 6 months
            else:
                self.valid_until = self.assessment_date + timedelta(days=365)  # 1 year
        
        super().save(*args, **kwargs)
        
        # Update customer risk information
        if self.is_current:
            # Mark other assessments as not current
            RiskAssessment.objects.filter(
                customer=self.customer,
                is_current=True
            ).exclude(pk=self.pk).update(is_current=False)
            
            # Update customer risk data
            self.customer.risk_score = self.final_score
            self.customer.risk_level = self.risk_level
            self.customer.last_review_date = self.assessment_date
            self.customer.next_review_date = self.valid_until
            self.customer.save(update_fields=[
                'risk_score', 'risk_level', 'last_review_date', 'next_review_date'
            ])
    
    def get_risk_color(self):
        """Get color for risk level display"""
        colors = {
            self.RiskLevel.LOW: 'green',
            self.RiskLevel.MEDIUM: 'orange',
            self.RiskLevel.HIGH: 'red',
            self.RiskLevel.CRITICAL: 'darkred',
        }
        return colors.get(self.risk_level, 'gray')
    
    def is_expired(self):
        """Check if assessment is expired"""
        if not self.valid_until:
            return False
        return timezone.now() > self.valid_until
    
    def calculate_score_with_factors(self):
        """Calculate final score applying risk factors"""
        score = self.base_score
        
        # Apply risk factors
        for application in self.riskfactorapplication_set.all():
            score += application.factor.risk_weight
        
        # Ensure score is within bounds
        score = max(0, min(100, score))
        
        return score


class RiskFactorApplication(models.Model):
    """Through model for risk factor application"""
    
    risk_assessment = models.ForeignKey(
        RiskAssessment,
        on_delete=models.CASCADE,
        verbose_name="Avaliação de Risco"
    )
    factor = models.ForeignKey(
        RiskFactor,
        on_delete=models.CASCADE,
        verbose_name="Fator de Risco"
    )
    
    # Application details
    applied_weight = models.IntegerField(
        verbose_name="Peso Aplicado",
        help_text="Peso efetivamente aplicado (pode diferir do peso padrão)"
    )
    justification = models.TextField(
        blank=True,
        verbose_name="Justificativa",
        help_text="Justificativa para aplicação deste fator"
    )
    
    # Metadata
    applied_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Aplicado em"
    )
    applied_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Aplicado por"
    )
    
    class Meta:
        verbose_name = "Aplicação de Fator de Risco"
        verbose_name_plural = "Aplicações de Fatores de Risco"
        unique_together = ['risk_assessment', 'factor']
    
    def __str__(self):
        return f"{self.factor.name} -> {self.risk_assessment}"
    
    def save(self, *args, **kwargs):
        """Override save to set default applied weight"""
        if not self.applied_weight:
            self.applied_weight = self.factor.risk_weight
        super().save(*args, **kwargs)


class RiskMatrix(models.Model):
    """Risk matrix configuration for different customer types"""
    
    class CustomerType(models.TextChoices):
        INDIVIDUAL = "INDIVIDUAL", "Pessoa Física"
        CORPORATE = "CORPORATE", "Pessoa Jurídica"
        PARTNERSHIP = "PARTNERSHIP", "Sociedade"
        TRUST = "TRUST", "Trust"
        FOUNDATION = "FOUNDATION", "Fundação"
        OTHER = "OTHER", "Outro"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name="Nome")
    description = models.TextField(verbose_name="Descrição")
    customer_type = models.CharField(
        max_length=20,
        choices=CustomerType.choices,
        verbose_name="Tipo de Cliente"
    )
    
    # Score thresholds
    low_risk_threshold = models.IntegerField(
        default=30,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Limite Baixo Risco"
    )
    medium_risk_threshold = models.IntegerField(
        default=60,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Limite Médio Risco"
    )
    high_risk_threshold = models.IntegerField(
        default=80,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Limite Alto Risco"
    )
    
    # Default factors for this matrix
    default_factors = models.ManyToManyField(
        RiskFactor,
        blank=True,
        verbose_name="Fatores Padrão"
    )
    
    # Metadata
    is_active = models.BooleanField(default=True, verbose_name="Ativa")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criada em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizada em")
    
    class Meta:
        verbose_name = "Matriz de Risco"
        verbose_name_plural = "Matrizes de Risco"
        ordering = ['customer_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_customer_type_display()})"
    
    def get_risk_level_for_score(self, score):
        """Get risk level for a given score"""
        if score >= self.high_risk_threshold:
            return RiskAssessment.RiskLevel.CRITICAL
        elif score >= self.medium_risk_threshold:
            return RiskAssessment.RiskLevel.HIGH
        elif score >= self.low_risk_threshold:
            return RiskAssessment.RiskLevel.MEDIUM
        else:
            return RiskAssessment.RiskLevel.LOW

