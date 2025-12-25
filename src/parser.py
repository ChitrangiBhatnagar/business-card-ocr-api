import re
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =========================
# DATA MODEL
# =========================

@dataclass
class ContactData:
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    linkedin: Optional[str] = None
    twitter: Optional[str] = None
    address: Optional[str] = None
    confidence_score: float = 0.0
    raw_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name or "",
            "first_name": self.first_name or "",
            "last_name": self.last_name or "",
            "title": self.title or "",
            "company": self.company or "",
            "email": self.email or "",
            "phone": [self.phone] if self.phone else [],
            "website": self.website or "",
            "linkedin": self.linkedin or "",
            "twitter": self.twitter or "",
            "address": self.address or "",
            "confidence_score": round(self.confidence_score, 2),
            "raw_text": self.raw_text or "",
        }


# =========================
# PARSER
# =========================

class ContactParser:
    def __init__(self):
        self.patterns = {
            "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
            # BETTER phone pattern - handles international, extensions, etc.
            "phone": re.compile(r"[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}"),
            "website": re.compile(r"(?:https?://)?(?:www\.)?[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?"),
            "linkedin": re.compile(r"(?:linkedin\.com/in/|linkedin\.com/company/)[^\s]+"),
            "twitter": re.compile(r"(?:twitter\.com/|@)[A-Za-z0-9_]+"),
            "zip": re.compile(r"\b\d{5}(?:-\d{4})?\b"),
        }

    # =========================
    # PIPELINE API
    # =========================

    def parse(self, text: str, ocr_confidence: float = 1.0) -> ContactData:
        contacts = self.parse_from_image_text(text)
        if not contacts:
            return ContactData(raw_text=text, confidence_score=0.0)

        contact = contacts[0]
        base_conf = self._calculate_confidence_score(contact)
        contact.confidence_score = max(base_conf * ocr_confidence, 0.35)
        return contact

    def parse_from_image_text(self, text: str) -> List[ContactData]:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        return self._parse_card(lines)

    # =========================
    # CORE PARSING
    # =========================

    def _parse_card(self, lines: List[str]) -> List[ContactData]:
        """Parse business card lines."""
        
        # DEBUG: Log what we're parsing
        logger.debug(f"Parsing {len(lines)} lines")
        
        card_text = " ".join(lines)

        contact = ContactData(
            name=self._extract_name(lines),
            title=self._extract_title(lines),
            company=self._extract_company(lines),
            email=self._extract_email(card_text),
            phone=self._extract_phone(card_text),
            website=self._extract_website(card_text),
            linkedin=self._extract_linkedin(card_text),
            twitter=self._extract_twitter(card_text),
            address=self._extract_address(card_text),
            raw_text="\n".join(lines),
        )
        
        # DEBUG: Log what was extracted
        logger.debug(f"Extracted - Name: {contact.name}, Company: {contact.company[:50] if contact.company else 'None'}")

        if contact.name:
            parts = contact.name.split()
            if len(parts) >= 2:
                contact.first_name = parts[0]
                contact.last_name = " ".join(parts[1:])

        return [contact]

    # =========================
    # HELPERS
    # =========================

    def _is_personal_info(self, text: str) -> bool:
        return (
            bool(self.patterns["email"].search(text))
            or bool(self.patterns["phone"].search(text))
            or "http" in text.lower()
        )

    def _extract_name(self, lines: List[str]) -> str:
        """Extract person's name from business card using enhanced logic."""
        
        # Company keywords that indicate this is NOT a person's name
        company_keywords = [
            "solutions", "technologies", "technology", "systems", "group",
            "corporation", "company", "corp", "inc", "llc", "ltd", "co",
            "enterprises", "associates", "partners", "consulting", "services",
            "international", "global", "worldwide", "industries", "holdings",
            "capital", "investments", "financial", "bank", "credit", "insurance",
            "real estate", "construction", "development", "manufacturing",
            "communications", "telecommunications", "media", "marketing",
            "consulting", "advisory", "management", "logistics", "transport",
            "healthcare", "medical", "dental", "legal", "law", "firm",
            "restaurant", "hotel", "retail", "store", "shop", "market",
            "business card", "card", "test", "sample", "demo", "wave"
        ]
        
        # Title keywords that might appear with names
        title_keywords = [
            "agent", "engineer", "developer", "manager", "director",
            "consultant", "designer", "president", "founder", "chairman",
            "captain", "officer", "ceo", "cto", "cfo", "vp", "vice president",
            "specialist", "analyst", "coordinator", "supervisor", "lead",
            "senior", "junior", "assistant", "associate", "principal", "chief"
        ]
        
        # Common first names to help identify person names (expanded)
        common_first_names = {
            "james", "robert", "john", "michael", "david", "william", "richard",
            "thomas", "christopher", "charles", "daniel", "matthew", "anthony",
            "mark", "donald", "steven", "paul", "joshua", "kenneth", "kevin",
            "brian", "george", "edward", "ronald", "timothy", "jason", "jeffrey",
            "ryan", "jacob", "gary", "nicholas", "eric", "jonathan", "stephen",
            "mary", "patricia", "jennifer", "linda", "elizabeth", "barbara",
            "susan", "jessica", "sarah", "karen", "nancy", "lisa", "betty",
            "helen", "sandra", "donna", "carol", "ruth", "sharon", "michelle",
            "laura", "sarah", "kimberly", "deborah", "dorothy", "amy", "angela",
            "brenda", "emma", "olivia", "cynthia", "marie", "janet", "catherine",
            "frances", "christine", "samantha", "debra", "rachel", "carolyn",
            "virginia", "heather", "diane", "julie", "joyce", "anna", "grace",
            "alex", "alexander", "alexandra", "andrew", "andy", "ben", "benjamin",
            "bill", "bob", "bobby", "chris", "christine", "christina", "dan",
            "dave", "dennis", "frank", "fred", "greg", "gregory", "jack", 
            "jake", "jim", "joe", "joseph", "kate", "katherine", "kelly",
            "ken", "kevin", "kim", "kimberly", "larry", "laura", "linda",
            "lisa", "margaret", "maria", "marie", "mark", "martin", "matt",
            "matthew", "max", "mike", "nancy", "nick", "nicholas", "pat",
            "patricia", "paul", "peter", "phil", "philip", "rick", "rob",
            "robert", "sam", "samuel", "sara", "scott", "steve", "steven",
            "susan", "tom", "thomas", "tim", "timothy", "tony", "william"
        }
        
        potential_names = []
        
        for i, line in enumerate(lines[:8]):  # Check more lines
            line = line.strip()
            if not line:
                continue
            
            lower_line = line.lower()
            
            # Skip contact info
            if self._is_personal_info(line):
                continue
                
            # Skip lines that are obviously companies - be more aggressive
            has_company_keyword = any(keyword in lower_line for keyword in company_keywords)
            if has_company_keyword:
                continue
            
            # Skip if line contains multiple company-like indicators
            company_score = 0
            if any(word in lower_line for word in ['inc', 'llc', 'ltd', 'corp', 'company']):
                company_score += 3
            if line.isupper() and len(line.split()) >= 3:
                company_score += 2
            if any(word in lower_line for word in ['solutions', 'services', 'systems', 'group']):
                company_score += 2
            
            if company_score >= 3:
                continue
            
            # Skip lines with too many numbers (addresses, phones)
            if sum(c.isdigit() for c in line) > 4:
                continue
            
            # Extract potential names from lines with titles
            if any(t in lower_line for t in title_keywords):
                # Find the part before the title
                for title in title_keywords:
                    if title in lower_line:
                        title_pos = lower_line.find(title)
                        before_title = line[:title_pos].strip().rstrip(',').strip()
                        if before_title:
                            words = before_title.split()
                            # Check if it looks like a person's name
                            if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if w.isalpha()):
                                potential_names.append((before_title, i, 'with_title'))
                        break
                continue
            
            # Look for lines that look like person names (2-4 capitalized words)
            words = [w for w in line.split() if w.replace(',', '').replace('.', '').isalpha()]
            if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words):
                # Check if first word is a common first name
                first_word = words[0].lower().replace(',', '').replace('.', '')
                
                # High priority for common first names
                if first_word in common_first_names:
                    potential_names.append((line.strip(), i, 'high'))
                # Medium priority for proper name patterns without company keywords
                elif len(words) == 2 and not has_company_keyword:
                    potential_names.append((line.strip(), i, 'medium'))
                # Lower priority for 3-4 word names (could be companies)
                elif 3 <= len(words) <= 4 and first_word in common_first_names:
                    potential_names.append((line.strip(), i, 'medium'))
        
        # Sort potential names by priority and position
        def name_priority(item):
            name, position, priority = item
            priority_score = {'high': 10, 'with_title': 8, 'medium': 5}.get(priority, 0)
            # Earlier lines get preference
            position_score = max(0, 8 - position) * 0.5
            return priority_score + position_score
        
        if potential_names:
            potential_names.sort(key=name_priority, reverse=True)
            return potential_names[0][0]
        
        return ""

    def _extract_title(self, lines: List[str]) -> str:
        """Extract job title."""
        title_keywords = [
            "real estate agent", "agent", "engineer", "developer",
            "manager", "director", "captain", "founder", "chairman",
            "consultant", "designer", "president", "ceo", "cto", "cfo",
            "vice president", "vp", "officer", "specialist", "analyst"
        ]

        for line in lines:
            lower = line.lower()
            if any(t in lower for t in title_keywords):
                return line

        return ""

    def _extract_company(self, lines: List[str]) -> str:
        """Extract company name with enhanced logic."""
        # Strong company indicators (must match exactly or as word)
        strong_indicators = [
            "inc", "llc", "ltd", "corp", "corporation", "company", "co",
            "technologies", "systems", "group", "solutions", "associates",
            "partners", "enterprises", "consulting", "services", "holdings",
            "international", "global", "industries", "manufacturing",
            "communications", "media", "healthcare", "financial", "capital",
            "investments", "management", "logistics", "development"
        ]
        
        # Weak indicators (context-dependent)
        weak_indicators = [
            "tech", "software", "design", "creative", "digital", "studio",
            "center", "clinic", "hospital", "medical", "legal", "law",
            "restaurant", "hotel", "retail", "construction", "engineering",
            "marketing", "communications", "real estate", "automotive",
            "insurance", "bank", "credit"
        ]
        
        # Skip patterns (never company names)
        skip_patterns = [
            "business card", "calling card", "test", "sample", "demo",
            "card", "front", "back", "side"
        ]
        
        # Name-like patterns to avoid
        name_patterns = [
            r'^[A-Z][a-z]+ [A-Z][a-z]+$',  # First Last
            r'^[A-Z][a-z]+ [A-Z]\. [A-Z][a-z]+$',  # First M. Last
            r'^[A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+$'  # First Middle Last
        ]
        
        potential_companies = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            lower_line = line.lower()
            
            # Skip contact info and personal info
            if self._is_personal_info(line):
                continue
            
            # Skip obvious non-company patterns
            if any(skip in lower_line for skip in skip_patterns):
                continue
                
            # Skip if it looks like a person's name
            is_name_like = any(re.match(pattern, line) for pattern in name_patterns)
            if is_name_like:
                # Double-check: if it has strong company indicators, keep it
                has_strong_indicator = any(
                    indicator in lower_line.split() or 
                    indicator + 's' in lower_line.split()
                    for indicator in strong_indicators
                )
                if not has_strong_indicator:
                    continue
            
            # Check for strong indicators (high priority)
            has_strong = any(
                indicator in lower_line.split() or 
                indicator + 's' in lower_line.split() or
                ('.' + indicator in lower_line) or
                (indicator + '.' in lower_line)
                for indicator in strong_indicators
            )
            
            if has_strong:
                potential_companies.append((line, i, 'strong'))
                continue
            
            # Check for weak indicators (medium priority)
            has_weak = any(indicator in lower_line for indicator in weak_indicators)
            if has_weak:
                potential_companies.append((line, i, 'weak'))
                continue
            
            # Check for all-caps (often company names) - but be careful
            if line.isupper() and len(line) > 5 and not is_name_like:
                # Make sure it's not just a person's name in caps
                words = line.split()
                if len(words) >= 2:  # Multi-word all-caps = likely company
                    potential_companies.append((line, i, 'caps'))
                    continue
            
            # Check for multi-word non-name patterns
            words = line.split()
            if len(words) >= 3:  # 3+ words are often companies
                # But exclude obvious name patterns
                if not is_name_like:
                    potential_companies.append((line, i, 'multi_word'))
        
        # Sort by priority and position
        def company_priority(item):
            company, position, priority_type = item
            priority_scores = {
                'strong': 10,
                'caps': 5,
                'weak': 3,
                'multi_word': 2
            }
            priority_score = priority_scores.get(priority_type, 0)
            # Earlier lines get slight preference (but not as much as priority)
            position_score = max(0, 10 - position) * 0.1
            return priority_score + position_score
        
        if potential_companies:
            potential_companies.sort(key=company_priority, reverse=True)
            return potential_companies[0][0]
        
        return ""

    def _extract_email(self, text: str) -> str:
        """Extract email address."""
        m = self.patterns["email"].search(text)
        return m.group(0) if m else ""

    def _extract_phone(self, text: str) -> str:
        """Extract phone number."""
        m = self.patterns["phone"].search(text)
        if m:
            phone = m.group(0)
            # Validate: must have at least 10 digits
            digits = ''.join(c for c in phone if c.isdigit())
            if 10 <= len(digits) <= 15:
                return phone
        return ""

    def _extract_website(self, text: str) -> str:
        """Extract website URL."""
        m = self.patterns["website"].search(text)
        if m:
            url = m.group(0)
            # Ensure it has protocol
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            return url
        return ""

    def _extract_linkedin(self, text: str) -> str:
        """Extract LinkedIn profile."""
        m = self.patterns["linkedin"].search(text)
        return m.group(0) if m else ""

    def _extract_twitter(self, text: str) -> str:
        """Extract Twitter handle."""
        m = self.patterns["twitter"].search(text)
        return m.group(0) if m else ""

    def _extract_address(self, text: str) -> str:
        """Extract address using ZIP code as anchor."""
        m = self.patterns["zip"].search(text)
        if not m:
            return ""
        start = max(0, m.start() - 50)
        return text[start:m.end()].strip()

    def _calculate_confidence_score(self, c: ContactData) -> float:
        """Calculate confidence score based on extracted fields."""
        score = 0
        total = 6

        if c.name: score += 1
        if c.title: score += 1
        if c.company: score += 1
        if c.email: score += 1
        if c.phone: score += 1
        if c.address: score += 1

        return score / total