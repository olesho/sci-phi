import os
import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional, List
import json
import datetime
from llm import llm
from llm.questions import question_list
from llm.summarize import get_available_summary_types, get_available_sizes
from database import update_extraction_status, get_processed_pdf
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


async def extract_pdf_async(uri: str) -> Dict:
    """
    Asynchronously extract structured data from a converted PDF.
    
    Args:
        uri: The URI of the PDF to extract from
        
    Returns:
        Dict with extraction results
    """
    try:
        # Mark extraction as started
        update_extraction_status(uri, extraction_started=True)
        logger.info(f"Starting extraction for PDF: {uri}")
        
        # Get PDF info from database
        pdf_info = get_processed_pdf(uri)
        if not pdf_info:
            raise ValueError(f"PDF not found in database: {uri}")
        
        # Check if PDF is converted first
        if not pdf_info.get('is_converted'):
            raise ValueError(f"PDF must be converted before extraction: {uri}")
        
        filename = pdf_info['filename']
        text_file_path = resolve_file_path(pdf_info.get('text_file_path', ''))
        images_folder_path = resolve_file_path(pdf_info.get('images_folder_path', ''))
        
        # Check if converted files exist
        if not text_file_path.exists():
            raise FileNotFoundError(f"Text file not found for extraction: {text_file_path}")
        
        logger.info(f"Extracting from text file: {text_file_path}")
        logger.info(f"Images folder: {images_folder_path}")
        
        # Read the text content
        with open(text_file_path, 'r', encoding='utf-8') as f:
            text_content = f.read()
        
        # Check for existing extraction data to extend
        existing_graph = {}
        if pdf_info.get('extraction_file_path'):
            existing_extraction_path = resolve_file_path(pdf_info.get('extraction_file_path', ''))
            if existing_extraction_path.exists():
                try:
                    with open(existing_extraction_path, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                        existing_graph = existing_data
                        logger.info(f"Found existing extraction data with {len(existing_data.get('summaries', []))} summaries and {len(existing_data.get('questions', []))} questions")
                except Exception as e:
                    logger.warning(f"Could not read existing extraction data: {str(e)}")
                    existing_graph = {}
        
        # Import strategy from config
        from config import TEXT_PROCESSING_STRATEGY
        
        # Run extraction in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        extracted_data = await loop.run_in_executor(
            None, 
            extract_structured_data, 
            text_content, 
            existing_graph,
            str(images_folder_path) if images_folder_path.exists() else None,
            TEXT_PROCESSING_STRATEGY
        )
        
        # Create extraction results folder
        pdf_folder = get_pdf_conversion_folder(filename)
        extraction_folder = pdf_folder / "extraction"
        extraction_folder.mkdir(exist_ok=True)
        
        # Save extraction results
        extraction_file_path = extraction_folder / "extracted_data.json"
        with open(extraction_file_path, 'w', encoding='utf-8') as f:
            json.dump(extracted_data, f, indent=2, ensure_ascii=False)
        
        # Store relative path in database for portability
        extraction_file_relative = make_path_relative(str(extraction_file_path))
        
        # Update database with successful extraction
        update_extraction_status(
            uri=uri,
            is_extracted=True,
            extraction_file_path=extraction_file_relative
        )
        
        logger.info(f"Successfully extracted data from PDF: {uri}")
        logger.info(f"Extraction results saved to: {extraction_file_path}")
        logger.info(f"Extracted {len(extracted_data.get('summaries', []))} summaries")
        logger.info(f"Extracted {len(extracted_data.get('questions', []))} questions")
        
        return {
            "success": True,
            "uri": uri,
            "extraction_file": str(extraction_file_path),
            "extracted_summaries": len(extracted_data.get('summaries', [])),
            "extracted_questions": len(extracted_data.get('questions', [])),
            "message": "PDF extraction completed successfully"
        }
        
    except Exception as e:
        error_msg = f"Error extracting from PDF {uri}: {str(e)}"
        logger.error(error_msg)
        
        # Update database with error
        update_extraction_status(uri=uri, extraction_error=error_msg)
        
        return {
            "success": False,
            "uri": uri,
            "error": error_msg,
            "message": "PDF extraction failed"
        }

