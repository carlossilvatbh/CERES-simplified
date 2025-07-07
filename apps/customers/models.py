"""
CERES Simplified - Customer Models
Simplified customer management models maintaining core business logic
"""

import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal


class CustomerQuerySet(models.QuerySet):
    """Optimized QuerySet for Customer model"""
    
    def with_risk_data(self):
        """Prefetch risk-related data to avoid N+1 queries"""
        return self.select_related('created_by').prefetch_related(
            'risk_assessments', 'beneficial_owners', 'documents'
        )
    
    def high_risk(self):
        """Filter high and critical risk customers"""
        return self.filter(risk_level__in=['HIGH', 'CRITICAL'])
    
    def pending_review(self):
        """Customers pending review"""
        return self.filter(
            models.Q(next_review_date__lte=timezone.now()) | 
            models.Q(next_review_date__isnull=True)
        )
    
    def by_status(self, status):
        """Filter by onboarding status"""
        return self.filter(onboarding_status=status)


class CustomerManager(models.Manager):
    """Custom manager for Customer model"""
    
    def get_queryset(self):
        return CustomerQuerySet(self.model, using=self._db)
    
    def with_risk_data(self):
        return self.get_queryset().with_risk_data()
    
    def high_risk(self):
        return self.get_queryset().high_risk()
    
    def pending_review(self):
        return self.get_queryset().pending_review()


