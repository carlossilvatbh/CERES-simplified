"""
CERES Simplified - Compliance Models
Simplified compliance models maintaining core business logic
"""

import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


class ComplianceRule(models.Model):
    """Compliance rules and regulations"""
    
    class RuleType(models.TextChoices):
        KYC = "KYC", "Know Your Customer"
        AML = "AML", "Anti-Money Laundering"
        SANCTIONS = "SANCTIONS", "Sanctions Screening"
        PEP = "PEP", "Politically Exposed Persons"
        FATCA = "FATCA", "FATCA"
        CRS = "CRS", "Common Reporting Standard"
        OTHER = "OTHER", "Outro"
    
    class Severity(models.TextChoices):
        LOW = "LOW", "Baixa"
        MEDIUM = "MEDIUM", "Média"
        HIGH = "HIGH", "Alta"
        CRITICAL = "CRITICAL", "Crítica"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name="Nome")
    description = models.TextField(verbose_name="Descrição")
    rule_type = models.CharField(
        max_length=20,
        choices=RuleType.choices,
        verbose_name="Tipo de Regra"
    )
    
    # Rule configuration
    severity = models.CharField(
        max_length=10,
        choices=Severity.choices,
        default=Severity.MEDIUM,
        verbose_name="Severidade"
    )
    auto_check = models.BooleanField(
        default=True,
        verbose_name="Verificação Automática"
    )
    requires_manual_review = models.BooleanField(
        default=False,
        verbose_name="Requer Revisão Manual"
    )
    
    # Rule logic (simplified)
    condition_logic = models.TextField(
        blank=True,
        verbose_name="Lógica da Condição",
        help_text="Descrição da lógica de verificação"
    )
    
    # Metadata
    is_active = models.BooleanField(default=True, verbose_name="Ativa")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criada em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizada em")
    
    class Meta:
        verbose_name = "Regra de Compliance"
        verbose_name_plural = "Regras de Compliance"
        ordering = ['rule_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_rule_type_display()})"


class ComplianceCheck(models.Model):
    """Compliance checks performed on customers"""
    
    class CheckStatus(models.TextChoices):
        PENDING = "PENDING", "Pendente"
        IN_PROGRESS = "IN_PROGRESS", "Em Andamento"
        PASSED = "PASSED", "Aprovado"
        FAILED = "FAILED", "Reprovado"
        REQUIRES_REVIEW = "REQUIRES_REVIEW", "Requer Revisão"
        EXEMPTED = "EXEMPTED", "Isento"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.CASCADE,
        related_name='compliance_checks',
        verbose_name="Cliente"
    )
    rule = models.ForeignKey(
        ComplianceRule,
        on_delete=models.PROTECT,
        verbose_name="Regra"
    )
    
    # Check details
    check_status = models.CharField(
        max_length=20,
        choices=CheckStatus.choices,
        default=CheckStatus.PENDING,
        verbose_name="Status da Verificação"
    )
    
    # Results
    result_details = models.TextField(
        blank=True,
        verbose_name="Detalhes do Resultado"
    )
    risk_score = models.IntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Score de Risco"
    )
    
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
    next_check_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Próxima Verificação"
    )
    
    # User tracking
    initiated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='initiated_compliance_checks',
        verbose_name="Iniciado por"
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_compliance_checks',
        verbose_name="Revisado por"
    )
    
    # Notes
    notes = models.TextField(blank=True, verbose_name="Observações")
    
    class Meta:
        verbose_name = "Verificação de Compliance"
        verbose_name_plural = "Verificações de Compliance"
        ordering = ['-check_date']
        unique_together = ['customer', 'rule', 'check_date']
        indexes = [
            models.Index(fields=['customer', 'check_status']),
            models.Index(fields=['rule', 'check_status']),
            models.Index(fields=['check_date']),
        ]
    
    def __str__(self):
        return f"{self.customer.full_name} - {self.rule.name} ({self.get_check_status_display()})"
    
    def save(self, *args, **kwargs):
        """Override save to set completion date"""
        if self.check_status in [
            self.CheckStatus.PASSED, 
            self.CheckStatus.FAILED, 
            self.CheckStatus.EXEMPTED
        ] and not self.completed_date:
            self.completed_date = timezone.now()
        
        super().save(*args, **kwargs)
    
    def is_passed(self):
        """Check if compliance check passed"""
        return self.check_status == self.CheckStatus.PASSED
    
    def needs_review(self):
        """Check if compliance check needs review"""
        return self.check_status == self.CheckStatus.REQUIRES_REVIEW


