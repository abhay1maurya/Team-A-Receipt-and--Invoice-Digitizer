I'll analyze your application structure and architecture to provide comprehensive technical documentation details.   

Read [](file:///d%3A/internship/spring%20board%20infosys/project/Team-A-Receipt-and--Invoice-Digitizer/app.py#1-1), lines 1 to 100

Read [](file:///d%3A/internship/spring%20board%20infosys/project/Team-A-Receipt-and--Invoice-Digitizer/requirements.txt)

Read [](file:///d%3A/internship/spring%20board%20infosys/project/Team-A-Receipt-and--Invoice-Digitizer/README.md#1-1), lines 1 to 100

Read [](file:///d%3A/internship/spring%20board%20infosys/project/Team-A-Receipt-and--Invoice-Digitizer/app.py#101-101), lines 101 to 200

Read [](file:///d%3A/internship/spring%20board%20infosys/project/Team-A-Receipt-and--Invoice-Digitizer/src/database.py#1-1), lines 1 to 100

Read [](file:///d%3A/internship/spring%20board%20infosys/project/Team-A-Receipt-and--Invoice-Digitizer/src/extraction/field_extractor.py#1-1), lines 1 to 100

Read [](file:///d%3A/internship/spring%20board%20infosys/project/Team-A-Receipt-and--Invoice-Digitizer/app.py#200-200), lines 200 to 300

Read [](file:///d%3A/internship/spring%20board%20infosys/project/Team-A-Receipt-and--Invoice-Digitizer/src/ocr.py#1-1), lines 1 to 50

Read [](file:///d%3A/internship/spring%20board%20infosys/project/Team-A-Receipt-and--Invoice-Digitizer/src/extraction/template_parser.py#1-1), lines 1 to 50

Read [](file:///d%3A/internship/spring%20board%20infosys/project/Team-A-Receipt-and--Invoice-Digitizer/src/dashboard/dashboard_page.py#1-1), lines 1 to 50

Read [](file:///d%3A/internship/spring%20board%20infosys/project/Team-A-Receipt-and--Invoice-Digitizer/src)

Read [](file:///d%3A/internship/spring%20board%20infosys/project/Team-A-Receipt-and--Invoice-Digitizer/src/validation.py)

Read [](file:///d%3A/internship/spring%20board%20infosys/project/Team-A-Receipt-and--Invoice-Digitizer/src/duplicate.py)

Searched for regex `class|def page_|def main` (`**/app.py`), 9 results

Read [](file:///d%3A/internship/spring%20board%20infosys/project/Team-A-Receipt-and--Invoice-Digitizer/src/extraction)

Read [](file:///d%3A/internship/spring%20board%20infosys/project/Team-A-Receipt-and--Invoice-Digitizer/src/dashboard)

Read [](file:///d%3A/internship/spring%20board%20infosys/project/Team-A-Receipt-and--Invoice-Digitizer/src/preprocessing.py#1-1), lines 1 to 50

Read [](file:///d%3A/internship/spring%20board%20infosys/project/Team-A-Receipt-and--Invoice-Digitizer/src/ingestion.py#1-1), lines 1 to 50

Read [](file:///d%3A/internship/spring%20board%20infosys/project/Team-A-Receipt-and--Invoice-Digitizer/src/dashboard/analytics.py#1-1), lines 1 to 100

Now let me read the routing section of app.py to see how pages are handled:  

Read [](file:///d%3A/internship/spring%20board%20infosys/project/Team-A-Receipt-and--Invoice-Digitizer/app.py#600-600), lines 600 to 637

Read [](file:///d%3A/internship/spring%20board%20infosys/project/Team-A-Receipt-and--Invoice-Digitizer/src/database.py#100-100), lines 100 to 200

Perfect! Now I have enough information to create comprehensive technical documentation. Let me compile it:

---

## **Application Structure & Architecture Documentation**

### **1. Application Overview**

**DigitizeBills** is an AI-powered receipt and invoice digitization platform built with a modular, layered architecture. The application automates document processing from upload to analytics using Google Gemini AI, spaCy NLP, and SQLite persistence.

**Tech Stack:**
- **Frontend:** Streamlit 1.52.2 (web UI framework)
- **AI/ML:** Google Gemini AI (OCR), spaCy 3.8.11 (NER), XGBoost 3.1.2 (ML)
- **Image Processing:** OpenCV 4.12, Pillow 12.1, pdf2image 1.17
- **Data & Analytics:** Pandas 2.3.3, NumPy 2.2.6, Plotly 6.5.0
- **Database:** SQLite 3 (serverless, file-based)
- **Reporting:** ReportLab 4.2.2 (PDF), XlsxWriter 3.2.9 (Excel)

---

### **2. System Architecture**

**Architecture Pattern:** Multi-tier MVC (Model-View-Controller) with modular components

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                       │
│  app.py (Streamlit UI) → Routes to page modules            │
│  ├─ Dashboard Page (analytics & charts)                     │
│  ├─ Upload & Process Page (document workflow)               │
│  ├─ History Page (bill list)                               │
│  └─ Admin Page (system management)                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    BUSINESS LOGIC LAYER                     │
│  src/ (Core processing modules)                             │
│  ├─ ingestion.py → File upload & hash validation           │
│  ├─ preprocessing.py → Image enhancement                    │
│  ├─ ocr.py → Gemini AI extraction                          │
│  ├─ extraction/ → Multi-tier field extraction               │
│  │   ├─ template_parser.py (vendor templates)              │
│  │   ├─ field_extractor.py (regex fallback)                │
│  │   ├─ normalizer.py (data standardization)               │
│  │   └─ currency_converter.py (FX conversion)              │
│  ├─ validation.py → Amount & logic checks                   │
│  ├─ duplicate.py → Duplicate detection                      │
│  └─ database.py → Data persistence                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     DATA LAYER                              │
│  SQLite Database (receipt_invoice.db)                       │
│  ├─ bills (invoice headers with indexes)                    │
│  └─ lineitems (item details with FK cascade)                │
└─────────────────────────────────────────────────────────────┘
```

---

### **3. Application Flow**

**Complete Document Processing Pipeline:**

```
1. INGESTION (ingestion.py)
   ├─ Upload validation (format, size)
   ├─ SHA256 hash generation (change detection)
   └─ PDF → PIL Image conversion (multi-page support)

2. PREPROCESSING (preprocessing.py)
   ├─ EXIF rotation correction
   ├─ Grayscale conversion
   ├─ Contrast enhancement
   ├─ Otsu binarization
   └─ Noise removal (morphological operations)

3. OCR & EXTRACTION (ocr.py + extraction/)
   ├─ Gemini AI structured extraction (primary)
   ├─ Template-based parsing (vendor-specific)
   └─ Regex fallback (deterministic)

4. NORMALIZATION (extraction/normalizer.py)
   ├─ Date parsing (multiple formats)
   ├─ Currency conversion to USD
   ├─ Amount calculations (subtotal + tax)
   └─ Field type coercion

5. VALIDATION (validation.py + duplicate.py)
   ├─ Amount validation (tax-inclusive/exclusive)
   ├─ Hard duplicate blocking (invoice number match)
   └─ Soft duplicate warning (logical similarity)

6. PERSISTENCE (database.py)
   ├─ Transaction-based insertion
   ├─ Line items cascade storage
   └─ Indexed queries for performance

7. ANALYTICS (dashboard/)
   ├─ KPI calculations (cached)
   ├─ Chart generation (Plotly)
   ├─ Filtering & search
   └─ Export (CSV/Excel/PDF)
```

---

### **4. Directory Structure**

```
Team-A-Receipt-and--Invoice-Digitizer/
│
├─ app.py                          # Main entry point & routing
├─ requirements.txt                # Python dependencies
├─ receipt_invoice.db             # SQLite database (auto-created)
│
├─ src/                            # Core business logic
│  ├─ __init__.py
│  ├─ ingestion.py                # File upload & hash validation
│  ├─ preprocessing.py            # Image enhancement (OpenCV)
│  ├─ ocr.py                      # Gemini AI OCR extraction
│  ├─ validation.py               # Amount & duplicate validation
│  ├─ duplicate.py                # Duplicate detection logic
│  ├─ database.py                 # SQLite CRUD operations
│  ├─ admin_page.py               # Admin UI page
│  │
│  ├─ extraction/                 # Multi-tier extraction layer
│  │  ├─ __init__.py
│  │  ├─ template_parser.py       # Vendor-specific templates
│  │  ├─ field_extractor.py       # Regex fallback extraction
│  │  ├─ normalizer.py            # Data standardization
│  │  ├─ currency_converter.py    # Multi-currency conversion
│  │  ├─ vendor_extractor_spacy.py # spaCy NER vendor detection
│  │  ├─ regex_patterns.py        # Compiled regex patterns
│  │  └─ templates/               # Vendor JSON templates
│  │     ├─ walmart.json
│  │     ├─ amazon.json
│  │     ├─ flipkart.json
│  │     └─ [... more vendors]
│  │
│  └─ dashboard/                  # Analytics & visualization
│     ├─ dashboard_page.py        # Main dashboard UI
│     ├─ analytics.py             # KPI & metric calculations
│     ├─ charts.py                # Plotly chart generation
│     ├─ insights.py              # Data insights engine
│     ├─ ai_insights.py           # AI-powered insights
│     └─ exports.py               # CSV/Excel/PDF export
│
├─ data/                          # Sample data (optional)
├─ documents/                     # Project documentation
└─ milestone files/               # Historical milestone code
```

---

### **5. Core Modules Deep Dive**

#### **5.1 app.py - Main Application**

**Responsibilities:**
- Session state management (17 state variables)
- Page routing (Dashboard, Upload, History, Admin)
- Sidebar navigation & API key handling
- File upload orchestration

**Key Session State Variables:**
```python
# Navigation
current_page: str              # Active page name

# Document State
file_type: str                 # 'image' or 'pdf'
images: List[PIL.Image]        # Converted PIL images
metadata: Dict                 # File metadata
ingestion_done: bool           # Upload complete flag
last_file_hash: str            # SHA256 for change detection

# Processing State
processed_pages: List[bool]    # Multi-page PDF tracking
processed_images: List[Image]  # Preprocessed images
extracted_bill_data: Dict      # Structured JSON from OCR
bill_saved: bool               # Database save flag
```

**Page Routing Logic:**
```python
# Conditional rendering based on session state
if st.session_state.current_page == "Dashboard":
    page_dashboard()
elif st.session_state.current_page == "Upload & Process":
    page_upload_process()
elif st.session_state.current_page == "History":
    page_history()
elif st.session_state.current_page == "Admin":
    page_admin()
```

---

#### **5.2 database.py - Data Persistence**

**Database Schema:**

```sql
-- Bills table (invoice headers)
CREATE TABLE bills (
    bill_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER DEFAULT 1,
    invoice_number VARCHAR(100),
    vendor_name VARCHAR(255) NOT NULL,
    purchase_date DATE NOT NULL,
    purchase_time TIME,
    subtotal DECIMAL(10,2),
    tax_amount DECIMAL(10,2),
    total_amount DECIMAL(10,2),
    currency VARCHAR(10) DEFAULT 'USD',
    original_currency VARCHAR(10),
    original_total_amount DECIMAL(10,2),
    exchange_rate DECIMAL(10,6),
    payment_method VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Line items table (individual products)
CREATE TABLE lineitems (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id INTEGER NOT NULL,
    description TEXT,
    quantity INTEGER DEFAULT 0,
    unit_price DECIMAL(10,2),
    total_price DECIMAL(10,2),
    FOREIGN KEY (bill_id) REFERENCES bills(bill_id) 
        ON DELETE CASCADE
);
```

**Performance Indexes:**
- `idx_bills_purchase_date` → Fast date range queries
- `idx_bills_vendor` → Fast vendor filtering
- `idx_bills_payment_method` → Payment analytics
- `idx_bills_total_amount` → Amount range filtering
- `idx_lineitems_bill_id` → Fast item lookups

**Key Functions:**
- `init_db()` → Schema creation with indexes
- `insert_bill(bill_data)` → Transaction-based insertion
- `get_all_bills()` → Fetch all invoices
- `get_filtered_bills(filters)` → Optimized filtering with WHERE clauses
- `get_monthly_spending()` → SQL aggregation for reports
- `delete_bill(bill_id)` → Cascade deletion

---

#### **5.3 src/extraction/ - Multi-Tier Extraction**

**Extraction Strategy (3-tier fallback):**

**Tier 1: Template Parser (template_parser.py)**
- Vendor-specific JSON templates with anchor keywords
- Regex patterns per field (invoice, date, totals)
- Template matching by vendor detection
- Highest accuracy for known vendors

**Tier 2: Field Extractor (field_extractor.py)**
- Deterministic regex patterns (regex_patterns.py)
- Label-based amount extraction
- Multi-format date/time parsing
- Fallback when Gemini extraction is weak

**Tier 3: Gemini AI (ocr.py)**
- Google Gemini Vision structured JSON extraction
- Schema-driven prompt engineering
- Raw OCR text returned for fallback analysis

**Normalizer (normalizer.py):**
- Post-extraction data standardization
- Date parsing (10+ formats supported)
- Currency conversion to USD
- Calculated fields (currency metadata)

**Vendor Templates Example (walmart.json):**
```json
{
  "vendor": "Walmart",
  "aliases": ["WAL-MART", "WALMART"],
  "fields": {
    "invoice_number": {
      "patterns": ["INVOICE[:#\\s]+(\\w+)"],
      "anchor": "invoice"
    },
    "total": {
      "label_patterns": ["TOTAL", "GRAND TOTAL"],
      "regex": "\\$?([0-9,]+\\.[0-9]{2})"
    }
  }
}
```

---

#### **5.4 validation.py - Data Validation**

**Two-Level Validation:**

**1. Amount Validation (`validate_bill_amounts`):**
- Supports tax-inclusive and tax-exclusive models
- Tolerance threshold (±0.02) for OCR rounding errors
- Returns detailed error breakdown

**Logic:**
```python
# Tax-inclusive: items_sum ≈ total
# Tax-exclusive: items_sum + tax ≈ total
is_valid = (items_sum ≈ total) OR (items_sum + tax ≈ total)
```

**2. Duplicate Detection (`detect_duplicate_bill_logical`):**
- **Hard duplicate (blocks save):** Invoice number + vendor + date + amount match
- **Soft duplicate (warns):** No invoice number, but vendor + date + amount match
- Uses indexed queries for fast lookups

---

#### **5.5 src/dashboard/ - Analytics Layer**

**Module Organization:**
- dashboard_page.py → UI orchestration, filters, caching
- analytics.py → Pure data processing (KPIs, aggregations)
- `charts.py` → Plotly chart generation
- `insights.py` → Insight generation logic
- `ai_insights.py` → AI-powered spending analysis
- `exports.py` → CSV/Excel/PDF export

**Caching Strategy:**
```python
@st.cache_data(ttl=60, show_spinner=False)
def _cached_bills():
    return get_all_bills() or []
```

**KPI Metrics:**
- Total spending (sum of all bills)
- Transaction count
- Average transaction amount
- Unique vendors count
- Average spending per month
- Month-over-month delta (% change)

**Filter Capabilities:**
- Date range filtering
- Amount range (min/max)
- Vendor selection
- Payment method
- Search by invoice number

**Export Formats:**
- CSV (raw data)
- Excel (formatted with headers)
- PDF (formatted report with ReportLab)

---

### **6. Data Flow Example**

**Uploading a Walmart receipt:**

```
1. User uploads walmart_receipt.jpg (2.3 MB)
   ↓
2. ingestion.py
   - Validates file size ≤ 5MB ✓
   - Generates SHA256: a3f8... 
   - Converts to PIL Image
   ↓
3. preprocessing.py
   - Fixes EXIF rotation
   - Converts to grayscale
   - Applies Otsu binarization
   - Removes noise with morphology
   ↓
4. ocr.py (Gemini AI)
   - Sends image to Gemini API
   - Receives JSON + raw OCR text
   - Extracts fields with confidence scores
   ↓
5. template_parser.py
   - Detects "WALMART" in OCR text
   - Loads walmart.json template
   - Applies vendor-specific patterns
   - Fills weak Gemini fields
   ↓
6. normalizer.py
   - Parses date: "01/15/2026" → 2026-01-15
   - Converts INR 1500 → USD 18.05 (rate: 83.13)
   - Stores original_currency, exchange_rate
   ↓
7. validation.py
   - Checks: items_sum + tax ≈ total ✓
   - No duplicate detected ✓
   - can_save = True
   ↓
8. database.py
   - INSERT INTO bills (transaction)
   - INSERT INTO lineitems (5 items)
   - COMMIT
   ↓
9. Dashboard updates (cache refreshes)
   - Total spending increases
   - Walmart vendor chart updates
   - Monthly trend recalculated
```

---

### **7. Key Design Patterns**

**1. Multi-Tier Fallback Strategy**
- Primary: Gemini AI extraction
- Secondary: Template-based parsing
- Tertiary: Regex fallback
- Defense against AI hallucinations

**2. Session State Management**
- Persistent state across Streamlit reruns
- Change detection via file hashing
- Prevents redundant processing

**3. Separation of Concerns**
- UI layer (app.py, dashboard_page.py)
- Business logic (src/*.py)
- Data layer (database.py)
- Clear module boundaries

**4. Caching & Performance**
- Streamlit `@st.cache_data` for expensive operations
- SQL aggregation for reports
- Indexed database queries
- Limited query result sets

**5. Error Resilience**
- Try-except blocks at module boundaries
- Graceful degradation (fallback extraction)
- User-friendly error messages
- Transaction rollbacks on failure

---

### **8. Security & Validation**

**Input Validation:**
- File size limit: 5 MB
- File type whitelist: JPG, PNG, PDF
- Image decompression bomb protection (10 MP limit)
- PDF page limit: 5 pages

**Data Integrity:**
- SHA256 file hashing
- Database foreign key constraints
- Cascade deletion for orphaned line items
- Transaction-based inserts (ACID compliance)

**API Security:**
- API key stored in session state (not logged)
- Password-type input field for key entry
- API key required before processing

---

### **9. Scalability Considerations**

**Current Limitations:**
- SQLite (single-writer constraint)
- Session state tied to user browser session
- No authentication/authorization
- Single-user MVP design

**Future Enhancements:**
- PostgreSQL/MySQL for multi-user
- Redis caching layer
- Async processing queue (Celery)
- User authentication (OAuth2)
- Horizontal scaling with load balancer

---

This documentation provides a comprehensive technical overview of your application's structure, architecture, data flow, and design patterns. You can use these sections directly in your milestone documentation or adapt them as needed!