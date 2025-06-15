import os
import requests
from urllib.parse import urlparse
from pathlib import Path

from fastapi import HTTPException
from pydantic import BaseModel
from database import store_processed_pdf, get_processed_pdf
from config import DATA_DIR, get_pdf_file_path, make_path_relative, resolve_file_path


class ProcessInputData(BaseModel):
    uri: str

def process_pdf(data: ProcessInputData):
    try:
        # Check if this PDF has already been processed
        existing_record = get_processed_pdf(data.uri)
        if existing_record and existing_record['is_downloaded'] and existing_record['status'] == 'success':
            # Resolve the path from database (might be relative or absolute)
            resolved_path = resolve_file_path(existing_record['file_path'])
            # Check if file still exists
            if resolved_path.exists():
                return {
                    "uri": data.uri,
                    "is_pdf": True,
                    "downloaded": True,
                    "file_path": str(resolved_path),  # Return absolute path in response
                    "file_size": existing_record['file_size'],
                    "message": "PDF already processed and available",
                    "from_cache": True,
                    "processed_at": existing_record['processed_at'],
                    "is_converted": existing_record.get('is_converted', False),
                    "conversion_status": "completed" if existing_record.get('is_converted') else "pending"
                }
        
        # Parse the URL
        parsed_url = urlparse(data.uri)
        
        # Make a HEAD request to check content type without downloading the full file
        response = requests.head(data.uri, allow_redirects=True, timeout=10)
        response.raise_for_status()
        
        # Check if the content type indicates PDF
        content_type = response.headers.get('content-type', '').lower()
        is_pdf = 'application/pdf' in content_type
        
        # Also check file extension as backup
        if not is_pdf:
            path = parsed_url.path.lower()
            is_pdf = path.endswith('.pdf')
        
        if not is_pdf:
            # Store failed attempt in database
            store_processed_pdf(
                uri=data.uri,
                filename="",
                file_path="",
                file_size=0,
                content_type=content_type,
                is_downloaded=False,
                status="error",
                error_message="URL does not point to a PDF resource"
            )
            
            return {
                "uri": data.uri,
                "is_pdf": False,
                "message": "The URL does not point to a PDF resource",
                "content_type": content_type
            }
        
        # Ensure data directory exists
        DATA_DIR.mkdir(exist_ok=True)
        
        # Extract filename from URL
        filename = os.path.basename(parsed_url.path)
        if not filename or not filename.endswith('.pdf'):
            filename = f"pdf_{hash(data.uri) % 10000}.pdf"
        
        # Full path for the downloaded file using centralized config
        file_path = get_pdf_file_path(filename)
        
        # Download the PDF
        download_response = requests.get(data.uri, timeout=30)
        download_response.raise_for_status()
        
        # Save the file
        downloaded = False
        with open(file_path, 'wb') as f:
            f.write(download_response.content)
            downloaded = True
        
        # Store relative path in database for portability
        relative_path = make_path_relative(str(file_path))
        
        # Store successful processing in database
        db_id = store_processed_pdf(
            uri=data.uri,
            filename=filename,
            file_path=relative_path,  # Store relative path
            file_size=len(download_response.content),
            content_type=content_type,
            is_downloaded=downloaded,
            status="success"
        )
        
        return {
            "uri": data.uri,
            "is_pdf": True,
            "downloaded": downloaded,
            "file_path": str(file_path),  # Return absolute path in response
            "file_size": len(download_response.content),
            "message": "PDF successfully downloaded and queued for conversion",
            "database_id": db_id,
            "from_cache": False,
            "is_converted": False,
            "conversion_status": "queued"
        }
        
    except requests.exceptions.RequestException as e:
        # Store failed attempt in database
        store_processed_pdf(
            uri=data.uri,
            filename="",
            file_path="",
            file_size=0,
            is_downloaded=False,
            status="error",
            error_message=f"Error accessing URL: {str(e)}"
        )
        raise HTTPException(status_code=400, detail=f"Error accessing URL: {str(e)}")
    except Exception as e:
        # Store failed attempt in database
        store_processed_pdf(
            uri=data.uri,
            filename="",
            file_path="",
            file_size=0,
            is_downloaded=False,
            status="error",
            error_message=f"Error processing request: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}") 