class ComplianceReport(models.Model):
    """Compliance reports and summaries"""
    
    class ReportType(models.TextChoices):
        CUSTOMER_SUMMARY = "CUSTOMER_SUMMARY", "Resumo do Cliente"
        PERIODIC_REVIEW = "PERIODIC_REVIEW", "Revisão Periódica"
        REGULATORY_FILING = "REGULATORY_FILING", "Arquivo Regulatório"
        AUDIT_REPORT = "AUDIT_REPORT", "Relatório de Auditoria"
        EXCEPTION_REPORT = "EXCEPTION_REPORT", "Relatório de Exceções"
    
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Rascunho"
        UNDER_REVIEW = "UNDER_REVIEW", "Em Revisão"
        APPROVED = "APPROVED", "Aprovado"
        SUBMITTED = "SUBMITTED", "Enviado"
        ARCHIVED = "ARCHIVED", "Arquivado"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=500, verbose_name="Título")
    description = models.TextField(verbose_name="Descrição")
    report_type = models.CharField(
        max_length=20,
        choices=ReportType.choices,
        verbose_name="Tipo de Relatório"
    )
    
    # Report scope
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.CASCADE,
        related_name='compliance_reports',
        blank=True,
        null=True,
        verbose_name="Cliente"
    )
    period_start = models.DateField(
        blank=True,
        null=True,
        verbose_name="Início do Período"
    )
    period_end = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fim do Período"
    )
    
    # Report content
    content = models.TextField(verbose_name="Conteúdo")
    summary = models.TextField(
        blank=True,
        verbose_name="Resumo Executivo"
    )
    recommendations = models.TextField(
        blank=True,
        verbose_name="Recomendações"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="Status"
    )
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    approved_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Aprovado em"
    )
    submitted_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Enviado em"
    )
    
    # User tracking
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_compliance_reports',
        verbose_name="Criado por"
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_compliance_reports',
        verbose_name="Aprovado por"
    )
    
    class Meta:
        verbose_name = "Relatório de Compliance"
        verbose_name_plural = "Relatórios de Compliance"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.get_report_type_display()})"


