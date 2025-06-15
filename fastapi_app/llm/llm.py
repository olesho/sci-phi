from .summarize import summarize_paper, generate_summary
from pydantic import BaseModel
from .questions import question_list
from .questions import question_paper
from .context_utils import (
    summarize_and_chunk, 
    estimate_tokens, 
    get_context_limit,
    extract_key_sections
)
import logging

logger = logging.getLogger(__name__)

class Graph(BaseModel):
    summary: dict[str, str]

model_list = [
    # "phi4:14b",
    # "granite3.2:8b", 
    "deepseek-r1:14b", 
    # "llama3-chatqa:8b", 
    # "qwen3:14b",
]

def extract_summaries(text: str, existing_graph: dict = {}, strategy: str = "intelligent") -> Graph:
    """
    Extract summaries with context window management.
    
    Args:
        text: Input text to summarize
        existing_graph: Existing graph data to update
        strategy: Text processing strategy ('truncate', 'chunk', 'extract_key', 'intelligent')
    """
    existing_summaries = existing_graph.get("summaries", [])
    existing_summary_models = [summary["model"] for summary in existing_summaries]
    
    # Define the 3 summary types to generate
    summary_types = [
        "abstract", 
        "key_points", 
        "comprehensive",
        "findings",
        "methodology",
    ]
    
    for model in model_list:
        # Check if this model already has summaries
        model_summaries = [s for s in existing_summaries if s["model"] == model]
        existing_types = [s.get("type", "comprehensive") for s in model_summaries]
        
        for summary_type in summary_types:
            # Skip if this model-type combination already exists
            if summary_type in existing_types:
                continue
                
            # Check if text fits in context window
            token_count = estimate_tokens(text, model)
            context_limit = get_context_limit(model)
            
            logger.info(f"Model {model}, Type {summary_type}: {token_count} tokens, limit: {context_limit}")
            
            # Process text based on strategy
            if token_count > context_limit - 1000:  # Reserve space for prompt and response
                logger.warning(f"Text too large for {model} ({token_count} tokens). Using strategy: {strategy}")
                
                if strategy == "chunk":
                    # For summarization with chunking, we'll summarize each chunk and combine
                    text_chunks = summarize_and_chunk(text, model, strategy="chunk")
                    summaries = []
                    
                    for i, chunk in enumerate(text_chunks):
                        logger.info(f"Processing chunk {i+1}/{len(text_chunks)} for {model} - {summary_type}")
                        chunk_summary = generate_summary(chunk, summary_type=summary_type, size="medium", model=model)
                        summaries.append(f"Part {i+1}: {chunk_summary}")
                    
                    combined_summary = "\n\n".join(summaries)
                    existing_summaries.append({
                        "model": model, 
                        "summary": combined_summary,
                        "type": summary_type,
                        "strategy": strategy
                    })
                else:
                    # Use single processed text
                    processed_chunks = summarize_and_chunk(text, model, strategy=strategy)
                    processed_text = processed_chunks[0] if processed_chunks else text[:10000]  # Fallback
                    summary = generate_summary(processed_text, summary_type=summary_type, size="medium", model=model)
                    existing_summaries.append({
                        "model": model, 
                        "summary": summary,
                        "type": summary_type,
                        "strategy": strategy
                    })
            else:
                # Text fits within context window
                summary = generate_summary(text, summary_type=summary_type, size="large", model=model)
                existing_summaries.append({
                    "model": model, 
                    "summary": summary,
                    "type": summary_type,
                    "strategy": "full_text"
                })
    
    existing_graph["summaries"] = existing_summaries
    return existing_graph

def extract_questions(text: str, existing_graph: dict = {}, strategy: str = "intelligent") -> Graph:
    """
    Extract question answers with context window management.
    
    Args:
        text: Input text to analyze
        existing_graph: Existing graph data to update  
        strategy: Text processing strategy ('truncate', 'chunk', 'extract_key', 'intelligent')
    """
    existing_questions = existing_graph.get("questions", [])
    existing_question_models = [question["model"] for question in existing_questions]

    for model in model_list:

        # Check if text fits in context window
        processed_text = text
        token_count = estimate_tokens(processed_text, model)
        context_limit = get_context_limit(model)

        while token_count > context_limit - 1000:
            logger.warning(f"Text too large for {model} questions ({token_count} tokens). Using strategy: {strategy}")
            processed_chunks = summarize_and_chunk(processed_text, model, strategy=strategy)
            processed_text = "\n\n".join(processed_chunks)
        
        for question in question_list:
            # Create a unique identifier for model-question combination
            question_id = f"{model}_{question}"
            if question_id in existing_question_models:
                continue
            else:
                answer = question_paper(processed_text, question, model=model)
                existing_questions.append({
                    "model": model, 
                    "question": answer,
                    "question_text": question,  # Store the original question for reference
                    "tokens_used": estimate_tokens(processed_text, model)
                })
    
    existing_graph["questions"] = existing_questions
    return existing_graph

def extract_graph(text: str, existing_graph: dict = {}, strategy: str = "intelligent") -> Graph:
    """
    Extract complete graph with context window management.
    
    Args:
        text: Input text to process
        existing_graph: Existing graph data to update
        strategy: Text processing strategy for handling large texts
    """
    logger.info(f"Starting extraction with strategy: {strategy}")
    logger.info(f"Input text length: {len(text)} characters, estimated tokens: {estimate_tokens(text)}")
    
    existing_graph = extract_summaries(text, existing_graph, strategy=strategy)
    # existing_graph = extract_questions(text, existing_graph, strategy=strategy)
    return existing_graph