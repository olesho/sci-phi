import tiktoken
import re
from typing import List, Dict, Tuple
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Model context limits (tokens)
MODEL_CONTEXT_LIMITS = {
    "granite3.2:8b": 131072,
    "phi4:14b": 16384,
    "deepseek-r1:14b": 131072,
    "llama3-chatqa:8b": 8192,
    "qwen3:14b": 40960,
    # Default fallback
    "default": 8000
}

def get_context_limit(model: str) -> int:
    """Get the context window limit for a specific model."""
    return MODEL_CONTEXT_LIMITS.get(model, MODEL_CONTEXT_LIMITS["default"])

def estimate_tokens(text: str, model: str = "default") -> int:
    """
    Estimate token count for text. Uses tiktoken for OpenAI models,
    rough estimation for other models.
    """
    try:
        # For most models, use gpt-3.5-turbo encoding as approximation
        encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        return len(encoding.encode(text))
    except:
        # Fallback: rough estimation (1 token ≈ 4 characters)
        return len(text) // 4

def truncate_text(text: str, model: str, reserve_tokens: int = 500) -> str:
    """
    Truncate text to fit within model's context window.
    
    Args:
        text: Input text to truncate
        model: Model name to get context limit
        reserve_tokens: Tokens to reserve for prompt template and response
    
    Returns:
        Truncated text that fits within context window
    """
    max_tokens = get_context_limit(model) - reserve_tokens
    
    if estimate_tokens(text, model) <= max_tokens:
        return text
    
    # Binary search to find optimal truncation point
    left, right = 0, len(text)
    best_text = text[:max_tokens * 4]  # Initial rough estimate
    
    while left < right:
        mid = (left + right + 1) // 2
        candidate = text[:mid]
        
        if estimate_tokens(candidate, model) <= max_tokens:
            best_text = candidate
            left = mid
        else:
            right = mid - 1
    
    return best_text

def chunk_text_intelligently(text: str, model: str, chunk_overlap: int = 200) -> List[str]:
    """
    Split text into chunks that fit within context window while preserving semantic meaning.
    
    Args:
        text: Input text to chunk
        model: Model name to get context limit
        chunk_overlap: Number of characters to overlap between chunks
    
    Returns:
        List of text chunks that fit within context window
    """
    max_tokens = get_context_limit(model) - 1000  # Reserve space for prompt and response
    max_chars = max_tokens * 4  # Rough conversion
    
    # Use RecursiveCharacterTextSplitter for intelligent splitting
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_chars,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=[
            "\n\n",  # Paragraph breaks
            "\n",    # Line breaks
            ". ",    # Sentence breaks
            "! ",    # Exclamation breaks
            "? ",    # Question breaks
            ", ",    # Comma breaks
            " ",     # Word breaks
            ""       # Character breaks (last resort)
        ]
    )
    
    chunks = text_splitter.split_text(text)
    
    # Validate each chunk fits within token limit
    validated_chunks = []
    for chunk in chunks:
        if estimate_tokens(chunk, model) <= max_tokens:
            validated_chunks.append(chunk)
        else:
            # If chunk is still too large, truncate it
            validated_chunks.append(truncate_text(chunk, model, reserve_tokens=1000))
    
    return validated_chunks

def extract_key_sections(text: str, model: str) -> str:
    """
    Extract key sections from academic papers to prioritize important content.
    
    Args:
        text: Full paper text
        model: Model name for context limits
    
    Returns:
        Condensed text with key sections prioritized
    """
    # Define section priorities (higher = more important)
    section_priorities = {
        'abstract': 10,
        'introduction': 8,
        'conclusion': 9,
        'conclusions': 9,
        'discussion': 7,
        'methodology': 6,
        'method': 6,
        'methods': 6,
        'results': 7,
        'related work': 5,
        'literature review': 5,
        'background': 4,
        'references': 1,
        'bibliography': 1,
        'acknowledgments': 1
    }
    
    # Split text into sections
    sections = []
    current_section = {"title": "Introduction", "content": "", "priority": 8}
    
    lines = text.split('\n')
    for line in lines:
        line_lower = line.lower().strip()
        
        # Check if line is a section header
        is_header = False
        for section_name, priority in section_priorities.items():
            if (line_lower.startswith(section_name) or 
                (len(line) < 100 and section_name in line_lower and 
                 (line.isupper() or line.endswith(':')))):
                
                # Save previous section
                if current_section["content"].strip():
                    sections.append(current_section)
                
                # Start new section
                current_section = {
                    "title": line.strip(),
                    "content": "",
                    "priority": priority
                }
                is_header = True
                break
        
        if not is_header:
            current_section["content"] += line + "\n"
    
    # Add last section
    if current_section["content"].strip():
        sections.append(current_section)
    
    # Sort sections by priority
    sections.sort(key=lambda x: x["priority"], reverse=True)
    
    # Build condensed text within context limits
    max_tokens = get_context_limit(model) - 1000
    condensed_text = ""
    
    for section in sections:
        section_text = f"\n\n{section['title']}\n{section['content']}"
        
        if estimate_tokens(condensed_text + section_text, model) <= max_tokens:
            condensed_text += section_text
        else:
            # Add as much of this section as possible
            remaining_tokens = max_tokens - estimate_tokens(condensed_text, model)
            if remaining_tokens > 100:  # Only add if we have meaningful space
                partial_section = truncate_text(section_text, model, 
                                              reserve_tokens=estimate_tokens(condensed_text, model))
                condensed_text += partial_section
            break
    
    return condensed_text.strip()

def summarize_and_chunk(text: str, model: str, strategy: str = "intelligent") -> List[str]:
    """
    Apply different strategies to handle large text inputs.
    
    Args:
        text: Input text
        model: Model name
        strategy: One of 'truncate', 'chunk', 'extract_key', 'intelligent'
    
    Returns:
        List of text chunks ready for processing
    """
    if strategy == "truncate":
        return [truncate_text(text, model)]
    
    elif strategy == "chunk":
        return chunk_text_intelligently(text, model)
    
    elif strategy == "extract_key":
        return [extract_key_sections(text, model)]
    
    elif strategy == "intelligent":
        # First try to extract key sections
        condensed = extract_key_sections(text, model)
        
        # If still too large, chunk it
        if estimate_tokens(condensed, model) > get_context_limit(model) - 1000:
            return chunk_text_intelligently(condensed, model)
        else:
            return [condensed]
    
    else:
        raise ValueError(f"Unknown strategy: {strategy}") 