# Document ingestion module for receipt and invoice processing
# Handles file uploads, format validation, and conversion to PIL images
# Supports multiple input types: file paths, BytesIO streams, Streamlit uploads
# Includes security measures against malicious files and memory bombs

import os
import hashlib
import io
import logging
from typing import List, Tuple, Union, Dict, BinaryIO
from PIL import Image
from pdf2image import convert_from_path, convert_from_bytes
from pdf2image.exceptions import PDFInfoNotInstalledError

# Configure logging for debugging and error tracking
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Type alias for flexible file input handling
# Supports file paths, BytesIO objects, and Streamlit UploadedFile objects
FileInput = Union[str, io.BytesIO, BinaryIO]

# Security and performance limits
MAX_PDF_PAGES = 5  # Limit PDF pages to prevent RAM exhaustion from large documents
Image.MAX_IMAGE_PIXELS = 10_000_000  # Prevent decompression bomb attacks (10 megapixel limit)

# Supported file format definitions
SUPPORTED_IMAGE_TYPES = {".jpg", ".jpeg", ".png"}
SUPPORTED_PDF_TYPES = {".pdf"}

def generate_file_hash(file_input: FileInput) -> str:
    """Generate SHA256 hash of file for integrity verification and change detection.
    
    Used to detect when user uploads a different file by comparing hashes.
    Prevents re-processing the same file multiple times.
    
    Args:
        file_input: File path, BytesIO, or Streamlit UploadedFile object
    
    Returns:
        Hexadecimal SHA256 hash string (64 characters)
    
    Raises:
        Exception: If file cannot be read or hashed
    """
    hasher = hashlib.sha256()  # Use SHA256 for secure, collision-resistant hashing

    try:
        # Handle file path input
        if isinstance(file_input, str):
            # Read file in chunks to handle large files efficiently
            with open(file_input, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
        else:
            # Handle stream objects (BytesIO, UploadedFile)
            # Need to handle different stream types with varying capabilities
            if hasattr(file_input, 'tell') and hasattr(file_input, 'seek'):
                # Stream supports position tracking
                try:
                    start_pos = file_input.tell()  # Remember current position
                    file_input.seek(0)  # Reset to beginning
                    hasher.update(file_input.read())  # Read entire content
                    file_input.seek(start_pos)  # Restore original position
                except (OSError, io.UnsupportedOperation):
                    # Fallback for streams that don't support tell()
                    file_input.seek(0)
                    hasher.update(file_input.read())
                    file_input.seek(0)  # Reset for next read
            else:
                # For Streamlit UploadedFile or similar objects without tell()
                file_input.seek(0)
                hasher.update(file_input.read())
                file_input.seek(0)  # Reset stream for subsequent operations
            
        return hasher.hexdigest()  # Return hash as hex string
    except Exception as e:
        logger.error(f"Hashing failed: {e}")
        raise

def load_image(file_input: FileInput) -> Image.Image:
    """Load and validate an image file with security checks.
    
    Performs two-pass loading:
    1. Verify file is actually an image (security check)
    2. Load image for processing
    
    Args:
        file_input: File path, BytesIO, or file-like object
    
    Returns:
        PIL Image object in RGB mode
    
    Raises:
        ValueError: If file is corrupted, not an image, or format is unsupported
    """
    try:
        # Step 1: Reset stream cursor if file is a stream object
        if hasattr(file_input, 'seek'):
            file_input.seek(0)
            
        # Step 2: Open image with lazy loading (doesn't load pixel data yet)
        image = Image.open(file_input)
        
        # Step 3: Security check - verify file is actually a valid image
        # This prevents malicious files disguised as images
        image.verify()  # Reads image header and validates format
        
        # Step 4: Re-open for processing (verify() closes the file pointer)
        if hasattr(file_input, 'seek'):
            file_input.seek(0)
        
        image = Image.open(file_input)
            
        # Step 5: Convert to RGB for consistent processing
        # This handles CMYK, grayscale, palette modes, etc.
        return image.convert("RGB")
        
    except Exception as e:
        raise ValueError(f"Invalid or corrupted image file. PIL could not read it. Details: {e}")

def convert_pdf(file_input: FileInput) -> List[Image.Image]:
    """Convert PDF pages to images with page limit enforcement.
    
    Uses pdf2image library which requires Poppler to be installed.
    Converts at 300 DPI for good quality OCR results.
    
    Args:
        file_input: File path or BytesIO containing PDF data
    
    Returns:
        List of PIL Images (one per page, up to MAX_PDF_PAGES)
    
    Raises:
        EnvironmentError: If Poppler is not installed
        RuntimeError: If PDF conversion fails
    """
    try:
        # Enforce page limit to prevent out-of-memory errors
        # Only convert first N pages of large PDFs
        if isinstance(file_input, str):
            # Convert from file path
            return convert_from_path(file_input, dpi=300, last_page=MAX_PDF_PAGES)
        else:
            # Convert from bytes (stream object)
            file_input.seek(0)  # Reset stream position
            pdf_bytes = file_input.read()  # Read entire PDF into memory
            file_input.seek(0)  # Reset for potential reuse
            return convert_from_bytes(pdf_bytes, dpi=300, last_page=MAX_PDF_PAGES)
            
    except PDFInfoNotInstalledError:
        # Provide helpful error message with installation instructions
        raise EnvironmentError(
            "Poppler is not installed. Install it to process PDFs.\n"
            "Windows: Download binary -> Add bin/ to PATH.\n"
            "Mac: brew install poppler\n"
            "Linux: sudo apt install poppler-utils"
        )
    except Exception as e:
        raise RuntimeError(f"PDF Conversion failed: {e}")

def ingest_document(file_input: FileInput, filename: str = "unknown") -> Tuple[List[Image.Image], Dict]:
    """Main entry point for document ingestion and conversion to images.
    
    Orchestrates the complete ingestion workflow:
    1. Validate file is not empty
    2. Generate integrity hash
    3. Route to appropriate converter (image or PDF)
    4. Return images and metadata
    
    Args:
        file_input: File path, BytesIO, or Streamlit UploadedFile
        filename: Original filename for extension detection and metadata
    
    Returns:
        Tuple of (images, metadata):
        - images: List of PIL Image objects (one per page)
        - metadata: Dict with filename, file_type, file_hash, num_pages, truncated flag
    
    Raises:
        ValueError: If file is empty or unsupported format
        RuntimeError: If no images could be extracted
    """
    
    # Step 1: Validate file is not empty
    if isinstance(file_input, str):
        # File path - check size on disk
        if os.path.getsize(file_input) == 0:
            raise ValueError("Cannot process empty file")
        ext = os.path.splitext(file_input)[1].lower()  # Extract extension
        filename = os.path.basename(file_input)  # Get filename from path
    else:
        # Stream object - check size attribute if available
        if hasattr(file_input, 'size') and file_input.size == 0:
            raise ValueError("Cannot process empty file")
        ext = os.path.splitext(filename)[1].lower()  # Extract from provided filename

    # Step 2: Generate integrity hash for change detection
    file_hash = generate_file_hash(file_input)

    # Step 3: Process file based on extension
    images = []
    file_type = "unknown"

    try:
        if ext in SUPPORTED_IMAGE_TYPES:
            # Single image file
            images.append(load_image(file_input))
            file_type = "image"
            
        elif ext in SUPPORTED_PDF_TYPES:
            # PDF - may have multiple pages
            images = convert_pdf(file_input)
            file_type = "pdf"
            
        else:
            # Unsupported format
            raise ValueError(f"Unsupported file format: {ext}")

    except Exception as e:
        logger.error(f"Failed to ingest {filename}: {e}")
        raise

    # Step 4: Validate extraction succeeded
    if not images:
        raise RuntimeError("File processed but no images were extracted.")

    # Step 5: Build metadata dictionary
    metadata = {
        "filename": filename,
        "file_type": file_type,  # "image" or "pdf"
        "file_hash": file_hash,  # SHA256 hash for change detection
        "num_pages": len(images),  # Number of pages/images extracted
        "truncated": len(images) == MAX_PDF_PAGES  # True if PDF was cut off at page limit
    }

    return images, metadata