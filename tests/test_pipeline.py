"""
Tests for CardResearchPipeline class.

Tests the full processing pipeline.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

from src.pipeline import CardResearchPipeline
from src.parser import ContactData


class TestCardResearchPipeline:
    """Test cases for CardResearchPipeline."""
    
    @pytest.fixture
    def pipeline(self, tmp_path):
        """Create pipeline instance with temp output folder."""
        return CardResearchPipeline(output_folder=str(tmp_path))
    
    @pytest.fixture
    def mock_pipeline(self, tmp_path):
        """Create pipeline with mocked components."""
        mock_ocr = Mock()
        mock_parser = Mock()
        mock_researcher = Mock()
        
        return CardResearchPipeline(
            ocr=mock_ocr,
            parser=mock_parser,
            researcher=mock_researcher,
            output_folder=str(tmp_path)
        )
    
    def test_pipeline_initialization(self, pipeline):
        """Test pipeline initializes correctly."""
        assert pipeline is not None
        assert pipeline.ocr is not None
        assert pipeline.parser is not None
        assert pipeline.researcher is not None
        assert pipeline.output_folder.exists()
    
    def test_pipeline_with_custom_components(self, mock_pipeline):
        """Test pipeline with injected components."""
        assert mock_pipeline.ocr is not None
        assert mock_pipeline.parser is not None
        assert mock_pipeline.researcher is not None
    
    def test_get_status(self, pipeline):
        """Test status retrieval."""
        status = pipeline.get_status()
        
        assert "ocr" in status
        assert "researcher" in status
        assert "output_folder" in status
        assert status["output_folder_exists"] is True
    
    def test_process_text(self, mock_pipeline):
        """Test text processing (skip OCR)."""
        # Setup mocks
        mock_contact = ContactData(
            name="John Doe",
            email="john@example.com"
        )
        mock_pipeline.parser.parse.return_value = mock_contact
        
        from src.researcher import EnrichedData
        mock_enriched = EnrichedData(email_verified=True)
        mock_pipeline.researcher.enrich.return_value = mock_enriched
        
        result = mock_pipeline.process_text("John Doe\njohn@example.com")
        
        assert result["success"] is True
        assert result["contact_data"] is not None
        mock_pipeline.parser.parse.assert_called_once()
    
    def test_process_text_without_enrich(self, mock_pipeline):
        """Test text processing without enrichment."""
        mock_contact = ContactData(name="John Doe")
        mock_pipeline.parser.parse.return_value = mock_contact
        
        result = mock_pipeline.process_text("John Doe", enrich=False)
        
        assert result["success"] is True
        assert result["enriched_data"] is None
        mock_pipeline.researcher.enrich.assert_not_called()
    
    def test_process_image(self, mock_pipeline, tmp_path):
        """Test image processing."""
        # Create mock image file
        image_path = tmp_path / "test_card.jpg"
        image_path.write_bytes(b"fake image data")
        
        # Setup mocks
        mock_pipeline.ocr.extract_text.return_value = [
            ("John Doe", 0.95),
            ("john@example.com", 0.92)
        ]
        mock_pipeline.ocr.get_confidence_stats.return_value = {
            "count": 2,
            "mean_confidence": 0.935
        }
        
        mock_contact = ContactData(
            name="John Doe",
            email="john@example.com"
        )
        mock_pipeline.parser.parse.return_value = mock_contact
        
        from src.researcher import EnrichedData
        mock_enriched = EnrichedData(email_verified=True)
        mock_pipeline.researcher.enrich.return_value = mock_enriched
        
        result = mock_pipeline.process_image(image_path)
        
        assert result["success"] is True
        assert result["ocr_text"] is not None
        assert result["contact_data"] is not None
        assert result["processing_time"] is not None
    
    def test_process_image_error(self, mock_pipeline, tmp_path):
        """Test image processing error handling."""
        image_path = tmp_path / "test_card.jpg"
        image_path.write_bytes(b"fake image data")
        
        mock_pipeline.ocr.extract_text.side_effect = ValueError("OCR failed")
        
        result = mock_pipeline.process_image(image_path)
        
        assert result["success"] is False
        assert result["error"] is not None
    
    def test_process_batch(self, mock_pipeline, tmp_path):
        """Test batch processing."""
        # Create mock image files
        image_paths = []
        for i in range(3):
            path = tmp_path / f"card_{i}.jpg"
            path.write_bytes(b"fake image data")
            image_paths.append(path)
        
        # Setup mocks for successful processing
        mock_pipeline.ocr.extract_text.return_value = [("Test", 0.9)]
        mock_pipeline.ocr.get_confidence_stats.return_value = {"count": 1, "mean_confidence": 0.9}
        mock_pipeline.parser.parse.return_value = ContactData(name="Test")
        
        from src.researcher import EnrichedData
        mock_pipeline.researcher.enrich.return_value = EnrichedData()
        
        result = mock_pipeline.process_batch(image_paths, generate_csv=False)
        
        assert result["total_images"] == 3
        assert result["processed"] == 3
        assert result["failed"] == 0
    
    def test_generate_csv(self, pipeline, tmp_path):
        """Test CSV generation."""
        results = [
            {
                "success": True,
                "contact_data": {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "phone": ["5551234567"],
                    "company": "Tech Corp",
                    "title": "Engineer",
                    "confidence_score": 0.85
                },
                "enriched_data": {
                    "email_verified": True,
                    "email_score": 95,
                    "company_info": {"domain": "techcorp.com"},
                    "github_profile": {},
                    "enrichment_sources": ["hunter.io"]
                },
                "image_path": "/path/to/image.jpg"
            },
            {
                "success": False,
                "error": "Processing failed"
            }
        ]
        
        csv_path = pipeline.generate_csv(results)
        
        assert csv_path.exists()
        assert csv_path.suffix == ".csv"
        
        # Read and verify CSV content
        import pandas as pd
        df = pd.read_csv(csv_path)
        
        assert len(df) == 1  # Only successful result
        assert df.iloc[0]["name"] == "John Doe"
        assert df.iloc[0]["email"] == "john@example.com"
    
    def test_generate_csv_custom_filename(self, pipeline):
        """Test CSV generation with custom filename."""
        results = [
            {
                "success": True,
                "contact_data": {"name": "Test"},
                "enriched_data": {},
                "image_path": "test.jpg"
            }
        ]
        
        csv_path = pipeline.generate_csv(results, filename="custom_output.csv")
        
        assert csv_path.name == "custom_output.csv"
    
    def test_process_folder(self, mock_pipeline, tmp_path):
        """Test folder processing."""
        # Create mock image files
        for i in range(2):
            (tmp_path / f"card_{i}.jpg").write_bytes(b"fake")
            (tmp_path / f"card_{i}.png").write_bytes(b"fake")
        
        # Create non-image file (should be ignored)
        (tmp_path / "readme.txt").write_text("not an image")
        
        # Setup mocks
        mock_pipeline.ocr.extract_text.return_value = [("Test", 0.9)]
        mock_pipeline.ocr.get_confidence_stats.return_value = {"count": 1, "mean_confidence": 0.9}
        mock_pipeline.parser.parse.return_value = ContactData(name="Test")
        
        from src.researcher import EnrichedData
        mock_pipeline.researcher.enrich.return_value = EnrichedData()
        
        result = mock_pipeline.process_folder(tmp_path, generate_csv=False)
        
        assert result["total_images"] == 4  # 2 jpg + 2 png
    
    def test_process_folder_not_found(self, mock_pipeline):
        """Test folder processing with non-existent folder."""
        with pytest.raises(FileNotFoundError):
            mock_pipeline.process_folder("/nonexistent/folder")
    
    def test_process_folder_empty(self, mock_pipeline, tmp_path):
        """Test folder processing with no images."""
        result = mock_pipeline.process_folder(tmp_path)
        
        assert result["success"] is False
        assert "No images found" in result["error"]


class TestPipelineIntegration:
    """Integration tests for pipeline (require full setup)."""
    
    @pytest.mark.skipif(
        True,  # Skip by default
        reason="Integration test - requires full setup"
    )
    def test_full_pipeline(self, tmp_path):
        """Test full pipeline with real components."""
        from PIL import Image
        
        # Create test image
        img = Image.new('RGB', (400, 200), color='white')
        img_path = tmp_path / "test_card.png"
        img.save(img_path)
        
        pipeline = CardResearchPipeline(output_folder=str(tmp_path))
        result = pipeline.process_image(img_path, enrich=False)
        
        assert "success" in result
