"""
Tests for ContactParser class.

Tests the parsing of OCR text into structured contact data.
"""

import pytest
from src.parser import ContactParser, ContactData


class TestContactParser:
    """Test cases for ContactParser."""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return ContactParser()
    
    def test_parser_initialization(self, parser):
        """Test parser initializes correctly."""
        assert parser is not None
        assert len(parser.PATTERNS) > 0
    
    def test_extract_email(self, parser):
        """Test email extraction."""
        test_cases = [
            ("Contact: john.doe@example.com", "john.doe@example.com"),
            ("Email: test@company.org", "test@company.org"),
            ("No email here", None),
            ("UPPERCASE@DOMAIN.COM", "uppercase@domain.com"),
            ("user.name+tag@domain.co.uk", "user.name+tag@domain.co.uk"),
        ]
        
        for text, expected in test_cases:
            result = parser._extract_email(text)
            assert result == expected, f"Failed for: {text}"
    
    def test_extract_phones(self, parser):
        """Test phone number extraction."""
        test_cases = [
            ("Call: 555-123-4567", ["5551234567"]),
            ("Phone: (555) 123-4567", ["5551234567"]),
            ("+1 555 123 4567", ["+15551234567"]),
            ("No phone here", []),
            ("Multiple: 555-111-2222 and 555-333-4444", ["5551112222", "5553334444"]),
        ]
        
        for text, expected in test_cases:
            result = parser._extract_phones(text)
            assert result == expected, f"Failed for: {text}"
    
    def test_extract_website(self, parser):
        """Test website extraction."""
        test_cases = [
            ("Visit www.example.com", "https://www.example.com"),
            ("https://company.org/about", "https://company.org/about"),
            ("No website", None),
        ]
        
        for text, expected in test_cases:
            result = parser._extract_website(text)
            assert result == expected, f"Failed for: {text}"
    
    def test_extract_linkedin(self, parser):
        """Test LinkedIn extraction."""
        test_cases = [
            ("linkedin.com/in/johndoe", "https://linkedin.com/in/johndoe"),
            ("LinkedIn: johndoe", None),  # Needs full pattern
        ]
        
        for text, expected in test_cases:
            result = parser._extract_linkedin(text)
            assert result == expected, f"Failed for: {text}"
    
    def test_extract_twitter(self, parser):
        """Test Twitter handle extraction."""
        result = parser._extract_twitter("Follow @johndoe on Twitter")
        assert result == "@johndoe"
    
    def test_split_name(self, parser):
        """Test name splitting."""
        test_cases = [
            ("John Doe", {"first_name": "John", "last_name": "Doe"}),
            ("John", {"first_name": "John", "last_name": None}),
            ("John Michael Doe", {"first_name": "John", "last_name": "Michael Doe"}),
            ("", {"first_name": None, "last_name": None}),
        ]
        
        for name, expected in test_cases:
            result = parser._split_name(name)
            assert result == expected, f"Failed for: {name}"
    
    def test_parse_full_card(self, parser):
        """Test parsing a complete business card."""
        card_text = """
        John Doe
        Senior Software Engineer
        Tech Solutions Inc.
        john.doe@techsolutions.com
        (555) 123-4567
        www.techsolutions.com
        linkedin.com/in/johndoe
        """
        
        result = parser.parse(card_text)
        
        assert isinstance(result, ContactData)
        assert result.email == "john.doe@techsolutions.com"
        assert len(result.phone) > 0
        assert result.confidence_score > 0
    
    def test_parse_minimal_card(self, parser):
        """Test parsing a minimal business card."""
        card_text = "john@example.com"
        
        result = parser.parse(card_text)
        
        assert result.email == "john@example.com"
        assert result.is_valid()
    
    def test_parse_empty_text(self, parser):
        """Test parsing empty text."""
        result = parser.parse("")
        
        assert result.confidence_score == 0.0
        assert not result.is_valid()
    
    def test_contact_data_to_dict(self, parser):
        """Test ContactData serialization."""
        contact = ContactData(
            name="John Doe",
            email="john@example.com",
            phone=["5551234567"]
        )
        
        data = contact.to_dict()
        
        assert data["name"] == "John Doe"
        assert data["email"] == "john@example.com"
        assert data["phone"] == ["5551234567"]
    
    def test_parse_batch(self, parser):
        """Test batch parsing."""
        texts = [
            "John Doe\njohn@example.com",
            "Jane Smith\njane@company.org"
        ]
        
        results = parser.parse_batch(texts)
        
        assert len(results) == 2
        assert all(isinstance(r, ContactData) for r in results)
    
    def test_extract_title(self, parser):
        """Test job title extraction."""
        lines = [
            "John Doe",
            "Senior Software Engineer",
            "Tech Company"
        ]
        
        result = parser._extract_title(lines)
        
        assert "Engineer" in result or "Senior" in result
    
    def test_extract_company_from_email(self, parser):
        """Test company extraction from email domain."""
        lines = ["John Doe"]
        email = "john@techcorp.com"
        
        result = parser._extract_company(lines, email)
        
        assert result is not None
        assert "Techcorp" in result or result == "Techcorp"
    
    def test_extract_company_with_indicator(self, parser):
        """Test company extraction with company indicator."""
        lines = [
            "John Doe",
            "Tech Solutions Inc.",
            "Software Engineer"
        ]
        
        result = parser._extract_company(lines, None)
        
        assert result is not None
        assert "Inc" in result
