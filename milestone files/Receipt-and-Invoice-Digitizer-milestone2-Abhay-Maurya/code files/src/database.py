# Database persistence layer for receipt and invoice data
# Handles SQLite connections and CRUD operations for invoices and line items
# Schema: bills table (header data) + lineitems table (individual items)
# Uses SQLite for lightweight, serverless database storage

import os
import sqlite3
from typing import Dict, List, Optional
from datetime import datetime

# SQLite database file location - can be overridden via environment variable
# Defaults to 'receipt_invoice.db' in the current directory
DB_PATH = os.getenv("SQLITE_DB_PATH", "receipt_invoice.db")


def get_connection():
    """Create a new SQLite database connection.
    Returns a connection object that must be closed after use.
    SQLite is thread-safe with check_same_thread=False for Streamlit compatibility."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Allow dict-like access to rows
    return conn



def init_db():
    """Initialize SQLite database with clean, updated schema.
    Creates bills and lineitems tables with all required fields.
    Currency conversion fields included for multi-currency support."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Bills table: stores invoice header data with currency conversion support
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bills (
                bill_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                invoice_number VARCHAR(100),
                vendor_name VARCHAR(255) NOT NULL,
                purchase_date DATE NOT NULL,
                purchase_time TIME,
                subtotal DECIMAL(10, 2) DEFAULT 0,
                tax_amount DECIMAL(10, 2) DEFAULT 0,
                total_amount DECIMAL(10, 2) DEFAULT 0,
                currency VARCHAR(10) DEFAULT 'USD',
                original_currency VARCHAR(10),
                original_total_amount DECIMAL(10, 2),
                exchange_rate DECIMAL(10, 6),
                payment_method VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Line items table: stores individual items from each bill
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lineitems (
                item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_id INTEGER NOT NULL,
                description TEXT,
                quantity INTEGER NOT NULL DEFAULT 0,
                unit_price DECIMAL(10, 2) DEFAULT 0,
                total_price DECIMAL(10, 2) DEFAULT 0,
                FOREIGN KEY (bill_id) REFERENCES bills(bill_id) ON DELETE CASCADE
            )
        """)
        
        # Performance indexes for fast queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_bills_purchase_date 
            ON bills(purchase_date)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_bills_vendor 
            ON bills(vendor_name)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_lineitems_bill_id 
            ON lineitems(bill_id)
        """)

        conn.commit()
    finally:
        conn.close()

