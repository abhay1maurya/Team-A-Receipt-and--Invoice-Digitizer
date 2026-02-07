from typing import Dict, List
from datetime import datetime

# Utility helpers to normalize OCR/Gemini outputs into DB-friendly shapes

# Safe converters

def _safe_str(value, default=""):
    """Convert value to string safely, handling None and empty values"""
    # Prevents None.strip() errors and normalizes whitespace
    return str(value).strip() if value else default


def _safe_float(value, default=0.0):
    """Convert value to float safely, returning default on error"""
    # Handles string numbers from OCR ("100.50" -> 100.5) without crashing
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# Date & time normalization

def _normalize_date(date_str: str) -> str:
    """Convert various date formats to YYYY-MM-DD for database storage"""
    if not date_str:
        return ""

    # Try common date formats found in receipts (ordered by likelihood)
    formats = [
        "%Y-%m-%d",    # ISO format: 2024-01-15
        "%d/%m/%Y",    # DD/MM/YYYY: 15/01/2024
        "%d-%m-%Y",    # DD-MM-YYYY: 15-01-2024
        "%d.%m.%Y",    # DD.MM.YYYY: 15.01.2024
    ]

    # Attempt parsing with each format; first match wins
    for fmt in formats:
        try:
            # Convert to standard database format regardless of input format
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass

    return ""


def _normalize_time(time_str: str) -> str:
    """Normalize time to HH:MM:SS format for database TIME type compatibility"""
    if not time_str:
        return ""
    
    # Try datetime.strptime first for strict format matching
    for fmt in ("%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M:%S %p"):
        try:
            dt = datetime.strptime(time_str.strip(), fmt)
            return dt.strftime("%H:%M:%S")
        except ValueError:
            pass
    
    # Fallback to regex for flexible formats OCR might produce
    import re
    match = re.match(r"^\s*(\d{1,2}):(\d{2})(?::(\d{2}))?\s*$", time_str.strip())
    if match:
        hh = int(match.group(1))
        mm = int(match.group(2))
        ss = int(match.group(3)) if match.group(3) else 0
        
        # Validate ranges to catch parsing errors
        if 0 <= hh <= 23 and 0 <= mm <= 59 and 0 <= ss <= 59:
            return f"{hh:02d}:{mm:02d}:{ss:02d}"
    
    return ""

# Line item normalization

def normalize_items(items: List[Dict]) -> List[Dict]:
    """Normalize line items with safe type conversions and calculations"""
    normalized = []

    for idx, item in enumerate(items, start=1):
        # Safe conversion handles OCR strings like "2.5" or "qty: 3"
        quantity = _safe_float(item.get("quantity"))
        unit_price = _safe_float(item.get("unit_price"))

        # Calculate item_total if Gemini didn't provide it (catches OCR errors)
        item_total = item.get("item_total")
        if item_total is None:
            item_total = quantity * unit_price

        normalized.append({
            "s_no": item.get("s_no", idx),
            "item_name": _safe_str(item.get("item_name")).upper(),
            "quantity": quantity,
            "unit_price": unit_price,
            "item_total": round(_safe_float(item_total), 2),  # Consistent precision
        })

    return normalized


# Main normalizer

def normalize_extracted_fields(extracted: Dict) -> Dict:
    """
    Normalize extracted fields for validation & DB storage.
    Ensures all fields meet database constraints and have consistent formats.
    
    This is called by ocr.py after Gemini extraction to standardize data.
    """
    # Enforce database VARCHAR length limits to prevent constraint violations
    invoice_number = _safe_str(extracted.get("invoice_number")).upper()[:100]
    vendor_name = _safe_str(extracted.get("vendor_name", "Unknown")).upper()[:255]
    currency = _safe_str(extracted.get("currency", "USD")).upper()[:10]
    payment_method = _safe_str(extracted.get("payment_method")).upper()[:50]
    
    # Safe conversion prevents "1000.50" string from crashing calculations
    subtotal = _safe_float(extracted.get("subtotal"))
    total_amount = _safe_float(extracted.get("total_amount"))
    tax_amount = _safe_float(extracted.get("tax_amount"))
    
    # Calculate subtotal if missing (needed for validation and reporting)
    if subtotal == 0 and total_amount > 0:
        subtotal = total_amount - tax_amount

    return {
        "invoice_number": invoice_number,
        "vendor_name": vendor_name,
        "purchase_date": _normalize_date(extracted.get("purchase_date")),
        "purchase_time": _normalize_time(extracted.get("purchase_time")),
        "currency": currency,
        "payment_method": payment_method,
        "tax_amount": round(tax_amount, 2),
        "subtotal": round(subtotal, 2),
        "total_amount": round(total_amount, 2),
        "items": normalize_items(extracted.get("items", [])),
    }
