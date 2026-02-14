import re
from typing import Dict, List

from .regex_patterns import (
    DATE_PATTERNS,
    TIME_PATTERNS,
    INVOICE_PATTERNS,
    CURRENCY_PATTERNS,
    PAYMENT_METHOD_PATERNS,
    TAX_PATTERNS,
    TOTAL_LABEL_PATTERNS,
    SUBTOTAL_LABEL_PATTERNS,
    AMOUNT_PATTERN,
    LINE_ITEM_PATTERN,
)


# WEAK FIELD DETECTION - Critical for fallback triggering

def is_field_weak(value) -> bool:
    """
    Determine if a field value is weak and needs regex fallback.
    
    A field is considered WEAK if:
    - Value is None
    - Value is empty string ""
    - Value is 0 or 0.0 (for numeric fields)
    - Value is empty list []
    
    Args:
        value: Field value from Gemini extraction
        
    Returns:
        bool: True if field is weak (needs fallback), False if strong (usable)
    """
    if value is None:
        return True
    if value == "":
        return True
    if value == 0 or value == 0.0:
        return True
    if isinstance(value, list) and len(value) == 0:
        return True
    return False


# Generic helpers

def _find_first(patterns: List[str], text: str) -> str:
    """Try each pattern until one matches, return first match found"""
    # Patterns ordered by specificity; first match usually most reliable
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return ""


def _find_amount_after_label(label_patterns: List[str], text: str) -> float:
    """Find monetary amount after a label (e.g., 'Total: $50.00')"""
    for label in label_patterns:
        # Build regex: label + optional separator + amount pattern
        # Separators vary (colon, dash, space) across receipt formats
        regex = rf"{label}\s*[:\-]?\s*({AMOUNT_PATTERN})"
        match = re.search(regex, text, re.IGNORECASE)
        if match:
            # Remove commas before converting (1,000.50 -> 1000.50)
            return float(match.group(1).replace(",", ""))
    return 0.0


# Field extractors

def extract_date(text: str) -> str:
    return _find_first(DATE_PATTERNS, text)


def extract_time(text: str) -> str:
    return _find_first(TIME_PATTERNS, text)


def extract_invoice_number(text: str) -> str:
    """Extract invoice/bill/receipt number from text"""
    for pattern in INVOICE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(2)  # Group 2 contains the actual number
    return ""


def extract_currency(text: str) -> str:
    """Detect currency from symbols ($, ₹, €) or codes (USD, INR, EUR)"""
    # Match currency symbols before codes; symbols are more visually distinct in OCR
    for currency, pattern in CURRENCY_PATTERNS.items():
        if re.search(pattern, text, re.IGNORECASE):
            return currency
    return ""


def extract_payment_method(text: str) -> str:
    """Identify payment method from keywords (CASH, CARD, UPI, etc.)"""
    # Used for expense tracking and reconciliation with payment records
    for method, pattern in PAYMENT_METHOD_PATERNS.items():
        if re.search(pattern, text, re.IGNORECASE):
            return method  # Return standardized payment method name
    return ""  # Unknown payment method


def extract_tax(text: str) -> float:
    """Extract tax amount from various tax labels (TAX, GST, VAT, etc.)"""
    for label in TAX_PATTERNS:
        # Build regex to find amount after tax label
        regex = rf"{label}\s*[:\-]?\s*({AMOUNT_PATTERN})"
        match = re.search(regex, text, re.IGNORECASE)
        if match:
            # Clean and convert amount to float
            return float(match.group(1).replace(",", ""))
    return 0.0  # No tax found


def extract_subtotal(text: str) -> float:
    return _find_amount_after_label(SUBTOTAL_LABEL_PATTERNS, text)


def extract_total(text: str) -> float:
    return _find_amount_after_label(TOTAL_LABEL_PATTERNS, text)


def extract_line_items(text: str) -> List[Dict]:
    """Extract itemized list from receipt (s_no, name, qty, price)"""
    items = []
    # Find all matches of line item pattern in text
    matches = re.findall(LINE_ITEM_PATTERN, text, re.IGNORECASE)

    # Convert each match to structured dictionary
    for idx, match in enumerate(matches, start=1):
        s_no, name, qty, price = match  # Unpack regex capture groups
        items.append({
            "s_no": int(s_no),  # Serial number
            "item_name": name.strip(),  # Remove extra whitespace
            "quantity": float(qty),  # Convert to number
            "unit_price": float(price),
            "item_total": round(float(qty) * float(price), 2),  # Calculate total
        })

    return items


# Main entry point

def extract_fields_from_ocr(ocr_text: str) -> Dict:
    """
    Extract raw fields from OCR text.
    """

    return {
        "invoice_number": extract_invoice_number(ocr_text),
        "vendor_name": "",  # vendor often needs NLP → left for later stage
        "purchase_date": extract_date(ocr_text),
        "purchase_time": extract_time(ocr_text),
        "currency": extract_currency(ocr_text),
        "payment_method": extract_payment_method(ocr_text),
        "tax_amount": extract_tax(ocr_text),
        "subtotal": extract_subtotal(ocr_text),
        "total_amount": extract_total(ocr_text),
        "items": extract_line_items(ocr_text),
    }
