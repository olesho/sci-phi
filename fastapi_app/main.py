from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import json
from processor import ProcessInputData, process_pdf
from database import (
    init_database, get_all_processed_pdfs, get_processed_pdf, get_processed_pdf_by_id, delete_processed_pdf, 
    get_processing_stats, check_uri_exists, check_content_exists, hash_file_content,
    reset_interrupted_conversions, reset_interrupted_extractions
)
from conversion_service import convert_pdf_async, process_conversion_queue
from extraction_service import extract_pdf_async, process_extraction_queue, extract_pdf_selective_async
from config import resolve_file_path, get_pdf_conversion_folder
from llm.questions import question_list
from llm.llm import model_list
import asyncio
from contextlib import asynccontextmanager

async def restart_interrupted_conversions():
    """Background task to restart interrupted conversions."""
    try:
        results = await process_conversion_queue()
        if results:
            print(f"Restarted conversion for {len(results)} PDFs")
        else:
            print("No PDFs needed conversion restart")
    except Exception as e:
        print(f"Error restarting conversions: {str(e)}")


async def restart_interrupted_extractions():
    """Background task to restart interrupted extractions."""
    try:
        results = await process_extraction_queue()
        if results:
            print(f"Restarted extraction for {len(results)} PDFs")
        else:
            print("No PDFs needed extraction restart")
    except Exception as e:
        print(f"Error restarting extractions: {str(e)}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_database()
    
    # Reset any conversions that were interrupted by server restart
    interrupted_count = reset_interrupted_conversions()
    if interrupted_count > 0:
        print(f"Reset {interrupted_count} interrupted conversions")
        
        # Start the conversion queue processing in the background (non-blocking)
        asyncio.create_task(restart_interrupted_conversions())
        print("Started background task to restart interrupted conversions")
    else:
        print("No interrupted conversions found")
    
    # Reset any extractions that were interrupted by server restart
    interrupted_extraction_count = reset_interrupted_extractions()
    if interrupted_extraction_count > 0:
        print(f"Reset {interrupted_extraction_count} interrupted extractions")
        
        # Start the extraction queue processing in the background (non-blocking)
        asyncio.create_task(restart_interrupted_extractions())
        print("Started background task to restart interrupted extractions")
    else:
        print("No interrupted extractions found")
    
    yield
    # Shutdown
    # Add any cleanup code here if needed

app = FastAPI(
    title="PDF Processor API",
    description="API for processing and storing PDF files with SQLite database integration, async conversion, and data extraction",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health")
def health():
    return {"status": "ok", "database": "connected"}


@app.post("/pdfs")
async def process_pdf_endpoint(data: ProcessInputData, background_tasks: BackgroundTasks):
    # Check if URI already exists and was successfully processed
    existing_pdf = check_uri_exists(data.uri)
    if existing_pdf:
        return {
            "message": "PDF with this URI already exists",
            "skipped": True,
            "existing_record": existing_pdf,
            "uri": data.uri
        }
    
    # Process the PDF
    result = process_pdf(data)
    
    # If PDF was successfully downloaded, check for content duplication
    if result.get("downloaded") and result.get("is_pdf") and result.get("file_path"):
        content_hash = hash_file_content(result["file_path"])
        if content_hash:
            existing_content = check_content_exists(content_hash)
            if existing_content:
                # Content already exists, but with different URI
                # Still store the new URI record but mark it as duplicate content
                result["content_duplicate"] = True
                result["original_record"] = existing_content
                result["message"] = "PDF content already exists with different URI"
            else:
                # Trigger conversion in background for new unique content
                background_tasks.add_task(convert_pdf_async, data.uri)
        else:
            # If we can't hash the content, still trigger conversion
            background_tasks.add_task(convert_pdf_async, data.uri)
    
    return result

@app.get("/pdfs")
def get_all_pdfs():
    """Get all processed PDF records from the database."""
    try:
        pdfs = get_all_processed_pdfs()
        
        # Resolve paths for each PDF record
        for pdf in pdfs:
            if pdf.get('file_path'):
                pdf['file_path'] = str(resolve_file_path(pdf['file_path']))
            if pdf.get('text_file_path'):
                pdf['text_file_path'] = str(resolve_file_path(pdf['text_file_path']))
            if pdf.get('images_folder_path'):
                pdf['images_folder_path'] = str(resolve_file_path(pdf['images_folder_path']))
        
        return {
            "count": len(pdfs),
            "pdfs": pdfs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving PDFs: {str(e)}")


@app.get("/pdfs/{uri:path}")
def get_pdf_by_uri(uri: str):
    """Get a specific PDF record by URI."""
    try:
        pdf = get_processed_pdf(uri)
        if not pdf:
            raise HTTPException(status_code=404, detail="PDF not found")
        
        # Resolve paths for response (convert relative to absolute)
        if pdf.get('file_path'):
            pdf['file_path'] = str(resolve_file_path(pdf['file_path']))
        if pdf.get('text_file_path'):
            pdf['text_file_path'] = str(resolve_file_path(pdf['text_file_path']))
        if pdf.get('images_folder_path'):
            pdf['images_folder_path'] = str(resolve_file_path(pdf['images_folder_path']))
            
        return pdf
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving PDF: {str(e)}")


@app.delete("/pdfs/{uri:path}")
def delete_pdf_by_uri(uri: str):
    """Delete a PDF record by URI."""
    try:
        deleted = delete_processed_pdf(uri)
        if not deleted:
            raise HTTPException(status_code=404, detail="PDF not found")
        return {"message": "PDF record deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting PDF: {str(e)}")


@app.post("/convert/{uri:path}")
async def convert_single_pdf(uri: str):
    """Manually trigger conversion for a specific PDF."""
    try:
        pdf = get_processed_pdf(uri)
        if not pdf:
            raise HTTPException(status_code=404, detail="PDF not found")
        
        if not pdf.get('is_downloaded') or pdf.get('status') != 'success':
            raise HTTPException(status_code=400, detail="PDF must be successfully downloaded before conversion")
        
        if pdf.get('is_converted'):
            return {"message": "PDF is already converted", "pdf": pdf}
        
        result = await convert_pdf_async(uri)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error converting PDF: {str(e)}")


@app.post("/convert/process-queue")
async def process_conversion_queue_endpoint():
    """Process all PDFs that are pending conversion."""
    try:
        results = await process_conversion_queue()
        return {
            "message": f"Processed {len(results)} PDFs",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing conversion queue: {str(e)}")


@app.get("/stats")
def get_stats():
    """Get processing statistics."""
    try:
        stats = get_processing_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving stats: {str(e)}")





@app.post("/extract/{paper_id}")
async def extract_single_pdf(paper_id: int):
    """Manually trigger extraction for a specific PDF."""
    try:
        pdf = get_processed_pdf_by_id(paper_id)
        if not pdf:
            raise HTTPException(status_code=404, detail="PDF not found")
        
        if not pdf.get('is_converted'):
            raise HTTPException(status_code=400, detail="PDF must be converted before extraction")
        
        # Use the URI from the PDF record for the async extraction
        result = await extract_pdf_async(pdf['uri'])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting PDF: {str(e)}")


@app.post("/extract/process-queue")
async def process_extraction_queue_endpoint():
    """Process all PDFs that are pending extraction."""
    try:
        results = await process_extraction_queue()
        return {
            "message": f"Processed {len(results)} PDFs",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing extraction queue: {str(e)}")


@app.get("/extract/template")
async def get_extraction_template_endpoint():
    """Get the extraction template structure showing available fields and models."""
    try:
        from extraction_service import get_extraction_template
        return get_extraction_template()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving extraction template: {str(e)}")


@app.get("/extract/{paper_id}")
async def get_extraction_results(paper_id: int):
    """Get extraction results for a specific PDF."""
    try:
        pdf = get_processed_pdf_by_id(paper_id)
        if not pdf:
            raise HTTPException(status_code=404, detail="PDF not found")
        
        if pdf.get('extraction_file_path'):
            extraction_file_path = resolve_file_path(pdf['extraction_file_path'])
        else:
            filename = pdf.get('filename') or Path(pdf.get('file_path', '')).name
            extraction_folder = get_pdf_conversion_folder(filename) / "extraction"
            extraction_file_path = extraction_folder / "extracted_data.json"
        if not extraction_file_path.exists():
            raise HTTPException(status_code=404, detail="Extraction file not found")
        
        # Read and return the extraction results
        with open(extraction_file_path, 'r', encoding='utf-8') as f:
            extraction_data = json.load(f)
        
        return {
            "paper_id": paper_id,
            "uri": pdf['uri'],
            "extraction_file": str(extraction_file_path),
            "extraction_data": extraction_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving extraction results: {str(e)}")

class SelectiveExtractionRequest(BaseModel):
    selected_fields: List[str]  # List of field titles to extract
    selected_models: Optional[List[str]] = None  # Optional list of models to use
    selected_size: Optional[str] = "medium"  # Size preference

@app.post("/extract/{paper_id}/selective")
async def extract_selective_pdf(paper_id: int, request: SelectiveExtractionRequest):
    """Trigger selective extraction for specific fields and models."""
    try:
        pdf = get_processed_pdf_by_id(paper_id)
        if not pdf:
            raise HTTPException(status_code=404, detail="PDF not found")
        
        if not pdf.get('is_converted'):
            raise HTTPException(status_code=400, detail="PDF must be converted before extraction")
        
        # Get the template to validate selected fields
        from extraction_service import get_extraction_template
        template = get_extraction_template()
        
        # Validate selected fields
        available_fields = [field["title"] for field in template["fields"]]
        invalid_fields = [field for field in request.selected_fields if field not in available_fields]
        if invalid_fields:
            raise HTTPException(status_code=400, detail=f"Invalid fields selected: {invalid_fields}")
        
        # Use specified models or default to all available models
        if request.selected_models:
            available_models = [model["name"] for model in template["models"]]
            invalid_models = [model for model in request.selected_models if model not in available_models]
            if invalid_models:
                raise HTTPException(status_code=400, detail=f"Invalid models selected: {invalid_models}")
            selected_models = request.selected_models
        else:
            selected_models = [model["name"] for model in template["models"]]
        
        # Use selective extraction
        result = await extract_pdf_selective_async(
            pdf['uri'], 
            request.selected_fields, 
            selected_models,
            request.selected_size or "medium"
        )
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in selective extraction: {str(e)}")