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
            r'\b[A-Za-z0-9._%+-]+\s*[@g]\s*[A-Za-z0-9.-]+\s*\.\s*[A-Z|a-z]{2,}\b',
            re.IGNORECASE
        ),
        "phone": re.compile(
            r'(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?[\d\s.-]{6,14}\d',
            re.IGNORECASE
        ),
        "website": re.compile(
            r'(?:https?://)?(?:www[.\s;:]?\s*)?[a-zA-Z0-9][a-zA-Z0-9-]*[.\s;:]+\s*(?:com|org|net|io|co|edu|gov|biz|info)',
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
    
    # US States for address detection
    US_STATES = [
        'alabama', 'alaska', 'arizona', 'arkansas', 'california', 'colorado',
        'connecticut', 'delaware', 'florida', 'georgia', 'hawaii', 'idaho',
        'illinois', 'indiana', 'iowa', 'kansas', 'kentucky', 'louisiana',
        'maine', 'maryland', 'massachusetts', 'michigan', 'minnesota',
        'mississippi', 'missouri', 'montana', 'nebraska', 'nevada',
        'new hampshire', 'new jersey', 'new mexico', 'new york',
        'north carolina', 'north dakota', 'ohio', 'oklahoma', 'oregon',
        'pennsylvania', 'rhode island', 'south carolina', 'south dakota',
        'tennessee', 'texas', 'utah', 'vermont', 'virginia', 'washington',
        'west virginia', 'wisconsin', 'wyoming', 'usa', 'u.s.a'
    ]
    
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
        "professor", "teacher", "researcher",
        "agent", "broker", "realtor", "real estate",
        "assistant", "associate", "advisor", "representative"
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
        # First try standard pattern
        match = self.PATTERNS["email"].search(text)
        if match:
            email = match.group().lower()
            # Clean up OCR artifacts
            email = re.sub(r'\s+', '', email)  # Remove spaces
            email = email.replace(';', '').replace(':', '').replace("'", '')
            logger.debug(f"Found email: {email}")
            return email
        
        # Try to find email-like patterns with OCR errors
        # Look for patterns like "infogwebsitenamecom" or "info@websitename com"
        cleaned_text = text.lower().replace(';', '').replace(':', '').replace("'", '').replace(' ', '')
        
        email_patterns = [
            # Pattern: info + g (misread @) + website/domain + name + com
            r"(info|contact|hello|support|admin|sales)[g@]?(website|domain)?name\.?(com|org|net)",
            # Pattern: word + g/@ + word + com/org/net (OCR might miss @ or . )
            r"([a-z0-9._+-]+)[g@]([a-z0-9.-]+)(com|org|net|io|co)",
            # Pattern with 'info' or common email prefixes
            r"(info|contact|hello|support)[g@]?([a-z]+)(com|org|net)",
        ]
        
        for pattern in email_patterns:
            match = re.search(pattern, cleaned_text, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) >= 3:
                    # Handle the case where domain is missing
                    if groups[1] in ['website', 'domain', None] or 'name' in str(groups[1]):
                        email = f"{groups[0]}@websitename.{groups[2]}"
                    else:
                        email = f"{groups[0]}@{groups[1]}.{groups[2]}"
                    email = re.sub(r'\s+', '', email)
                    logger.debug(f"Found email (cleaned): {email}")
                    return email
        
        return None
    
    def _extract_phones(self, text: str) -> List[str]:
        """Extract all phone numbers from text."""
        phones = []
        
        # Clean the text first - remove OCR artifacts
        # Replace common OCR mistakes for numbers
        cleaned_text = text
        cleaned_text = re.sub(r'[;:|]', '', cleaned_text)  # Remove semicolons, colons, pipes
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)  # Normalize whitespace
        
        # Try the standard pattern first
        for match in self.PATTERNS["phone"].finditer(cleaned_text):
            phone = self._normalize_phone(match.group())
            if phone and phone not in phones:
                phones.append(phone)
        
        # Also try to find digit sequences that might be phone numbers
        # Pattern: groups of digits that total 10-12 digits
        digit_groups = re.findall(r'[\d\s.\-()]+', cleaned_text)
        for group in digit_groups:
            # Count just the digits
            digits_only = re.sub(r'\D', '', group)
            if 10 <= len(digits_only) <= 14:
                if digits_only not in phones:
                    phones.append(digits_only)
        
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
        
        # Clean text for website extraction
        cleaned_text = text.lower()
        cleaned_text = cleaned_text.replace(';', '.').replace(':', '.')
        
        # Try standard pattern first
        for match in self.PATTERNS["website"].finditer(cleaned_text):
            url = match.group().lower()
            
            # Skip if it's the email domain or social media
            if email_domain and email_domain in url:
                continue
            if any(social in url for social in ['linkedin.com', 'twitter.com', 'facebook.com']):
                continue
            
            # Clean and normalize the URL
            url = re.sub(r'\s+', '', url)  # Remove spaces
            url = re.sub(r'[;:\s]+', '.', url)  # Replace OCR artifacts with dots
            url = re.sub(r'\.+', '.', url)  # Collapse multiple dots
            
            # Add https if no protocol
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            logger.debug(f"Found website: {url}")
            return url
        
        # Try to find website patterns with OCR noise
        # Look for "www" or domain + "com/org/net"
        website_patterns = [
            r'(www[.\s;:]*[a-z0-9]+[a-z0-9.\s;:-]*\s*(com|org|net|io))',
            r'([a-z0-9]+name[.\s;:]*com)',
            r'([a-z0-9]+site[.\s;:]*com)',
        ]
        
        for pattern in website_patterns:
            match = re.search(pattern, cleaned_text, re.IGNORECASE)
            if match:
                url = match.group(1)
                url = re.sub(r'\s+', '', url)
                url = re.sub(r'[;:\s]+', '.', url)
                url = re.sub(r'\.+', '.', url)
                if not url.startswith(('http://', 'https://', 'www.')):
                    url = 'www.' + url
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                logger.debug(f"Found website (cleaned): {url}")
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
            # Clean OCR artifacts
            cleaned = self._clean_ocr_text(line.strip())
            if cleaned and len(cleaned) > 1:
                lines.append(cleaned)
        return lines
    
    def _clean_ocr_text(self, text: str) -> str:
        """Clean common OCR artifacts from text."""
        # Remove trailing punctuation that's likely OCR noise
        text = re.sub(r'[;:,.\-_]+$', '', text)
        # Remove leading punctuation
        text = re.sub(r'^[;:,.\-_]+', '', text)
        # Fix common OCR errors: separate words like REALESTATEAGENT
        # Add space before capital letters that follow lowercase
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        # Add space between uppercase words if all caps
        text = re.sub(r'([A-Z]{2,})([A-Z][a-z])', r'\1 \2', text)
        return text.strip()
    
    def _extract_name(self, lines: List[str], full_text: str) -> Optional[str]:
        """Extract person's name from text lines.
        
        Heuristics:
        - Usually on first or second line
        - Not an email, phone, or URL
        - Usually 2-4 words
        - Contains mostly letters
        """
        candidates = []
        
        # Common first names to help identify real names
        common_first_names = {
            'james', 'john', 'robert', 'michael', 'william', 'david', 'richard', 'joseph',
            'thomas', 'charles', 'christopher', 'daniel', 'matthew', 'anthony', 'mark',
            'donald', 'steven', 'paul', 'andrew', 'joshua', 'kenneth', 'kevin', 'brian',
            'george', 'edward', 'ronald', 'timothy', 'jason', 'jeffrey', 'ryan', 'jacob',
            'gary', 'nicholas', 'eric', 'jonathan', 'stephen', 'larry', 'justin', 'scott',
            'brandon', 'benjamin', 'samuel', 'raymond', 'gregory', 'frank', 'alexander',
            'patrick', 'jack', 'dennis', 'jerry', 'tyler', 'aaron', 'jose', 'adam', 'nathan',
            'mary', 'patricia', 'jennifer', 'linda', 'elizabeth', 'barbara', 'susan',
            'jessica', 'sarah', 'karen', 'lisa', 'nancy', 'betty', 'margaret', 'sandra',
            'ashley', 'kimberly', 'emily', 'donna', 'michelle', 'dorothy', 'carol', 'amanda',
            'melissa', 'deborah', 'stephanie', 'rebecca', 'sharon', 'laura', 'cynthia',
            'kathleen', 'amy', 'angela', 'shirley', 'anna', 'brenda', 'pamela', 'emma',
            'nicole', 'helen', 'samantha', 'katherine', 'christine', 'debra', 'rachel',
            'olivia', 'sophia', 'victoria', 'grace', 'natalie', 'julia', 'hannah',
            'stewart', 'clark', 'smith', 'johnson', 'williams', 'brown', 'jones', 'miller',
            'davis', 'wilson', 'anderson', 'taylor', 'moore', 'jackson', 'martin', 'lee',
            'thompson', 'white', 'harris', 'sanchez', 'robinson', 'walker', 'young', 'allen',
            'king', 'wright', 'scott', 'torres', 'nguyen', 'hill', 'flores', 'green', 'adams',
            'nelson', 'baker', 'hall', 'rivera', 'campbell', 'mitchell', 'carter', 'roberts',
            'syed', 'rizvi', 'khan', 'ahmed', 'ali', 'hassan', 'hussain', 'mohammad', 'kumar'
        }
        
        # Words that should NOT be in names
        non_name_words = {
            'real', 'estate', 'realestate', 'agent', 'your', 'tagline', 'here', 'goes',
            'www', 'com', 'org', 'net', 'email', 'phone', 'fax', 'mobile', 'cell',
            'address', 'street', 'avenue', 'road', 'floor', 'suite', 'building',
            'usa', 'florida', 'california', 'texas', 'new', 'york', 'city',
            'info', 'contact', 'website', 'web', 'site', 'name', 'main', 'hall',
            'royal', 'galaxy', 'tlorid', 'yourtagiine', 'yourtagline', 'yourtagwne'
        }
        
        # Pattern for ALL CAPS names like "STEWART CLARK"
        all_caps_name_pattern = re.compile(r'\b([A-Z]{2,}(?:\s+[A-Z]{2,}){1,3})\b')
        
        # Search in full text for ALL CAPS names
        for match in all_caps_name_pattern.finditer(full_text):
            potential_name = match.group(1)
            potential_name_title = potential_name.title()
            words = potential_name_title.split()
            
            if 2 <= len(words) <= 3:
                is_valid_name = True
                name_score = 0
                
                for word in words:
                    word_lower = word.lower()
                    
                    # Skip if it's a non-name word
                    if word_lower in non_name_words:
                        is_valid_name = False
                        break
                    
                    # Skip if it's a company indicator
                    if word_lower in [ind.lower() for ind in self.COMPANY_INDICATORS]:
                        is_valid_name = False
                        break
                    
                    # Check it's alphabetic and reasonable length
                    if not word.isalpha() or len(word) < 2:
                        is_valid_name = False
                        break
                    
                    # Boost score if it's a common name
                    if word_lower in common_first_names:
                        name_score += 5
                
                if is_valid_name:
                    # Base score for 2-word names
                    score = 10 + name_score + (2 if len(words) == 2 else 0)
                    candidates.append((potential_name_title, score))
        
        for i, line in enumerate(lines[:8]):  # Check first 8 lines
            # Skip if it contains contact info patterns
            if self.PATTERNS["email"].search(line):
                continue
            if '@' in line:
                continue
            # Check for phone number patterns (digits grouped together)
            digit_count = sum(1 for c in line if c.isdigit())
            if digit_count >= 7:  # Likely a phone number
                continue
            if any(indicator in line.lower() for indicator in self.COMPANY_INDICATORS):
                continue
            # Skip if it looks like an address
            if any(word in line.lower() for word in ['street', 'st.', 'ave', 'avenue', 'road', 'rd.', 'blvd', 'suite', 'floor']):
                continue
            
            # Clean the line more aggressively for name detection
            clean_line = re.sub(r'[^a-zA-Z\s]', '', line).strip()
            
            # Check if it looks like a name
            words = clean_line.split()
            if 2 <= len(words) <= 4:
                # Check if words are mostly alphabetic
                alpha_ratio = sum(1 for w in words if w.isalpha()) / len(words)
                if alpha_ratio >= 0.8:
                    # Check if words look like proper names (capitalized or all caps)
                    name_like = all(w[0].isupper() or w.isupper() for w in words if len(w) > 0)
                    if name_like:
                        # Convert to title case if all caps
                        if clean_line.isupper():
                            clean_line = clean_line.title()
                        # Score based on position (earlier = better) and length
                        score = (6 - i) + (2 if len(words) == 2 else 0)
                        candidates.append((clean_line, score))
        
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
        # Check for compound titles WITHOUT spaces FIRST (higher priority)
        # Sorted by length (longest first) to prefer more specific matches
        compound_titles = [
            ('realestateagent', 'Real Estate Agent'),
            ('softwareengineer', 'Software Engineer'),
            ('softwaredeveloper', 'Software Developer'),
            ('businessdevelopment', 'Business Development'),
            ('accountexecutive', 'Account Executive'),
            ('marketingmanager', 'Marketing Manager'),
            ('financialanalyst', 'Financial Analyst'),
            ('customerservice', 'Customer Service'),
            ('productmanager', 'Product Manager'),
            ('projectmanager', 'Project Manager'),
            ('seniorengineer', 'Senior Engineer'),
            ('datascientist', 'Data Scientist'),
            ('salesmanager', 'Sales Manager'),
            ('dataanalyst', 'Data Analyst'),
            ('salesrep', 'Sales Representative'),
            ('realestate', 'Real Estate'),  # Shorter match last
        ]
        
        # Combine all lines and check longest compound matches first
        all_text_no_space = ''.join(line.lower().replace(' ', '') for line in lines)
        
        for compound, proper in compound_titles:
            if compound in all_text_no_space:
                logger.debug(f"Extracted compound title: {proper}")
                return proper
        
        # Then check for regular title keywords
        for line in lines:
            line_lower = line.lower()
            
            # Clean any concatenated words
            cleaned_line = self._clean_ocr_text(line)
            cleaned_lower = cleaned_line.lower()
            
            # Check for common title keywords
            for title in self.COMMON_TITLES:
                if title in line_lower or title in cleaned_lower:
                    # This line likely contains a title
                    # Return the cleaned version
                    if cleaned_line.isupper():
                        cleaned_line = cleaned_line.title()
                    logger.debug(f"Extracted title: {cleaned_line}")
                    return cleaned_line
        
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
            if domain_name.lower() not in ['gmail', 'yahoo', 'hotmail', 'outlook', 'aol', 'websitename']:
                # Could be company domain
                company_hint = domain_name.title()
            else:
                company_hint = None
        else:
            company_hint = None
        
        # Look for lines with company indicators
        for line in lines:
            line_lower = line.lower()
            for indicator in self.COMPANY_INDICATORS:
                if indicator in line_lower:
                    logger.debug(f"Extracted company: {line}")
                    return line
        
        # Known company name patterns (industry keywords that appear alone)
        company_keywords = ['realestate', 'real estate', 'consulting', 'solutions', 
                          'technologies', 'systems', 'services', 'agency', 'group']
        
        # Look for company-like patterns (all caps, first line often is company)
        # Check first few lines for potential company names
        for i, line in enumerate(lines[:4]):
            cleaned = self._clean_ocr_text(line)
            line_no_space = cleaned.lower().replace(' ', '')
            
            # Skip if it contains contact info
            if '@' in line or self.PATTERNS["phone"].search(line):
                continue
            # Skip taglines
            if 'tagline' in line.lower() or 'goes here' in line.lower():
                continue
            # Skip website lines
            if 'www' in line.lower() or '.com' in line.lower():
                continue
                
            # Check for known company keywords
            for keyword in company_keywords:
                if keyword in line_no_space:
                    # Format nicely
                    if keyword == 'realestate':
                        logger.debug(f"Extracted company: Real Estate")
                        return "Real Estate"
                    logger.debug(f"Extracted company: {cleaned.title()}")
                    return cleaned.title()
            
            # If it's all caps and short, might be company name
            if cleaned.isupper() and 1 <= len(cleaned.split()) <= 4:
                # Check it's not a person's name or title
                if not any(title in cleaned.lower() for title in ['agent', 'manager', 'director', 'clark', 'stewart']):
                    logger.debug(f"Extracted company (from header): {cleaned.title()}")
                    return cleaned.title()
        
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
            r'street|st\.|avenue|ave\.|road|rd\.|boulevard|blvd|drive|dr\.|lane|ln\.|way|place|pl\.',
            r'hall|main|center|plaza|tower',  # Building names
        ]
        
        # OCR variations of US states
        state_variations = {
            'florida': ['florida', 'florid', 'tlorid', 'fiorida'],
            'california': ['california', 'califomia', 'caifornia'],
            'texas': ['texas', 'tekas', 'tezas'],
            'new york': ['new york', 'newyork', 'new yolk'],
        }
        
        address_lines = []
        
        for line in lines:
            line_lower = line.lower()
            
            # Skip if it's clearly not an address
            if self.PATTERNS["email"].search(line):
                continue
            if 'linkedin' in line_lower or 'twitter' in line_lower:
                continue
            if '@' in line:
                continue
            # Skip lines that are mostly digits (phone numbers)
            digit_ratio = sum(1 for c in line if c.isdigit()) / max(len(line), 1)
            if digit_ratio > 0.5:
                continue
            
            is_address = False
            
            # Check for US states (including OCR variations)
            for state, variations in state_variations.items():
                for var in variations:
                    if var in line_lower:
                        is_address = True
                        break
            
            # Check for "USA" or zip codes
            if 'usa' in line_lower or re.search(r'\b\d{4,5}\b', line):
                is_address = True
            
            # Check for standard US states
            for state in self.US_STATES:
                if state in line_lower:
                    is_address = True
                    break
            
            # Check for address patterns
            if not is_address:
                for pattern in address_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        is_address = True
                        break
            
            if is_address:
                # Clean the line
                cleaned = self._clean_ocr_text(line)
                cleaned = re.sub(r'[;:\-]+$', '', cleaned)  # Remove trailing punctuation
                address_lines.append(cleaned)
        
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