class ComplianceAlert(models.Model):
    """Compliance alerts and notifications"""
    
    class AlertType(models.TextChoices):
        RULE_VIOLATION = "RULE_VIOLATION", "Violação de Regra"
        THRESHOLD_EXCEEDED = "THRESHOLD_EXCEEDED", "Limite Excedido"
        REVIEW_DUE = "REVIEW_DUE", "Revisão Vencida"
        DOCUMENT_EXPIRED = "DOCUMENT_EXPIRED", "Documento Expirado"
        SANCTIONS_MATCH = "SANCTIONS_MATCH", "Correspondência de Sanções"
        HIGH_RISK_ACTIVITY = "HIGH_RISK_ACTIVITY", "Atividade de Alto Risco"
    
    class Severity(models.TextChoices):
        INFO = "INFO", "Informativo"
        WARNING = "WARNING", "Aviso"
        ERROR = "ERROR", "Erro"
        CRITICAL = "CRITICAL", "Crítico"
    
    class Status(models.TextChoices):
        OPEN = "OPEN", "Aberto"
        ACKNOWLEDGED = "ACKNOWLEDGED", "Reconhecido"
        IN_PROGRESS = "IN_PROGRESS", "Em Andamento"
        RESOLVED = "RESOLVED", "Resolvido"
        DISMISSED = "DISMISSED", "Dispensado"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    alert_type = models.CharField(
        max_length=20,
        choices=AlertType.choices,
        verbose_name="Tipo de Alerta"
    )
    severity = models.CharField(
        max_length=10,
        choices=Severity.choices,
        default=Severity.WARNING,
        verbose_name="Severidade"
    )
    
    # Alert details
    title = models.CharField(max_length=500, verbose_name="Título")
    message = models.TextField(verbose_name="Mensagem")
    
    # Related entities
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.CASCADE,
        related_name='compliance_alerts',
        blank=True,
        null=True,
        verbose_name="Cliente"
    )
    rule = models.ForeignKey(
        ComplianceRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Regra"
    )
    case = models.ForeignKey(
        'cases.Case',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Caso"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        verbose_name="Status"
    )
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    acknowledged_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Reconhecido em"
    )
    resolved_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Resolvido em"
    )
    
    # User tracking
    acknowledged_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_alerts',
        verbose_name="Reconhecido por"
    )
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_alerts',
        verbose_name="Resolvido por"
    )
    
    # Resolution
    resolution_notes = models.TextField(
        blank=True,
        verbose_name="Notas da Resolução"
    )
    
    class Meta:
        verbose_name = "Alerta de Compliance"
        verbose_name_plural = "Alertas de Compliance"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'severity']),
            models.Index(fields=['customer']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.get_severity_display()})"
    
    def save(self, *args, **kwargs):
        """Override save to set timestamps"""
        if self.status == self.Status.ACKNOWLEDGED and not self.acknowledged_at:
            self.acknowledged_at = timezone.now()
        
        if self.status == self.Status.RESOLVED and not self.resolved_at:
            self.resolved_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    def get_severity_color(self):
        """Get color for severity display"""
        colors = {
            self.Severity.INFO: 'blue',
            self.Severity.WARNING: 'orange',
            self.Severity.ERROR: 'red',
            self.Severity.CRITICAL: 'darkred',
        }
        return colors.get(self.severity, 'gray')
    
    def is_open(self):
        """Check if alert is open"""
        return self.status == self.Status.OPEN
    
    def is_critical(self):
        """Check if alert is critical"""
        return self.severity == self.Severity.CRITICAL


class ComplianceMetric(models.Model):
    """Compliance metrics and KPIs"""
    
    class MetricType(models.TextChoices):
        COMPLETION_RATE = "COMPLETION_RATE", "Taxa de Conclusão"
        APPROVAL_RATE = "APPROVAL_RATE", "Taxa de Aprovação"
        AVERAGE_PROCESSING_TIME = "AVERAGE_PROCESSING_TIME", "Tempo Médio de Processamento"
        EXCEPTION_RATE = "EXCEPTION_RATE", "Taxa de Exceções"
        RISK_SCORE_DISTRIBUTION = "RISK_SCORE_DISTRIBUTION", "Distribuição de Score de Risco"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name="Nome")
    description = models.TextField(verbose_name="Descrição")
    metric_type = models.CharField(
        max_length=30,
        choices=MetricType.choices,
        verbose_name="Tipo de Métrica"
    )
    
    # Metric value
    value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Valor"
    )
    target_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Valor Alvo"
    )
    unit = models.CharField(
        max_length=50,
        default="%",
        verbose_name="Unidade"
    )
    
    # Period
    period_start = models.DateField(verbose_name="Início do Período")
    period_end = models.DateField(verbose_name="Fim do Período")
    
    # Metadata
    calculated_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Calculado em"
    )
    calculated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Calculado por"
    )
    
    class Meta:
        verbose_name = "Métrica de Compliance"
        verbose_name_plural = "Métricas de Compliance"
        ordering = ['-calculated_at']
        unique_together = ['metric_type', 'period_start', 'period_end']
    
    def __str__(self):
        return f"{self.name}: {self.value}{self.unit}"
    
    def is_target_met(self):
        """Check if target is met"""
        if not self.target_value:
            return None
        return self.value >= self.target_value
    
    def get_performance_color(self):
        """Get color based on performance vs target"""
        if not self.target_value:
            return 'gray'
        
        if self.value >= self.target_value:
            return 'green'
        elif self.value >= self.target_value * 0.8:  # Within 80% of target
            return 'orange'
        else:
            return 'red'

