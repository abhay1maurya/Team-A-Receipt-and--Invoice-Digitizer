
# 📄 Receipt and Invoice Digitizer

An end-to-end AI-powered document digitization system that converts receipts and invoices into validated, normalized, and analytics-ready structured data.

Built with **Streamlit, Google Gemini AI, spaCy, and SQLite**, this project focuses on accuracy, fault tolerance, and a modular architecture.

---

## 🚀 Overview

Receipt and Invoice Digitizer automates the full lifecycle of document processing:

* Secure document ingestion
* AI-based OCR extraction
* Multi-tier fallback recovery
* Data normalization and validation
* Currency conversion
* Duplicate detection
* Persistent storage
* Interactive analytics dashboard

---

## ✨ Core Features

### 📥 Document Processing

* Image and PDF support (JPG, PNG, PDF)
* Hash-based change detection
* PDF-to-image conversion
* Image preprocessing for OCR optimization

### 🤖 AI-Powered Extraction

* Google Gemini structured JSON extraction
* Regex-based deterministic fallback
* spaCy NER vendor extraction
* Multi-tier recovery strategy

### 💱 Currency and Financial Integrity

* Multi-currency support
* Automatic conversion to USD
* Original currency and exchange rate preserved
* Tax-inclusive and tax-exclusive validation support

### 🔁 Duplicate Detection

* Hard duplicate blocking (invoice-level)
* Soft duplicate warning (logical similarity)

### 🗃️ Storage and Management

* SQLite database with normalized schema
* Bill history view
* Detailed bill inspection
* Cascade deletion of line items

### 📊 Analytics Dashboard

* KPI metrics (total spend, average bill, vendors, transactions)
* Monthly trend analysis
* Vendor distribution
* Payment method breakdown
* Export to CSV, Excel, and PDF
* Insight generation below charts

---

## 🧠 System Architecture

```
Upload Document
      ↓
Ingestion and Hash Validation
      ↓
Image Preprocessing
      ↓
Gemini OCR (JSON + Raw Text)
      ↓
Multi-Tier Extraction
      ↓
Normalization and Currency Conversion
      ↓
Validation and Duplicate Detection
      ↓
SQLite Storage
      ↓
Dashboard and Analytics
```

---

## 🧰 Technology Stack

| Layer            | Technology              |
| ---------------- | ----------------------- |
| Frontend         | Streamlit               |
| OCR Engine       | Google Gemini 2.5 Flash |
| NLP / NER        | spaCy (en_core_web_sm)  |
| Image Processing | PIL, OpenCV             |
| PDF Processing   | pdf2image               |
| Database         | SQLite                  |
| Analytics        | Pandas, Plotly          |
| Language         | Python 3.13+            |

---

## 📁 Project Structure

```
Receipt-and-Invoice-Digitizer/
│
├── app.py                         # Main Streamlit application
├── receipt_invoice.db             # SQLite database (auto-generated)
├── requirements.txt
├── steps_pull.md                  # Team workflow notes
├── README.md
│
├── data/                          # Sample data
├── documents/                     # Uploaded documents
├── milestone files/               # Milestone deliverables
├── static/                        # Static assets
│
└── src/
    ├── __init__.py
    ├── admin_page.py              # Admin tools and maintenance UI
    ├── ingestion.py               # File ingestion and hashing
    ├── preprocessing.py           # Image preprocessing
    ├── ocr.py                     # Gemini OCR orchestration
    ├── validation.py              # Amount and duplicate validation
    ├── duplicate.py               # Logical duplicate detection
    ├── database.py                # SQLite persistence
    │
    ├── extraction/
    │   ├── __init__.py
    │   ├── field_extractor.py     # Regex-based extraction
    │   ├── regex_patterns.py      # Regex patterns library
    │   ├── vendor_extractor_spacy.py  # spaCy NER vendor extraction
    │   ├── normalizer.py          # Data normalization
    │   └── currency_converter.py  # Currency conversion to USD
    │
    └── dashboard/
        ├── analytics.py           # KPI and aggregation logic
        ├── charts.py              # Plotly chart builders
        ├── insights.py            # Narrative insights from data
        ├── exports.py             # CSV, Excel, PDF exports
        └── dashboard_page.py      # Streamlit dashboard UI
```

---

## 🧩 Dashboard Module (src/dashboard)

The dashboard package is intentionally separated into layers:

* analytics.py: KPI calculations and aggregations (no Streamlit code)
* charts.py: Plotly chart builders with shared theming
* insights.py: Short narrative insights derived from chart data
* exports.py: CSV, Excel, and PDF export helpers
* dashboard_page.py: Streamlit UI with filters, KPIs, charts, and tables

---

## 🧪 Multi-Tier Extraction Strategy

OCR is probabilistic. This system reduces failure risk using layered extraction.

* Tier 1: Gemini AI structured JSON extraction
* Tier 2: Regex fallback for missing fields
* Tier 3: spaCy NER vendor detection (ORG entities)

---

## 💱 Currency Handling

* Supports INR, USD, EUR, GBP, MYR (extensible)
* Converts analytics to USD
* Preserves original currency, original amount, and exchange rate

---

## ✅ Validation Strategy

* Amount validation accepts tax-inclusive or tax-exclusive totals within tolerance (±0.02)
* Hard duplicates are blocked, soft duplicates are warned

---

## 🔐 Security and Stability

* File size and PDF page limits enforced
* SHA-256 file hashing
* Parameterized SQLite queries
* Defensive JSON parsing
* API keys never stored in the database
* Graceful error handling across layers

---

## ⚙️ Getting Started

### Prerequisites

* Python 3.13+
* Google Gemini API key
* poppler-utils (for PDF processing)

### Setup

```bash
git clone https://github.com/yourusername/Receipt-and-Invoice-Digitizer.git
cd Receipt-and-Invoice-Digitizer
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

Set your API key using the `GOOGLE_API_KEY` environment variable, or enter it in the app sidebar.

Run the app:

```bash
streamlit run app.py
```

Open:

```
http://localhost:8501
```

---

## 📊 Dashboard Capabilities

* Spending KPIs
* Monthly trend visualization
* Vendor and payment distribution
* Transaction distribution analysis
* Year-over-year comparison
* Insight generation below charts
* CSV, Excel, and PDF exports

---

## 🛣️ Future Roadmap

* Multi-user authentication
* Budget tracking and alerts
* Expense categorization
* Mobile-optimized UI
* Advanced filtering and search
* REST API integration
* Batch uploads
* Manual editing interface

---

## 🏁 Current Status

**Version:** v1.0
**Status:** Stable, production-ready architecture

Completed:

* Multi-tier extraction
* Validation and duplicate detection
* Currency normalization
* SQLite persistence
* Analytics dashboard
* Export functionality
* Modular codebase structure

---

## 📌 Design Philosophy

* Never trust OCR blindly
* Fail safe, not silently
* No data corruption
* Deterministic fallbacks
* Modular, scalable architecture

---

### 5️⃣ Install spaCy Model

```bash
python -m spacy download en_core_web_sm
```

---

### 6️⃣ Configure API Key

Set `GOOGLE_API_KEY` in your environment or enter the API key inside the application sidebar.

---

### 7️⃣ Run the Application

```bash
streamlit run app.py
```

Open in browser:

```
http://localhost:8501
```

---

## 🔹 Optional: Export Conda Environment

To reproduce the exact environment:

```bash
conda env export --no-builds > environment.yml
```

To recreate:

```bash
conda env create -f environment.yml
conda activate ridvenv
```

---

This ensures:

* Dependency stability
* Reproducible development environment
* Clean team collaboration

---