def extract_structured_data(text_content: str, existing_graph: dict = {}, images_folder: Optional[str] = None, strategy: str = "intelligent") -> Dict:
    """
    Extract structured data from PDF text content with context window management.
    
    Args:
        text_content: The text content from the PDF
        existing_graph: Existing extraction data to update
        images_folder: Path to folder containing extracted images (optional)
        strategy: Strategy for handling large texts ('intelligent', 'truncate', 'chunk', 'extract_key')
    
    Returns:
        Dict containing extracted structured data
    """
    new_graph = llm.extract_graph(text_content, existing_graph=existing_graph, strategy=strategy)
    return new_graph

# def extract_structured_data(text_content: str, images_folder: Optional[str] = None) -> Dict:
#     """
#     Extract structured data from PDF text content.
#     This is a placeholder implementation - customize based on your needs.
    
#     Args:
#         text_content: The text content from the PDF
#         images_folder: Path to folder containing extracted images (optional)
        
#     Returns:
#         Dict containing extracted structured data
#     """
#     # Basic text analysis and extraction
#     lines = text_content.split('\n')
#     non_empty_lines = [line.strip() for line in lines if line.strip()]
    
#     # Extract sections (lines that look like headers)
#     sections = []
#     current_section = None
#     current_content = []
    
#     for line in non_empty_lines:
#         # Simple heuristic: lines with all caps or ending with ':' might be headers
#         if (len(line) < 100 and 
#             (line.isupper() or line.endswith(':') or 
#              any(keyword in line.lower() for keyword in ['section', 'chapter', 'part', 'introduction', 'conclusion']))):
            
#             # Save previous section
#             if current_section:
#                 sections.append({
#                     "title": current_section,
#                     "content": '\n'.join(current_content),
#                     "word_count": len(' '.join(current_content).split())
#                 })
            
#             # Start new section
#             current_section = line
#             current_content = []
#         else:
#             current_content.append(line)
    
#     # Add the last section
#     if current_section:
#         sections.append({
#             "title": current_section,
#             "content": '\n'.join(current_content),
#             "word_count": len(' '.join(current_content).split())
#         })
    
#     # Extract potential entities (simple pattern matching)
#     import re
#     entities = []
    
#     # Email addresses
#     emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text_content)
#     entities.extend([{"type": "email", "value": email} for email in set(emails)])
    
#     # URLs
#     urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text_content)
#     entities.extend([{"type": "url", "value": url} for url in set(urls)])
    
#     # Phone numbers (simple pattern)
#     phones = re.findall(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text_content)
#     entities.extend([{"type": "phone", "value": phone} for phone in set(phones)])
    
#     # Dates (simple pattern)
#     dates = re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', text_content)
#     entities.extend([{"type": "date", "value": date} for date in set(dates)])
    
#     # Image information if available
#     image_info = []
#     if images_folder and Path(images_folder).exists():
#         image_files = list(Path(images_folder).glob("*.png"))
#         image_info = [{"filename": img.name, "path": str(img)} for img in image_files]
    
#     return {
#         "text_statistics": {
#             "total_characters": len(text_content),
#             "total_words": len(text_content.split()),
#             "total_lines": len(lines),
#             "non_empty_lines": len(non_empty_lines)
#         },
#         "sections": sections,
#         "entities": entities,
#         "images": image_info,
#         "extraction_metadata": {
#             "extraction_method": "basic_text_analysis",
#             "timestamp": datetime.datetime.now().isoformat()
#         }
#     }


async def process_extraction_queue():
    """
    Process all PDFs that are pending extraction.
    This can be called periodically or triggered manually.
    """
    from database import get_pdfs_for_extraction
    
    pending_pdfs = get_pdfs_for_extraction()
    logger.info(f"Found {len(pending_pdfs)} PDFs pending extraction")
    
    results = []
    for pdf_info in pending_pdfs:
        result = await extract_pdf_async(pdf_info['uri'])
        results.append(result)
        
        # Add a small delay between extractions to avoid overwhelming the system
        await asyncio.sleep(1)
    
    return results


