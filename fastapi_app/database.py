import sqlite3
import datetime
import hashlib
from pathlib import Path
from typing import List, Dict, Optional
from contextlib import contextmanager
from config import DATABASE_PATH, get_pdf_conversion_folder
import os
import shutil


def init_database():
    """Initialize the SQLite database and create tables if they don't exist."""
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_pdfs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,             -- unique identifier
                uri TEXT NOT NULL UNIQUE,                         -- source URI of the PDF
                uri_hash TEXT NOT NULL,                           -- hash of the URI for lookups
                content_hash TEXT,                                -- hash of the downloaded file
                filename TEXT NOT NULL,                           -- original filename
                file_path TEXT NOT NULL,                          -- path to the downloaded PDF
                file_size INTEGER,                                -- size on disk in bytes
                content_type TEXT,                                -- HTTP content type from download
                is_downloaded BOOLEAN DEFAULT FALSE,              -- whether the file was downloaded
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- when the record was created
                status TEXT DEFAULT 'success',                    -- success or error state
                error_message TEXT,                               -- error details if any
                is_converted BOOLEAN DEFAULT FALSE,               -- whether conversion to text/images finished
                conversion_started_at TIMESTAMP,                  -- conversion start time
                conversion_completed_at TIMESTAMP,                -- conversion completion time
                conversion_error TEXT,                            -- error message from conversion
                text_file_path TEXT,                              -- path to generated text file
                images_folder_path TEXT                           -- folder containing extracted images
            )
        """)
        
        # Add new columns to existing table if they don't exist
        try:
            cursor.execute("ALTER TABLE processed_pdfs ADD COLUMN uri_hash TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
            
        try:
            cursor.execute("ALTER TABLE processed_pdfs ADD COLUMN content_hash TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE processed_pdfs ADD COLUMN is_converted BOOLEAN DEFAULT FALSE")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE processed_pdfs ADD COLUMN conversion_started_at TIMESTAMP")
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute("ALTER TABLE processed_pdfs ADD COLUMN conversion_completed_at TIMESTAMP")
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute("ALTER TABLE processed_pdfs ADD COLUMN conversion_error TEXT")
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute("ALTER TABLE processed_pdfs ADD COLUMN text_file_path TEXT")
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute("ALTER TABLE processed_pdfs ADD COLUMN images_folder_path TEXT")
        except sqlite3.OperationalError:
            pass
        
        # Extraction tracking columns removed
        
        # Create index on hashes for faster lookups
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_uri_hash ON processed_pdfs(uri_hash)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_hash ON processed_pdfs(content_hash)")
        except sqlite3.OperationalError:
            pass
        
        # Update existing records with missing uri_hash
        cursor.execute("SELECT id, uri FROM processed_pdfs WHERE uri_hash IS NULL")
        rows = cursor.fetchall()
        for row in rows:
            uri_hash = hashlib.sha256(row[1].encode('utf-8')).hexdigest()
            cursor.execute("UPDATE processed_pdfs SET uri_hash = ? WHERE id = ?", (uri_hash, row[0]))
        
        conn.commit()


def hash_uri(uri: str) -> str:
    """Generate a SHA256 hash of the URI."""
    return hashlib.sha256(uri.encode('utf-8')).hexdigest()


def hash_file_content(file_path: str) -> str:
    """Generate a SHA256 hash of file content."""
    hash_sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except Exception:
        return None


def check_uri_exists(uri: str) -> Optional[Dict]:
    """Check if a URI has already been successfully processed."""
    uri_hash = hash_uri(uri)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM processed_pdfs 
            WHERE uri_hash = ? AND is_downloaded = 1 AND status = 'success'
        """, (uri_hash,))
        row = cursor.fetchone()
        return dict(row) if row else None


def check_content_exists(content_hash: str) -> Optional[Dict]:
    """Check if content with this hash already exists."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM processed_pdfs 
            WHERE content_hash = ? AND is_downloaded = 1 AND status = 'success'
        """, (content_hash,))
        row = cursor.fetchone()
        return dict(row) if row else None


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
    try:
        yield conn
    finally:
        conn.close()


