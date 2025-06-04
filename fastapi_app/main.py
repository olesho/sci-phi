from fastapi import FastAPI, HTTPException, BackgroundTasks
from processor import ProcessInputData, process_pdf
from database import (
    init_database, get_all_processed_pdfs, get_processed_pdf, delete_processed_pdf, 
    get_processing_stats, check_uri_exists, check_content_exists, hash_file_content,
    reset_interrupted_conversions
)
from conversion_service import convert_pdf_async, process_conversion_queue
from config import resolve_file_path
import asyncio

app = FastAPI(
    title="PDF Processor API",
    description="API for processing and storing PDF files with SQLite database integration and async conversion",
    version="1.0.0"
)

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

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
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


@app.get("/duplicates")
def get_duplicates():
    """Get information about duplicate content."""
    try:
        from database import get_db_connection
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Find duplicate content (same content_hash, different URIs)
            cursor.execute("""
                SELECT content_hash, COUNT(*) as count, 
                       GROUP_CONCAT(uri, '|') as uris,
                       GROUP_CONCAT(filename, '|') as filenames,
                       MAX(file_size) as file_size
                FROM processed_pdfs 
                WHERE content_hash IS NOT NULL AND is_downloaded = 1 AND status = 'success'
                GROUP BY content_hash 
                HAVING COUNT(*) > 1
                ORDER BY count DESC
            """)
            
            duplicates = []
            for row in cursor.fetchall():
                duplicates.append({
                    "content_hash": row[0],
                    "duplicate_count": row[1],
                    "uris": row[2].split('|') if row[2] else [],
                    "filenames": row[3].split('|') if row[3] else [],
                    "file_size": row[4]
                })
            
            # Get total duplicate stats
            cursor.execute("""
                SELECT COUNT(*) as total_duplicates,
                       SUM(duplicate_files - 1) as wasted_space_count,
                       SUM((duplicate_files - 1) * file_size) as wasted_space_bytes
                FROM (
                    SELECT content_hash, COUNT(*) as duplicate_files, MAX(file_size) as file_size
                    FROM processed_pdfs 
                    WHERE content_hash IS NOT NULL AND is_downloaded = 1 AND status = 'success'
                    GROUP BY content_hash 
                    HAVING COUNT(*) > 1
                )
            """)
            
            stats_row = cursor.fetchone()
            
            return {
                "duplicate_groups": duplicates,
                "summary": {
                    "total_duplicate_groups": len(duplicates),
                    "total_duplicate_files": stats_row[1] if stats_row[1] else 0,
                    "wasted_space_bytes": stats_row[2] if stats_row[2] else 0
                }
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving duplicates: {str(e)}")


@app.post("/deduplicate")
def deduplicate_existing():
    """Analyze existing files and update their content hashes (for files processed before deduplication was implemented)."""
    try:
        from database import get_db_connection, hash_file_content
        from pathlib import Path
        
        updated_count = 0
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get files without content hash
            cursor.execute("""
                SELECT id, file_path FROM processed_pdfs 
                WHERE content_hash IS NULL AND is_downloaded = 1 AND status = 'success'
            """)
            
            files_to_update = cursor.fetchall()
            
            for file_record in files_to_update:
                file_id, file_path = file_record
                # Resolve the file path
                resolved_path = resolve_file_path(file_path)
                if resolved_path.exists():
                    content_hash = hash_file_content(str(resolved_path))
                    if content_hash:
                        cursor.execute("""
                            UPDATE processed_pdfs SET content_hash = ? WHERE id = ?
                        """, (content_hash, file_id))
                        updated_count += 1
            
            conn.commit()
            
        return {
            "message": f"Updated content hashes for {updated_count} files",
            "updated_count": updated_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during deduplication: {str(e)}")