# Business Card Processing API

A production-ready REST API for extracting and enriching contact data from business card images using OCR.

## Features

- 📷 **OCR Extraction**: Extract text from business card images using EasyOCR
- 📝 **Smart Parsing**: Parse extracted text into structured contact fields (name, email, phone, company, etc.)
- 🔍 **Data Enrichment**: Enrich contacts using free APIs (Hunter.io, Abstract API, GitHub)
- 📊 **CSV Export**: Export processed leads to CSV files
- 🚀 **REST API**: Full-featured Flask REST API
- 💰 **Zero Cost**: Uses only free tools and API tiers

## Tech Stack

- **Python 3.8+**
- **Flask 2.3** - Web framework
- **EasyOCR** - Optical character recognition
- **Pandas** - Data processing
- **Free APIs** - Hunter.io, Abstract API, GitHub

## Project Structure

```
business-card-api/
├── app.py                 # Flask entry point
├── config.py              # Configuration management
├── requirements.txt       # Dependencies
├── .env.example           # Environment template
├── src/
│   ├── ocr.py             # CardOCR class
│   ├── parser.py          # CardDataParser class
│   ├── researcher.py      # FreeLeadResearcher class
│   └── pipeline.py        # CardResearchPipeline orchestrator
├── api/
│   └── routes.py          # Flask routes
└── tests/
    └── test_*.py          # Test files
```

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-repo/business-card-api.git
   cd business-card-api
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys (optional)
   ```

5. **Run the server**
   ```bash
   python app.py
   ```

The API will be available at `http://localhost:5000`

## API Endpoints

### Health & Status

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/status` | GET | API and pipeline status |

### Processing

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/process` | POST | Process single business card image |
| `/api/batch` | POST | Process multiple images |
| `/api/parse-text` | POST | Parse raw text (skip OCR) |
| `/api/enrich` | POST | Enrich contact data |

### Files

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/files` | GET | List available CSV files |
| `/api/download/<filename>` | GET | Download CSV file |

## Usage Examples

### Process Single Image

```bash
curl -X POST http://localhost:5000/api/process \
  -F "file=@business_card.jpg"
```

### Process Multiple Images

```bash
curl -X POST http://localhost:5000/api/batch \
  -F "files=@card1.jpg" \
  -F "files=@card2.jpg" \
  -F "files=@card3.jpg"
```

### Parse Text (Skip OCR)

```bash
curl -X POST http://localhost:5000/api/parse-text \
  -H "Content-Type: application/json" \
  -d '{"text": "John Doe\nSoftware Engineer\njohn@company.com\n555-123-4567"}'
```

### Enrich Contact

```bash
curl -X POST http://localhost:5000/api/enrich \
  -H "Content-Type: application/json" \
  -d '{"email": "john@company.com", "name": "John Doe"}'
```

## Response Format

### Success Response

```json
{
  "success": true,
  "data": {
    "contact_data": {
      "name": "John Doe",
      "email": "john@company.com",
      "phone": ["5551234567"],
      "company": "Tech Corp",
      "title": "Software Engineer"
    },
    "enriched_data": {
      "email_verified": true,
      "email_score": 95
    }
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": "Error message here"
}
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CARD_API_ENV` | Environment (development/production) | development |
| `CARD_API_DEBUG` | Enable debug mode | True |
| `CARD_API_SECRET_KEY` | Flask secret key | dev-secret-key |
| `CARD_API_OCR_GPU` | Use GPU for OCR | False |
| `HUNTER_API_KEY` | Hunter.io API key | None |
| `ABSTRACT_API_KEY` | Abstract API key | None |
| `GITHUB_TOKEN` | GitHub token | None |

## Free API Limits

| API | Free Tier |
|-----|-----------|
| Hunter.io | 50 requests/month |
| Abstract API | 100 requests/month |
| GitHub | 5000 requests/hour |

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov=api

# Run specific test file
pytest tests/test_parser.py
```

## Development

### Code Style

- Use snake_case for functions and variables
- Use PascalCase for classes
- Add Google-style docstrings
- Add type hints to function signatures
- Use logging instead of print statements

### Adding New Features

1. Create feature branch
2. Add tests for new functionality
3. Implement the feature
4. Run tests: `pytest`
5. Submit pull request

## License

MIT License - See LICENSE file for details.

## Contributing

Contributions are welcome! Please read the contributing guidelines before submitting a pull request.
