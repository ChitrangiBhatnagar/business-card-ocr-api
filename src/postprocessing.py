# src/postprocessing.py
"""
Enhanced post-processing for parsed contact data.
Cleans and structures the data after OCR and basic parsing.
"""
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class StructuredContact:
    """Structured contact data after post-processing."""
    name: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    phone: List[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    confidence: float = 0.0
    
    def __post_init__(self):
        if self.phone is None:
            self.phone = []


class ContactPostProcessor:
    """Post-processes parsed contact data to structure it properly."""
    
    # Job title patterns (common titles)
    TITLE_PATTERNS = [
        r'\b(?:Senior|Junior|Lead|Chief|Head|Principal)\s+\w+\s*\w*\b',
        r'\b(?:Manager|Director|Engineer|Developer|Designer|Analyst|Specialist|Consultant)\b',
        r'\b(?:CEO|CTO|CFO|COO|VP|President|Founder|Partner)\b',
        r'\bCommunications Manager\b',
        r'\bReal Estate Agent\b',
        r'\bSoftware Engineer\b',
        r'\bMarketing Manager\b',
        r'\bSales Representative\b'
    ]
    
    # Company indicators
    COMPANY_INDICATORS = [
        'Inc', 'LLC', 'Ltd', 'Corp', 'Corporation', 'Company', 'Co',
        'Group', 'Technologies', 'Technology', 'Solutions', 'Systems',
        '& Co', 'and Co', 'Associates', 'Partners'
    ]
    
    # Address patterns
    ADDRESS_PATTERNS = [
        r'\b\d+\s+\w+\s+(?:Street|St|Road|Rd|Avenue|Ave|Boulevard|Blvd)\b',
        r'\b(?:Suite|Ste|Apt|Apartment|Floor|Fl)\s+\w+\b',
        r'\b(?:City|State|Province|Country|Zip|Postal)\b',
        r'\b\d{5}(?:-\d{4})?\b'  # ZIP codes
    ]
    
    def __init__(self):
        # Compile regex patterns
        self.title_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.TITLE_PATTERNS]
        self.address_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.ADDRESS_PATTERNS]
    
    def process(self, raw_contact: Dict) -> StructuredContact:
        """
        Process raw contact data into structured format.
        
        Args:
            raw_contact: Raw contact dictionary from parser
            
        Returns:
            StructuredContact object
        """
        # Initialize structured contact
        contact = StructuredContact()
        
        # Get raw text for analysis
        raw_text = raw_contact.get('raw_text', '') if isinstance(raw_contact, dict) else ''
        if not raw_text and hasattr(raw_contact, 'raw_text'):
            raw_text = raw_contact.raw_text
        
        # If raw_text is empty, use the company field (which seems to contain everything)
        if not raw_text and 'company' in raw_contact and raw_contact['company']:
            raw_text = raw_contact['company']
        
        # Split into lines for analysis
        lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
        
        # Extract components
        self._extract_from_lines(lines, contact, raw_contact)
        
        # Clean and validate
        self._clean_and_validate(contact)
        
        # Calculate confidence
        contact.confidence = self._calculate_confidence(contact)
        
        return contact
    
    def _extract_from_lines(self, lines: List[str], contact: StructuredContact, raw_contact: Dict):
        """Extract structured data from text lines."""
        
        # Use existing parsed data
        if isinstance(raw_contact, dict):
            contact.name = raw_contact.get('name')
            contact.email = raw_contact.get('email')
            contact.phone = raw_contact.get('phone', [])
            if isinstance(contact.phone, str):
                contact.phone = [contact.phone] if contact.phone else []
            contact.website = raw_contact.get('website')
            contact.title = raw_contact.get('title')
            
            # For company, only use if it's reasonable length
            raw_company = raw_contact.get('company', '')
            if raw_company and len(raw_company) < 100:
                contact.company = raw_company
            else:
                # If company is too long, it's corrupted - try to extract from lines
                contact.company = self._extract_company_from_lines(lines)
    
    def _extract_company_from_lines(self, lines: List[str]) -> Optional[str]:
        """Extract company name from text lines."""
        company_indicators = [
            'inc', 'llc', 'ltd', 'corp', 'corporation', 'company', 'co',
            'group', 'technologies', 'technology', 'solutions', 'systems',
            'associates', 'partners', 'enterprises', 'consulting'
        ]
        
        for line in lines:
            lower = line.lower()
            # Skip lines with email/phone/website
            if '@' in line or 'www' in lower or 'http' in lower:
                continue
            # Skip lines that are mostly numbers (phone/address)
            if sum(c.isdigit() for c in line) > len(line) * 0.3:
                continue
            # Check for company indicators
            if any(ind in lower for ind in company_indicators):
                return line.strip()
        
        # Fallback: look for all-caps lines (often company names)
        for line in lines[:5]:
            if line.isupper() and len(line) > 3 and len(line) < 50:
                return line.strip()
        
        return None
    
    def _clean_and_validate(self, contact: StructuredContact):
        """Clean and validate extracted data."""
        
        # Clean name
        if contact.name:
            # Remove titles from name
            for pattern in self.TITLE_PATTERNS:
                if re.search(pattern, contact.name, re.IGNORECASE):
                    contact.name = re.sub(pattern, '', contact.name, flags=re.IGNORECASE).strip()
        
        # Clean company
        if contact.company:
            # Remove email/phone/website from company
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            phone_pattern = r'(\+?\d{1,3}[\s\-]?)?(\(?\d{3}\)?[\s\-]?)?\d{3}[\s\-]?\d{4}'
            url_pattern = r'(https?://)?(www\.)?[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}'
            
            contact.company = re.sub(email_pattern, '', contact.company)
            contact.company = re.sub(phone_pattern, '', contact.company)
            contact.company = re.sub(url_pattern, '', contact.company)
            contact.company = ' '.join(contact.company.split())  # Remove extra spaces
        
        # Clean phone numbers
        cleaned_phones = []
        for phone in contact.phone:
            # Remove non-numeric except +, -, (, )
            cleaned = re.sub(r'[^\d\+\-\(\)\s]', '', phone)
            if cleaned:
                cleaned_phones.append(cleaned)
        contact.phone = cleaned_phones
    
    def _calculate_confidence(self, contact: StructuredContact) -> float:
        """Calculate confidence score based on extracted fields."""
        fields = [
            contact.name,
            contact.email,
            contact.phone,
            contact.company,
            contact.title,
            contact.website
        ]
        
        # Count non-empty fields
        valid_count = sum(1 for field in fields if field)
        if isinstance(contact.phone, list):
            valid_count += len(contact.phone) - 1  # Phone list counts as one
        
        return min(valid_count / 6, 1.0)


# Helper functions
def postprocess_contact(raw_contact: Dict) -> Dict:
    """
    Convenience function to post-process contact data.
    
    Args:
        raw_contact: Raw contact dictionary from parser
        
    Returns:
        Cleaned and structured contact dictionary
    """
    processor = ContactPostProcessor()
    structured = processor.process(raw_contact)
    
    return {
    'name': structured.name,
    'title': structured.title,
    'company': structured.company,
    'email': structured.email,
    'phone': structured.phone,
    'website': structured.website,
    'address': structured.address,
    'confidence_score': structured.confidence
}