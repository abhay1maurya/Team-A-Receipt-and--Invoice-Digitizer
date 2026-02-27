def validate_bill_amounts(bill_data, tolerance=0.02):
    """
    Validates bill totals safely without assuming tax-inclusive or tax-exclusive pricing.
    """

    items = bill_data.get("items", [])
    tax = float(bill_data.get("tax", 0) or 0)
    total = float(bill_data.get("total_amount", 0) or 0)

    items_sum = sum(
        float(item.get("item_total", 0) or 0) for item in items
    )

    def approx_equal(a, b):
        return abs(a - b) <= tolerance

    # Two safe validation paths
    matches_inclusive = approx_equal(items_sum, total)
    matches_exclusive = approx_equal(items_sum + tax, total)

    is_valid = matches_inclusive or matches_exclusive

    errors = []
    if not is_valid:
        errors.append({
            "type": "AMOUNT_MISMATCH",
            "items_sum": round(items_sum, 2),
            "tax": round(tax, 2),
            "extracted_total": round(total, 2)
        })

    return {
        "is_valid": is_valid,
        "items_sum": round(items_sum, 2),
        "tax": round(tax, 2),
        "total_amount": round(total, 2),
        "errors": errors
    }