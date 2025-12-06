"""
Parser module for Business Card Processing API.

Parses OCR text into structured contact data fields.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class ContactData:
    """Structured contact data from a business card.
    
    Attributes:
        name: Full name of the contact
        first_name: First name
        last_name: Last name
        email: Email address
        phone: Phone number(s)
        company: Company/organization name
        title: Job title/position
        website: Website URL
        address: Physical address
        linkedin: LinkedIn profile URL
        twitter: Twitter handle
        raw_text: Original OCR text
        confidence_score: Overall parsing confidence
    """
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: List[str] = field(default_factory=list)
    company: Optional[str] = None
    title: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    linkedin: Optional[str] = None
    twitter: Optional[str] = None
    raw_text: Optional[str] = None
    confidence_score: float = 0.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return asdict(self)
    
    def is_valid(self) -> bool:
        """Check if contact has minimum required fields."""
        return bool(self.name or self.email or self.phone)


class CardDataParser:
    """Parses OCR text into structured contact data.
    
    Uses regex patterns and heuristics to extract contact information
    from business card text.
    """
    
    # Regex patterns for data extraction
    PATTERNS = {
        "email": re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            re.IGNORECASE
        ),
        "phone": re.compile(
            r'(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}|\b\d{10,11}\b'
        ),
        "website": re.compile(
            r'(?:https?://)?(?:www\.)?[a-zA-Z0-9][a-zA-Z0-9-]*\.[a-zA-Z]{2,}(?:/\S*)?',
            re.IGNORECASE
        ),
        "linkedin": re.compile(
            r'(?:linkedin\.com/in/|linkedin:\s*)([a-zA-Z0-9_-]+)',
            re.IGNORECASE
        ),
        "twitter": re.compile(
            r'(?:@|twitter\.com/)([a-zA-Z0-9_]+)',
            re.IGNORECASE
        ),
    }
    
    # Common job titles for detection
    COMMON_TITLES = [
        "ceo", "cto", "cfo", "coo", "cio", "cmo",
        "president", "vice president", "vp",
        "director", "manager", "senior", "junior",
        "engineer", "developer", "designer", "analyst",
        "consultant", "specialist", "coordinator",
        "executive", "officer", "lead", "head",
        "founder", "co-founder", "partner", "owner",
        "sales", "marketing", "hr", "human resources",
        "accountant", "attorney", "lawyer", "physician",
        "professor", "teacher", "researcher"
    ]
    
    # Words that indicate company names
    COMPANY_INDICATORS = [
        "inc", "inc.", "llc", "llp", "ltd", "ltd.",
        "corp", "corp.", "corporation", "company", "co.",
        "group", "partners", "solutions", "services",
        "technologies", "tech", "systems", "consulting",
        "industries", "enterprises", "associates"
    ]
    
    def __init__(self) -> None:
        """Initialize the CardDataParser."""
        logger.info("CardDataParser initialized")
    
    def parse(
        self, 
        text: str, 
        ocr_results: Optional[List[Tuple[str, float]]] = None
    ) -> ContactData:
        """Parse text into structured contact data.
        
        Args:
            text: Raw text from OCR
            ocr_results: Optional list of (text, confidence) tuples
            
        Returns:
            ContactData object with extracted fields
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for parsing")
            return ContactData(raw_text=text, confidence_score=0.0)
        
        logger.debug(f"Parsing text: {text[:100]}...")
        
        contact = ContactData(raw_text=text)
        
        # Extract structured fields
        contact.email = self._extract_email(text)
        contact.phone = self._extract_phones(text)
        contact.website = self._extract_website(text)
        contact.linkedin = self._extract_linkedin(text)
        contact.twitter = self._extract_twitter(text)
        
        # Parse lines for name, title, company, address
        lines = self._clean_lines(text)
        
        contact.name = self._extract_name(lines, text)
        if contact.name:
            name_parts = self._split_name(contact.name)
            contact.first_name = name_parts.get("first_name")
            contact.last_name = name_parts.get("last_name")
        
        contact.title = self._extract_title(lines)
        contact.company = self._extract_company(lines, contact.email)
        contact.address = self._extract_address(lines)
        
        # Calculate confidence score
        contact.confidence_score = self._calculate_confidence(contact, ocr_results)
        
        logger.info(
            f"Parsed contact: {contact.name or 'Unknown'}, "
            f"confidence: {contact.confidence_score:.2f}"
        )
        
        return contact
    
    def _extract_email(self, text: str) -> Optional[str]:
        """Extract email address from text."""
        match = self.PATTERNS["email"].search(text)
        if match:
            email = match.group().lower()
            logger.debug(f"Found email: {email}")
            return email
        return None
    
    def _extract_phones(self, text: str) -> List[str]:
        """Extract all phone numbers from text."""
        phones = []
        for match in self.PATTERNS["phone"].finditer(text):
            phone = self._normalize_phone(match.group())
            if phone and phone not in phones:
                phones.append(phone)
        
        if phones:
            logger.debug(f"Found phones: {phones}")
        return phones
    
    def _normalize_phone(self, phone: str) -> Optional[str]:
        """Normalize phone number format."""
        # Remove all non-digit characters except +
        digits = re.sub(r'[^\d+]', '', phone)
        
        # Basic validation - should have at least 10 digits
        digit_count = len(re.sub(r'\D', '', digits))
        if digit_count < 10:
            return None
        
        return digits
    
    def _extract_website(self, text: str) -> Optional[str]:
        """Extract website URL from text."""
        # Skip email domains
        email = self._extract_email(text)
        email_domain = email.split('@')[1] if email and '@' in email else None
        
        for match in self.PATTERNS["website"].finditer(text):
            url = match.group().lower()
            
            # Skip if it's the email domain or social media
            if email_domain and email_domain in url:
                continue
            if any(social in url for social in ['linkedin.com', 'twitter.com', 'facebook.com']):
                continue
            
            # Add https if no protocol
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            logger.debug(f"Found website: {url}")
            return url
        
        return None
    
    def _extract_linkedin(self, text: str) -> Optional[str]:
        """Extract LinkedIn profile URL."""
        match = self.PATTERNS["linkedin"].search(text)
        if match:
            username = match.group(1)
            url = f"https://linkedin.com/in/{username}"
            logger.debug(f"Found LinkedIn: {url}")
            return url
        return None
    
    def _extract_twitter(self, text: str) -> Optional[str]:
        """Extract Twitter handle."""
        match = self.PATTERNS["twitter"].search(text)
        if match:
            handle = f"@{match.group(1)}"
            logger.debug(f"Found Twitter: {handle}")
            return handle
        return None
    
    def _clean_lines(self, text: str) -> List[str]:
        """Clean and split text into lines."""
        lines = []
        for line in text.split('\n'):
            cleaned = line.strip()
            if cleaned and len(cleaned) > 1:
                lines.append(cleaned)
        return lines
    
    def _extract_name(self, lines: List[str], full_text: str) -> Optional[str]:
        """Extract person's name from text lines.
        
        Heuristics:
        - Usually on first or second line
        - Not an email, phone, or URL
        - Usually 2-4 words
        - Contains mostly letters
        """
        candidates = []
        
        for i, line in enumerate(lines[:5]):  # Check first 5 lines
            # Skip if it contains contact info patterns
            if self.PATTERNS["email"].search(line):
                continue
            if self.PATTERNS["phone"].search(line):
                continue
            if any(indicator in line.lower() for indicator in self.COMPANY_INDICATORS):
                continue
            
            # Check if it looks like a name
            words = line.split()
            if 2 <= len(words) <= 4:
                # Check if words are mostly alphabetic
                alpha_ratio = sum(1 for w in words if w.replace('.', '').isalpha()) / len(words)
                if alpha_ratio >= 0.8:
                    # Score based on position (earlier = better) and length
                    score = (5 - i) + (1 if len(words) == 2 else 0)
                    candidates.append((line, score))
        
        if candidates:
            # Sort by score descending
            candidates.sort(key=lambda x: x[1], reverse=True)
            name = candidates[0][0]
            logger.debug(f"Extracted name: {name}")
            return name
        
        return None
    
    def _split_name(self, full_name: str) -> Dict[str, Optional[str]]:
        """Split full name into first and last name."""
        parts = full_name.strip().split()
        
        if len(parts) == 0:
            return {"first_name": None, "last_name": None}
        elif len(parts) == 1:
            return {"first_name": parts[0], "last_name": None}
        else:
            return {"first_name": parts[0], "last_name": " ".join(parts[1:])}
    
    def _extract_title(self, lines: List[str]) -> Optional[str]:
        """Extract job title from text lines."""
        for line in lines:
            line_lower = line.lower()
            
            # Check for common title keywords
            for title in self.COMMON_TITLES:
                if title in line_lower:
                    # This line likely contains a title
                    logger.debug(f"Extracted title: {line}")
                    return line
        
        return None
    
    def _extract_company(
        self, 
        lines: List[str], 
        email: Optional[str]
    ) -> Optional[str]:
        """Extract company name from text lines."""
        # Try to infer from email domain
        if email and '@' in email:
            domain = email.split('@')[1]
            domain_name = domain.split('.')[0]
            if domain_name.lower() not in ['gmail', 'yahoo', 'hotmail', 'outlook', 'aol']:
                # Could be company domain
                company_hint = domain_name.title()
        else:
            company_hint = None
        
        # Look for lines with company indicators
        for line in lines:
            line_lower = line.lower()
            for indicator in self.COMPANY_INDICATORS:
                if indicator in line_lower:
                    logger.debug(f"Extracted company: {line}")
                    return line
        
        # If we have a hint from email, use it
        if company_hint:
            logger.debug(f"Inferred company from email: {company_hint}")
            return company_hint
        
        return None
    
    def _extract_address(self, lines: List[str]) -> Optional[str]:
        """Extract physical address from text lines."""
        address_patterns = [
            r'\d+\s+[A-Za-z]',  # Street number followed by name
            r'[A-Za-z]+,?\s*[A-Z]{2}\s*\d{5}',  # City, State ZIP
            r'suite|floor|building|bldg|apt|unit',  # Address keywords
        ]
        
        address_lines = []
        
        for line in lines:
            line_lower = line.lower()
            
            # Skip if it's clearly not an address
            if self.PATTERNS["email"].search(line):
                continue
            if 'linkedin' in line_lower or 'twitter' in line_lower:
                continue
            
            # Check for address patterns
            for pattern in address_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    address_lines.append(line)
                    break
        
        if address_lines:
            address = ", ".join(address_lines)
            logger.debug(f"Extracted address: {address}")
            return address
        
        return None
    
    def _calculate_confidence(
        self, 
        contact: ContactData,
        ocr_results: Optional[List[Tuple[str, float]]] = None
    ) -> float:
        """Calculate overall confidence score for parsed data."""
        score = 0.0
        max_score = 0.0
        
        # Field weights
        weights = {
            "name": 0.25,
            "email": 0.25,
            "phone": 0.15,
            "company": 0.15,
            "title": 0.10,
            "website": 0.05,
            "address": 0.05
        }
        
        for field_name, weight in weights.items():
            max_score += weight
            value = getattr(contact, field_name, None)
            
            if value:
                if isinstance(value, list) and len(value) > 0:
                    score += weight
                elif isinstance(value, str) and value.strip():
                    score += weight
        
        # Factor in OCR confidence if available
        if ocr_results:
            ocr_confidence = sum(conf for _, conf in ocr_results) / len(ocr_results)
            final_score = (score / max_score) * 0.7 + ocr_confidence * 0.3
        else:
            final_score = score / max_score if max_score > 0 else 0.0
        
        return round(final_score, 4)
    
    def parse_batch(
        self, 
        texts: List[str]
    ) -> List[ContactData]:
        """Parse multiple texts into contact data.
        
        Args:
            texts: List of OCR texts to parse
            
        Returns:
            List of ContactData objects
        """
        results = []
        for i, text in enumerate(texts):
            try:
                contact = self.parse(text)
                results.append(contact)
            except Exception as e:
                logger.error(f"Error parsing text {i}: {str(e)}")
                results.append(ContactData(raw_text=text, confidence_score=0.0))
        
        return results