def insert_bill(bill_data: Dict, user_id: int = 1, currency: str = "USD", file_path: Optional[str] = None) -> int:
    """Insert a bill and its line items into the database.
    
    Args:
        bill_data: Dictionary containing bill fields and items array
        user_id: User ID for multi-user support (default: 1)
        currency: Target currency (default: 'USD', already converted by currency_converter)
        file_path: Optional source file path (unused, kept for API compatibility)
    
    Returns:
        Newly created bill_id
    
    Raises:
        Exception: Database insertion error (rolls back transaction)
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Extract fields with sensible defaults for incomplete OCR data
        invoice_number = bill_data.get("invoice_number") or None
        vendor = bill_data.get("vendor_name") or "Unknown"
        purchase_date = bill_data.get("purchase_date") or datetime.today().strftime("%Y-%m-%d")
        purchase_time = bill_data.get("purchase_time") or None
        subtotal = bill_data.get("subtotal", 0) or 0
        tax_amount = bill_data.get("tax_amount", 0) or 0
        total_amount = bill_data.get("total_amount", 0) or 0
        payment_method = bill_data.get("payment_method") or None
        
        # Currency conversion fields (preserved from original bill)
        currency_value = bill_data.get("currency", currency)
        original_currency = bill_data.get("original_currency")
        original_total_amount = bill_data.get("original_total_amount")
        exchange_rate = bill_data.get("exchange_rate")

        # Insert bill header into bills table
        cursor.execute(
            """
            INSERT INTO bills (
                user_id, invoice_number, vendor_name, purchase_date, purchase_time,
                subtotal, tax_amount, total_amount, currency,
                original_currency, original_total_amount, exchange_rate, payment_method
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, invoice_number, vendor, purchase_date, purchase_time,
             subtotal, tax_amount, total_amount, currency_value,
             original_currency, original_total_amount, exchange_rate, payment_method),
        )
        bill_id = cursor.lastrowid

        # Insert line items
        items = bill_data.get("items", []) or []
        for item in items:
            description = item.get("item_name", "")
            
            # Safely convert quantity to integer
            qty_val = item.get("quantity") or 0
            try:
                qty = int(round(float(qty_val)))
            except Exception:
                qty = 0
                
            unit_price = item.get("unit_price") or 0
            total_price = item.get("item_total") or (qty * unit_price)
            
            cursor.execute(
                """
                INSERT INTO lineitems (bill_id, description, quantity, unit_price, total_price)
                VALUES (?, ?, ?, ?, ?)
                """,
                (bill_id, description, qty, unit_price, total_price),
            )

        conn.commit()
        return bill_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_all_bills() -> List[Dict]:
    """Fetch all bills from database with standardized key mapping.
    
    Returns:
        List of bill dictionaries sorted by newest first, with consistent field types
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT bill_id AS id,
                   invoice_number,
                   vendor_name,
                   purchase_date,
                   purchase_time,
                   subtotal,
                   tax_amount,
                   total_amount,
                   currency,
                   original_currency,
                   original_total_amount,
                   exchange_rate,
                   payment_method
            FROM bills
            ORDER BY bill_id DESC
            """
        )
        rows = cursor.fetchall()
        bills = []
        for r in rows:
            bills.append(
                {
                    "id": r["id"],
                    "invoice_number": r["invoice_number"],
                    "vendor_name": r["vendor_name"],
                    "purchase_date": r["purchase_date"],
                    "purchase_time": r["purchase_time"],
                    "subtotal": float(r["subtotal"] or 0),
                    "tax_amount": float(r["tax_amount"] or 0),
                    "total_amount": float(r["total_amount"] or 0),
                    "currency": r["currency"] or "USD",
                    "original_currency": r["original_currency"],
                    "original_total_amount": float(r["original_total_amount"]) if r["original_total_amount"] else None,
                    "exchange_rate": float(r["exchange_rate"]) if r["exchange_rate"] else None,
                    "payment_method": r["payment_method"],
                }
            )
        return bills
    finally:
        conn.close()


def get_bill_items(bill_id: int) -> List[Dict]:
    """Fetch all line items for a specific bill.
    
    Args:
        bill_id: Primary key of bill to fetch items for
    
    Returns:
        List of line items with standardized field names and sequential numbering
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT item_id AS id,
                   description AS item_name,
                   quantity,
                   unit_price,
                   total_price AS item_total
            FROM lineitems
            WHERE bill_id = ?
            ORDER BY item_id
            """,
            (bill_id,),
        )
        rows = cursor.fetchall()
        items = []
        for idx, r in enumerate(rows, 1):
            items.append(
                {
                    "s_no": idx,
                    "item_name": r["item_name"] or "",
                    "quantity": r["quantity"] or 0,
                    "unit_price": float(r["unit_price"] or 0),
                    "item_total": float(r["item_total"] or 0),
                }
            )
        return items
    finally:
        conn.close()


def get_bill_details(bill_id: int) -> Optional[Dict]:
    """Fetch complete bill data including header and all line items.
    
    Args:
        bill_id: Primary key of bill to fetch
    
    Returns:
        Complete bill dictionary with header fields and items array, or None if not found
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT bill_id AS id,
                   vendor_name,
                   purchase_date,
                   purchase_time,
                   subtotal,
                   tax_amount,
                   total_amount,
                   currency,
                   payment_method
            FROM bills
            WHERE bill_id = ?
            """,
            (bill_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        bill = {
            "id": row["id"],
            "vendor_name": row["vendor_name"],
            "purchase_date": row["purchase_date"],
            "purchase_time": row["purchase_time"],
            "subtotal": float(row["subtotal"] or 0),
            "tax_amount": float(row["tax_amount"] or 0),
            "total_amount": float(row["total_amount"] or 0),
            "currency": row["currency"] or "USD",
            "payment_method": row["payment_method"] or "",
            "items": get_bill_items(bill_id)
        }
        return bill
    finally:
        conn.close()


def delete_bill(bill_id: int) -> bool:
    """Delete a bill and its associated line items from the database.
    
    Args:
        bill_id: Primary key of bill to delete
    
    Returns:
        True if bill was deleted, False if bill_id not found
    
    Note: Line items are automatically deleted via CASCADE constraint
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bills WHERE bill_id = ?", (bill_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