def store_processed_pdf(
    uri: str,
    filename: str,
    file_path: str,
    file_size: int,
    content_type: str = None,
    is_downloaded: bool = True,
    status: str = "success",
    error_message: str = None
) -> int:
    """Store information about a processed PDF file."""
    uri_hash = hash_uri(uri)
    content_hash = None
    
    # Calculate content hash if file was successfully downloaded
    if is_downloaded and status == "success" and Path(file_path).exists():
        content_hash = hash_file_content(file_path)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO processed_pdfs 
            (uri, uri_hash, content_hash, filename, file_path, file_size, content_type, is_downloaded, processed_at, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            uri, uri_hash, content_hash, filename, file_path, file_size, content_type, 
            is_downloaded, datetime.datetime.now(), status, error_message
        ))
        conn.commit()
        return cursor.lastrowid


def get_processed_pdf(uri: str) -> Optional[Dict]:
    """Retrieve information about a processed PDF by URI."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM processed_pdfs WHERE uri = ?", (uri,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_processed_pdf_by_id(paper_id: int) -> Optional[Dict]:
    """Retrieve information about a processed PDF by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM processed_pdfs WHERE id = ?", (paper_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_processed_pdfs() -> List[Dict]:
    """Retrieve all processed PDF records."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM processed_pdfs ORDER BY processed_at DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def delete_processed_pdf(uri: str) -> bool:
    """Delete a processed PDF record by URI and associated files."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # First, get the file paths before deleting the record
        cursor.execute("SELECT filename, file_path, text_file_path, images_folder_path FROM processed_pdfs WHERE uri = ?", (uri,))
        row = cursor.fetchone()
        
        if not row:
            return False  # Record not found
        
        filename, file_path, text_file_path, images_folder_path = row
        extraction_folder = get_pdf_conversion_folder(filename) / "extraction"
        extraction_file_path = extraction_folder / "extracted_data.json"
        
        # Delete the database record
        cursor.execute("DELETE FROM processed_pdfs WHERE uri = ?", (uri,))
        deleted = cursor.rowcount > 0
        
        if deleted:
            # Delete the physical files if they exist
            try:
                # Delete the original PDF file
                if file_path and Path(file_path).exists():
                    os.remove(file_path)
                
                # Delete the text file from conversion
                if text_file_path and Path(text_file_path).exists():
                    os.remove(text_file_path)
                
                # Delete the images folder from conversion
                if images_folder_path and Path(images_folder_path).exists():
                    shutil.rmtree(images_folder_path)
                
                # Delete the extraction file
                if extraction_file_path and Path(extraction_file_path).exists():
                    os.remove(extraction_file_path)
                    # Also try to remove the extraction folder if it's empty
                    try:
                        extraction_folder = Path(extraction_file_path).parent
                        if extraction_folder.exists() and extraction_folder.name == "extraction":
                            extraction_folder.rmdir()  # Only removes if empty
                    except OSError:
                        pass  # Folder not empty or other issue
                    
            except Exception as e:
                print(f"Warning: Could not delete some files for {uri}: {str(e)}")
                # Continue even if file deletion fails - the DB record is already deleted
        
        conn.commit()
        return deleted


