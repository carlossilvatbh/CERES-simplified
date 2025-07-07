"""
CERES Simplified - Sanctions Screening Services
Business logic for sanctions screening and matching
"""

import logging
import re
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import User

from .models import SanctionsList, SanctionsEntry, SanctionsCheck, SanctionsMatch
from apps.customers.models import Customer, BeneficialOwner

logger = logging.getLogger(__name__)


class SanctionsScreeningService:
    """Service for sanctions screening and matching"""
    
    def __init__(self):
        self.match_threshold = 0.85  # Minimum similarity for exact match
        self.potential_match_threshold = 0.70  # Minimum similarity for potential match
        self.fuzzy_match_threshold = 0.60  # Minimum similarity for fuzzy match
    
    def screen_customer(self, customer: Customer, initiated_by: User = None) -> SanctionsCheck:
        """
        Perform comprehensive sanctions screening for customer
        
        Args:
            customer: Customer instance to screen
            initiated_by: User who initiated the screening
            
        Returns:
            SanctionsCheck instance with results
        """
        logger.info(f"Starting sanctions screening for customer {customer.id}")
        
        try:
            with transaction.atomic():
                # Create screening record
                sanctions_check = SanctionsCheck.objects.create(
                    customer=customer,
                    check_date=timezone.now(),
                    match_status='PENDING',
                    initiated_by=initiated_by
                )
                
                # Get active sanctions lists
                active_lists = SanctionsList.objects.filter(is_active=True)
                
                # Perform screening against all lists
                all_matches = []
                for sanctions_list in active_lists:
                    matches = self._screen_against_list(customer, sanctions_list)
                    all_matches.extend(matches)
                
                # Determine overall match status
                match_status = self._determine_match_status(all_matches)
                
                # Update sanctions check
                sanctions_check.match_status = match_status
                sanctions_check.total_matches = len(all_matches)
                sanctions_check.notes = f"Screened against {active_lists.count()} sanctions lists"
                sanctions_check.save()
                
                # Create match records
                for match_data in all_matches:
                    SanctionsMatch.objects.create(
                        sanctions_check=sanctions_check,
                        sanctions_entry=match_data['entry'],
                        match_type=match_data['match_type'],
                        match_score=match_data['score'],
                        matched_field=match_data['field'],
                        review_status='PENDING'
                    )
                
                logger.info(f"Sanctions screening completed for customer {customer.id}: "
                           f"{match_status} with {len(all_matches)} matches")
                
                return sanctions_check
                
        except Exception as e:
            logger.error(f"Error in sanctions screening for customer {customer.id}: {str(e)}")
            raise
    
    def screen_beneficial_owner(self, beneficial_owner: BeneficialOwner, 
                              initiated_by: User = None) -> SanctionsCheck:
        """
        Perform sanctions screening for beneficial owner
        
        Args:
            beneficial_owner: BeneficialOwner instance to screen
            initiated_by: User who initiated the screening
            
        Returns:
            SanctionsCheck instance with results
        """
        logger.info(f"Starting sanctions screening for beneficial owner {beneficial_owner.id}")
        
        try:
            with transaction.atomic():
                # Create screening record
                sanctions_check = SanctionsCheck.objects.create(
                    beneficial_owner=beneficial_owner,
                    check_date=timezone.now(),
                    match_status='PENDING',
                    initiated_by=initiated_by
                )
                
                # Get active sanctions lists
                active_lists = SanctionsList.objects.filter(is_active=True)
                
                # Perform screening against all lists
                all_matches = []
                for sanctions_list in active_lists:
                    matches = self._screen_beneficial_owner_against_list(beneficial_owner, sanctions_list)
                    all_matches.extend(matches)
                
                # Determine overall match status
                match_status = self._determine_match_status(all_matches)
                
                # Update sanctions check
                sanctions_check.match_status = match_status
                sanctions_check.total_matches = len(all_matches)
                sanctions_check.notes = f"Screened against {active_lists.count()} sanctions lists"
                sanctions_check.save()
                
                # Create match records
                for match_data in all_matches:
                    SanctionsMatch.objects.create(
                        sanctions_check=sanctions_check,
                        sanctions_entry=match_data['entry'],
                        match_type=match_data['match_type'],
                        match_score=match_data['score'],
                        matched_field=match_data['field'],
                        review_status='PENDING'
                    )
                
                logger.info(f"Sanctions screening completed for beneficial owner {beneficial_owner.id}: "
                           f"{match_status} with {len(all_matches)} matches")
                
                return sanctions_check
                
        except Exception as e:
            logger.error(f"Error in sanctions screening for beneficial owner {beneficial_owner.id}: {str(e)}")
            raise
    
    def _screen_against_list(self, customer: Customer, sanctions_list: SanctionsList) -> List[Dict]:
        """Screen customer against specific sanctions list"""
        
        matches = []
        entries = SanctionsEntry.objects.filter(
            sanctions_list=sanctions_list,
            is_active=True
        )
        
        # Prepare customer data for matching
        customer_data = self._prepare_customer_data(customer)
        
        for entry in entries:
            entry_matches = self._match_customer_against_entry(customer_data, entry)
            matches.extend(entry_matches)
        
        return matches
    
    def _screen_beneficial_owner_against_list(self, beneficial_owner: BeneficialOwner, 
                                            sanctions_list: SanctionsList) -> List[Dict]:
        """Screen beneficial owner against specific sanctions list"""
        
        matches = []
        entries = SanctionsEntry.objects.filter(
            sanctions_list=sanctions_list,
            is_active=True
        )
        
        # Prepare beneficial owner data for matching
        bo_data = self._prepare_beneficial_owner_data(beneficial_owner)
        
        for entry in entries:
            entry_matches = self._match_beneficial_owner_against_entry(bo_data, entry)
            matches.extend(entry_matches)
        
        return matches
    
    def _prepare_customer_data(self, customer: Customer) -> Dict:
        """Prepare customer data for sanctions matching"""
        
        return {
            'names': [
                customer.full_name,
                customer.legal_name if customer.legal_name else None,
                # Add any aliases or alternative names
            ],
            'documents': [
                customer.document_number,
                customer.tax_id if hasattr(customer, 'tax_id') else None,
            ],
            'dates': [
                customer.date_of_birth,
                customer.incorporation_date if hasattr(customer, 'incorporation_date') else None,
            ],
            'locations': [
                customer.country,
                customer.nationality if hasattr(customer, 'nationality') else None,
            ]
        }
    
    def _prepare_beneficial_owner_data(self, beneficial_owner: BeneficialOwner) -> Dict:
        """Prepare beneficial owner data for sanctions matching"""
        
        return {
            'names': [
                beneficial_owner.full_name,
                # Add any aliases
            ],
            'documents': [
                beneficial_owner.document_number,
            ],
            'dates': [
                beneficial_owner.date_of_birth,
            ],
            'locations': [
                beneficial_owner.nationality,
                beneficial_owner.country_of_residence if hasattr(beneficial_owner, 'country_of_residence') else None,
            ]
        }
    
    def _match_customer_against_entry(self, customer_data: Dict, entry: SanctionsEntry) -> List[Dict]:
        """Match customer data against sanctions entry"""
        
        matches = []
        
        # Name matching
        for customer_name in customer_data['names']:
            if customer_name:
                name_matches = self._match_names(customer_name, entry)
                matches.extend(name_matches)
        
        # Document matching
        for customer_doc in customer_data['documents']:
            if customer_doc:
                doc_matches = self._match_documents(customer_doc, entry)
                matches.extend(doc_matches)
        
        # Date matching
        for customer_date in customer_data['dates']:
            if customer_date:
                date_matches = self._match_dates(customer_date, entry)
                matches.extend(date_matches)
        
        return matches
    
    def _match_beneficial_owner_against_entry(self, bo_data: Dict, entry: SanctionsEntry) -> List[Dict]:
        """Match beneficial owner data against sanctions entry"""
        
        matches = []
        
        # Name matching
        for bo_name in bo_data['names']:
            if bo_name:
                name_matches = self._match_names(bo_name, entry)
                matches.extend(name_matches)
        
        # Document matching
        for bo_doc in bo_data['documents']:
            if bo_doc:
                doc_matches = self._match_documents(bo_doc, entry)
                matches.extend(doc_matches)
        
        # Date matching
        for bo_date in bo_data['dates']:
            if bo_date:
                date_matches = self._match_dates(bo_date, entry)
                matches.extend(date_matches)
        
        return matches
    
    def _match_names(self, name: str, entry: SanctionsEntry) -> List[Dict]:
        """Match names using various algorithms"""
        
        matches = []
        
        # Normalize names for comparison
        normalized_name = self._normalize_name(name)
        
        # Check against primary name
        if entry.primary_name:
            normalized_entry_name = self._normalize_name(entry.primary_name)
            score = self._calculate_name_similarity(normalized_name, normalized_entry_name)
            
            if score >= self.match_threshold:
                matches.append({
                    'entry': entry,
                    'match_type': 'EXACT',
                    'score': score,
                    'field': 'primary_name'
                })
            elif score >= self.potential_match_threshold:
                matches.append({
                    'entry': entry,
                    'match_type': 'POTENTIAL',
                    'score': score,
                    'field': 'primary_name'
                })
            elif score >= self.fuzzy_match_threshold:
                matches.append({
                    'entry': entry,
                    'match_type': 'FUZZY',
                    'score': score,
                    'field': 'primary_name'
                })
        
        # Check against aliases
        if entry.aliases:
            aliases = entry.aliases.split(';')
            for alias in aliases:
                if alias.strip():
                    normalized_alias = self._normalize_name(alias.strip())
                    score = self._calculate_name_similarity(normalized_name, normalized_alias)
                    
                    if score >= self.potential_match_threshold:
                        matches.append({
                            'entry': entry,
                            'match_type': 'POTENTIAL' if score >= self.match_threshold else 'FUZZY',
                            'score': score,
                            'field': 'alias'
                        })
        
        return matches
    
    def _match_documents(self, document: str, entry: SanctionsEntry) -> List[Dict]:
        """Match document numbers"""
        
        matches = []
        
        # Normalize document for comparison
        normalized_doc = self._normalize_document(document)
        
        # Check passport number
        if entry.passport_number:
            normalized_passport = self._normalize_document(entry.passport_number)
            if normalized_doc == normalized_passport:
                matches.append({
                    'entry': entry,
                    'match_type': 'EXACT',
                    'score': 1.0,
                    'field': 'passport_number'
                })
        
        # Check national ID
        if entry.national_id:
            normalized_national_id = self._normalize_document(entry.national_id)
            if normalized_doc == normalized_national_id:
                matches.append({
                    'entry': entry,
                    'match_type': 'EXACT',
                    'score': 1.0,
                    'field': 'national_id'
                })
        
        return matches
    
    def _match_dates(self, date, entry: SanctionsEntry) -> List[Dict]:
        """Match dates (birth dates, etc.)"""
        
        matches = []
        
        # Check date of birth
        if entry.date_of_birth and date == entry.date_of_birth:
            matches.append({
                'entry': entry,
                'match_type': 'EXACT',
                'score': 1.0,
                'field': 'date_of_birth'
            })
        
        return matches
    
    def _normalize_name(self, name: str) -> str:
        """Normalize name for comparison"""
        
        if not name:
            return ""
        
        # Convert to uppercase
        normalized = name.upper()
        
        # Remove common prefixes/suffixes
        prefixes = ['MR.', 'MRS.', 'MS.', 'DR.', 'PROF.']
        suffixes = ['JR.', 'SR.', 'III', 'IV']
        
        for prefix in prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):].strip()
        
        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)].strip()
        
        # Remove special characters and extra spaces
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def _normalize_document(self, document: str) -> str:
        """Normalize document number for comparison"""
        
        if not document:
            return ""
        
        # Remove spaces, hyphens, and other separators
        normalized = re.sub(r'[\s\-\.]', '', document.upper())
        
        return normalized
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names"""
        
        if not name1 or not name2:
            return 0.0
        
        # Use SequenceMatcher for basic similarity
        basic_similarity = SequenceMatcher(None, name1, name2).ratio()
        
        # Additional matching techniques
        
        # Token-based matching (order-independent)
        tokens1 = set(name1.split())
        tokens2 = set(name2.split())
        
        if tokens1 and tokens2:
            token_similarity = len(tokens1.intersection(tokens2)) / len(tokens1.union(tokens2))
        else:
            token_similarity = 0.0
        
        # Weighted combination
        final_similarity = (basic_similarity * 0.7) + (token_similarity * 0.3)
        
        return final_similarity
    
    def _determine_match_status(self, matches: List[Dict]) -> str:
        """Determine overall match status from individual matches"""
        
        if not matches:
            return 'NO_MATCH'
        
        # Check for exact matches
        exact_matches = [m for m in matches if m['match_type'] == 'EXACT']
        if exact_matches:
            return 'MATCH'
        
        # Check for potential matches
        potential_matches = [m for m in matches if m['match_type'] == 'POTENTIAL']
        if potential_matches:
            return 'POTENTIAL_MATCH'
        
        # Only fuzzy matches
        return 'POTENTIAL_MATCH'
    
    def review_match(self, match_id: int, reviewer: User, decision: str, notes: str = "") -> SanctionsMatch:
        """
        Review a sanctions match
        
        Args:
            match_id: ID of the SanctionsMatch to review
            reviewer: User performing the review
            decision: Review decision ('CONFIRMED', 'FALSE_POSITIVE', 'NEEDS_INVESTIGATION')
            notes: Review notes
            
        Returns:
            Updated SanctionsMatch instance
        """
        try:
            match = SanctionsMatch.objects.get(id=match_id)
            
            match.review_status = decision
            match.reviewed_by = reviewer
            match.reviewed_at = timezone.now()
            match.review_notes = notes
            match.save()
            
            # Update parent sanctions check if all matches reviewed
            sanctions_check = match.sanctions_check
            self._update_sanctions_check_status(sanctions_check)
            
            logger.info(f"Sanctions match {match_id} reviewed by {reviewer.username}: {decision}")
            
            return match
            
        except SanctionsMatch.DoesNotExist:
            logger.error(f"Sanctions match {match_id} not found")
            raise
    
    def _update_sanctions_check_status(self, sanctions_check: SanctionsCheck):
        """Update sanctions check status based on match reviews"""
        
        matches = sanctions_check.matches.all()
        
        if not matches.exists():
            return
        
        # Check if all matches have been reviewed
        unreviewed_matches = matches.filter(review_status='PENDING')
        if unreviewed_matches.exists():
            return  # Still pending reviews
        
        # Determine final status based on reviews
        confirmed_matches = matches.filter(review_status='CONFIRMED')
        if confirmed_matches.exists():
            sanctions_check.match_status = 'MATCH'
        else:
            sanctions_check.match_status = 'NO_MATCH'
        
        sanctions_check.save()
        
        logger.info(f"Sanctions check {sanctions_check.id} status updated to {sanctions_check.match_status}")


class SanctionsListManagementService:
    """Service for managing sanctions lists and entries"""
    
    def update_sanctions_list(self, list_name: str, entries_data: List[Dict]) -> SanctionsList:
        """
        Update sanctions list with new entries
        
        Args:
            list_name: Name of the sanctions list
            entries_data: List of entry dictionaries
            
        Returns:
            Updated SanctionsList instance
        """
        logger.info(f"Updating sanctions list: {list_name}")
        
        try:
            with transaction.atomic():
                # Get or create sanctions list
                sanctions_list, created = SanctionsList.objects.get_or_create(
                    name=list_name,
                    defaults={
                        'description': f'Sanctions list: {list_name}',
                        'source_url': '',
                        'is_active': True
                    }
                )
                
                # Mark existing entries as inactive
                SanctionsEntry.objects.filter(
                    sanctions_list=sanctions_list
                ).update(is_active=False)
                
                # Add new entries
                entries_created = 0
                for entry_data in entries_data:
                    entry, entry_created = SanctionsEntry.objects.update_or_create(
                        sanctions_list=sanctions_list,
                        primary_name=entry_data.get('primary_name', ''),
                        defaults={
                            'aliases': entry_data.get('aliases', ''),
                            'date_of_birth': entry_data.get('date_of_birth'),
                            'place_of_birth': entry_data.get('place_of_birth', ''),
                            'nationality': entry_data.get('nationality', ''),
                            'passport_number': entry_data.get('passport_number', ''),
                            'national_id': entry_data.get('national_id', ''),
                            'address': entry_data.get('address', ''),
                            'entity_type': entry_data.get('entity_type', 'INDIVIDUAL'),
                            'sanctions_reason': entry_data.get('sanctions_reason', ''),
                            'listing_date': entry_data.get('listing_date'),
                            'is_active': True
                        }
                    )
                    
                    if entry_created:
                        entries_created += 1
                
                # Update list metadata
                sanctions_list.last_updated = timezone.now()
                sanctions_list.total_entries = SanctionsEntry.objects.filter(
                    sanctions_list=sanctions_list,
                    is_active=True
                ).count()
                sanctions_list.save()
                
                logger.info(f"Sanctions list {list_name} updated: {entries_created} new entries, "
                           f"{sanctions_list.total_entries} total active entries")
                
                return sanctions_list
                
        except Exception as e:
            logger.error(f"Error updating sanctions list {list_name}: {str(e)}")
            raise
    
    def get_sanctions_statistics(self) -> Dict:
        """Get statistics about sanctions lists and screening"""
        
        # List statistics
        total_lists = SanctionsList.objects.filter(is_active=True).count()
        total_entries = SanctionsEntry.objects.filter(is_active=True).count()
        
        # Screening statistics
        total_checks = SanctionsCheck.objects.count()
        recent_checks = SanctionsCheck.objects.filter(
            check_date__gte=timezone.now() - timezone.timedelta(days=30)
        ).count()
        
        # Match statistics
        total_matches = SanctionsMatch.objects.count()
        confirmed_matches = SanctionsMatch.objects.filter(review_status='CONFIRMED').count()
        false_positives = SanctionsMatch.objects.filter(review_status='FALSE_POSITIVE').count()
        pending_reviews = SanctionsMatch.objects.filter(review_status='PENDING').count()
        
        return {
            'lists': {
                'total_active_lists': total_lists,
                'total_active_entries': total_entries
            },
            'screening': {
                'total_checks': total_checks,
                'recent_checks_30_days': recent_checks
            },
            'matches': {
                'total_matches': total_matches,
                'confirmed_matches': confirmed_matches,
                'false_positives': false_positives,
                'pending_reviews': pending_reviews
            }
        }

