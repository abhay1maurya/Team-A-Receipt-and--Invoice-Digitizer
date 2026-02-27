# OCR and structured data extraction using Google Gemini AI
# This module handles text extraction from receipt/invoice images
# and parses the extracted data into structured JSON format matching database schema

from typing import Dict
from google import genai
from PIL import Image
import json
import re

# Import normalizer for data standardization after Gemini extraction
from .extraction.normalizer import normalize_extracted_fields
from .extraction.currency_converter import convert_to_usd

def run_ocr_and_extract_bill(image: Image.Image, api_key: str) -> Dict:
    """Extract structured bill data from image using Gemini AI.
    
    This function combines OCR and data extraction in a single API call.
    Gemini analyzes the image and returns structured JSON matching our schema.
    
    Args:
        image: PIL Image object of receipt or invoice
        api_key: Google Gemini API key for authentication
    
    Returns:
        Dictionary containing extracted bill data with normalized fields,
        or error dictionary if extraction fails.
    
    Process:
        1. Validate inputs (API key and image)
        2. Send image to Gemini with structured prompt
        3. Parse JSON response
        4. Normalize data types and add calculated fields
    """
    # Early validation to fail fast without wasting API quota
    if not api_key or not api_key.strip():
        return {"error": "API key is required"}

    if not isinstance(image, Image.Image):
        return {"error": "Invalid image provided"}

    client = genai.Client(api_key=api_key)

    # Enforce deterministic JSON output to prevent Gemini hallucinations and markdown wrapping
    # CRITICAL: Request raw OCR text as fallback for weak extractions
    prompt = (
        "Extract receipt/invoice data AND return the raw OCR text.\n"
        "Return ONLY valid JSON.\n"
        "Do NOT include explanations.\n"
        "If a field is missing or uncertain, return an empty string or null.\n\n"
        "Schema:\n"
        "{"
        "\"ocr_text\": \"raw text from receipt (REQUIRED for fallback)\","
        "\"invoice_number\": string,"  # Invoice/Receipt ID or number
        "\"vendor_name\": string,"  # Store or business name
        "\"purchase_date\": \"YYYY-MM-DD\","  # Date format for database DATE type
        "\"purchase_time\": \"HH:MM\","  # Optional time of purchase
        "\"currency\": string,"  # ISO currency code (USD, INR, EUR, etc.)
        "\"items\": ["  # Array of line items
        " {\"s_no\": int, \"item_name\": string, \"quantity\": number, "
        "  \"unit_price\": number, \"item_total\": number}"
        "],"
        "\"tax_amount\": number,"  # Total tax amount
        "\"total_amount\": number,"  # Grand total including tax
        "\"payment_method\": string"  # Cash, Card, UPI, etc.
        "}"
    )


    # Make API request to Gemini with image and prompt
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",  # Fast model optimized for document understanding
            contents=[prompt, image],  # Send both text prompt and image
            config={
                "temperature": 0.0,  # Deterministic output for consistent extraction
                "max_output_tokens": 4096,  # Enough for large receipts with many items
                "response_mime_type": "application/json"  # Force JSON response format
            },
        )

    except Exception as e:
        
        # API call failed - network error, quota exceeded, invalid key, etc.
        return {"error": f"Gemini request failed: {e}"}

    # Parse JSON response from Gemini
    bill_data = None
    ocr_text = ""
    json_parse_failed = False
    
    try:
        bill_data = json.loads(response.text)
        ocr_text = bill_data.get("ocr_text", "")
    except Exception as e:
        # JSON parsing failed - attempt to extract ocr_text from raw response
        json_parse_failed = True
        
        # Try to extract ocr_text field even if JSON is malformed
        # Pattern: "ocr_text": "..." (handles escaped quotes)
        ocr_match = re.search(r'"ocr_text"\s*:\s*"((?:\\.|[^"\\])*)"', response.text)
        if ocr_match:
            ocr_text = ocr_match.group(1)
            # Unescape the string
            ocr_text = ocr_text.replace('\\"', '"').replace('\\n', '\n').replace('\\\\', '\\')
        
        # If we extracted ocr_text, attempt regex fallback instead of hard failure
        if not ocr_text:
            return {
                "error": "Gemini returned invalid JSON (hard failure) and no OCR text could be extracted",
                "raw_response": response.text[:2000]  # Capture first 2000 chars for debugging
            }
        
        # Initialize empty bill_data for fallback processing
        bill_data = {
            "ocr_text": ocr_text,
            "invoice_number": None,
            "vendor_name": None,
            "purchase_date": None,
            "purchase_time": None,
            "currency": None,
            "items": [],
            "tax_amount": 0,
            "total_amount": 0,
            "payment_method": None
        }

    
    # STEP 3: REGEX FALLBACK - Run before normalization
    # Trigger fallback when fields are missing or weak (empty/null values)
    from .extraction.field_extractor import extract_fields_from_ocr, is_field_weak
    
    weak_fields = []  # Track which fields needed fallback
    
    # Check each critical field for weakness
    if is_field_weak(bill_data.get("invoice_number")):
        weak_fields.append("invoice_number")
    if is_field_weak(bill_data.get("vendor_name")):
        weak_fields.append("vendor_name")
    if is_field_weak(bill_data.get("purchase_date")):
        weak_fields.append("purchase_date")
    if is_field_weak(bill_data.get("currency")):
        weak_fields.append("currency")
    if is_field_weak(bill_data.get("total_amount")):
        weak_fields.append("total_amount")
    
    # Always trigger regex fallback if JSON parse failed (best-effort recovery)
    if json_parse_failed or (weak_fields and ocr_text):
        try:
            regex_extracted = extract_fields_from_ocr(ocr_text)
            
            # Merge regex results for weak or missing fields
            for field in weak_fields + (["invoice_number", "vendor_name", "purchase_date", "currency", "total_amount"] if json_parse_failed else []):
                if regex_extracted.get(field):
                    bill_data[field] = regex_extracted[field]
                    
        except Exception as e:
            # Regex fallback failed - log but don't crash
            pass
    
    # STEP 3B: spaCy NER Vendor Fallback
    # Use Named Entity Recognition as second-level fallback if vendor_name is still weak
    # spaCy identifies ORG entities; often better for noisy OCR than pure regex
    if is_field_weak(bill_data.get("vendor_name")) and ocr_text:
        from .extraction.vendor_extractor_spacy import extract_vendor_spacy
        
        vendor_spacy = extract_vendor_spacy(ocr_text)
        if vendor_spacy:
            bill_data["vendor_name"] = vendor_spacy

    # STEP 4: NOW NORMALIZE (SAFE) - After regex fallback
    # Use normalizer module to standardize all fields
    # This ensures consistent formatting for database storage and validation
    # Normalizer handles:
    #   - Date/time format conversion (YYYY-MM-DD, HH:MM:SS)
    #   - Numeric conversions (string to float, rounding)
    #   - Field length constraints (VARCHAR limits)
    #   - Default values for missing fields
    #   - Type safety (safe conversions with fallbacks)
    normalized_data = normalize_extracted_fields(bill_data)

    # Currency conversion: convert monetary fields to USD while preserving originals
    converted_data = convert_to_usd(normalized_data)

    
    # Return fully normalized and currency-converted data ready for validation/storage
    return converted_data