def trigger_extraction_background(uri: str):
    """
    Trigger extraction in the background without waiting.
    This is the function to call when a PDF is converted.
    """
    try:
        # Create a new event loop if one doesn't exist
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Schedule the extraction
        task = asyncio.create_task(extract_pdf_async(uri))
        logger.info(f"Scheduled background extraction for: {uri}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to schedule extraction for {uri}: {str(e)}")
        return False

def get_extraction_template() -> Dict:
    """
    Get the extraction template that defines the structure of extracted reports.
    
    Returns:
        Dict containing the template structure with fields and models
    """
    # Get available summary types and sizes
    summary_types = get_available_summary_types()
    size_info = get_available_sizes()
    available_sizes = [s["size"] for s in size_info]
    
    # Build fields structure
    fields = []
    
    # Add summary fields
    for summary_type in summary_types:
        supported_sizes = available_sizes.copy()  # All sizes supported for summaries
        fields.append({
            "kind": "summary",
            "title": summary_type,
            "supported_size": supported_sizes,
            "description": get_summary_description(summary_type)
        })
    
    # Add question fields
    for question in question_list:
        fields.append({
            "kind": "question",
            "title": question,
            "supported_size": ["small", "medium"],  # Questions typically use smaller sizes
            "description": f"Answer to: {question}"
        })
    
    # Define models with their context sizes
    models = [
        {
            "name": "deepseek-r1:14b",
            "context_size": 131072,
            "description": "DeepSeek R1 14B parameter model"
        },
        {
            "name": "granite3.2:8b", 
            "context_size": 131072,
            "description": "Granite 3.2 8B parameter model"
        },
        {
            "name": "phi4:14b",
            "context_size": 16384,
            "description": "Phi-4 14B parameter model"
        },
        {
            "name": "llama3-chatqa:8b",
            "context_size": 8192,
            "description": "Llama 3 ChatQA 8B parameter model"
        },
        {
            "name": "qwen3:14b",
            "context_size": 40960,
            "description": "Qwen 3 14B parameter model"
        }
    ]
    
    return {
        "fields": fields,
        "models": models,
        "size_limits": {
            size_info[i]["size"]: size_info[i]["limit"] 
            for i in range(len(size_info))
        },
        "metadata": {
            "total_summary_types": len(summary_types),
            "total_questions": len(question_list),
            "total_fields": len(fields),
            "template_version": "1.0.0"
        }
    }


def get_summary_description(summary_type: str) -> str:
    """Get description for each summary type."""
    descriptions = {
        "abstract": "Brief abstract-style summary capturing main research question, methodology, findings, and implications (under 300 words)",
        "key_points": "Bulleted list of the most important points including research question, methodology, findings, conclusions, and limitations",
        "methodology": "Detailed summary focused on research methods, study design, data collection, analysis techniques, and tools used",
        "findings": "Summary focused on main results, discoveries, statistical significance, patterns, and practical implications",
        "comprehensive": "Complete detailed summary covering all aspects: introduction, methodology, results, discussion, and conclusions"
    }
    return descriptions.get(summary_type, f"Summary of type: {summary_type}")

