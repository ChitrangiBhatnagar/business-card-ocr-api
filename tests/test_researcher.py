"""
Tests for FreeLeadResearcher class.

Tests the data enrichment functionality.
"""

import pytest
from unittest.mock import Mock, patch
import requests

from src.researcher import FreeLeadResearcher, EnrichedData
from src.parser import ContactData


class TestFreeLeadResearcher:
    """Test cases for FreeLeadResearcher."""
    
    @pytest.fixture
    def researcher(self):
        """Create researcher instance without API keys."""
        return FreeLeadResearcher()
    
    @pytest.fixture
    def researcher_with_keys(self):
        """Create researcher instance with mock API keys."""
        return FreeLeadResearcher(
            hunter_api_key="test_hunter_key",
            abstract_api_key="test_abstract_key",
            github_token="test_github_token"
        )
    
    def test_researcher_initialization(self, researcher):
        """Test researcher initializes correctly."""
        assert researcher is not None
        assert researcher.hunter_api_key is None
        assert researcher.abstract_api_key is None
        assert researcher.github_token is None
    
    def test_researcher_with_keys(self, researcher_with_keys):
        """Test researcher with API keys."""
        assert researcher_with_keys.hunter_api_key == "test_hunter_key"
        assert researcher_with_keys.abstract_api_key == "test_abstract_key"
        assert researcher_with_keys.github_token == "test_github_token"
    
    def test_enriched_data_to_dict(self):
        """Test EnrichedData serialization."""
        enriched = EnrichedData(
            email_verified=True,
            email_score=85,
            enrichment_sources=["hunter.io"]
        )
        
        data = enriched.to_dict()
        
        assert data["email_verified"] is True
        assert data["email_score"] == 85
        assert "hunter.io" in data["enrichment_sources"]
    
    def test_enrich_without_api_keys(self, researcher):
        """Test enrichment without API keys returns empty enrichment."""
        contact = ContactData(
            name="John Doe",
            email="john@example.com"
        )
        
        result = researcher.enrich(contact)
        
        assert isinstance(result, EnrichedData)
        assert len(result.enrichment_sources) == 0
    
    def test_get_api_usage(self, researcher):
        """Test API usage tracking."""
        usage = researcher.get_api_usage()
        
        assert "hunter" in usage
        assert "abstract" in usage
        assert "github" in usage
        assert all(v == 0 for v in usage.values())
    
    @patch('requests.get')
    def test_verify_email_hunter(self, mock_get, researcher_with_keys):
        """Test Hunter.io email verification."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "status": "valid",
                "score": 95
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = researcher_with_keys._verify_email_hunter("test@example.com")
        
        assert result is not None
        assert result["status"] == "valid"
        assert result["score"] == 95
    
    @patch('requests.get')
    def test_verify_email_hunter_error(self, mock_get, researcher_with_keys):
        """Test Hunter.io error handling."""
        mock_get.side_effect = requests.exceptions.RequestException("API Error")
        
        with pytest.raises(requests.exceptions.RequestException):
            researcher_with_keys._verify_email_hunter("test@example.com")
    
    @patch('requests.get')
    def test_validate_email_abstract(self, mock_get, researcher_with_keys):
        """Test Abstract API email validation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "deliverability": "DELIVERABLE",
            "quality_score": 0.9
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = researcher_with_keys._validate_email_abstract("test@example.com")
        
        assert result is not None
        assert result["deliverability"] == "DELIVERABLE"
    
    @patch('requests.get')
    def test_github_user_search(self, mock_get, researcher_with_keys):
        """Test GitHub user search."""
        # Mock search response
        search_response = Mock()
        search_response.status_code = 200
        search_response.json.return_value = {
            "total_count": 1,
            "items": [{"login": "johndoe"}]
        }
        search_response.raise_for_status = Mock()
        
        # Mock user details response
        user_response = Mock()
        user_response.status_code = 200
        user_response.json.return_value = {
            "login": "johndoe",
            "name": "John Doe",
            "html_url": "https://github.com/johndoe",
            "bio": "Developer",
            "public_repos": 50,
            "followers": 100
        }
        user_response.raise_for_status = Mock()
        
        mock_get.side_effect = [search_response, user_response]
        
        result = researcher_with_keys._search_github_by_email("john@example.com")
        
        assert result is not None
        assert result["username"] == "johndoe"
        assert result["followers"] == 100
    
    def test_get_github_headers_without_token(self, researcher):
        """Test GitHub headers without token."""
        headers = researcher._get_github_headers()
        
        assert "Accept" in headers
        assert "User-Agent" in headers
        assert "Authorization" not in headers
    
    def test_get_github_headers_with_token(self, researcher_with_keys):
        """Test GitHub headers with token."""
        headers = researcher_with_keys._get_github_headers()
        
        assert "Authorization" in headers
        assert "token test_github_token" in headers["Authorization"]
    
    @patch('requests.get')
    def test_full_enrichment(self, mock_get, researcher_with_keys):
        """Test full enrichment pipeline."""
        # Mock all API responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"status": "valid", "score": 90}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        contact = ContactData(
            name="John Doe",
            email="john@techcorp.com",
            company="Tech Corp"
        )
        
        result = researcher_with_keys.enrich(contact)
        
        assert isinstance(result, EnrichedData)
        assert len(result.enrichment_sources) > 0 or len(result.enrichment_errors) > 0
    
    @patch('time.sleep')  # Speed up test
    @patch('requests.get')
    def test_enrich_batch(self, mock_get, mock_sleep, researcher):
        """Test batch enrichment."""
        contacts = [
            ContactData(name="John Doe", email="john@example.com"),
            ContactData(name="Jane Smith", email="jane@example.com")
        ]
        
        results = researcher.enrich_batch(contacts, delay=0)
        
        assert len(results) == 2
        assert all(isinstance(r, EnrichedData) for r in results)
