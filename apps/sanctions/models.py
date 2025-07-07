"""
CERES Simplified - Sanctions Screening Models
Simplified sanctions screening models maintaining core business logic
"""

import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


class SanctionsList(models.Model):
    """Sanctions lists configuration"""
    
    class ListType(models.TextChoices):
        OFAC = "OFAC", "OFAC (US Treasury)"
        UN = "UN", "UN Security Council"
        EU = "EU", "European Union"
        UK = "UK", "UK HM Treasury"
        NATIONAL = "NATIONAL", "Lista Nacional"
        OTHER = "OTHER", "Outra"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name="Nome")
    description = models.TextField(verbose_name="Descrição")
    list_type = models.CharField(
        max_length=20,
        choices=ListType.choices,
        verbose_name="Tipo de Lista"
    )
    
    # Configuration
    source_url = models.URLField(
        blank=True,
        verbose_name="URL da Fonte",
        help_text="URL para download da lista"
    )
    is_active = models.BooleanField(default=True, verbose_name="Ativa")
    auto_update = models.BooleanField(
        default=False,
        verbose_name="Atualização Automática"
    )
    
    # Update tracking
    last_updated = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Última Atualização"
    )
    update_frequency_days = models.IntegerField(
        default=7,
        verbose_name="Frequência de Atualização (dias)"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criada em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizada em")
    
    class Meta:
        verbose_name = "Lista de Sanções"
        verbose_name_plural = "Listas de Sanções"
        ordering = ['list_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_list_type_display()})"
    
    def needs_update(self):
        """Check if list needs update"""
        if not self.auto_update or not self.last_updated:
            return False
        
        from datetime import timedelta
        next_update = self.last_updated + timedelta(days=self.update_frequency_days)
        return timezone.now() >= next_update


class SanctionsEntry(models.Model):
    """Individual entries in sanctions lists"""
    
    class EntryType(models.TextChoices):
        INDIVIDUAL = "INDIVIDUAL", "Pessoa Física"
        ENTITY = "ENTITY", "Entidade"
        VESSEL = "VESSEL", "Embarcação"
        AIRCRAFT = "AIRCRAFT", "Aeronave"
        OTHER = "OTHER", "Outro"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sanctions_list = models.ForeignKey(
        SanctionsList,
        on_delete=models.CASCADE,
        related_name='entries',
        verbose_name="Lista de Sanções"
    )
    
    # Entry details
    entry_type = models.CharField(
        max_length=20,
        choices=EntryType.choices,
        default=EntryType.INDIVIDUAL,
        verbose_name="Tipo de Entrada"
    )
    
    # Names and identifiers
    primary_name = models.CharField(max_length=500, verbose_name="Nome Principal")
    alternative_names = models.TextField(
        blank=True,
        verbose_name="Nomes Alternativos",
        help_text="Um nome por linha"
    )
    
    # Identification
    date_of_birth = models.DateField(
        blank=True,
        null=True,
        verbose_name="Data de Nascimento"
    )
    place_of_birth = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Local de Nascimento"
    )
    nationality = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Nacionalidade"
    )
    
    # Documents
    passport_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Número do Passaporte"
    )
    national_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Documento Nacional"
    )
    
    # Address
    address = models.TextField(blank=True, verbose_name="Endereço")
    
    # Sanctions details
    sanctions_program = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Programa de Sanções"
    )
    listing_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Data de Inclusão"
    )
    
    # External reference
    external_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="ID Externo",
        help_text="ID na lista original"
    )
    
    # Metadata
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    
    class Meta:
        verbose_name = "Entrada de Sanções"
        verbose_name_plural = "Entradas de Sanções"
        ordering = ['primary_name']
        indexes = [
            models.Index(fields=['primary_name']),
            models.Index(fields=['passport_number']),
            models.Index(fields=['national_id']),
            models.Index(fields=['sanctions_list', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.primary_name} ({self.sanctions_list.name})"
    
    def get_all_names(self):
        """Get all names (primary + alternatives) as a list"""
        names = [self.primary_name]
        if self.alternative_names:
            names.extend([name.strip() for name in self.alternative_names.split('\n') if name.strip()])
        return names


class SanctionsCheck(models.Model):
    """Sanctions screening checks"""
    
    class CheckType(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Cliente"
        BENEFICIAL_OWNER = "BENEFICIAL_OWNER", "Beneficiário Final"
        MANUAL = "MANUAL", "Manual"
    
    class CheckStatus(models.TextChoices):
        PENDING = "PENDING", "Pendente"
        IN_PROGRESS = "IN_PROGRESS", "Em Andamento"
        COMPLETED = "COMPLETED", "Concluída"
        FAILED = "FAILED", "Falhou"
    
    class MatchStatus(models.TextChoices):
        NO_MATCH = "NO_MATCH", "Sem Correspondência"
        POTENTIAL_MATCH = "POTENTIAL_MATCH", "Correspondência Potencial"
        CONFIRMED_MATCH = "CONFIRMED_MATCH", "Correspondência Confirmada"
        FALSE_POSITIVE = "FALSE_POSITIVE", "Falso Positivo"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # What is being checked
    check_type = models.CharField(
        max_length=20,
        choices=CheckType.choices,
        verbose_name="Tipo de Verificação"
    )
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.CASCADE,
        related_name='sanctions_checks',
        blank=True,
        null=True,
        verbose_name="Cliente"
    )
    beneficial_owner = models.ForeignKey(
        'customers.BeneficialOwner',
        on_delete=models.CASCADE,
        related_name='sanctions_checks',
        blank=True,
        null=True,
        verbose_name="Beneficiário Final"
    )
    
    # Search parameters
    search_name = models.CharField(max_length=500, verbose_name="Nome Pesquisado")
    search_document = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Documento Pesquisado"
    )
    search_date_of_birth = models.DateField(
        blank=True,
        null=True,
        verbose_name="Data de Nascimento Pesquisada"
    )
    
    # Check details
    check_status = models.CharField(
        max_length=20,
        choices=CheckStatus.choices,
        default=CheckStatus.PENDING,
        verbose_name="Status da Verificação"
    )
    match_status = models.CharField(
        max_length=20,
        choices=MatchStatus.choices,
        default=MatchStatus.NO_MATCH,
        verbose_name="Status da Correspondência"
    )
    
    # Lists checked
    lists_checked = models.ManyToManyField(
        SanctionsList,
        verbose_name="Listas Verificadas"
    )
    
    # Results
    total_matches = models.IntegerField(default=0, verbose_name="Total de Correspondências")
    
    # Dates
    check_date = models.DateTimeField(
        default=timezone.now,
        verbose_name="Data da Verificação"
    )
    completed_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Data de Conclusão"
    )
    
    # User tracking
    initiated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='initiated_sanctions_checks',
        verbose_name="Iniciado por"
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_sanctions_checks',
        verbose_name="Revisado por"
    )
    
    # Notes
    notes = models.TextField(blank=True, verbose_name="Observações")
    
    class Meta:
        verbose_name = "Verificação de Sanções"
        verbose_name_plural = "Verificações de Sanções"
        ordering = ['-check_date']
        indexes = [
            models.Index(fields=['customer', 'check_date']),
            models.Index(fields=['beneficial_owner', 'check_date']),
            models.Index(fields=['match_status']),
            models.Index(fields=['check_date']),
        ]
    
    def __str__(self):
        target = self.customer or self.beneficial_owner
        return f"Verificação {target} - {self.get_match_status_display()} ({self.check_date.date()})"
    
    def save(self, *args, **kwargs):
        """Override save to update completion date"""
        if self.check_status == self.CheckStatus.COMPLETED and not self.completed_date:
            self.completed_date = timezone.now()
        super().save(*args, **kwargs)
    
    def get_target_name(self):
        """Get the name of the target being checked"""
        if self.customer:
            return self.customer.full_name
        elif self.beneficial_owner:
            return self.beneficial_owner.full_name
        return self.search_name
    
    def has_matches(self):
        """Check if there are any matches"""
        return self.total_matches > 0
    
    def needs_review(self):
        """Check if check needs manual review"""
        return self.match_status in [
            self.MatchStatus.POTENTIAL_MATCH,
            self.MatchStatus.CONFIRMED_MATCH
        ]