async def extract_pdf_selective_async(
    uri: str, 
    selected_fields: List[str], 
    selected_models: List[str],
    selected_size: str = "medium"
) -> Dict:
    """
    Asynchronously extract selected fields from a converted PDF.
    
    Args:
        uri: The URI of the PDF to extract from
        selected_fields: List of field titles to extract
        selected_models: List of models to use for extraction
        selected_size: Size preference for extraction
        
    Returns:
        Dict with extraction results
    """
    try:
        # Mark extraction as started
        update_extraction_status(uri, extraction_started=True)
        logger.info(f"Starting selective extraction for PDF: {uri}")
        logger.info(f"Selected fields: {selected_fields}")
        logger.info(f"Selected models: {selected_models}")
        
        # Get PDF info from database
        pdf_info = get_processed_pdf(uri)
        if not pdf_info:
            raise ValueError(f"PDF not found in database: {uri}")
        
        # Check if PDF is converted first
        if not pdf_info.get('is_converted'):
            raise ValueError(f"PDF must be converted before extraction: {uri}")
        
        filename = pdf_info['filename']
        text_file_path = resolve_file_path(pdf_info.get('text_file_path', ''))
        images_folder_path = resolve_file_path(pdf_info.get('images_folder_path', ''))
        
        # Check if converted files exist
        if not text_file_path.exists():
            raise FileNotFoundError(f"Text file not found for extraction: {text_file_path}")
        
        logger.info(f"Extracting from text file: {text_file_path}")
        
        # Read the text content
        with open(text_file_path, 'r', encoding='utf-8') as f:
            text_content = f.read()
        
        # Check for existing extraction data to extend
        existing_graph = {}
        if pdf_info.get('extraction_file_path'):
            existing_extraction_path = resolve_file_path(pdf_info.get('extraction_file_path', ''))
            if existing_extraction_path.exists():
                try:
                    with open(existing_extraction_path, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                        existing_graph = existing_data
                        logger.info(f"Found existing extraction data")
                except Exception as e:
                    logger.warning(f"Could not read existing extraction data: {str(e)}")
                    existing_graph = {}
        
        # Import strategy from config
        from config import TEXT_PROCESSING_STRATEGY
        
        # Run selective extraction in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        extracted_data = await loop.run_in_executor(
            None, 
            extract_selective_structured_data, 
            text_content, 
            selected_fields,
            selected_models,
            selected_size,
            existing_graph,
            str(images_folder_path) if images_folder_path.exists() else None,
            TEXT_PROCESSING_STRATEGY
        )
        
        # Create extraction results folder
        pdf_folder = get_pdf_conversion_folder(filename)
        extraction_folder = pdf_folder / "extraction"
        extraction_folder.mkdir(exist_ok=True)
        
        # Save extraction results
        extraction_file_path = extraction_folder / "extracted_data.json"
        with open(extraction_file_path, 'w', encoding='utf-8') as f:
            json.dump(extracted_data, f, indent=2, ensure_ascii=False)
        
        # Store relative path in database for portability
        extraction_file_relative = make_path_relative(str(extraction_file_path))
        
        # Update database with successful extraction
        update_extraction_status(
            uri=uri,
            is_extracted=True,
            extraction_file_path=extraction_file_relative
        )
        
        logger.info(f"Successfully extracted selected data from PDF: {uri}")
        logger.info(f"Extraction results saved to: {extraction_file_path}")
        logger.info(f"Extracted {len(extracted_data.get('summaries', []))} summaries")
        logger.info(f"Extracted {len(extracted_data.get('questions', []))} questions")
        
        return {
            "success": True,
            "uri": uri,
            "extraction_file": str(extraction_file_path),
            "extracted_summaries": len(extracted_data.get('summaries', [])),
            "extracted_questions": len(extracted_data.get('questions', [])),
            "selected_fields": selected_fields,
            "selected_models": selected_models,
            "message": "Selective PDF extraction completed successfully"
        }
        
    except Exception as e:
        error_msg = f"Error in selective extraction from PDF {uri}: {str(e)}"
        logger.error(error_msg)
        
        # Update database with error
        update_extraction_status(uri=uri, extraction_error=error_msg)
        
        return {
            "success": False,
            "uri": uri,
            "error": error_msg,
            "message": "Selective PDF extraction failed"
        }


