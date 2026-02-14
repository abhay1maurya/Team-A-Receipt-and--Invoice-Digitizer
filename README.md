
---

# 📄 Receipt & Invoice Digitizer

An end-to-end AI-powered document digitization system that converts physical receipts and invoices into validated, normalized, and analytics-ready structured data.

Built with **Streamlit, Google Gemini AI, spaCy NLP, and SQLite**, this project is designed as a scalable foundation for financial tracking and analytics — not just an OCR demo.

---

# 🚀 Overview

Receipt & Invoice Digitizer automates the full lifecycle of document processing:

* Secure document ingestion
* AI-based OCR extraction
* Multi-tier fallback recovery
* Data normalization & validation
* Currency conversion
* Duplicate detection
* Persistent storage
* Interactive analytics dashboard

The system prioritizes **accuracy, fault tolerance, and modular architecture** to ensure reliable structured outputs.

---

# ✨ Core Features

### 📥 Document Processing

* Image & PDF support (JPG, PNG, PDF)
* Secure ingestion with hash-based change detection
* PDF-to-image conversion
* Image preprocessing for OCR optimization

### 🤖 AI-Powered Extraction

* Google Gemini structured JSON extraction
* Regex-based deterministic fallback
* spaCy NER vendor extraction
* Multi-tier recovery strategy

### 💱 Currency & Financial Integrity

* Multi-currency support
* Automatic conversion to USD
* Original currency + exchange rate preserved
* Tax-inclusive & tax-exclusive validation support

### 🔁 Duplicate Detection

* Hard duplicate blocking (invoice-level)
* Soft duplicate warning (logical similarity)

### 🗃️ Storage & Management

* SQLite database with normalized schema
* Bill history view
* Detailed bill inspection
* Cascade deletion of line items

### 📊 Analytics Dashboard (Milestone 3)

* KPI metrics (Total spend, Avg bill, Vendors, etc.)
* Monthly trend analysis
* Vendor distribution
* Payment method breakdown
* Export to CSV / Excel / PDF
* Insight generation below charts

---

# 🧠 System Architecture

```
Upload Document
      ↓
Ingestion & Hash Validation
      ↓
Image Preprocessing
      ↓
Gemini OCR (JSON + Raw Text)
      ↓
Multi-Tier Extraction
      ↓
Normalization & Currency Conversion
      ↓
Validation & Duplicate Detection
      ↓
SQLite Storage
      ↓
Dashboard & Analytics
```

---

# 🧰 Technology Stack

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

# 📁 Project Structure

```
Receipt-and-Invoice-Digitizer/
│
├── app.py
├── receipt_invoice.db
├── requirements.txt
├── setup.md
│
├── src/
│   ├── ingestion.py
│   ├── preprocessing.py
│   ├── ocr.py
│   ├── validation.py
│   ├── duplicate.py
│   ├── database.py
│   │
│   ├── extraction/
│   │   ├── field_extractor.py
│   │   ├── vendor_extractor_spacy.py
│   │   ├── normalizer.py
│   │   └── currency_converter.py
│   │
│   └── dashboard/
│       ├── analytics.py
│       ├── charts.py
│       ├── insights.py
│       ├── exports.py
│       └── dashboard_page.py
│
└── data/
```

---

# 🧩 Milestone 3 – Dashboard Module

The `src/dashboard` package is cleanly separated into layers:

### analytics.py

* Computes KPIs
* Aggregates monthly, vendor, and payment statistics
* No Streamlit or UI logic

### charts.py

* Plotly chart builders
* Consistent theming
* Interactive tooltips
* Responsive layouts

### insights.py

* Generates short textual insights from aggregated data
* Converts visual data into readable intelligence

### exports.py

* CSV, Excel, and PDF export utilities
* Summary & detailed exports

### dashboard_page.py

* Streamlit UI layer
* Applies filters
* Renders KPIs, charts, and insights

---

# 🧪 Multi-Tier Extraction Strategy

OCR is probabilistic. This system reduces failure risk using layered extraction.

### Tier 1 – Gemini AI

Primary structured JSON extraction.

### Tier 2 – Regex Fallback

Deterministic recovery for missing fields.

### Tier 3 – spaCy NER

ML-based vendor detection using ORG entities.

No heuristic scoring.
No fragile rule-based hacks.
Only deterministic and ML-backed logic.

---

# 💱 Currency Handling

* Supports INR, USD, EUR, GBP, MYR (extensible)
* Converts all analytics to USD
* Preserves:

  * Original currency
  * Original amount
  * Exchange rate used

Ensures global consistency.

---

# ✅ Validation Strategy

### Amount Validation

Accepts data if either:

* Tax-inclusive model matches
* Tax-exclusive model matches

Within tolerance (±0.02).

### Duplicate Detection

Hard duplicate → blocked
Soft duplicate → warned

Prevents accidental data corruption.

---

# 🗃️ Database Schema

### Bills Table

Stores normalized financial records with currency metadata and timestamps.

### Line Items Table

Stores item-level data with cascade deletion support.

Normalized and relational.

---

# 🔐 Security & Stability

* File size limits enforced
* PDF page limits enforced
* SHA-256 file hashing
* Parameterized SQLite queries
* Defensive JSON parsing
* API keys never stored in DB
* Graceful error handling across all layers

---

# ⚙️ Getting Started

### Prerequisites

* Python 3.13+
* Google Gemini API key
* poppler-utils (for PDF processing)

---

### Installation

```bash
git clone https://github.com/yourusername/Receipt-and-Invoice-Digitizer.git
cd Receipt-and-Invoice-Digitizer
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```


Run the app:

```bash
streamlit run app.py
```

Open:

```
http://localhost:8501
```

---

# 📊 Dashboard Capabilities

* Spending KPIs
* Monthly trend visualization
* Vendor & payment distribution
* Transaction distribution analysis
* Year-over-year comparison
* Insight generation below charts
* CSV / Excel / PDF exports

---

# 🛣️ Future Roadmap

* Multi-user authentication
* Budget tracking
* Expense categorization
* Mobile-optimized UI
* Advanced filtering
* REST API integration
* Batch uploads
* Manual editing interface

---

# 🏁 Current Status

**Version:** v1.0
**Status:** Stable, production-ready architecture

Completed:

* Multi-tier extraction
* Validation & duplicate detection
* Currency normalization
* SQLite persistence
* Analytics dashboard
* Export functionality
* Modular codebase structure

---

# 📌 Design Philosophy

* Never trust OCR blindly
* Fail safe, not silently
* No data corruption
* Deterministic fallbacks
* Modular, scalable architecture

---

---

# ⚙️ Getting Started

## 🔹 Prerequisites

* Python 3.13+
* Conda (Miniconda or Anaconda recommended)
* Google Gemini API key
* poppler-utils (required for PDF processing)

---

## 🔹 Setup Using Conda (Recommended)

This project was developed using a dedicated Conda environment to ensure dependency stability.

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/yourusername/Receipt-and-Invoice-Digitizer.git
cd Receipt-and-Invoice-Digitizer
```

---

### 2️⃣ Create a Conda Environment

```bash
conda create -n ridvenv python=3.13.11
```

---

### 3️⃣ Activate the Environment

```bash
conda activate ridvenv
```

---

### 4️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 5️⃣ Install spaCy Model

```bash
python -m spacy download en_core_web_sm
```

---

### 6️⃣ Configure API Key

Create a `.env` file in the root directory:

```
GOOGLE_API_KEY="your_gemini_api_key_here"
```

Alternatively, you can enter the API key inside the application sidebar.

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
