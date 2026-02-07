# Regular expression patterns for extracting structured data from receipt/invoice images
# Alternative to Gemini OCR when AI extraction fails or for validation purposes
# Ordered by specificity/likelihood to match most common format first

import re

# DATE_PATTERNS: Multiple formats needed because OCR quality and regional variations mean
# receipts from India (DD/MM/YYYY), Europe (DD.MM.YYYY), and US (MM/DD/YYYY) all appear
# Ordered by likelihood: ISO format most reliable, European separators also common
DATE_PATTERNS = [
    r"\b(\d{4}-\d{2}-\d{2})\b",          # ISO 8601 (most reliable in modern systems)
    r"\b(\d{2}/\d{2}/\d{4})\b",          # DD/MM/YYYY (India/EU common)
    r"\b(\d{2}-\d{2}-\d{4})\b",          # DD-MM-YYYY (alternative separator)
    r"\b(\d{2}\.\d{2}\.{4})\b",          # DD.MM.YYYY (Germany/Europe)
]

# TIME_PATTERNS: HH:MM is checked before HH:MM:SS because OCR often truncates seconds
# This ensures we capture time even if OCR quality is degraded
TIME_PATTERNS = [
    r"\b(\d{2}:\d{2})\b",                # HH:MM (most common on receipts)
    r"\b(\d{2}:\d{2}:\d{2})\b",          # HH:MM:SS (when available)
]

# INVOICE_PATTERNS: Different receipt vendors use inconsistent labeling
# (Invoice, Bill, Receipt, INV#, etc). Multiple patterns catch variations
# Capture group 2 gets the actual number (group 1 is the label)
INVOICE_PATTERNS = [
    r"(invoice|bill|receipt)[\s-:#]*([A-Z0-9\-\/]+)",  # Flexible label + number
    r"\bINV[\s\-:]?([A-Z0-9]+)\b",                      # Abbreviated "INV" format
    r"\bBILL[\s\-:]?([A-Z0-9\-\/]+)\b",                 # Abbreviated "BILL" format
]

# CURRENCY_PATTERNS: Dictionary allows symbol-first matching ($ before USD text)
# Symbols ($, ₹) are more visually distinct in OCR than currency codes
# Early match prevents ambiguity (e.g., USD $ both in same receipt)
CURRENCY_PATTERNS = {
    "USD": r"\bUSD\b|\$",                               # Match symbol first
    "INR": r"\bINR\b|₹",                                # Indian Rupee symbol more reliable
    "MYR": r"\bMYR\b|\bRM\b",                            # Malaysian Ringgit
    "EUR": r"\bEUR\b|€",                                # Euro symbol
    "GBP": r"\bGBP\b|£",                                # British Pound symbol
}

# PAYMENT_METHOD_PATTERNS: Enables expense categorization for accounting/analytics
# Typo "PATERNS" kept for backward compatibility with existing code
# Multiple aliases for same method catch OCR variations (PAYTM, PayTM, paytm)
PAYMENT_METHOD_PATERNS = {
    "CASH": r"\bCASH\b",                                # Direct payment
    "CARD": r"\bCARD\b|\bCREDIT\b|\bDEBIT\b",          # Card variants
    "UPI": r"\bUPI\b",                                  # India-specific (critical market)
    "NET BANKING": r"\bNET BANKING\b|\bONLINE\b",      # Bank transfers
    "WALLET": r"\bPAYTM\b|\bPHONEPE\b|\bGPAY\b",       # Popular mobile wallets
}

# TAX_PATTERNS: Tax detection enables invoice validation (total = subtotal + tax)
# Different regions: India (GST/CGST/SGST), Europe (VAT), US (Tax)
# Order: specific (CGST/SGST) before generic (GST) to avoid false matches
TAX_PATTERNS = [
    r"\bTAX\b",                                         # Generic fallback
    r"\bGST\b",                                         # India nationwide
    r"\bVAT\b",                                         # Europe/UK
    r"\bCGST\b",                                        # Central GST (India)
    r"\bSGST\b",                                        # State GST (India)
    r"\bIGST\b",                                        # Integrated GST (India)
]

# TOTAL_LABEL_PATTERNS: Identifies final payable amount
# Different receipts use different terminology depending on context
# Critical for validation: total_amount field must be detected accurately
TOTAL_LABEL_PATTERNS = [
    r"\bTOTAL\b",                                       # Most common
    r"\bAMOUNT DUE\b",                                  # Invoices often use this
    r"\bGRAND TOTAL\b",                                 # Itemized receipts
]

# SUBTOTAL_LABEL_PATTERNS: Detects pre-tax amount needed for validation logic
# Distinguishes: subtotal + tax = total (tax-exclusive model)
# vs: subtotal = total (tax-inclusive model, common in India)
SUBTOTAL_LABEL_PATTERNS = [
    r"\bSUBTOTAL\b",                                    # Standard spelling
    r"\bSUB TOTAL\b",                                   # Space variant
]

# AMOUNT_PATTERN: Matches currency values with thousand separators
# Handles 1000, 1,000, 1000.00 variations across different locales
# Non-capturing groups (?:) improve performance vs capturing groups
AMOUNT_PATTERN = r"\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b"

# LINE_ITEM_PATTERN: Parses individual line items (product lines on receipt)
# Format: serial_no + item_name + quantity + unit_price
# Note: High variance in receipt formats; may need regex tuning per vendor
LINE_ITEM_PATTERN = r"(\d+)\s+([A-Z0-9\s\-\.]+)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)"