def extract_selective_structured_data(
    text_content: str, 
    selected_fields: List[str],
    selected_models: List[str], 
    selected_size: str,
    existing_graph: dict = {}, 
    images_folder: Optional[str] = None, 
    strategy: str = "intelligent"
) -> Dict:
    """
    Extract selected structured data from PDF text content.
    
    Args:
        text_content: The text content from the PDF
        selected_fields: List of field titles to extract
        selected_models: List of models to use for extraction
        selected_size: Size preference for extraction
        existing_graph: Existing extraction data to update
        images_folder: Path to folder containing extracted images (optional)
        strategy: Strategy for handling large texts
    
    Returns:
        Dict containing extracted structured data for selected fields only
    """
    from llm.summarize import generate_summary
    from llm.questions import question_paper
    from llm.context_utils import summarize_and_chunk, estimate_tokens, get_context_limit
    
    # Get template to understand field types
    template = get_extraction_template()
    field_lookup = {field["title"]: field for field in template["fields"]}
    
    # Separate summary fields from question fields
    summary_fields = [field for field in selected_fields if field_lookup.get(field, {}).get("kind") == "summary"]
    question_fields = [field for field in selected_fields if field_lookup.get(field, {}).get("kind") == "question"]
    
    # Initialize result structure
    result = {
        "summaries": existing_graph.get("summaries", []),
        "questions": existing_graph.get("questions", [])
    }
    
    # Process summary fields
    if summary_fields:
        logger.info(f"Processing {len(summary_fields)} summary fields: {summary_fields}")
        for model in selected_models:
            for summary_type in summary_fields:
                # Check if this combination already exists
                existing_summaries = [s for s in result["summaries"] 
                                    if s.get("model") == model and s.get("type") == summary_type]
                if existing_summaries:
                    logger.info(f"Skipping existing summary: {model} - {summary_type}")
                    continue
                
                try:
                    # Check context window
                    token_count = estimate_tokens(text_content, model)
                    context_limit = get_context_limit(model)
                    
                    processed_text = text_content
                    if token_count > context_limit - 1000:
                        logger.warning(f"Text too large for {model} ({token_count} tokens). Using strategy: {strategy}")
                        processed_chunks = summarize_and_chunk(text_content, model, strategy=strategy)
                        processed_text = processed_chunks[0] if processed_chunks else text_content[:10000]
                    
                    # Generate summary
                    summary = generate_summary(
                        processed_text, 
                        summary_type=summary_type, 
                        size=selected_size, 
                        model=model
                    )
                    
                    result["summaries"].append({
                        "model": model,
                        "summary": summary,
                        "type": summary_type,
                        "strategy": strategy,
                        "selective_extraction": True
                    })
                    
                    logger.info(f"Generated {summary_type} summary with {model}")
                    
                except Exception as e:
                    logger.error(f"Error generating summary {summary_type} with {model}: {str(e)}")
    
    # Process question fields
    if question_fields:
        logger.info(f"Processing {len(question_fields)} question fields")
        for model in selected_models:
            for question in question_fields:
                # Create unique identifier for model-question combination
                question_id = f"{model}_{question}"
                existing_questions = [q for q in result["questions"] 
                                    if q.get("model") == model and q.get("question_text") == question]
                if existing_questions:
                    logger.info(f"Skipping existing question: {model} - {question}")
                    continue
                
                try:
                    # Check context window
                    token_count = estimate_tokens(text_content, model)
                    context_limit = get_context_limit(model)
                    
                    processed_text = text_content
                    if token_count > context_limit - 1000:
                        logger.warning(f"Text too large for {model} ({token_count} tokens). Using strategy: {strategy}")
                        processed_chunks = summarize_and_chunk(text_content, model, strategy=strategy)
                        processed_text = "\n\n".join(processed_chunks)
                    
                    # Generate answer
                    answer = question_paper(processed_text, question, model=model)
                    
                    result["questions"].append({
                        "model": model,
                        "question": answer,
                        "question_text": question,
                        "tokens_used": estimate_tokens(processed_text, model),
                        "selective_extraction": True
                    })
                    
                    logger.info(f"Generated answer for '{question}' with {model}")
                    
                except Exception as e:
                    logger.error(f"Error generating answer for '{question}' with {model}: {str(e)}")
    
    return result