class Customer(models.Model):
    """Simplified customer model with core business logic"""

    class CustomerType(models.TextChoices):
        INDIVIDUAL = "INDIVIDUAL", "Pessoa Física"
        CORPORATE = "CORPORATE", "Pessoa Jurídica"
        PARTNERSHIP = "PARTNERSHIP", "Sociedade"
        TRUST = "TRUST", "Trust"
        FOUNDATION = "FOUNDATION", "Fundação"
        OTHER = "OTHER", "Outro"

    class OnboardingStatus(models.TextChoices):
        PENDING = "PENDING", "Pendente"
        IN_PROGRESS = "IN_PROGRESS", "Em Andamento"
        ADDITIONAL_INFO = "ADDITIONAL_INFO", "Informações Adicionais Necessárias"
        UNDER_REVIEW = "UNDER_REVIEW", "Em Análise"
        APPROVED = "APPROVED", "Aprovado"
        REJECTED = "REJECTED", "Rejeitado"
        SUSPENDED = "SUSPENDED", "Suspenso"
        CLOSED = "CLOSED", "Encerrado"

    class RiskLevel(models.TextChoices):
        LOW = "LOW", "Baixo Risco"
        MEDIUM = "MEDIUM", "Médio Risco"
        HIGH = "HIGH", "Alto Risco"
        CRITICAL = "CRITICAL", "Risco Crítico"

    # Basic Information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer_type = models.CharField(
        max_length=20,
        choices=CustomerType.choices,
        default=CustomerType.INDIVIDUAL,
        verbose_name="Tipo de Cliente"
    )
    
    # Personal/Corporate Information
    full_name = models.CharField(max_length=255, verbose_name="Nome Completo")
    legal_name = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name="Razão Social",
        help_text="Para pessoas jurídicas"
    )
    document_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Número do Documento",
        help_text="CPF, CNPJ, Passaporte, etc."
    )
    document_type = models.CharField(
        max_length=20,
        default="CPF",
        verbose_name="Tipo de Documento"
    )
    
    # Contact Information
    email = models.EmailField(verbose_name="E-mail")
    phone = models.CharField(max_length=20, verbose_name="Telefone")
    address = models.TextField(verbose_name="Endereço")
    city = models.CharField(max_length=100, verbose_name="Cidade")
    state = models.CharField(max_length=100, verbose_name="Estado")
    country = models.CharField(max_length=100, default="Brasil", verbose_name="País")
    postal_code = models.CharField(max_length=20, verbose_name="CEP")
    
    # Business Information (for corporate customers)
    business_type = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Tipo de Negócio"
    )
    industry = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Setor"
    )
    annual_revenue = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Receita Anual"
    )
    
    # Status and Risk
    onboarding_status = models.CharField(
        max_length=20,
        choices=OnboardingStatus.choices,
        default=OnboardingStatus.PENDING,
        verbose_name="Status do Onboarding"
    )
    risk_level = models.CharField(
        max_length=10,
        choices=RiskLevel.choices,
        default=RiskLevel.MEDIUM,
        verbose_name="Nível de Risco"
    )
    risk_score = models.IntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Score de Risco"
    )
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    last_review_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Última Revisão"
    )
    next_review_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Próxima Revisão"
    )
    
    # User tracking (simplified)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_customers',
        verbose_name="Criado por"
    )
    
    # Flags
    is_pep = models.BooleanField(
        default=False,
        verbose_name="Pessoa Politicamente Exposta",
        help_text="Pessoa Politicamente Exposta (PEP)"
    )
    is_sanctions_checked = models.BooleanField(
        default=False,
        verbose_name="Verificado contra Sanções"
    )
    sanctions_last_check = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Última Verificação de Sanções"
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        verbose_name="Observações"
    )
    
    objects = CustomerManager()
    
    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['document_number']),
            models.Index(fields=['onboarding_status']),
            models.Index(fields=['risk_level']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.full_name} ({self.document_number})"
    
    def save(self, *args, **kwargs):
        """Override save to trigger risk assessment"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Trigger initial risk assessment for new customers
        if is_new:
            self.calculate_initial_risk()
    
    def calculate_initial_risk(self):
        """Calculate initial risk score based on basic criteria"""
        score = 50  # Base score
        
        # Country risk (simplified)
        high_risk_countries = ['AF', 'IR', 'KP', 'SY']  # Example
        if self.country in high_risk_countries:
            score += 30
        
        # PEP status
        if self.is_pep:
            score += 25
        
        # Business type risk (for corporate)
        if self.customer_type == self.CustomerType.CORPORATE:
            high_risk_industries = ['crypto', 'gambling', 'money_transfer']
            if self.industry and any(risk in self.industry.lower() for risk in high_risk_industries):
                score += 20
        
        # Ensure score is within bounds
        score = max(0, min(100, score))
        
        # Update risk level based on score
        if score >= 80:
            risk_level = self.RiskLevel.CRITICAL
        elif score >= 60:
            risk_level = self.RiskLevel.HIGH
        elif score >= 30:
            risk_level = self.RiskLevel.MEDIUM
        else:
            risk_level = self.RiskLevel.LOW
        
        # Update without triggering save recursion
        Customer.objects.filter(pk=self.pk).update(
            risk_score=score,
            risk_level=risk_level
        )
    
    def get_risk_color(self):
        """Get color for risk level display"""
        colors = {
            self.RiskLevel.LOW: 'green',
            self.RiskLevel.MEDIUM: 'orange',
            self.RiskLevel.HIGH: 'red',
            self.RiskLevel.CRITICAL: 'darkred',
        }
        return colors.get(self.risk_level, 'gray')
    
    def needs_review(self):
        """Check if customer needs review"""
        if not self.next_review_date:
            return True
        return self.next_review_date <= timezone.now()
    
    def is_high_risk(self):
        """Check if customer is high risk"""
        return self.risk_level in [self.RiskLevel.HIGH, self.RiskLevel.CRITICAL]


class BeneficialOwner(models.Model):
    """Simplified beneficial owner model"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='beneficial_owners',
        verbose_name="Cliente"
    )
    
    # Personal Information
    full_name = models.CharField(max_length=255, verbose_name="Nome Completo")
    document_number = models.CharField(max_length=50, verbose_name="Número do Documento")
    document_type = models.CharField(max_length=20, default="CPF", verbose_name="Tipo de Documento")
    
    # Ownership Information
    ownership_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(Decimal('100.00'))],
        verbose_name="Percentual de Participação"
    )
    
    # Contact Information
    email = models.EmailField(blank=True, verbose_name="E-mail")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Telefone")
    address = models.TextField(blank=True, verbose_name="Endereço")
    country = models.CharField(max_length=100, default="Brasil", verbose_name="País")
    
    # Risk Information
    is_pep = models.BooleanField(
        default=False,
        verbose_name="Pessoa Politicamente Exposta"
    )
    is_sanctions_checked = models.BooleanField(
        default=False,
        verbose_name="Verificado contra Sanções"
    )
    sanctions_last_check = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Última Verificação de Sanções"
    )
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    
    # Notes
    notes = models.TextField(blank=True, verbose_name="Observações")
    
    class Meta:
        verbose_name = "Beneficiário Final"
        verbose_name_plural = "Beneficiários Finais"
        ordering = ['-ownership_percentage', 'full_name']
        unique_together = ['customer', 'document_number']
        indexes = [
            models.Index(fields=['customer', 'ownership_percentage']),
            models.Index(fields=['document_number']),
        ]
    
    def __str__(self):
        return f"{self.full_name} ({self.ownership_percentage}% - {self.customer.full_name})"
    
    def save(self, *args, **kwargs):
        """Override save to update customer risk if needed"""
        super().save(*args, **kwargs)
        
        # If this beneficial owner is PEP, update customer risk
        if self.is_pep and not self.customer.is_pep:
            self.customer.is_pep = True
            self.customer.save()


class CustomerNote(models.Model):
    """Simple note system for customers"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='customer_notes',
        verbose_name="Cliente"
    )
    
    title = models.CharField(max_length=200, verbose_name="Título")
    content = models.TextField(verbose_name="Conteúdo")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Criado por"
    )
    
    # Flags
    is_important = models.BooleanField(default=False, verbose_name="Importante")
    is_internal = models.BooleanField(default=True, verbose_name="Nota Interna")
    
    class Meta:
        verbose_name = "Nota do Cliente"
        verbose_name_plural = "Notas dos Clientes"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.customer.full_name}"

