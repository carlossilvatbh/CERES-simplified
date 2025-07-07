"""
CERES Simplified - Document Management Models
Simplified document management models maintaining core business logic
"""

import uuid
import os
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from django.conf import settings


def document_upload_path(instance, filename):
    """Generate upload path for documents"""
    # Create path: documents/customer_id/year/month/filename
    if instance.customer:
        customer_id = str(instance.customer.id)
    else:
        customer_id = 'general'
    
    now = timezone.now()
    return f'documents/{customer_id}/{now.year}/{now.month:02d}/{filename}'


class DocumentType(models.Model):
    """Types of documents that can be uploaded"""
    
    class Category(models.TextChoices):
        IDENTIFICATION = "IDENTIFICATION", "Identificação"
        ADDRESS_PROOF = "ADDRESS_PROOF", "Comprovante de Endereço"
        INCOME_PROOF = "INCOME_PROOF", "Comprovante de Renda"
        CORPORATE = "CORPORATE", "Documentos Corporativos"
        COMPLIANCE = "COMPLIANCE", "Compliance"
        OTHER = "OTHER", "Outros"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name="Nome")
    description = models.TextField(verbose_name="Descrição")
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        verbose_name="Categoria"
    )
    
    # Configuration
    is_required = models.BooleanField(
        default=False,
        verbose_name="Obrigatório"
    )
    allowed_extensions = models.CharField(
        max_length=200,
        default="pdf,jpg,jpeg,png,doc,docx",
        verbose_name="Extensões Permitidas",
        help_text="Extensões separadas por vírgula"
    )
    max_file_size_mb = models.IntegerField(
        default=10,
        verbose_name="Tamanho Máximo (MB)"
    )
    
    # Validation rules
    requires_approval = models.BooleanField(
        default=True,
        verbose_name="Requer Aprovação"
    )
    auto_approve = models.BooleanField(
        default=False,
        verbose_name="Aprovação Automática"
    )
    
    # Metadata
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    
    class Meta:
        verbose_name = "Tipo de Documento"
        verbose_name_plural = "Tipos de Documentos"
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"
    
    def get_allowed_extensions_list(self):
        """Get allowed extensions as a list"""
        return [ext.strip().lower() for ext in self.allowed_extensions.split(',')]


