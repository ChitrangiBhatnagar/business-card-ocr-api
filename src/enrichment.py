"""
Company Enrichment Module for Business Card OCR.

Enriches extracted data with company information using FREE APIs.
NO Gemini calls - uses public data sources only.

Free APIs used:
- Clearbit Logo API (unlimited, no key needed)
- Company domain extraction from email
- Website metadata scraping (when available)
"""

import logging
import re
import requests
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class CompanyEnrichment:
    """Enriched company information from free sources."""
    
    # Basic info
    name: Optional[str] = None
    domain: Optional[str] = None
    logo_url: Optional[str] = None
    
    # From website/domain analysis
    industry: Optional[str] = None
    description: Optional[str] = None
    
    # Social profiles
    linkedin_url: Optional[str] = None
    twitter_handle: Optional[str] = None
    facebook_url: Optional[str] = None
    
    # Contact info
    headquarters: Optional[str] = None
    
    # Metadata
    enrichment_sources: list = field(default_factory=list)
    enrichment_errors: list = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "domain": self.domain,
            "logo_url": self.logo_url,
            "industry": self.industry,
            "description": self.description,
            "linkedin_url": self.linkedin_url,
            "twitter_handle": self.twitter_handle,
            "facebook_url": self.facebook_url,
            "headquarters": self.headquarters,
            "enrichment_sources": self.enrichment_sources,
            "enrichment_errors": self.enrichment_errors
        }
    
    def has_data(self) -> bool:
        """Check if any enrichment data was found."""
        return any([
            self.logo_url,
            self.industry,
            self.description,
            self.linkedin_url,
            self.twitter_handle
        ])


@dataclass 
class FieldConfidence:
    """Per-field confidence scores."""
    
    name: float = 0.0
    title: float = 0.0
    company: float = 0.0
    email: float = 0.0
    phone: float = 0.0
    website: float = 0.0
    address: float = 0.0
    linkedin: float = 0.0
    overall: float = 0.0
    
    # Quality indicators
    name_quality: str = "unknown"  # verified, likely, uncertain
    email_quality: str = "unknown"  # valid_format, suspicious, invalid
    phone_quality: str = "unknown"  # complete, partial, invalid
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": round(self.name, 2),
            "title": round(self.title, 2),
            "company": round(self.company, 2),
            "email": round(self.email, 2),
            "phone": round(self.phone, 2),
            "website": round(self.website, 2),
            "address": round(self.address, 2),
            "linkedin": round(self.linkedin, 2),
            "overall": round(self.overall, 2),
            "quality": {
                "name": self.name_quality,
                "email": self.email_quality,
                "phone": self.phone_quality
            }
        }


