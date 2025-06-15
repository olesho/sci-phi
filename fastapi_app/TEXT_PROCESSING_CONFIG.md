# Text Processing Configuration

This document explains how to configure text processing strategies for handling large documents that exceed LLM context windows.

## Environment Variables

Set these environment variables to configure text processing behavior:

```bash
# Text processing strategy (default: intelligent)
# Options: intelligent, truncate, chunk, extract_key
TEXT_PROCESSING_STRATEGY=intelligent

# Maximum character overlap between chunks (default: 200)
MAX_CHUNK_OVERLAP=200

# Enable context window warnings (default: true)
ENABLE_CONTEXT_WARNINGS=true
```

## Processing Strategies

### 1. `intelligent` (Recommended)
- First attempts to extract key sections from academic papers
- If still too large, intelligently chunks the text
- Best balance of information preservation and context management

### 2. `truncate`
- Simply truncates text to fit within context window
- Fastest but may lose important information
- Good for quick testing or when speed is critical

### 3. `chunk`
- Splits text into multiple chunks that fit within context window
- For summaries: creates separate summaries for each chunk
- For questions: uses the first chunk only
- Good for very long documents where all content is important

### 4. `extract_key`
- Extracts and prioritizes key sections from academic papers
- Sections are ordered by importance (Abstract > Conclusion > Introduction > etc.)
- Best for academic papers where specific sections are most relevant

## Model Context Limits

The system automatically handles different model context windows:

| Model | Context Limit (tokens) |
|-------|----------------------|
| granite3.3:8b | 16,000 |
| granite3.2:8b | 8,000 |
| phi4:14b | 16,000 |
| deepseek-r1:14b | 16,000 |
| llama3-chatqa:8b | 8,000 |
| qwen3:14b | 16,000 |

## Usage Examples

### Set via Environment Variables
```bash
export TEXT_PROCESSING_STRATEGY=intelligent
export MAX_CHUNK_OVERLAP=300
export ENABLE_CONTEXT_WARNINGS=true
```

### Check Current Configuration
```bash
cd fastapi_app
python config.py
```

## Token Estimation

The system uses tiktoken for accurate token counting and falls back to character-based estimation (1 token ≈ 4 characters) for models without specific tokenizers.

## Logging

When context window limits are exceeded, the system logs warnings with:
- Model name and its context limit
- Actual token count of the input text
- Strategy being used to handle the large text

Enable detailed logging to monitor text processing behavior. 