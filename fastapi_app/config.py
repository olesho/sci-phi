import os
from pathlib import Path

# Get the directory where this config file is located (fastapi_app directory)
BASE_DIR = Path(__file__).parent

# Data directory - where all PDFs and converted content are stored
DATA_DIR = BASE_DIR / "data"

# Database file path
DATABASE_PATH = BASE_DIR / "processed_pdfs.db"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

def get_pdf_file_path(filename: str) -> Path:
    """Get the full path for a PDF file."""
    return DATA_DIR / filename

def get_pdf_conversion_folder(filename: str) -> Path:
    """Get the conversion folder for a PDF (without extension)."""
    pdf_name = Path(filename).stem
    return DATA_DIR / pdf_name

def get_pdf_text_file_path(filename: str) -> Path:
    """Get the text file path for a converted PDF."""
    pdf_name = Path(filename).stem
    return get_pdf_conversion_folder(filename) / f"{pdf_name}.txt"

def get_pdf_images_folder_path(filename: str) -> Path:
    """Get the images folder path for a converted PDF."""
    return get_pdf_conversion_folder(filename) / "images"

def make_path_relative(file_path: str) -> str:
    """Convert an absolute path to relative path from BASE_DIR."""
    try:
        abs_path = Path(file_path)
        if abs_path.is_absolute():
            # Try to make it relative to BASE_DIR
            rel_path = abs_path.relative_to(BASE_DIR)
            return str(rel_path)
        else:
            # Already relative
            return file_path
    except ValueError:
        # Can't make relative to BASE_DIR, store as absolute
        return file_path

def resolve_file_path(file_path: str) -> Path:
    """Resolve a potentially relative path to absolute path."""
    path = Path(file_path)
    if path.is_absolute():
        return path
    else:
        # Relative to BASE_DIR
        return BASE_DIR / path

# Print configuration for debugging
if __name__ == "__main__":
    print(f"BASE_DIR: {BASE_DIR}")
    print(f"DATA_DIR: {DATA_DIR}")
    print(f"DATABASE_PATH: {DATABASE_PATH}") 