# OCR and structured data extraction using Google Gemini AI
# This module handles text extraction from receipt/invoice images
# and parses the extracted data into structured JSON format matching database schema

from typing import Dict
from google import genai
from PIL import Image
import json
import re

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
    # Validate API key before making expensive API call
    if not api_key or not api_key.strip():
        return {"error": "API key is required"}

    # Validate image input
    if not isinstance(image, Image.Image):
        return {"error": "Invalid image provided"}

    # Initialize Gemini AI client with provided API key
    client = genai.Client(api_key=api_key)

    # Structured prompt instructs Gemini to extract data in exact JSON schema
    # Key requirements:
    # - ONLY return JSON (no markdown, explanations, or extra text)
    # - Use defaults for missing fields to prevent incomplete responses
    # - Follow exact schema structure for database compatibility
    prompt = (
        "Extract receipt/invoice data.\n"
        "Return ONLY valid JSON.\n"
        "Do NOT include explanations.\n"
        "If a field is missing, use defaults.\n\n"
        "Schema:\n"
        "{"
        "\"invoice_number\": string,"  # Invoice/Receipt ID or number
        "\"vendor_name\": string,"  # Store or business name
        "\"purchase_date\": \"YYYY-MM-DD\","  # Date format for database DATE type
        "\"purchase_time\": \"HH:MM\","  # Optional time of purchase
        "\"currency\": \"USD\","  # ISO currency code
        "\"items\": ["  # Array of line items
        " {\"s_no\": int, \"item_name\": string, \"quantity\": number, "
        "  \"unit_price\": number, \"item_total\": number}"
        "],"
        "\"tax\": number,"  # Total tax amount
        "\"total_amount\": number,"  # Grand total including tax
        "\"payment_method\": string"  # Cash, Card, etc.
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
        return {"error": f"Gemini request failed: {e}"}

    # Parse JSON response from Gemini
    try:
        bill_data = json.loads(response.text)
    except Exception as e:
        # Return error with partial response for debugging
        return {
            "error": "Gemini returned invalid JSON (hard failure)",
            "raw_response": response.text[:1000]  # First 1000 chars for debugging
        }

    # Data normalization - ensure all required fields exist with proper defaults
    # This prevents KeyError when accessing fields in downstream code
    defaults = {
        "invoice_number": "",  # Empty string if invoice number not found
        "vendor_name": "",  # Empty string if vendor not detected
        "purchase_date": "",  # Empty string if date not found
        "purchase_time": "",  # Optional field
        "currency": "USD",  # Default to USD if currency not specified
        "items": [],  # Empty array if no items detected
        "tax": 0,  # Zero tax if not specified
        "total_amount": 0,  # Zero total if not detected
        "payment_method": ""  # Empty string if payment method not found
        }

    # Apply defaults for any missing keys
    for k, v in defaults.items():
        bill_data.setdefault(k, v)

    # Normalize invoice_number length for DB constraint (VARCHAR 100)
    bill_data["invoice_number"] = str(bill_data.get("invoice_number", "")).strip()[:100]

    # Normalize purchase_time to HH:MM:SS for MySQL TIME compatibility
    t = bill_data.get("purchase_time", "")
    if isinstance(t, str) and t.strip():
        m = re.match(r"^\s*(\d{1,2}):(\d{2})(?::(\d{2}))?\s*$", t)
        if m:
            hh = int(m.group(1))
            mm = int(m.group(2))
            ss = int(m.group(3)) if m.group(3) else 0
            bill_data["purchase_time"] = f"{hh:02d}:{mm:02d}:{ss:02d}"
        else:
            # If time cannot be parsed, set empty to avoid DB errors
            bill_data["purchase_time"] = ""

    # Normalize currency and payment_method lengths for DB constraints
    bill_data["currency"] = str(bill_data.get("currency", "USD")).upper()[:10]
    bill_data["payment_method"] = str(bill_data.get("payment_method", "")).strip()[:50]

    # Normalize numeric fields - convert strings to floats for database storage
    # Gemini may return numbers as strings, so we ensure proper type conversion
    for key in ("tax", "total_amount"):
        try:
            bill_data[key] = float(bill_data[key])
        except Exception:
            bill_data[key] = 0.0  # Fallback to 0 if conversion fails

    # Normalize line items - ensure consistent structure and data types
    # Each item gets sequential s_no and proper numeric conversions
    normalized_items = []
    for idx, item in enumerate(bill_data["items"], 1):
        # Skip invalid items (non-dictionary entries)
        if not isinstance(item, dict):
            continue

        # Convert quantity to integer for DB (INT NOT NULL) with safe coercion
        try:
            quantity = int(round(float(item.get("quantity", 0))))
        except:
            quantity = 0

        # Convert unit_price to float with error handling
        try:
            unit_price = float(item.get("unit_price", 0))
        except:
            unit_price = 0.0

        # Calculate item_total if not provided (quantity * unit_price)
        try:
            item_total = float(item.get("item_total", quantity * unit_price))
        except:
            item_total = quantity * unit_price

        # Build normalized item dictionary
        normalized_items.append({
            "s_no": idx,  # Sequential number for display
            "item_name": item.get("item_name", ""),  # Item description
            "quantity": quantity,
            "unit_price": unit_price,
            "item_total": item_total
        })

    # Replace items array with normalized version
    bill_data["items"] = normalized_items

    # Add backward compatibility fields for database insert function
    # Database schema uses tax_amount, but OCR returns tax
    bill_data["tax_amount"] = bill_data["tax"]
    # Calculate subtotal for display purposes (total - tax)
    bill_data["subtotal"] = bill_data["total_amount"] - bill_data["tax_amount"]

    return bill_data