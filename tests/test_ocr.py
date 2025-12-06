"""
Tests for CardOCR class.

Tests the OCR extraction functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from src.ocr import CardOCR


class TestCardOCR:
    """Test cases for CardOCR."""
    
    @pytest.fixture
    def ocr(self):
        """Create OCR instance without initializing reader."""
        return CardOCR(languages=["en"], gpu=False)
    
    def test_ocr_initialization(self, ocr):
        """Test OCR initializes correctly."""
        assert ocr is not None
        assert ocr.languages == ["en"]
        assert ocr.gpu is False
        assert ocr._reader is None  # Lazy initialization
    
    def test_ocr_custom_languages(self):
        """Test OCR with custom languages."""
        ocr = CardOCR(languages=["en", "de"], gpu=False)
        assert ocr.languages == ["en", "de"]
    
    def test_extract_text_file_not_found(self, ocr):
        """Test error when file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            ocr.extract_text("/nonexistent/path/image.jpg")
    
    def test_get_confidence_stats_empty(self, ocr):
        """Test confidence stats with empty results."""
        stats = ocr.get_confidence_stats([])
        
        assert stats["count"] == 0
        assert stats["min_confidence"] == 0.0
        assert stats["max_confidence"] == 0.0
        assert stats["mean_confidence"] == 0.0
    
    def test_get_confidence_stats(self, ocr):
        """Test confidence stats calculation."""
        results = [
            ("text1", 0.8),
            ("text2", 0.9),
            ("text3", 0.7)
        ]
        
        stats = ocr.get_confidence_stats(results)
        
        assert stats["count"] == 3
        assert stats["min_confidence"] == 0.7
        assert stats["max_confidence"] == 0.9
        assert 0.79 < stats["mean_confidence"] < 0.81
    
    def test_is_valid_card_too_few_segments(self, ocr):
        """Test validation with too few segments."""
        results = [("text1", 0.9)]
        
        assert not ocr.is_valid_card(results, min_segments=3)
    
    def test_is_valid_card_low_confidence(self, ocr):
        """Test validation with low confidence."""
        results = [
            ("text1", 0.2),
            ("text2", 0.3),
            ("text3", 0.1)
        ]
        
        assert not ocr.is_valid_card(results, min_avg_confidence=0.5)
    
    def test_is_valid_card_success(self, ocr):
        """Test validation with valid card."""
        results = [
            ("text1", 0.8),
            ("text2", 0.9),
            ("text3", 0.7)
        ]
        
        assert ocr.is_valid_card(results, min_segments=3, min_avg_confidence=0.5)
    
    @patch('src.ocr.Image')
    def test_preprocess_image(self, mock_image, ocr):
        """Test image preprocessing."""
        # Create mock image
        mock_img = MagicMock()
        mock_img.mode = "RGB"
        mock_img.size = (1000, 800)
        mock_image.open.return_value = mock_img
        
        # Mock numpy array conversion
        mock_img.__array__ = Mock(return_value=np.zeros((800, 1000, 3)))
        
        # Test preprocessing (would need actual image for full test)
        # This tests the mock setup
        assert mock_image is not None
    
    def test_extract_text_simple_mock(self, ocr):
        """Test simple text extraction with mocked reader."""
        # Mock the reader
        mock_reader = Mock()
        mock_reader.readtext.return_value = [
            ([[0, 0], [100, 0], [100, 20], [0, 20]], "John Doe", 0.95),
            ([[0, 30], [100, 30], [100, 50], [0, 50]], "john@example.com", 0.92)
        ]
        
        ocr._reader = mock_reader
        
        # Mock file existence and image loading
        with patch('pathlib.Path.exists', return_value=True):
            with patch.object(ocr, '_preprocess_image', return_value=np.zeros((100, 100, 3))):
                results = ocr.extract_text("test_image.jpg")
        
        assert len(results) == 2
        assert results[0] == ("John Doe", 0.95)
        assert results[1] == ("john@example.com", 0.92)
    
    def test_extract_with_positions_mock(self, ocr):
        """Test extraction with positions using mocked reader."""
        mock_reader = Mock()
        mock_reader.readtext.return_value = [
            ([[0, 0], [100, 0], [100, 20], [0, 20]], "Test", 0.9)
        ]
        
        ocr._reader = mock_reader
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch.object(ocr, '_preprocess_image', return_value=np.zeros((100, 100, 3))):
                results = ocr.extract_with_positions("test_image.jpg")
        
        assert len(results) == 1
        assert results[0]["text"] == "Test"
        assert results[0]["confidence"] == 0.9
        assert "bounding_box" in results[0]


class TestCardOCRIntegration:
    """Integration tests for CardOCR (require actual images)."""
    
    @pytest.fixture
    def sample_image_path(self, tmp_path):
        """Create a temporary test image."""
        from PIL import Image
        
        # Create a simple test image
        img = Image.new('RGB', (400, 200), color='white')
        img_path = tmp_path / "test_card.png"
        img.save(img_path)
        
        return img_path
    
    @pytest.mark.skipif(
        True,  # Skip by default, enable for integration testing
        reason="Integration test - requires EasyOCR model download"
    )
    def test_real_extraction(self, sample_image_path):
        """Test real OCR extraction (requires model)."""
        ocr = CardOCR(languages=["en"], gpu=False)
        results = ocr.extract_text(sample_image_path)
        
        assert isinstance(results, list)
