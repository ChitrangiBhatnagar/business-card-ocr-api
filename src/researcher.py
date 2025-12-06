"""
Researcher module for Business Card Processing API.

Enriches contact data using free APIs (Hunter, Abstract, GitHub).
"""

import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import requests

from .parser import ContactData

logger = logging.getLogger(__name__)


@dataclass
class EnrichedData:
    """Enriched contact data from external APIs.
    
    Attributes:
        email_verified: Whether email was verified
        email_deliverable: Whether email is deliverable
        email_score: Email quality score (0-100)
        company_info: Company information from APIs
        social_profiles: Additional social profiles found
        github_profile: GitHub profile data
        enrichment_sources: List of APIs used for enrichment
        enrichment_errors: Any errors during enrichment
    """
    email_verified: Optional[bool] = None
    email_deliverable: Optional[bool] = None
    email_score: Optional[int] = None
    company_info: Dict[str, Any] = field(default_factory=dict)
    social_profiles: Dict[str, str] = field(default_factory=dict)
    github_profile: Dict[str, Any] = field(default_factory=dict)
    enrichment_sources: List[str] = field(default_factory=list)
    enrichment_errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "email_verified": self.email_verified,
            "email_deliverable": self.email_deliverable,
            "email_score": self.email_score,
            "company_info": self.company_info,
            "social_profiles": self.social_profiles,
            "github_profile": self.github_profile,
            "enrichment_sources": self.enrichment_sources,
            "enrichment_errors": self.enrichment_errors
        }


