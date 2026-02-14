# Image preprocessing pipeline for improving OCR accuracy
# Handles format conversion, transparency, noise removal, and enhancement
# Designed specifically for receipt/invoice images to maximize text clarity
# Compatible with Google Gemini Vision API requirements

from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from typing import Union
import numpy as np
import cv2

def preprocess_image(image_input: Union[str, Image.Image]) -> Image.Image:
    """Apply comprehensive preprocessing to improve OCR accuracy.
    
    This function prepares images for AI-based OCR by:
    - Handling transparency and various color modes
    - Converting to grayscale
    - Enhancing contrast
    - Applying binarization (Otsu thresholding)
    - Removing noise
    - Resizing large images for faster processing
    
    Args:
        image_input: File path string, PIL Image, or file-like object
    
    Returns:
        Preprocessed PIL Image in grayscale mode optimized for OCR
    
    Raises:
        ValueError: If image cannot be loaded or has invalid dimensions
    """
    # Step 1: Safe image loading with format detection
    try:
        # Handle different input types (file path, PIL Image, BytesIO)
        if isinstance(image_input, str):
            img = Image.open(image_input)  # Load from file path
        elif isinstance(image_input, Image.Image):
            img = image_input.copy()  # Copy to avoid modifying original
        else:
            # Assume it's a file-like object (BytesIO, UploadedFile)
            img = Image.open(image_input)

        # Normalize orientation using EXIF metadata if present
        # This fixes photos taken with rotated cameras
        img = ImageOps.exif_transpose(img)
    except Exception as e:
        raise ValueError(f"Could not load image for preprocessing: {e}")

    # Validation: Check for empty or corrupted images
    if img.width == 0 or img.height == 0:
        raise ValueError("Image has invalid dimensions (width or height is 0)")

    # Step 2: Handle transparency properly to prevent black backgrounds
    # Direct RGBA->RGB conversion turns transparent areas black
    # Solution: paste onto white background first
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        # Create white background matching image size
        background = Image.new('RGB', img.size, (255, 255, 255))
        
        # Convert palette mode to RGBA if it has transparency
        if img.mode == 'P':
            img = img.convert('RGBA')
        
        # Extract alpha channel for transparency masking
        if img.mode == 'RGBA':
            alpha_channel = img.split()[3]  # RGBA has alpha at index 3
        elif img.mode == 'LA':
            alpha_channel = img.split()[1]  # LA (grayscale + alpha) has alpha at index 1
        else:
            alpha_channel = None
        
        # Paste image onto white background using alpha mask
        # This preserves anti-aliasing while avoiding black artifacts
        if alpha_channel:
            background.paste(img, mask=alpha_channel)
        else:
            background.paste(img)
        
        img = background
    elif img.mode != 'RGB':
        # Convert other modes (CMYK, LAB, etc.) to RGB
        img = img.convert('RGB')
    
    # Step 3: Convert to grayscale for OCR processing
    # Grayscale simplifies image and improves binarization results
    if img.mode != 'L':
        img = img.convert('L')  # L mode = 8-bit grayscale

    # Step 4: Enhance contrast to make text more distinct from background
    # Factor of 1.8 increases difference between light and dark areas
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.8)  # 1.0 = original, >1.0 = higher contrast

    # Step 5: Binarization using Otsu's method for automatic thresholding
    # Converts grayscale to pure black/white for optimal OCR
    # Otsu automatically finds best threshold value based on image histogram
    img_np = np.array(img)  # Convert PIL to NumPy for OpenCV processing
    _, binary_np = cv2.threshold(
        img_np, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    # Step 6: Noise removal using median filter
    # Removes small artifacts while preserving text edges
    # 3x3 kernel balances noise removal vs detail preservation
    binary_np = cv2.medianBlur(binary_np, 3)

    # Step 7: Resize large images to reduce API costs and processing time
    # Gemini has token limits based on image resolution
    # 2000px max dimension provides good balance of quality vs speed
    max_dimension = 2000
    if max(img.size) > max_dimension:
        # Calculate scaling factor to preserve aspect ratio
        scale = max_dimension / max(img.size)
        new_size = (int(img.width * scale), int(img.height * scale))
        # Use LANCZOS resampling for high-quality downsampling
        img = img.resize(new_size, Image.LANCZOS)

    # Step 8: Return preprocessed image without rotation correction
    # Deskewing can crop important content, so we skip it
    # The binarized image with enhanced contrast is ready for OCR
    return Image.fromarray(binary_np, mode='L')  # Convert NumPy back to PIL