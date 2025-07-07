"""
CERES Simplified - Case Management Models
Simplified case management models maintaining core business logic
"""

import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


class CaseType(models.Model):
    """Types of cases that can be created"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name="Nome")
    description = models.TextField(verbose_name="Descrição")
    
    # Configuration
    default_priority = models.CharField(
        max_length=10,
        choices=[
            ('LOW', 'Baixa'),
            ('MEDIUM', 'Média'),
            ('HIGH', 'Alta'),
            ('CRITICAL', 'Crítica'),
        ],
        default='MEDIUM',
        verbose_name="Prioridade Padrão"
    )
    auto_assign = models.BooleanField(
        default=False,
        verbose_name="Atribuição Automática"
    )
    sla_hours = models.IntegerField(
        blank=True,
        null=True,
        verbose_name="SLA (horas)",
        help_text="Tempo limite para resolução em horas"
    )
    
    # Metadata
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    
    class Meta:
        verbose_name = "Tipo de Caso"
        verbose_name_plural = "Tipos de Casos"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Case(models.Model):
    """Case management for investigations and follow-ups"""
    
    class Priority(models.TextChoices):
        LOW = "LOW", "Baixa"
        MEDIUM = "MEDIUM", "Média"
        HIGH = "HIGH", "Alta"
        CRITICAL = "CRITICAL", "Crítica"
    
    class Status(models.TextChoices):
        OPEN = "OPEN", "Aberto"
        IN_PROGRESS = "IN_PROGRESS", "Em Andamento"
        PENDING_INFO = "PENDING_INFO", "Aguardando Informações"
        UNDER_REVIEW = "UNDER_REVIEW", "Em Análise"
        RESOLVED = "RESOLVED", "Resolvido"
        CLOSED = "CLOSED", "Fechado"
        CANCELLED = "CANCELLED", "Cancelado"
    
    class Resolution(models.TextChoices):
        APPROVED = "APPROVED", "Aprovado"
        REJECTED = "REJECTED", "Rejeitado"
        ESCALATED = "ESCALATED", "Escalado"
        NO_ACTION = "NO_ACTION", "Nenhuma Ação Necessária"
        REFERRED = "REFERRED", "Encaminhado"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Número do Caso"
    )
    
    # Case details
    case_type = models.ForeignKey(
        CaseType,
        on_delete=models.PROTECT,
        verbose_name="Tipo de Caso"
    )
    title = models.CharField(max_length=500, verbose_name="Título")
    description = models.TextField(verbose_name="Descrição")
    
    # Related entities
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.CASCADE,
        related_name='cases',
        blank=True,
        null=True,
        verbose_name="Cliente"
    )
    beneficial_owner = models.ForeignKey(
        'customers.BeneficialOwner',
        on_delete=models.CASCADE,
        related_name='cases',
        blank=True,
        null=True,
        verbose_name="Beneficiário Final"
    )
    
    # Status and priority
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        verbose_name="Status"
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        verbose_name="Prioridade"
    )
    
    # Assignment
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_cases',
        verbose_name="Atribuído para"
    )
    assigned_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Atribuído em"
    )
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    due_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Data Limite"
    )
    resolved_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Resolvido em"
    )
    closed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Fechado em"
    )
    
    # Resolution
    resolution = models.CharField(
        max_length=20,
        choices=Resolution.choices,
        blank=True,
        verbose_name="Resolução"
    )
    resolution_notes = models.TextField(
        blank=True,
        verbose_name="Notas da Resolução"
    )
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_cases',
        verbose_name="Resolvido por"
    )
    
    # User tracking
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_cases',
        verbose_name="Criado por"
    )
    
    # Flags
    is_escalated = models.BooleanField(default=False, verbose_name="Escalado")
    requires_approval = models.BooleanField(
        default=False,
        verbose_name="Requer Aprovação"
    )
    
    # Tags for categorization
    tags = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Tags",
        help_text="Tags separadas por vírgula"
    )
    
    class Meta:
        verbose_name = "Caso"
        verbose_name_plural = "Casos"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['case_number']),
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['customer']),
            models.Index(fields=['created_at']),
            models.Index(fields=['due_date']),
        ]
    
    def __str__(self):
        return f"{self.case_number} - {self.title}"
    
    def save(self, *args, **kwargs):
        """Override save to generate case number and set dates"""
        if not self.case_number:
            self.case_number = self.generate_case_number()
        
        # Set due date based on SLA if not set
        if not self.due_date and self.case_type.sla_hours:
            from datetime import timedelta
            self.due_date = self.created_at + timedelta(hours=self.case_type.sla_hours)
        
        # Set resolved_at when status changes to resolved
        if self.status == self.Status.RESOLVED and not self.resolved_at:
            self.resolved_at = timezone.now()
        
        # Set closed_at when status changes to closed
        if self.status == self.Status.CLOSED and not self.closed_at:
            self.closed_at = timezone.now()
        
        # Set assigned_at when assigned_to changes
        if self.assigned_to and not self.assigned_at:
            self.assigned_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    def generate_case_number(self):
        """Generate unique case number"""
        from datetime import datetime
        year = datetime.now().year
        
        # Get last case number for this year
        last_case = Case.objects.filter(
            case_number__startswith=f"CASE-{year}-"
        ).order_by('-case_number').first()
        
        if last_case:
            # Extract sequence number and increment
            try:
                last_seq = int(last_case.case_number.split('-')[-1])
                seq = last_seq + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        
        return f"CASE-{year}-{seq:06d}"
    
    def get_priority_color(self):
        """Get color for priority display"""
        colors = {
            self.Priority.LOW: 'green',
            self.Priority.MEDIUM: 'orange',
            self.Priority.HIGH: 'red',
            self.Priority.CRITICAL: 'darkred',
        }
        return colors.get(self.priority, 'gray')
    
    def get_status_color(self):
        """Get color for status display"""
        colors = {
            self.Status.OPEN: 'blue',
            self.Status.IN_PROGRESS: 'orange',
            self.Status.PENDING_INFO: 'purple',
            self.Status.UNDER_REVIEW: 'yellow',
            self.Status.RESOLVED: 'green',
            self.Status.CLOSED: 'gray',
            self.Status.CANCELLED: 'red',
        }
        return colors.get(self.status, 'black')
    
    def is_overdue(self):
        """Check if case is overdue"""
        if not self.due_date:
            return False
        return timezone.now() > self.due_date and self.status not in [
            self.Status.RESOLVED, self.Status.CLOSED, self.Status.CANCELLED
        ]
    
    def is_open(self):
        """Check if case is open"""
        return self.status not in [
            self.Status.RESOLVED, self.Status.CLOSED, self.Status.CANCELLED
        ]
    
    def get_age_days(self):
        """Get case age in days"""
        end_date = self.closed_at or timezone.now()
        return (end_date - self.created_at).days
    
    def get_related_entity(self):
        """Get the main related entity (customer or beneficial owner)"""
        return self.customer or self.beneficial_owner


class CaseNote(models.Model):
    """Notes and updates for cases"""
    
    class NoteType(models.TextChoices):
        GENERAL = "GENERAL", "Geral"
        UPDATE = "UPDATE", "Atualização"
        INVESTIGATION = "INVESTIGATION", "Investigação"
        DECISION = "DECISION", "Decisão"
        COMMUNICATION = "COMMUNICATION", "Comunicação"
        ESCALATION = "ESCALATION", "Escalação"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name='notes',
        verbose_name="Caso"
    )
    
    # Note details
    note_type = models.CharField(
        max_length=20,
        choices=NoteType.choices,
        default=NoteType.GENERAL,
        verbose_name="Tipo de Nota"
    )
    title = models.CharField(max_length=200, verbose_name="Título")
    content = models.TextField(verbose_name="Conteúdo")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criada em")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Criada por"
    )
    
    # Flags
    is_internal = models.BooleanField(
        default=True,
        verbose_name="Nota Interna"
    )
    is_important = models.BooleanField(
        default=False,
        verbose_name="Importante"
    )
    
    class Meta:
        verbose_name = "Nota do Caso"
        verbose_name_plural = "Notas dos Casos"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.case.case_number}"


class CaseAssignment(models.Model):
    """Track case assignment history"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name='assignment_history',
        verbose_name="Caso"
    )
    
    # Assignment details
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='case_assignments',
        verbose_name="Atribuído para"
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='made_assignments',
        verbose_name="Atribuído por"
    )
    
    # Dates
    assigned_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Atribuído em"
    )
    unassigned_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Desatribuído em"
    )
    
    # Reason
    assignment_reason = models.TextField(
        blank=True,
        verbose_name="Motivo da Atribuição"
    )
    
    # Flags
    is_current = models.BooleanField(default=True, verbose_name="Atribuição Atual")
    
    class Meta:
        verbose_name = "Atribuição de Caso"
        verbose_name_plural = "Atribuições de Casos"
        ordering = ['-assigned_at']
    
    def __str__(self):
        return f"{self.case.case_number} -> {self.assigned_to.get_full_name() or self.assigned_to.username}"


class CaseStatusHistory(models.Model):
    """Track case status changes"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name='status_history',
        verbose_name="Caso"
    )
    
    # Status change details
    from_status = models.CharField(
        max_length=20,
        choices=Case.Status.choices,
        blank=True,
        verbose_name="Status Anterior"
    )
    to_status = models.CharField(
        max_length=20,
        choices=Case.Status.choices,
        verbose_name="Novo Status"
    )
    
    # Change details
    changed_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Alterado em"
    )
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Alterado por"
    )
    change_reason = models.TextField(
        blank=True,
        verbose_name="Motivo da Alteração"
    )
    
    class Meta:
        verbose_name = "Histórico de Status"
        verbose_name_plural = "Históricos de Status"
        ordering = ['-changed_at']
    
    def __str__(self):
        return f"{self.case.case_number}: {self.from_status} -> {self.to_status}"

