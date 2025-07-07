"""
CERES Simplified - Customer Views
Basic API views for customer management
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q, Count
from .models import Customer, BeneficialOwner, CustomerNote


class CustomerViewSet(viewsets.ModelViewSet):
    """ViewSet for Customer model"""
    
    queryset = Customer.objects.with_risk_data()
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter queryset based on query parameters"""
        queryset = super().get_queryset()
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(onboarding_status=status_filter)
        
        # Filter by risk level
        risk_filter = self.request.query_params.get('risk_level')
        if risk_filter:
            queryset = queryset.filter(risk_level=risk_filter)
        
        # Filter high risk customers
        if self.request.query_params.get('high_risk') == 'true':
            queryset = queryset.high_risk()
        
        # Filter customers needing review
        if self.request.query_params.get('needs_review') == 'true':
            queryset = queryset.pending_review()
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def calculate_risk(self, request, pk=None):
        """Recalculate risk for a customer"""
        customer = self.get_object()
        customer.calculate_initial_risk()
        customer.refresh_from_db()
        
        return Response({
            'message': 'Risk recalculated successfully',
            'risk_score': customer.risk_score,
            'risk_level': customer.risk_level
        })
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a customer"""
        customer = self.get_object()
        customer.onboarding_status = Customer.OnboardingStatus.APPROVED
        customer.last_review_date = timezone.now()
        customer.save()
        
        return Response({'message': 'Customer approved successfully'})
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a customer"""
        customer = self.get_object()
        customer.onboarding_status = Customer.OnboardingStatus.REJECTED
        customer.save()
        
        return Response({'message': 'Customer rejected successfully'})
    
    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Get dashboard statistics"""
        total_customers = Customer.objects.count()
        
        stats = {
            'total_customers': total_customers,
            'by_status': {},
            'by_risk_level': {},
            'high_risk_count': Customer.objects.high_risk().count(),
            'pending_review_count': Customer.objects.pending_review().count(),
        }
        
        # Count by status
        for status, _ in Customer.OnboardingStatus.choices:
            count = Customer.objects.filter(onboarding_status=status).count()
            stats['by_status'][status] = count
        
        # Count by risk level
        for risk_level, _ in Customer.RiskLevel.choices:
            count = Customer.objects.filter(risk_level=risk_level).count()
            stats['by_risk_level'][risk_level] = count
        
        return Response(stats)


class BeneficialOwnerViewSet(viewsets.ModelViewSet):
    """ViewSet for BeneficialOwner model"""
    
    queryset = BeneficialOwner.objects.select_related('customer')
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter by customer if provided"""
        queryset = super().get_queryset()
        customer_id = self.request.query_params.get('customer')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        return queryset


class CustomerNoteViewSet(viewsets.ModelViewSet):
    """ViewSet for CustomerNote model"""
    
    queryset = CustomerNote.objects.select_related('customer', 'created_by')
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter by customer if provided"""
        queryset = super().get_queryset()
        customer_id = self.request.query_params.get('customer')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        return queryset
    
    def perform_create(self, serializer):
        """Set created_by to current user"""
        serializer.save(created_by=self.request.user)

