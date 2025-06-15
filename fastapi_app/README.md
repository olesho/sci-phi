# PDF Processor API

API for PDF processing.

## Features

- Download PDF files from URLs
- Store processing information in SQLite database
- Caching: Avoid re-downloading already processed PDFs
- Comprehensive API endpoints for managing processed PDFs
- Processing statistics and analytics

## Installation

1. Install dependencies:
```bash
uv sync
```

2. Run the application:

**For development with hot reload (excluding data directory from reload):**
```bash
# Option 1: Using the development script
python start_dev.py

# Option 2: Using uv run uvicorn directly with excludes
uv run uvicorn main:app --reload --reload-exclude "data/*" --reload-exclude "*.db" --reload-exclude "__pycache__/*"

# Option 3: Using the uvicorn config file
python uvicorn_config.py

# Option 4: Using Docker Compose development profile
docker-compose --profile development up fastapi-app-dev
```

**For production:**
```bash
# Basic uvicorn (no hot reload)
uv run uvicorn main:app

# Using Docker Compose production profile
docker-compose --profile production up fastapi-app
```

The application will be available at `http://localhost:8000`

## API Endpoints

### Core Processing
- `POST /process` - Process a PDF from URL
- `GET /health` - Health check endpoint

### Database Operations
- `GET /pdfs` - Get all processed PDF records
- `GET /pdfs/{uri}` - Get specific PDF record by URI
- `DELETE /pdfs/{uri}` - Delete PDF record by URI
- `GET /stats` - Get processing statistics

## Database Schema

The SQLite database stores processed PDF information with the following fields:

- `id` - Primary key
- `uri` - Original PDF URL (unique)
- `filename` - Local filename
- `file_path` - Full path to downloaded file
- `file_size` - File size in bytes
- `content_type` - HTTP content type
- `is_downloaded` - Whether download was successful
- `processed_at` - Timestamp of processing
- `status` - Processing status (success/error)
- `error_message` - Error details if processing failed

## Usage Examples

### Process a PDF
```bash
curl -X POST "http://localhost:8000/process" \
     -H "Content-Type: application/json" \
     -d '{"uri": "https://example.com/document.pdf"}'
```

### Get all processed PDFs
```bash
curl -X GET "http://localhost:8000/pdfs"
```

### Get processing statistics
```bash
curl -X GET "http://localhost:8000/stats"
```

### Get specific PDF by URI
```bash
curl -X GET "http://localhost:8000/pdfs/https%3A//example.com/document.pdf"
```

## Features

- **Caching**: Already processed PDFs are retrieved from the database without re-downloading
- **Error Handling**: Failed processing attempts are logged in the database
- **Statistics**: Track processing success rates and storage usage
- **File Management**: Downloads are stored in the `data/` directory
- **Database Persistence**: All processing history is maintained in `processed_pdfs.db`

## API Documentation

Once running, visit `http://localhost:8000/docs` for interactive API documentation (Swagger UI) or `http://localhost:8000/redoc` for ReDoc documentation. 