class FreeLeadResearcher:
    """Enriches contact data using free API tiers.
    
    Supported APIs:
    - Hunter.io: Email verification (50 free/month)
    - Abstract API: Email validation (100 free/month)
    - GitHub API: Developer profile lookup (5000 free/hour)
    
    All API calls are optional and gracefully handle missing keys.
    """
    
    # API endpoints
    HUNTER_API_URL = "https://api.hunter.io/v2"
    ABSTRACT_API_URL = "https://emailvalidation.abstractapi.com/v1"
    GITHUB_API_URL = "https://api.github.com"
    
    # Request timeout in seconds
    TIMEOUT = 10
    
    def __init__(
        self,
        hunter_api_key: Optional[str] = None,
        abstract_api_key: Optional[str] = None,
        github_token: Optional[str] = None
    ) -> None:
        """Initialize the FreeLeadResearcher.
        
        Args:
            hunter_api_key: Hunter.io API key (optional)
            abstract_api_key: Abstract API key (optional)
            github_token: GitHub personal access token (optional)
        """
        self.hunter_api_key = hunter_api_key
        self.abstract_api_key = abstract_api_key
        self.github_token = github_token
        
        # Track API usage
        self._api_calls = {
            "hunter": 0,
            "abstract": 0,
            "github": 0
        }
        
        available_apis = []
        if hunter_api_key:
            available_apis.append("Hunter.io")
        if abstract_api_key:
            available_apis.append("Abstract API")
        if github_token:
            available_apis.append("GitHub")
        
        logger.info(
            f"FreeLeadResearcher initialized with APIs: "
            f"{', '.join(available_apis) if available_apis else 'None'}"
        )
    
    def enrich(self, contact: ContactData) -> EnrichedData:
        """Enrich contact data with external API information.
        
        Args:
            contact: ContactData object to enrich
            
        Returns:
            EnrichedData object with additional information
        """
        enriched = EnrichedData()
        
        # Email verification/validation
        if contact.email:
            self._enrich_email(contact.email, enriched)
        
        # Company information
        if contact.company or (contact.email and '@' in contact.email):
            self._enrich_company(contact, enriched)
        
        # GitHub profile lookup
        if contact.email or contact.name:
            self._enrich_github(contact, enriched)
        
        logger.info(
            f"Enrichment complete. Sources: {enriched.enrichment_sources}, "
            f"Errors: {len(enriched.enrichment_errors)}"
        )
        
        return enriched
    
    def _enrich_email(self, email: str, enriched: EnrichedData) -> None:
        """Enrich email data using available APIs."""
        # Try Hunter.io first
        if self.hunter_api_key:
            try:
                result = self._verify_email_hunter(email)
                if result:
                    enriched.email_verified = result.get("status") == "valid"
                    enriched.email_score = result.get("score")
                    enriched.enrichment_sources.append("hunter.io")
            except Exception as e:
                error_msg = f"Hunter API error: {str(e)}"
                logger.warning(error_msg)
                enriched.enrichment_errors.append(error_msg)
        
        # Try Abstract API as fallback or additional source
        if self.abstract_api_key:
            try:
                result = self._validate_email_abstract(email)
                if result:
                    enriched.email_deliverable = result.get("deliverability") == "DELIVERABLE"
                    if enriched.email_score is None:
                        enriched.email_score = result.get("quality_score")
                    enriched.enrichment_sources.append("abstract_api")
            except Exception as e:
                error_msg = f"Abstract API error: {str(e)}"
                logger.warning(error_msg)
                enriched.enrichment_errors.append(error_msg)
    
    def _verify_email_hunter(self, email: str) -> Optional[Dict]:
        """Verify email using Hunter.io API.
        
        Args:
            email: Email address to verify
            
        Returns:
            API response data or None
        """
        if not self.hunter_api_key:
            return None
        
        url = f"{self.HUNTER_API_URL}/email-verifier"
        params = {
            "email": email,
            "api_key": self.hunter_api_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=self.TIMEOUT)
            response.raise_for_status()
            
            self._api_calls["hunter"] += 1
            data = response.json()
            
            logger.debug(f"Hunter.io response for {email}: {data.get('data', {})}")
            return data.get("data", {})
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Hunter.io API request failed: {str(e)}")
            raise
    
    def _validate_email_abstract(self, email: str) -> Optional[Dict]:
        """Validate email using Abstract API.
        
        Args:
            email: Email address to validate
            
        Returns:
            API response data or None
        """
        if not self.abstract_api_key:
            return None
        
        url = self.ABSTRACT_API_URL
        params = {
            "api_key": self.abstract_api_key,
            "email": email
        }
        
        try:
            response = requests.get(url, params=params, timeout=self.TIMEOUT)
            response.raise_for_status()
            
            self._api_calls["abstract"] += 1
            data = response.json()
            
            logger.debug(f"Abstract API response for {email}: {data}")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Abstract API request failed: {str(e)}")
            raise
    
    def _enrich_company(
        self, 
        contact: ContactData, 
        enriched: EnrichedData
    ) -> None:
        """Enrich company information."""
        # Extract domain from email
        domain = None
        if contact.email and '@' in contact.email:
            domain = contact.email.split('@')[1]
            
            # Skip personal email domains
            personal_domains = [
                'gmail.com', 'yahoo.com', 'hotmail.com', 
                'outlook.com', 'aol.com', 'icloud.com'
            ]
            if domain in personal_domains:
                domain = None
        
        # Try Hunter.io domain search for company info
        if domain and self.hunter_api_key:
            try:
                result = self._search_domain_hunter(domain)
                if result:
                    enriched.company_info = {
                        "domain": domain,
                        "organization": result.get("organization"),
                        "country": result.get("country"),
                        "industry": result.get("industry"),
                        "linkedin": result.get("linkedin"),
                        "twitter": result.get("twitter"),
                        "facebook": result.get("facebook")
                    }
                    
                    # Add discovered social profiles
                    if result.get("linkedin"):
                        enriched.social_profiles["company_linkedin"] = result["linkedin"]
                    if result.get("twitter"):
                        enriched.social_profiles["company_twitter"] = result["twitter"]
                    
                    if "hunter.io" not in enriched.enrichment_sources:
                        enriched.enrichment_sources.append("hunter.io")
                        
            except Exception as e:
                error_msg = f"Hunter domain search error: {str(e)}"
                logger.warning(error_msg)
                enriched.enrichment_errors.append(error_msg)
    
    def _search_domain_hunter(self, domain: str) -> Optional[Dict]:
        """Search for company info by domain using Hunter.io.
        
        Args:
            domain: Domain to search
            
        Returns:
            API response data or None
        """
        if not self.hunter_api_key:
            return None
        
        url = f"{self.HUNTER_API_URL}/domain-search"
        params = {
            "domain": domain,
            "api_key": self.hunter_api_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=self.TIMEOUT)
            response.raise_for_status()
            
            self._api_calls["hunter"] += 1
            data = response.json()
            
            return data.get("data", {})
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Hunter.io domain search failed: {str(e)}")
            raise
    
    def _enrich_github(
        self, 
        contact: ContactData, 
        enriched: EnrichedData
    ) -> None:
        """Enrich with GitHub profile data."""
        if not self.github_token:
            return
        
        # Search by email first (most accurate)
        if contact.email:
            try:
                result = self._search_github_by_email(contact.email)
                if result:
                    enriched.github_profile = result
                    enriched.social_profiles["github"] = result.get("html_url", "")
                    enriched.enrichment_sources.append("github")
                    return
            except Exception as e:
                error_msg = f"GitHub email search error: {str(e)}"
                logger.warning(error_msg)
                enriched.enrichment_errors.append(error_msg)
        
        # Fall back to name search
        if contact.name:
            try:
                result = self._search_github_by_name(contact.name)
                if result:
                    enriched.github_profile = result
                    enriched.social_profiles["github"] = result.get("html_url", "")
                    if "github" not in enriched.enrichment_sources:
                        enriched.enrichment_sources.append("github")
            except Exception as e:
                error_msg = f"GitHub name search error: {str(e)}"
                logger.warning(error_msg)
                enriched.enrichment_errors.append(error_msg)
    
    def _search_github_by_email(self, email: str) -> Optional[Dict]:
        """Search GitHub for user by email.
        
        Args:
            email: Email address to search
            
        Returns:
            User profile data or None
        """
        headers = self._get_github_headers()
        
        url = f"{self.GITHUB_API_URL}/search/users"
        params = {"q": f"{email} in:email"}
        
        try:
            response = requests.get(
                url, 
                headers=headers, 
                params=params, 
                timeout=self.TIMEOUT
            )
            response.raise_for_status()
            
            self._api_calls["github"] += 1
            data = response.json()
            
            if data.get("total_count", 0) > 0:
                user = data["items"][0]
                return self._get_github_user_details(user["login"])
            
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"GitHub search failed: {str(e)}")
            raise
    
    def _search_github_by_name(self, name: str) -> Optional[Dict]:
        """Search GitHub for user by name.
        
        Args:
            name: Name to search
            
        Returns:
            User profile data or None
        """
        headers = self._get_github_headers()
        
        url = f"{self.GITHUB_API_URL}/search/users"
        params = {"q": f"{name} in:name"}
        
        try:
            response = requests.get(
                url, 
                headers=headers, 
                params=params, 
                timeout=self.TIMEOUT
            )
            response.raise_for_status()
            
            self._api_calls["github"] += 1
            data = response.json()
            
            if data.get("total_count", 0) > 0:
                # Return first match (may not be accurate)
                user = data["items"][0]
                return self._get_github_user_details(user["login"])
            
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"GitHub search failed: {str(e)}")
            raise
    
    def _get_github_user_details(self, username: str) -> Dict:
        """Get detailed GitHub user profile.
        
        Args:
            username: GitHub username
            
        Returns:
            User profile data
        """
        headers = self._get_github_headers()
        
        url = f"{self.GITHUB_API_URL}/users/{username}"
        
        try:
            response = requests.get(url, headers=headers, timeout=self.TIMEOUT)
            response.raise_for_status()
            
            self._api_calls["github"] += 1
            data = response.json()
            
            return {
                "username": data.get("login"),
                "name": data.get("name"),
                "html_url": data.get("html_url"),
                "avatar_url": data.get("avatar_url"),
                "bio": data.get("bio"),
                "company": data.get("company"),
                "location": data.get("location"),
                "blog": data.get("blog"),
                "twitter_username": data.get("twitter_username"),
                "public_repos": data.get("public_repos"),
                "followers": data.get("followers"),
                "following": data.get("following")
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"GitHub user details failed: {str(e)}")
            raise
    
    def _get_github_headers(self) -> Dict[str, str]:
        """Get headers for GitHub API requests."""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "BusinessCardAPI/1.0"
        }
        
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        
        return headers
    
    def get_api_usage(self) -> Dict[str, int]:
        """Get API call counts.
        
        Returns:
            Dictionary with API call counts
        """
        return self._api_calls.copy()
    
    def enrich_batch(
        self, 
        contacts: List[ContactData],
        delay: float = 0.5
    ) -> List[EnrichedData]:
        """Enrich multiple contacts with rate limiting.
        
        Args:
            contacts: List of ContactData objects
            delay: Delay between API calls in seconds
            
        Returns:
            List of EnrichedData objects
        """
        results = []
        
        for i, contact in enumerate(contacts):
            logger.info(f"Enriching contact {i + 1}/{len(contacts)}")
            
            try:
                enriched = self.enrich(contact)
                results.append(enriched)
            except Exception as e:
                logger.error(f"Error enriching contact {i}: {str(e)}")
                results.append(EnrichedData(
                    enrichment_errors=[str(e)]
                ))
            
            # Rate limiting
            if i < len(contacts) - 1:
                time.sleep(delay)
        
        return results
