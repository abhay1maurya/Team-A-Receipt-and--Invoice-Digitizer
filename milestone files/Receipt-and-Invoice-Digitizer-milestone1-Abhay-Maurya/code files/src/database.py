# Database persistence layer for receipt and invoice data
# Handles MySQL connections and CRUD operations for invoices and line items
# Schema: invoices table (header data) + lineitems table (individual items)
# Uses environment variables for flexible deployment across dev/prod environments

import os
import mysql.connector
from typing import Dict, List, Optional
from datetime import datetime

# MySQL connection settings - can be overridden via environment variables
# This allows different credentials for dev/staging/production without code changes
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")  # Database server address
MYSQL_USER = os.getenv("MYSQL_USER", "root")  # Database username
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "Panda008")  # Database password
MYSQL_DB = os.getenv("MYSQL_DB", "receipt_invoice_db")  # Database name


def get_connection():
    """Create a new MySQL database connection.
    Returns a connection object that must be closed after use.
    Each function creates its own connection to avoid threading issues."""
    return mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
    )


def init_db():
    """Placeholder to satisfy app imports; schema is managed externally.
    Database tables (invoices, lineitems) should be created manually or via migration scripts.
    Returns None to indicate schema management is external to this application."""
    return None


def insert_bill(bill_data: Dict, user_id: int = 1, currency: str = "USD", file_path: Optional[str] = None) -> int:
    """Insert a bill and its line items into MySQL database (new schema).

    Tables:
        - bills(bill_id, user_id, vendor_name, purchase_date, purchase_time, total_amount, tax_amount, currency, payment_method)
        - lineitems(item_id, bill_id, description, quantity, unit_price, total_price)

    Returns the newly created bill_id.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Extract bill header fields with fallback defaults
        invoice_number = bill_data.get("invoice_number") or None
        vendor = bill_data.get("vendor_name") or "Unknown"
        # purchase_date is NOT NULL; default to today's date if missing
        purchase_date = bill_data.get("purchase_date") or datetime.today().strftime("%Y-%m-%d")
        purchase_time = bill_data.get("purchase_time") or None
        tax_amount = bill_data.get("tax", bill_data.get("tax_amount", 0)) or 0
        total_amount = bill_data.get("total_amount", 0) or 0
        currency_value = bill_data.get("currency", currency)
        payment_method = bill_data.get("payment_method") or None

        # Insert bill header data into bills table
        cursor.execute(
            """
            INSERT INTO bills (user_id, invoice_number, vendor_name, purchase_date, purchase_time, total_amount, tax_amount, currency, payment_method)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (user_id, invoice_number, vendor, purchase_date, purchase_time, total_amount, tax_amount, currency_value, payment_method),
        )
        # Get auto-generated bill_id for linking line items
        bill_id = cursor.lastrowid

        # Insert each line item with foreign key reference to bill
        items = bill_data.get("items", []) or []
        for s_no, item in enumerate(items, 1):
            description = item.get("item_name", "")  # Item description from OCR
            # quantity is INT NOT NULL; coerce to int safely
            qty_val = item.get("quantity") or 0
            try:
                qty = int(round(float(qty_val)))
            except Exception:
                qty = 0
            unit_price = item.get("unit_price") or 0
            # Calculate total_price if not provided
            total_price = item.get("item_total") or (qty * unit_price)
            cursor.execute(
                """
                INSERT INTO lineitems (bill_id, description, quantity, unit_price, total_price)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (bill_id, description, qty, unit_price, total_price),
            )

        # Commit transaction - saves both invoice and all line items atomically
        conn.commit()
        return bill_id
    except Exception as e:
        # Rollback on any error to maintain data consistency
        conn.rollback()
        raise e
    finally:
        # Always close connection to free resources
        conn.close()


def get_all_bills() -> List[Dict]:
    """Fetch all bills from database with app-friendly key mapping (new schema).
    Returns rows sorted by newest first."""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)  # Return results as dictionaries
        cursor.execute(
            """
            SELECT bill_id AS id,
                   invoice_number,
                   vendor_name,
                   purchase_date,
                   total_amount,
                   tax_amount,
                   currency,
                   payment_method,
                   purchase_time
            FROM bills
            ORDER BY bill_id DESC
            """
        )
        rows = cursor.fetchall()
        bills = []
        # Transform each row to ensure consistent data types and handle nulls
        for r in rows:
            bills.append(
                {
                    "id": r["id"],
                    "invoice_number": r.get("invoice_number"),
                    "vendor_name": r["vendor_name"],
                    "purchase_date": r.get("purchase_date"),  # May be None if not provided
                    "total_amount": float(r.get("total_amount") or 0),  # Convert Decimal to float
                    "tax_amount": float(r.get("tax_amount") or 0),
                    "currency": r.get("currency", "USD"),
                    "payment_method": r.get("payment_method"),
                    "purchase_time": r.get("purchase_time"),
                }
            )
        return bills
    finally:
        conn.close()


def get_bill_items(bill_id: int) -> List[Dict]:
    """Fetch all line items for a specific invoice.
    
    Args:
        bill_id: Primary key of bill to fetch items for
    
    Returns:
        List of dictionaries containing line item data with renamed columns:
        - description -> item_name (matches OCR extraction keys)
        - total_price -> item_total (consistent with app naming)
        - s_no added as sequential number for display purposes
    """
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT item_id AS id,
                   description AS item_name,
                   quantity,
                   unit_price,
                   total_price AS item_total
            FROM lineitems
            WHERE bill_id = %s
            ORDER BY item_id
            """,
            (bill_id,),
        )
        rows = cursor.fetchall()
        items = []
        # Add sequential numbering for display in tables
        for idx, r in enumerate(rows, 1):
            items.append(
                {
                    "s_no": idx,  # Serial number for table display
                    "item_name": r.get("item_name", ""),
                    "quantity": r.get("quantity", 0),
                    "unit_price": float(r.get("unit_price") or 0),  # Convert Decimal to float
                    "item_total": float(r.get("item_total") or 0),
                }
            )
        return items
    finally:
        conn.close()