def update_conversion_status(
    uri: str,
    is_converted: bool = False,
    conversion_started: bool = False,
    conversion_error: str = None,
    text_file_path: str = None,
    images_folder_path: str = None
):
    """Update conversion status for a PDF."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        if conversion_started and not is_converted:
            # Starting conversion
            cursor.execute("""
                UPDATE processed_pdfs 
                SET conversion_started_at = ?, conversion_error = NULL
                WHERE uri = ?
            """, (datetime.datetime.now(), uri))
        elif is_converted:
            # Conversion completed successfully
            cursor.execute("""
                UPDATE processed_pdfs 
                SET is_converted = ?, conversion_completed_at = ?, 
                    text_file_path = ?, images_folder_path = ?, conversion_error = NULL
                WHERE uri = ?
            """, (True, datetime.datetime.now(), text_file_path, images_folder_path, uri))
        elif conversion_error:
            # Conversion failed
            cursor.execute("""
                UPDATE processed_pdfs 
                SET conversion_error = ?
                WHERE uri = ?
            """, (conversion_error, uri))
        
        conn.commit()


def get_pdfs_for_conversion() -> List[Dict]:
    """Get PDFs that are downloaded but not converted yet."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM processed_pdfs 
            WHERE is_downloaded = 1 AND status = 'success' AND is_converted = 0
            ORDER BY processed_at ASC
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_processing_stats() -> Dict:
    """Get statistics about processed PDFs."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Total count
        cursor.execute("SELECT COUNT(*) as total FROM processed_pdfs")
        total = cursor.fetchone()['total']
        
        # Successful downloads
        cursor.execute("SELECT COUNT(*) as successful FROM processed_pdfs WHERE status = 'success' AND is_downloaded = 1")
        successful = cursor.fetchone()['successful']
        
        # Failed attempts
        cursor.execute("SELECT COUNT(*) as failed FROM processed_pdfs WHERE status = 'error'")
        failed = cursor.fetchone()['failed']
        
        # Converted PDFs
        cursor.execute("SELECT COUNT(*) as converted FROM processed_pdfs WHERE is_converted = 1")
        converted = cursor.fetchone()['converted']
        
        # Pending conversion
        cursor.execute("SELECT COUNT(*) as pending FROM processed_pdfs WHERE is_downloaded = 1 AND is_converted = 0")
        pending_conversion = cursor.fetchone()['pending']
        
        extracted = 0
        pending_extraction = 0
        
        # Total file size
        cursor.execute("SELECT SUM(file_size) as total_size FROM processed_pdfs WHERE is_downloaded = 1")
        total_size = cursor.fetchone()['total_size'] or 0
        
        return {
            "total_processed": total,
            "successful_downloads": successful,
            "failed_attempts": failed,
            "converted_pdfs": converted,
            "pending_conversion": pending_conversion,
            "extracted_pdfs": extracted,
            "pending_extraction": pending_extraction,
            "total_file_size_bytes": total_size
        }


def reset_interrupted_conversions() -> int:
    """Find and reset conversions that were started but never completed (interrupted by server restart)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Find PDFs that have conversion_started_at but no conversion_completed_at and is_converted = 0
        # These are conversions that were interrupted
        cursor.execute("""
            SELECT id, uri FROM processed_pdfs 
            WHERE conversion_started_at IS NOT NULL 
            AND conversion_completed_at IS NULL 
            AND is_converted = 0
            AND is_downloaded = 1 
            AND status = 'success'
        """)
        
        interrupted_conversions = cursor.fetchall()
        
        if interrupted_conversions:
            # Reset the conversion status for interrupted conversions
            cursor.execute("""
                UPDATE processed_pdfs 
                SET conversion_started_at = NULL, conversion_error = 'Conversion interrupted by server restart - will retry'
                WHERE conversion_started_at IS NOT NULL 
                AND conversion_completed_at IS NULL 
                AND is_converted = 0
                AND is_downloaded = 1 
                AND status = 'success'
            """)
            
            conn.commit()
            
        return len(interrupted_conversions)


def update_extraction_status(
    uri: str,
    is_extracted: bool = False,
    extraction_started: bool = False,
    extraction_error: str = None,
    extraction_file_path: str = None
):
    """Deprecated: extraction tracking removed."""
    return


def get_pdfs_for_extraction() -> List[Dict]:
    """Get PDFs that are ready for extraction (converted)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM processed_pdfs
            WHERE is_downloaded = 1 AND status = 'success' AND is_converted = 1
            ORDER BY conversion_completed_at ASC
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def reset_interrupted_extractions() -> int:
    """Deprecated: extraction tracking removed."""
    return 0
