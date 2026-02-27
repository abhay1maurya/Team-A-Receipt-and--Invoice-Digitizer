"""Duplicate detection utilities for bills.

Strong duplicate (block): invoice_number present and matches vendor + date + total (±0.02).
Soft duplicate (warn): missing invoice_number but vendor + date + total (±0.02) matches.
"""

from typing import Dict

from .database import get_connection


def detect_duplicate_bill_logical(bill_data: dict, user_id: int) -> Dict[str, bool]:
    invoice_number = bill_data.get("invoice_number")
    vendor = bill_data.get("vendor_name")
    purchase_date = bill_data.get("purchase_date")
    total_amount = float(bill_data.get("total_amount", 0))

    # Cannot compare without vendor/date
    if not vendor or not purchase_date:
        return {
            "duplicate": False,
            "soft_duplicate": False,
            "reason": "Insufficient data for comparison"
        }

    conn = get_connection()
    try:
        cursor = conn.cursor()

        if invoice_number:
            cursor.execute(
                """
                SELECT bill_id
                FROM bills
                WHERE invoice_number = ?
                  AND LOWER(vendor_name) = LOWER(?)
                  AND purchase_date = ?
                  AND ABS(total_amount - ?) <= 0.02
                LIMIT 1
                """,
                (invoice_number, vendor, purchase_date, total_amount)
            )
            match = cursor.fetchone()
            if match:
                return {
                    "duplicate": True,
                    "soft_duplicate": False,
                    "reason": f"Invoice #{invoice_number} from {vendor} on {purchase_date} already exists"
                }
            return {
                "duplicate": False,
                "soft_duplicate": False,
                "reason": "No duplicate detected"
            }

        # Soft match: no invoice number, rely on vendor/date/amount only
        cursor.execute(
            """
            SELECT bill_id
            FROM bills
            WHERE LOWER(vendor_name) = LOWER(?)
              AND purchase_date = ?
              AND ABS(total_amount - ?) <= 0.02
            LIMIT 1
            """,
            (vendor, purchase_date, total_amount)
        )
        match = cursor.fetchone()
        if match:
            return {
                "duplicate": False,
                "soft_duplicate": True,
                "reason": f"Similar bill from {vendor} on {purchase_date} with amount ${total_amount:.2f} already exists (soft match)"
            }
        return {
            "duplicate": False,
            "soft_duplicate": False,
            "reason": "No duplicate detected"
        }
    finally:
        conn.close()