def get_bill_details(bill_id: int) -> Optional[Dict]:
    """Fetch complete bill data including invoice header and all line items.
    
    Args:
        bill_id: Primary key of bill to fetch
    
    Returns:
        Dictionary containing complete bill data with both header and items,
        or None if bill_id not found.
    
    Note: Includes calculated fields (subtotal) and placeholder fields
    (purchase_time, payment_method, ocr_text) for backward compatibility.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT bill_id AS id,
                   vendor_name,
                   purchase_date,
                   purchase_time,
                   total_amount,
                   tax_amount,
                   currency,
                   payment_method
            FROM bills
            WHERE bill_id = %s
            """,
            (bill_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None  # Bill not found

        # Build complete bill dictionary with calculated and placeholder fields
        bill = {
            "id": row["id"],
            "vendor_name": row["vendor_name"],
            "purchase_date": row.get("purchase_date"),
            "purchase_time": row.get("purchase_time"),
            "subtotal": float(row.get("total_amount") or 0) - float(row.get("tax_amount") or 0),  # Calculated
            "discount": 0.0,  # Not stored in schema
            "tax": float(row.get("tax_amount") or 0),
            "total_amount": float(row.get("total_amount") or 0),
            "payment_method": row.get("payment_method", ""),
            "currency": row.get("currency", "USD"),
            "ocr_text": "",  # Not stored in schema - would need separate table
        }
        # Attach line items to complete the bill details
        bill["items"] = get_bill_items(bill_id)
        return bill
    finally:
        conn.close()


def delete_bill(bill_id: int) -> bool:
    """Delete a bill from the database.
    
    Args:
        bill_id: Primary key of bill to delete
    
    Returns:
        True if bill was deleted, False if bill_id not found
    
    Note: Line items are automatically deleted via CASCADE constraint
    defined in the database schema.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bills WHERE bill_id = %s", (bill_id,))
        conn.commit()
        return cursor.rowcount > 0  # True if any rows were affected
    except Exception as e:
        conn.rollback()  # Undo changes on error
        raise e
    finally:
        conn.close()