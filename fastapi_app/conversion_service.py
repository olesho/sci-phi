import os
import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional
import json

from converter import convert_pdf
from database import update_conversion_status, get_processed_pdf
from config import (
    DATA_DIR, 
    get_pdf_conversion_folder, 
    get_pdf_text_file_path, 
    get_pdf_images_folder_path,
    resolve_file_path,
    make_path_relative
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def convert_pdf_async(uri: str) -> Dict:
    """
    Asynchronously convert a PDF to text and images.
    
    Args:
        uri: The URI of the PDF to convert
        
    Returns:
        Dict with conversion results
    """
    try:
        # Mark conversion as started
        update_conversion_status(uri, conversion_started=True)
        logger.info(f"Starting conversion for PDF: {uri}")
        
        # Get PDF info from database
        pdf_info = get_processed_pdf(uri)
        if not pdf_info:
            raise ValueError(f"PDF not found in database: {uri}")
        
        # Resolve the file path (handles both relative and absolute paths)
        pdf_path = resolve_file_path(pdf_info['file_path'])
        filename = pdf_info['filename']
        
        # Check if PDF file exists
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        # Create subfolder for this PDF using centralized config
        pdf_folder = get_pdf_conversion_folder(filename)
        pdf_folder.mkdir(exist_ok=True)
        
        logger.info(f"Converting PDF at: {pdf_path}")
        logger.info(f"Saving conversion results to: {pdf_folder}")
        
        # Run PDF conversion in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        text, images = await loop.run_in_executor(None, convert_pdf, str(pdf_path))
        
        # Save text to file using centralized config
        text_file_path = get_pdf_text_file_path(filename)
        with open(text_file_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        # Save images using centralized config
        images_folder = get_pdf_images_folder_path(filename)
        images_folder.mkdir(exist_ok=True)
        
        # Save images and create manifest
        image_paths = []
        for i, image in enumerate(images):
            image_path = images_folder / f"image_{i:03d}.png"
            # Assuming images are PIL Image objects - save them
            if hasattr(image, 'save'):
                image.save(image_path)
                image_paths.append(str(image_path))
        
        # Save image manifest
        manifest_path = images_folder / "manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump({
                "total_images": len(image_paths),
                "image_files": [Path(p).name for p in image_paths],
                "conversion_completed": True
            }, f, indent=2)
        
        # Store relative paths in database for portability
        text_file_relative = make_path_relative(str(text_file_path))
        images_folder_relative = make_path_relative(str(images_folder))
        
        # Update database with successful conversion
        update_conversion_status(
            uri=uri,
            is_converted=True,
            text_file_path=text_file_relative,  # Store relative path
            images_folder_path=images_folder_relative  # Store relative path
        )
        
        logger.info(f"Successfully converted PDF: {uri}")
        logger.info(f"Text saved to: {text_file_path}")
        logger.info(f"Images saved to: {images_folder}")
        logger.info(f"Total images extracted: {len(image_paths)}")
        
        # Trigger extraction after successful conversion
        try:
            from extraction_service import trigger_extraction_background
            trigger_extraction_background(uri)
        except Exception as e:
            logger.warning(f"Failed to trigger extraction for {uri}: {str(e)}")
        
        return {
            "success": True,
            "uri": uri,
            "text_file": str(text_file_path),  # Return absolute path in response
            "images_folder": str(images_folder),  # Return absolute path in response
            "image_count": len(image_paths),
            "message": "PDF converted successfully"
        }
        
    except Exception as e:
        error_msg = f"Error converting PDF {uri}: {str(e)}"
        logger.error(error_msg)
        
        # Update database with error
        update_conversion_status(uri=uri, conversion_error=error_msg)
        
        return {
            "success": False,
            "uri": uri,
            "error": error_msg,
            "message": "PDF conversion failed"
        }


async def process_conversion_queue():
    """
    Process all PDFs that are pending conversion.
    This can be called periodically or triggered manually.
    """
    from database import get_pdfs_for_conversion
    
    pending_pdfs = get_pdfs_for_conversion()
    logger.info(f"Found {len(pending_pdfs)} PDFs pending conversion")
    
    results = []
    for pdf_info in pending_pdfs:
        result = await convert_pdf_async(pdf_info['uri'])
        results.append(result)
        
        # Add a small delay between conversions to avoid overwhelming the system
        await asyncio.sleep(1)
    
    return results


def trigger_conversion_background(uri: str):
    """
    Trigger conversion in the background without waiting.
    This is the function to call when a PDF is added.
    """
    try:
        # Create a new event loop if one doesn't exist
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Schedule the conversion
        task = asyncio.create_task(convert_pdf_async(uri))
        logger.info(f"Scheduled background conversion for: {uri}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to schedule conversion for {uri}: {str(e)}")
        return False 