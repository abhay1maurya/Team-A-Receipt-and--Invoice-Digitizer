

from typing import Dict

CURRENCY_RATES_TO_USD = {
    "USD": 1.0,
    "INR": 0.012,
    "MYR": 0.21,
    "EUR": 1.08,
    "GBP": 1.27,
    "RM" : 0.21
}


def convert_to_usd(bill_data: Dict) -> Dict:
    """
    Converts all monetary values to USD.
    Preserves original currency and amounts.
    """

    currency = (bill_data.get("currency") or "USD").upper()
    rate = CURRENCY_RATES_TO_USD.get(currency)

    if rate is None:
        # Unknown currency → DO NOT CONVERT
        bill_data["conversion_warning"] = f"Unsupported currency: {currency}"
        return bill_data

    def safe_mul(value):
        try:
            return round(float(value) * rate, 2)
        except Exception:
            return 0.0

    # Preserve originals
    bill_data["original_currency"] = currency
    bill_data["original_total_amount"] = bill_data.get("total_amount", 0)
    bill_data["exchange_rate"] = rate

    # Convert header values
    bill_data["subtotal"] = safe_mul(bill_data.get("subtotal", 0))
    bill_data["tax_amount"] = safe_mul(bill_data.get("tax_amount", 0))
    bill_data["total_amount"] = safe_mul(bill_data.get("total_amount", 0))

    # Convert line items
    for item in bill_data.get("items", []):
        item["unit_price"] = safe_mul(item.get("unit_price", 0))
        item["item_total"] = safe_mul(item.get("item_total", 0))

    # Normalize currency field to USD
    bill_data["currency"] = "USD"

    return bill_data