class SanctionsMatch(models.Model):
    """Individual matches found during sanctions screening"""
    
    class MatchType(models.TextChoices):
        EXACT_NAME = "EXACT_NAME", "Nome Exato"
        PARTIAL_NAME = "PARTIAL_NAME", "Nome Parcial"
        FUZZY_NAME = "FUZZY_NAME", "Nome Aproximado"
        DOCUMENT = "DOCUMENT", "Documento"
        DATE_OF_BIRTH = "DATE_OF_BIRTH", "Data de Nascimento"
    
    class ReviewStatus(models.TextChoices):
        PENDING = "PENDING", "Pendente"
        CONFIRMED = "CONFIRMED", "Confirmado"
        FALSE_POSITIVE = "FALSE_POSITIVE", "Falso Positivo"
        NEEDS_INVESTIGATION = "NEEDS_INVESTIGATION", "Requer Investigação"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sanctions_check = models.ForeignKey(
        SanctionsCheck,
        on_delete=models.CASCADE,
        related_name='matches',
        verbose_name="Verificação de Sanções"
    )
    sanctions_entry = models.ForeignKey(
        SanctionsEntry,
        on_delete=models.CASCADE,
        related_name='matches',
        verbose_name="Entrada de Sanções"
    )
    
    # Match details
    match_type = models.CharField(
        max_length=20,
        choices=MatchType.choices,
        verbose_name="Tipo de Correspondência"
    )
    match_score = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Score da Correspondência",
        help_text="Score de 0-100 indicando qualidade da correspondência"
    )
    matched_field = models.CharField(
        max_length=100,
        verbose_name="Campo Correspondente",
        help_text="Campo que gerou a correspondência"
    )
    matched_value = models.CharField(
        max_length=500,
        verbose_name="Valor Correspondente"
    )
    
    # Review
    review_status = models.CharField(
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING,
        verbose_name="Status da Revisão"
    )
    review_notes = models.TextField(
        blank=True,
        verbose_name="Notas da Revisão"
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Revisado por"
    )
    reviewed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Revisado em"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    
    class Meta:
        verbose_name = "Correspondência de Sanções"
        verbose_name_plural = "Correspondências de Sanções"
        ordering = ['-match_score', '-created_at']
        indexes = [
            models.Index(fields=['sanctions_check', 'match_score']),
            models.Index(fields=['review_status']),
        ]
    
    def __str__(self):
        return f"Match: {self.matched_value} ({self.match_score}%)"
    
    def save(self, *args, **kwargs):
        """Override save to update review timestamp"""
        if self.review_status != self.ReviewStatus.PENDING and not self.reviewed_at:
            self.reviewed_at = timezone.now()
        super().save(*args, **kwargs)
    
    def is_high_confidence(self):
        """Check if match is high confidence"""
        return self.match_score >= 80
    
    def needs_review(self):
        """Check if match needs review"""
        return self.review_status == self.ReviewStatus.PENDING