class Document(models.Model):
    """Document storage and management"""
    
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendente"
        UNDER_REVIEW = "UNDER_REVIEW", "Em Análise"
        APPROVED = "APPROVED", "Aprovado"
        REJECTED = "REJECTED", "Rejeitado"
        EXPIRED = "EXPIRED", "Expirado"
        REPLACED = "REPLACED", "Substituído"
    
    class Source(models.TextChoices):
        UPLOAD = "UPLOAD", "Upload Manual"
        EMAIL = "EMAIL", "E-mail"
        SCAN = "SCAN", "Digitalização"
        API = "API", "API"
        IMPORT = "IMPORT", "Importação"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Document details
    document_type = models.ForeignKey(
        DocumentType,
        on_delete=models.PROTECT,
        verbose_name="Tipo de Documento"
    )
    title = models.CharField(max_length=500, verbose_name="Título")
    description = models.TextField(blank=True, verbose_name="Descrição")
    
    # Related entities
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.CASCADE,
        related_name='documents',
        blank=True,
        null=True,
        verbose_name="Cliente"
    )
    beneficial_owner = models.ForeignKey(
        'customers.BeneficialOwner',
        on_delete=models.CASCADE,
        related_name='documents',
        blank=True,
        null=True,
        verbose_name="Beneficiário Final"
    )
    case = models.ForeignKey(
        'cases.Case',
        on_delete=models.CASCADE,
        related_name='documents',
        blank=True,
        null=True,
        verbose_name="Caso"
    )
    
    # File information
    file = models.FileField(
        upload_to=document_upload_path,
        verbose_name="Arquivo",
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx', 'txt']
            )
        ]
    )
    original_filename = models.CharField(
        max_length=500,
        verbose_name="Nome Original do Arquivo"
    )
    file_size = models.BigIntegerField(verbose_name="Tamanho do Arquivo (bytes)")
    file_hash = models.CharField(
        max_length=64,
        blank=True,
        verbose_name="Hash do Arquivo",
        help_text="SHA-256 hash for integrity verification"
    )
    
    # Status and approval
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Status"
    )
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.UPLOAD,
        verbose_name="Origem"
    )
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    expiry_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Data de Expiração"
    )
    
    # User tracking
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_documents',
        verbose_name="Enviado por"
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_documents',
        verbose_name="Revisado por"
    )
    reviewed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Revisado em"
    )
    
    # Review details
    review_notes = models.TextField(
        blank=True,
        verbose_name="Notas da Revisão"
    )
    rejection_reason = models.TextField(
        blank=True,
        verbose_name="Motivo da Rejeição"
    )
    
    # Flags
    is_sensitive = models.BooleanField(
        default=False,
        verbose_name="Documento Sensível"
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name="Verificado"
    )
    
    # Version control
    version = models.IntegerField(default=1, verbose_name="Versão")
    replaced_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replaces',
        verbose_name="Substituído por"
    )
    
    # Tags for categorization
    tags = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Tags",
        help_text="Tags separadas por vírgula"
    )
    
    class Meta:
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'document_type']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['expiry_date']),
            models.Index(fields=['file_hash']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.document_type.name})"
    
    def save(self, *args, **kwargs):
        """Override save to set file metadata"""
        if self.file:
            # Set original filename if not set
            if not self.original_filename:
                self.original_filename = self.file.name
            
            # Set file size
            if hasattr(self.file, 'size'):
                self.file_size = self.file.size
            
            # Calculate file hash
            if not self.file_hash:
                self.file_hash = self.calculate_file_hash()
        
        # Set reviewed_at when status changes to approved/rejected
        if self.status in [self.Status.APPROVED, self.Status.REJECTED] and not self.reviewed_at:
            self.reviewed_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    def calculate_file_hash(self):
        """Calculate SHA-256 hash of the file"""
        import hashlib
        
        if not self.file:
            return ""
        
        hash_sha256 = hashlib.sha256()
        try:
            self.file.seek(0)
            for chunk in iter(lambda: self.file.read(4096), b""):
                hash_sha256.update(chunk)
            self.file.seek(0)
            return hash_sha256.hexdigest()
        except Exception:
            return ""
    
    def get_status_color(self):
        """Get color for status display"""
        colors = {
            self.Status.PENDING: 'orange',
            self.Status.UNDER_REVIEW: 'blue',
            self.Status.APPROVED: 'green',
            self.Status.REJECTED: 'red',
            self.Status.EXPIRED: 'gray',
            self.Status.REPLACED: 'purple',
        }
        return colors.get(self.status, 'black')
    
    def is_expired(self):
        """Check if document is expired"""
        if not self.expiry_date:
            return False
        return timezone.now().date() > self.expiry_date
    
    def is_image(self):
        """Check if document is an image"""
        if not self.file:
            return False
        
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
        file_ext = os.path.splitext(self.file.name)[1].lower()
        return file_ext in image_extensions
    
    def is_pdf(self):
        """Check if document is a PDF"""
        if not self.file:
            return False
        
        return os.path.splitext(self.file.name)[1].lower() == '.pdf'
    
    def get_file_size_mb(self):
        """Get file size in MB"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0
    
    def get_related_entity(self):
        """Get the main related entity"""
        return self.customer or self.beneficial_owner
    
    def can_be_replaced(self):
        """Check if document can be replaced"""
        return self.status not in [self.Status.REPLACED] and not self.replaced_by


class DocumentVersion(models.Model):
    """Track document versions"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='versions',
        verbose_name="Documento"
    )
    
    # Version details
    version_number = models.IntegerField(verbose_name="Número da Versão")
    change_description = models.TextField(
        verbose_name="Descrição da Alteração"
    )
    
    # File information
    file_path = models.CharField(
        max_length=500,
        verbose_name="Caminho do Arquivo"
    )
    file_size = models.BigIntegerField(verbose_name="Tamanho do Arquivo")
    file_hash = models.CharField(max_length=64, verbose_name="Hash do Arquivo")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criada em")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Criada por"
    )
    
    class Meta:
        verbose_name = "Versão do Documento"
        verbose_name_plural = "Versões dos Documentos"
        ordering = ['-version_number']
        unique_together = ['document', 'version_number']
    
    def __str__(self):
        return f"{self.document.title} v{self.version_number}"


class DocumentReview(models.Model):
    """Document review history"""
    
    class Action(models.TextChoices):
        SUBMITTED = "SUBMITTED", "Enviado"
        REVIEWED = "REVIEWED", "Revisado"
        APPROVED = "APPROVED", "Aprovado"
        REJECTED = "REJECTED", "Rejeitado"
        REQUESTED_CHANGES = "REQUESTED_CHANGES", "Solicitadas Alterações"
        RESUBMITTED = "RESUBMITTED", "Reenviado"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='review_history',
        verbose_name="Documento"
    )
    
    # Review details
    action = models.CharField(
        max_length=20,
        choices=Action.choices,
        verbose_name="Ação"
    )
    comments = models.TextField(blank=True, verbose_name="Comentários")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criada em")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Criada por"
    )
    
    class Meta:
        verbose_name = "Revisão de Documento"
        verbose_name_plural = "Revisões de Documentos"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.document.title} - {self.get_action_display()}"


class DocumentTemplate(models.Model):
    """Templates for document generation"""
    
    class TemplateType(models.TextChoices):
        LETTER = "LETTER", "Carta"
        REPORT = "REPORT", "Relatório"
        FORM = "FORM", "Formulário"
        CERTIFICATE = "CERTIFICATE", "Certificado"
        OTHER = "OTHER", "Outro"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name="Nome")
    description = models.TextField(verbose_name="Descrição")
    template_type = models.CharField(
        max_length=20,
        choices=TemplateType.choices,
        verbose_name="Tipo de Template"
    )
    
    # Template content
    content = models.TextField(
        verbose_name="Conteúdo",
        help_text="Template content with placeholders like {{customer.name}}"
    )
    
    # Configuration
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    requires_approval = models.BooleanField(
        default=False,
        verbose_name="Requer Aprovação"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Criado por"
    )
    
    class Meta:
        verbose_name = "Template de Documento"
        verbose_name_plural = "Templates de Documentos"
        ordering = ['template_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"
    
    def render(self, context):
        """Render template with context data"""
        # Simple template rendering (could be enhanced with Jinja2 or Django templates)
        content = self.content
        
        # Replace placeholders with context values
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            content = content.replace(placeholder, str(value))
        
        return content

