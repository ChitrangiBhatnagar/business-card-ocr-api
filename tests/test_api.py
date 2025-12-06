"""
Tests for Flask API routes.

Tests the REST API endpoints.
"""

import pytest
import json
import io
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from app import create_app
from config import TestingConfig


class TestAPIRoutes:
    """Test cases for API routes."""
    
    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        app = create_app("testing")
        app.config["TESTING"] = True
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "name" in data
        assert "version" in data
        assert "endpoints" in data
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/health")
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["status"] == "healthy"
    
    def test_status_endpoint(self, client):
        """Test status endpoint."""
        with patch('api.routes.get_pipeline') as mock_get_pipeline:
            mock_pipeline = Mock()
            mock_pipeline.get_status.return_value = {
                "ocr": {"languages": ["en"]},
                "researcher": {"api_usage": {}}
            }
            mock_get_pipeline.return_value = mock_pipeline
            
            response = client.get("/api/status")
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
    
    def test_process_no_file(self, client):
        """Test process endpoint without file."""
        response = client.post("/api/process")
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
    
    def test_process_empty_filename(self, client):
        """Test process endpoint with empty filename."""
        response = client.post(
            "/api/process",
            data={"file": (io.BytesIO(b""), "")},
            content_type="multipart/form-data"
        )
        
        assert response.status_code == 400
    
    def test_process_invalid_extension(self, client):
        """Test process endpoint with invalid file type."""
        response = client.post(
            "/api/process",
            data={"file": (io.BytesIO(b"test"), "test.txt")},
            content_type="multipart/form-data"
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "not allowed" in data["error"]
    
    @patch('api.routes.get_pipeline')
    def test_process_success(self, mock_get_pipeline, client, tmp_path):
        """Test successful file processing."""
        # Setup mock pipeline
        mock_pipeline = Mock()
        mock_pipeline.process_image.return_value = {
            "success": True,
            "contact_data": {"name": "John Doe"},
            "enriched_data": {}
        }
        mock_get_pipeline.return_value = mock_pipeline
        
        # Create test image
        image_data = io.BytesIO(b"fake image data")
        
        response = client.post(
            "/api/process",
            data={"file": (image_data, "test_card.jpg")},
            content_type="multipart/form-data"
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
    
    def test_batch_no_files(self, client):
        """Test batch endpoint without files."""
        response = client.post("/api/batch")
        
        assert response.status_code == 400
    
    @patch('api.routes.get_pipeline')
    def test_batch_success(self, mock_get_pipeline, client):
        """Test successful batch processing."""
        mock_pipeline = Mock()
        mock_pipeline.process_batch.return_value = {
            "success": True,
            "total_images": 2,
            "processed": 2,
            "failed": 0
        }
        mock_get_pipeline.return_value = mock_pipeline
        
        files = [
            (io.BytesIO(b"data1"), "card1.jpg"),
            (io.BytesIO(b"data2"), "card2.jpg")
        ]
        
        response = client.post(
            "/api/batch",
            data={"files": files},
            content_type="multipart/form-data"
        )
        
        assert response.status_code == 200
    
    def test_parse_text_no_data(self, client):
        """Test parse-text endpoint without data."""
        response = client.post("/api/parse-text")
        
        assert response.status_code == 400
    
    def test_parse_text_no_text_field(self, client):
        """Test parse-text endpoint without text field."""
        response = client.post(
            "/api/parse-text",
            data=json.dumps({"other": "data"}),
            content_type="application/json"
        )
        
        assert response.status_code == 400
    
    @patch('api.routes.get_pipeline')
    def test_parse_text_success(self, mock_get_pipeline, client):
        """Test successful text parsing."""
        mock_pipeline = Mock()
        mock_pipeline.process_text.return_value = {
            "success": True,
            "contact_data": {"name": "John Doe"}
        }
        mock_get_pipeline.return_value = mock_pipeline
        
        response = client.post(
            "/api/parse-text",
            data=json.dumps({"text": "John Doe\njohn@example.com"}),
            content_type="application/json"
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
    
    def test_enrich_no_data(self, client):
        """Test enrich endpoint without data."""
        response = client.post("/api/enrich")
        
        assert response.status_code == 400
    
    def test_enrich_missing_required(self, client):
        """Test enrich endpoint without email or name."""
        response = client.post(
            "/api/enrich",
            data=json.dumps({"company": "Test Corp"}),
            content_type="application/json"
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "email" in data["error"] or "name" in data["error"]
    
    @patch('api.routes.get_pipeline')
    def test_enrich_success(self, mock_get_pipeline, client):
        """Test successful enrichment."""
        from src.researcher import EnrichedData
        
        mock_pipeline = Mock()
        mock_pipeline.researcher.enrich.return_value = EnrichedData(
            email_verified=True
        )
        mock_get_pipeline.return_value = mock_pipeline
        
        response = client.post(
            "/api/enrich",
            data=json.dumps({"email": "john@example.com", "name": "John Doe"}),
            content_type="application/json"
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
    
    def test_download_invalid_extension(self, client):
        """Test download with non-CSV file."""
        response = client.get("/api/download/file.txt")
        
        assert response.status_code == 400
    
    def test_download_not_found(self, client):
        """Test download with non-existent file."""
        response = client.get("/api/download/nonexistent.csv")
        
        assert response.status_code == 404
    
    def test_list_files(self, client):
        """Test list files endpoint."""
        response = client.get("/api/files")
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert "files" in data["data"]
