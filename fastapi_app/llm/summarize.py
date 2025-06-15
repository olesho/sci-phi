from langchain_ollama import ChatOllama
from langchain.prompts import ChatPromptTemplate
from langchain_community.cache import SQLiteCache
from langchain.globals import set_llm_cache
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
import langchain
from dotenv import load_dotenv
import os
import getpass

# Load environment variables from .env file
load_dotenv()

# if "GROQ_API_KEY" not in os.environ:
#     os.environ["GROQ_API_KEY"] = getpass.getpass("Enter your Groq API key: ")

# Initialize the cache with SQLite
set_llm_cache(SQLiteCache(database_path=".langchain.db"))

small_summary_size = 8000
medium_summary_size = 32000
large_summary_size = 128000

prompt_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an expert summarization algorithm. "
            "You are given a scientific paper and you need to summarize it in a concise manner. "
            "Only highlight the relevant information from the text. "
        ),
        # Please see the how-to about improving performance with
        # reference examples.
        # MessagesPlaceholder('examples'),
        ("human", "{text}"),
    ]
)

# Different prompt templates for different summary types
summary_prompts = {
    "abstract": ChatPromptTemplate.from_messages([
        (
            "system",
            "You are an expert at creating concise abstracts for scientific papers. "
            "Create a brief abstract that captures the main research question, methodology, "
            "key findings, and implications. Keep it under 300 words."
        ),
        ("human", "{text}"),
    ]),
    
    "key_points": ChatPromptTemplate.from_messages([
        (
            "system",
            "You are an expert at extracting key points from scientific papers. "
            "Extract the most important points as a bulleted list. Focus on: "
            "- Main research question/hypothesis "
            "- Methodology used "
            "- Key findings "
            "- Conclusions and implications "
            "- Limitations mentioned"
        ),
        ("human", "{text}"),
    ]),
    
    "methodology": ChatPromptTemplate.from_messages([
        (
            "system",
            "You are an expert at summarizing research methodologies. "
            "Focus specifically on how the research was conducted: "
            "- Study design "
            "- Data collection methods "
            "- Analysis techniques "
            "- Sample size and characteristics "
            "- Tools and instruments used"
        ),
        ("human", "{text}"),
    ]),
    
    "findings": ChatPromptTemplate.from_messages([
        (
            "system",
            "You are an expert at summarizing research findings and results. "
            "Focus specifically on: "
            "- Main results and discoveries "
            "- Statistical significance "
            "- Patterns and trends identified "
            "- Comparisons with previous research "
            "- Practical implications"
        ),
        ("human", "{text}"),
    ]),
    
    "comprehensive": ChatPromptTemplate.from_messages([
        (
            "system",
            "You are an expert summarization algorithm. "
            "Create a comprehensive summary that covers all aspects of the paper: "
            "introduction, methodology, results, discussion, and conclusions. "
            "Maintain academic tone and include important details."
        ),
        ("human", "{text}"),
    ])
}

def clean_think_tags(output: str) -> str:
    import re
    return re.sub(r"<think>.*?</think>", "", output, flags=re.DOTALL)


def summarize_paper(text: str, model: str = "qwen3:14b") -> str:
    # llm = ChatOllama(model="llama3-chatqa:8b", temperature=0.0)
    llm = ChatOllama(model=model, temperature=0.0)
    # llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.0)  # Uncomment to use Groq
    # llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
    prompt = prompt_template.invoke({"text": text})
    results = llm.invoke(prompt)
    # print(clean_think_tags(results.content))
    return clean_think_tags(results.content)


def generate_summary(
    text: str, 
    summary_type: str = "comprehensive",
    size: str = "medium",
    model: str = "qwen3:14b"
) -> str:
    """
    Generate different types of summaries for scientific papers.
    
    Args:
        text (str): The input text to summarize
        summary_type (str): Type of summary to generate. Options:
            - "abstract": Brief abstract-style summary (under 300 words)
            - "key_points": Bulleted list of key points
            - "methodology": Focus on research methods and approach
            - "findings": Focus on results and discoveries
            - "comprehensive": Complete summary of all aspects
        size (str): Target size of summary. Options:
            - "small": Up to 8000 characters
            - "medium": Up to 32000 characters  
            - "large": Up to 128000 characters
        model (str): LLM model to use for generation
    
    Returns:
        str: Generated summary
    
    Raises:
        ValueError: If invalid summary_type or size is provided
    """
    
    # Validate summary type
    if summary_type not in summary_prompts:
        raise ValueError(f"Invalid summary_type. Must be one of: {list(summary_prompts.keys())}")
    
    # Get size limit
    size_limits = {
        "small": small_summary_size,
        "medium": medium_summary_size,
        "large": large_summary_size
    }
    
    if size not in size_limits:
        raise ValueError(f"Invalid size. Must be one of: {list(size_limits.keys())}")
    
    max_chars = size_limits[size]
    
    # Truncate input text if it's too long for the selected size
    if len(text) > max_chars:
        text = text[:max_chars] + "..."
    
    # Initialize LLM
    llm = ChatOllama(model=model, temperature=0.0)
    # Alternative LLM options (uncomment as needed):
    # llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.0)
    # llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
    
    # Get the appropriate prompt template
    prompt_template = summary_prompts[summary_type]
    
    # Add size constraint to the system message for non-abstract types
    if summary_type != "abstract":
        # Get the current system message and add size constraint
        messages = prompt_template.messages.copy()
        system_msg = messages[0]
        size_constraint = f" Keep the summary under {max_chars} characters."
        
        # Create new system message with size constraint
        updated_system = (
            "system",
            system_msg.prompt.template + size_constraint
        )
        messages[0] = updated_system
        
        # Create new prompt template with updated messages
        prompt_template = ChatPromptTemplate.from_messages(messages)
    
    # Generate the summary
    prompt = prompt_template.invoke({"text": text})
    results = llm.invoke(prompt)
    
    return clean_think_tags(results.content)


def get_available_summary_types() -> list:
    """
    Get list of available summary types.
    
    Returns:
        list: Available summary types
    """
    return list(summary_prompts.keys())


def get_available_sizes() -> list:
    """
    Get list of available summary sizes.
    
    Returns:
        list: Available sizes with their character limits
    """
    return [
        {"size": "small", "limit": small_summary_size},
        {"size": "medium", "limit": medium_summary_size},
        {"size": "large", "limit": large_summary_size}
    ]