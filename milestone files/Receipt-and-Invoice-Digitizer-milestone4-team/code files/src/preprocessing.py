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
        # Streamlit's UploadedFile implements file-like interface
        if isinstance(image_input, str):
            img = Image.open(image_input)
        elif isinstance(image_input, Image.Image):
            img = image_input.copy()  # Avoid modifying caller's original
        else:
            img = Image.open(image_input)

        # Fix EXIF rotations from mobile phones/cameras
        # Otherwise upside-down receipts fail OCR completely
        img = ImageOps.exif_transpose(img)
    except Exception as e:
        raise ValueError(f"Could not load image for preprocessing: {e}")

    # Validation to catch corrupted files early
    if img.width == 0 or img.height == 0:
        raise ValueError("Image has invalid dimensions (width or height is 0)")

    # Step 2: Convert transparency to white background
    # Direct RGBA->RGB conversion produces black backgrounds that confuse OCR
    # White background matches typical receipt paper color
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        background = Image.new('RGB', img.size, (255, 255, 255))
        
        if img.mode == 'P':
            img = img.convert('RGBA')
        
        # Extract alpha channel to preserve anti-aliasing edges
        if img.mode == 'RGBA':
            alpha_channel = img.split()[3]
        elif img.mode == 'LA':
            alpha_channel = img.split()[1]
        else:
            alpha_channel = None
        
        # Paste with alpha mask to keep semi-transparent pixels
        if alpha_channel:
            background.paste(img, mask=alpha_channel)
        else:
            background.paste(img)
        
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Step 3: Convert to grayscale
    # Simplifies image and improves binarization (text is single channel)
    if img.mode != 'L':
        img = img.convert('L')

    # Step 4: Enhance contrast
    # Increases light/dark separation for crisper text edges
    # Factor > 1.0 means high contrast; 1.8 is aggressive but handles poor lighting
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.8)

    # Step 5: Binarization via Otsu thresholding
    # Converts grayscale to pure black/white (no grays)
    # Otsu's method automatically chooses threshold based on histogram
    # Critical for OCR: AI models expect high contrast binary images
    img_np = np.array(img)
    _, binary_np = cv2.threshold(
        img_np, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    # Step 6: Median blur for noise removal
    # Removes dust/speckles while preserving sharp text edges
    # 3x3 kernel is minimal; larger kernels blur text
    binary_np = cv2.medianBlur(binary_np, 3)

    # Step 7: Resize large images
    # Gemini charges per image token; smaller images = lower cost
    # 2000px retains detail while reducing processing time by 4x
    max_dimension = 2000
    if max(img.size) > max_dimension:
        scale = max_dimension / max(img.size)
        new_size = (int(img.width * scale), int(img.height * scale))
        # LANCZOS resampling better than BILINEAR for downsampling
        img = img.resize(new_size, Image.LANCZOS)

    # Return preprocessed binary image ready for Gemini
    return Image.fromarray(binary_np, mode='L')