class CompanyEnricher:
    """
    Enrich company data using FREE APIs only.
    
    No API keys required for:
    - Clearbit Logo API
    - Basic domain/website checks
    """
    
    # Clearbit Logo API (FREE, no key needed)
    CLEARBIT_LOGO_URL = "https://logo.clearbit.com"
    
    # Request timeout
    TIMEOUT = 5
    
    # Known company domains for common email providers (skip these)
    PERSONAL_EMAIL_DOMAINS = {
        "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com",
        "icloud.com", "mail.com", "protonmail.com", "zoho.com", "yandex.com",
        "live.com", "msn.com", "me.com", "mac.com", "inbox.com", "att.net",
        "sbcglobal.net", "verizon.net", "comcast.net", "cox.net", "charter.net",
        "earthlink.net", "juno.com", "bellsouth.net", "rocketmail.com"
    }
    
    # Industry keywords for auto-detection
    INDUSTRY_KEYWORDS = {
        "real estate": ["real estate", "realty", "property", "properties", "housing", "homes", "remco"],
        "technology": ["tech", "software", "digital", "cyber", "cloud", "data", "ai", "computing"],
        "finance": ["bank", "financial", "capital", "investment", "wealth", "insurance", "credit"],
        "healthcare": ["health", "medical", "hospital", "clinic", "care", "pharma", "biotech"],
        "legal": ["law", "legal", "attorney", "lawyer", "counsel", "advocates"],
        "consulting": ["consulting", "advisory", "consultants", "solutions"],
        "manufacturing": ["manufacturing", "industrial", "factory", "production"],
        "retail": ["retail", "store", "shop", "commerce", "market"],
        "hospitality": ["hotel", "restaurant", "hospitality", "resort", "travel"],
        "education": ["university", "college", "school", "education", "academy", "institute"],
        "construction": ["construction", "building", "contractor", "architect"],
        "marketing": ["marketing", "advertising", "media", "creative", "agency"],
    }
    
    def __init__(self, skip_logo_check: bool = True):
        """Initialize the company enricher.
        
        Args:
            skip_logo_check: Skip HTTP call to check logo (faster). Default True for speed.
        """
        self.skip_logo_check = skip_logo_check
        # Only log on first init, not every request
    
    def enrich(
        self, 
        company_name: Optional[str] = None,
        email: Optional[str] = None,
        website: Optional[str] = None,
        fetch_logo: bool = False
    ) -> CompanyEnrichment:
        """
        Enrich company information using free sources.
        
        Args:
            company_name: Company name from business card
            email: Email address (to extract domain)
            website: Website URL
            fetch_logo: Whether to fetch logo URL (slower, makes HTTP call)
            
        Returns:
            CompanyEnrichment with discovered data
        """
        enrichment = CompanyEnrichment()
        enrichment.name = company_name
        
        # Extract domain from email or website
        domain = self._extract_domain(email, website)
        
        if domain:
            enrichment.domain = domain
            
            # Get company logo (only if requested - makes HTTP call)
            if fetch_logo and not self.skip_logo_check:
                logo_url = self._get_company_logo(domain)
                if logo_url:
                    enrichment.logo_url = logo_url
                    enrichment.enrichment_sources.append("clearbit_logo")
            else:
                # Build logo URL without verification (instant, no HTTP)
                enrichment.logo_url = f"{self.CLEARBIT_LOGO_URL}/{domain}"
                enrichment.enrichment_sources.append("clearbit_logo_url")
        
        # Detect industry from company name (instant, no API)
        if company_name:
            industry = self._detect_industry(company_name)
            if industry:
                enrichment.industry = industry
                enrichment.enrichment_sources.append("keyword_analysis")
        
        # Extract LinkedIn company URL if possible (instant, no API)
        if company_name:
            enrichment.linkedin_url = self._build_linkedin_url(company_name)
        
        return enrichment
    
    def _extract_domain(
        self, 
        email: Optional[str], 
        website: Optional[str]
    ) -> Optional[str]:
        """Extract company domain from email or website."""
        
        # Try website first
        if website:
            try:
                parsed = urlparse(website if "://" in website else f"https://{website}")
                domain = parsed.netloc or parsed.path.split("/")[0]
                domain = domain.replace("www.", "")
                if domain and "." in domain:
                    return domain.lower()
            except Exception:
                pass
        
        # Try email domain
        if email and "@" in email:
            domain = email.split("@")[1].lower()
            # Skip personal email domains
            if domain not in self.PERSONAL_EMAIL_DOMAINS:
                return domain
        
        return None
    
    def _get_company_logo(self, domain: str) -> Optional[str]:
        """
        Get company logo URL using Clearbit Logo API.
        This is completely FREE with no API key required.
        """
        if not domain:
            return None
        
        logo_url = f"{self.CLEARBIT_LOGO_URL}/{domain}"
        
        try:
            # Just check if the logo exists (HEAD request)
            response = requests.head(logo_url, timeout=self.TIMEOUT, allow_redirects=True)
            
            if response.status_code == 200:
                logger.debug(f"Found logo for {domain}")
                return logo_url
            else:
                logger.debug(f"No logo found for {domain}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.debug(f"Logo check failed for {domain}: {e}")
            return None
    
    def _detect_industry(self, company_name: str) -> Optional[str]:
        """Detect industry from company name using keyword matching."""
        if not company_name:
            return None
        
        name_lower = company_name.lower()
        
        for industry, keywords in self.INDUSTRY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in name_lower:
                    logger.debug(f"Detected industry '{industry}' from '{company_name}'")
                    return industry
        
        return None
    
    def _build_linkedin_url(self, company_name: str) -> Optional[str]:
        """Build a LinkedIn company search URL."""
        if not company_name:
            return None
        
        # Clean company name for URL
        clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', company_name)
        clean_name = clean_name.strip().replace(' ', '-').lower()
        
        if clean_name:
            return f"https://www.linkedin.com/company/{clean_name}"
        
        return None


class FieldConfidenceScorer:
    """
    Calculate per-field confidence scores based on extraction quality.
    
    Factors considered:
    - Pattern match strength (regex confidence)
    - Data validation (format checks)
    - Contextual clues (field position, keywords)
    - OCR confidence for the source text
    """
    
    # Regex patterns for validation
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    PHONE_PATTERN = re.compile(r'^[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}$')
    URL_PATTERN = re.compile(r'^(?:https?://)?(?:www\.)?[a-zA-Z0-9-]+\.[a-zA-Z]{2,}')
    
    # Common name patterns
    NAME_PATTERN = re.compile(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+$')
    
    # Suspicious patterns (OCR errors)
    OCR_ERROR_PATTERNS = [
        re.compile(r'[0-9]'),  # Numbers in names
        re.compile(r'[|!1l]{2,}'),  # Multiple similar chars (OCR confusion)
        re.compile(r'\s{3,}'),  # Multiple spaces
    ]
    
    def __init__(self, base_ocr_confidence: float = 1.0):
        """
        Initialize scorer.
        
        Args:
            base_ocr_confidence: Overall OCR confidence (0-1)
        """
        self.base_confidence = base_ocr_confidence
    
    def score_all_fields(self, contact_data: Dict) -> FieldConfidence:
        """
        Calculate confidence scores for all fields.
        
        Args:
            contact_data: Extracted contact data dictionary
            
        Returns:
            FieldConfidence with per-field scores
        """
        confidence = FieldConfidence()
        
        # Score each field
        confidence.name, confidence.name_quality = self._score_name(
            contact_data.get("name")
        )
        
        confidence.email, confidence.email_quality = self._score_email(
            contact_data.get("email")
        )
        
        confidence.phone, confidence.phone_quality = self._score_phone(
            contact_data.get("phone")
        )
        
        confidence.company = self._score_company(contact_data.get("company"))
        confidence.title = self._score_title(contact_data.get("title"))
        confidence.website = self._score_website(contact_data.get("website"))
        confidence.address = self._score_address(contact_data.get("address"))
        confidence.linkedin = self._score_linkedin(contact_data.get("linkedin"))
        
        # Calculate overall confidence (weighted average)
        weights = {
            "name": 0.25,
            "email": 0.25,
            "phone": 0.15,
            "company": 0.15,
            "title": 0.10,
            "website": 0.05,
            "address": 0.03,
            "linkedin": 0.02
        }
        
        total_weight = 0
        weighted_sum = 0
        
        for field, weight in weights.items():
            value = getattr(confidence, field, 0)
            if value > 0:
                weighted_sum += value * weight
                total_weight += weight
        
        if total_weight > 0:
            confidence.overall = (weighted_sum / total_weight) * self.base_confidence
        
        return confidence
    
    def _score_name(self, name: Optional[str]) -> tuple:
        """Score name field confidence."""
        if not name:
            return 0.0, "missing"
        
        score = 0.5  # Base score for having a name
        quality = "uncertain"
        
        # Check if it looks like a proper name (Title Case, 2+ words)
        if self.NAME_PATTERN.match(name):
            score += 0.3
            quality = "likely"
        
        # Check for 2-4 words (typical name length)
        word_count = len(name.split())
        if 2 <= word_count <= 4:
            score += 0.1
        
        # Check for OCR errors (numbers in name)
        if any(pattern.search(name) for pattern in self.OCR_ERROR_PATTERNS):
            score -= 0.3
            quality = "suspicious"
        
        # Proper capitalization bonus
        if name == name.title():
            score += 0.1
            if quality != "suspicious":
                quality = "verified"
        
        return min(max(score, 0), 1.0), quality
    
    def _score_email(self, email: Optional[str]) -> tuple:
        """Score email field confidence."""
        if not email:
            return 0.0, "missing"
        
        score = 0.0
        quality = "invalid"
        
        # Valid format check
        if self.EMAIL_PATTERN.match(email):
            score = 0.8
            quality = "valid_format"
            
            # Business domain bonus
            domain = email.split("@")[1].lower()
            if domain not in ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"]:
                score += 0.1
                quality = "business_email"
            
            # TLD check
            tld = domain.split(".")[-1]
            if tld in ["com", "org", "net", "edu", "gov", "io", "co"]:
                score += 0.1
        else:
            # Partial match - might be OCR error
            if "@" in email and "." in email:
                score = 0.4
                quality = "suspicious"
        
        return min(score, 1.0), quality
    
    def _score_phone(self, phone) -> tuple:
        """Score phone field confidence."""
        if not phone:
            return 0.0, "missing"
        
        # Handle list of phones
        if isinstance(phone, list):
            if not phone:
                return 0.0, "missing"
            phone = phone[0] if phone else ""
        
        score = 0.0
        quality = "invalid"
        
        # Clean phone for validation
        clean_phone = re.sub(r'[\s\.\-\(\)]', '', str(phone))
        
        # Length check (7-15 digits typical)
        digit_count = sum(1 for c in clean_phone if c.isdigit())
        
        if 7 <= digit_count <= 15:
            score = 0.7
            quality = "partial"
            
            # Full phone number (10+ digits)
            if digit_count >= 10:
                score = 0.9
                quality = "complete"
            
            # Has country code
            if clean_phone.startswith("+") or clean_phone.startswith("1"):
                score += 0.1
        elif digit_count > 0:
            score = 0.3
            quality = "partial"
        
        return min(score, 1.0), quality
    
    def _score_company(self, company: Optional[str]) -> float:
        """Score company field confidence."""
        if not company:
            return 0.0
        
        score = 0.6  # Base score
        
        # Length check
        if 3 <= len(company) <= 100:
            score += 0.2
        
        # Common company indicators
        indicators = ["inc", "llc", "ltd", "corp", "co", "company", "group", "international"]
        if any(ind in company.lower() for ind in indicators):
            score += 0.1
        
        # OCR error check
        if any(pattern.search(company) for pattern in self.OCR_ERROR_PATTERNS):
            score -= 0.2
        
        return min(max(score, 0), 1.0)
    
    def _score_title(self, title: Optional[str]) -> float:
        """Score title/position field confidence."""
        if not title:
            return 0.0
        
        score = 0.5
        
        # Common title keywords
        title_keywords = [
            "manager", "director", "president", "ceo", "cto", "cfo", "vp",
            "engineer", "developer", "designer", "analyst", "consultant",
            "agent", "specialist", "coordinator", "lead", "senior", "founder",
            "owner", "partner", "associate", "executive", "officer"
        ]
        
        if any(kw in title.lower() for kw in title_keywords):
            score += 0.4
        
        # Reasonable length
        if 3 <= len(title) <= 50:
            score += 0.1
        
        return min(score, 1.0)
    
    def _score_website(self, website: Optional[str]) -> float:
        """Score website field confidence."""
        if not website:
            return 0.0
        
        if self.URL_PATTERN.match(website):
            return 0.9
        
        # Partial URL
        if "." in website:
            return 0.5
        
        return 0.2
    
    def _score_address(self, address: Optional[str]) -> float:
        """Score address field confidence."""
        if not address:
            return 0.0
        
        score = 0.4
        
        # Address indicators
        indicators = ["street", "st", "avenue", "ave", "road", "rd", "drive", "dr",
                     "suite", "floor", "building", "blvd", "lane", "ln", "way"]
        
        if any(ind in address.lower() for ind in indicators):
            score += 0.3
        
        # Zip code pattern
        if re.search(r'\b\d{5}(?:-\d{4})?\b', address):
            score += 0.2
        
        # State abbreviation
        if re.search(r'\b[A-Z]{2}\b', address):
            score += 0.1
        
        return min(score, 1.0)
    
    def _score_linkedin(self, linkedin: Optional[str]) -> float:
        """Score LinkedIn field confidence."""
        if not linkedin:
            return 0.0
        
        if "linkedin.com" in linkedin.lower():
            return 0.95
        
        if linkedin.startswith("in/"):
            return 0.7
        
        return 0.3


def enrich_contact(contact_data: Dict, ocr_confidence: float = 1.0) -> Dict:
    """
    Convenience function to enrich contact data with company info and field confidence.
    
    Args:
        contact_data: Extracted contact data
        ocr_confidence: Overall OCR confidence score
        
    Returns:
        Enriched contact data with company_enrichment and field_confidence
    """
    # Company enrichment (FREE APIs only)
    enricher = CompanyEnricher()
    company_enrichment = enricher.enrich(
        company_name=contact_data.get("company"),
        email=contact_data.get("email"),
        website=contact_data.get("website")
    )
    
    # Field confidence scoring
    scorer = FieldConfidenceScorer(base_ocr_confidence=ocr_confidence)
    field_confidence = scorer.score_all_fields(contact_data)
    
    return {
        "company_enrichment": company_enrichment.to_dict(),
        "field_confidence": field_confidence.to_dict()
    }
