from typing import Dict

from .duplicate import detect_duplicate_bill_logical


def validate_bill_amounts(bill_data, tolerance=0.02):
    """
    Validates bill totals safely without assuming tax-inclusive or tax-exclusive pricing.
    """
    items = bill_data.get("items", [])
    tax_amount = float(bill_data.get("tax_amount", 0) or 0)
    total = float(bill_data.get("total_amount", 0) or 0)

    items_sum = sum(
        float(item.get("item_total", 0) or 0) for item in items
    )

    def approx_equal(a, b):
        # Use tolerance to handle floating-point rounding errors from OCR text parsing
        return abs(a - b) <= tolerance

    # Different regions use different tax models; check both to support global receipts
    matches_inclusive = approx_equal(items_sum, total)
    matches_exclusive = approx_equal(items_sum + tax_amount, total)

    # Accept either model; exact match is often impossible with OCR noise
    is_valid = matches_inclusive or matches_exclusive

    # Build error details if validation fails
    errors = []
    if not is_valid:
        errors.append({
            "type": "AMOUNT_MISMATCH",
            "items_sum": round(items_sum, 2),
            "tax_amount": round(tax_amount, 2),
            "extracted_total": round(total, 2)
        })

    # Return validation result with detailed breakdown
    return {
        "is_valid": is_valid,
        "items_sum": round(items_sum, 2),
        "tax_amount": round(tax_amount, 2),
        "total_amount": round(total, 2),
        "errors": errors
    }


def validate_bill_complete(bill_data: dict, user_id: int = 1) -> Dict:
    """Unified validation function that checks both amount validation and duplicate detection.
    
    Args:
        bill_data: Dictionary containing bill fields and items
        user_id: User ID for duplicate detection scope
    
    Returns:
        {
            "amount_validation": {...},  # Result from validate_bill_amounts
            "duplicate_check": {...},    # Result from detect_duplicate_bill_logical
            "can_save": bool,            # True only if amounts valid and no hard duplicate
            "warnings": []                # List of warning messages
        }
    """
    # Check amount validation
    amount_validation = validate_bill_amounts(bill_data)
    
    # Check for duplicates
    duplicate_check = detect_duplicate_bill_logical(bill_data, user_id)
    
    # Determine if save is allowed
    can_save = amount_validation["is_valid"] and not duplicate_check["duplicate"]
    
    # Build warnings
    warnings = []
    if not amount_validation["is_valid"]:
        warnings.append("Amount validation failed")
    if duplicate_check["duplicate"]:
        warnings.append("Hard duplicate detected - save blocked")
    if duplicate_check["soft_duplicate"]:
        warnings.append("Soft duplicate detected - similar bill exists")
    
    return {
        "amount_validation": amount_validation,
        "duplicate_check": duplicate_check,
        "can_save": can_save,
        "warnings": warnings
    }
