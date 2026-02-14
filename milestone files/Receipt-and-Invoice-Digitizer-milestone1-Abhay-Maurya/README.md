

# 📄 Receipt & Invoice Digitizer

**Milestone 1 – Document Digitization & Structured Data Extraction**

⚠️ Important Note This repository contains only Milestone 1 of the Receipt & Invoice Digitizer project.

🔗 Main Project Repository (Milestone 1 + Milestone 2): https://github.com/abhay1maurya/Receipt-and-Invoice-Digitizer

Milestone 1 covers ingestion, preprocessing, OCR, UI, and base persistence. 
---

## 📌 Project Overview

The **Receipt & Invoice Digitizer** is a multi-page Streamlit-based web application that converts physical receipts and invoices into structured digital records.
The system automates document ingestion, preprocessing, OCR, structured data extraction using **Google Gemini AI**, and persistent storage in a **MySQL database**, while providing analytics and history through an interactive UI.

This project addresses the real-world problem of **manual bill entry**, **expense tracking**, and **data loss from physical receipts**.

---

## 🎯 Objectives (Milestone 1)

The primary objective of **Milestone 1** is to establish a **stable, secure, and extensible document digitization pipeline** that reliably converts uploaded receipt and invoice documents into structured digital data.

Milestone 1 focuses on:

* Supporting ingestion of **JPG, PNG, and PDF** documents
* Converting all documents into **OCR-ready image formats**
* Automatically preprocessing images for optimal OCR accuracy
* Performing **OCR and structured data extraction** using Google Gemini AI
* Enforcing **schema-controlled structured output**
* Maintaining application state across Streamlit reruns
* Providing a **clean and user-friendly UI** for inspection
* Implementing **controlled error handling and graceful failures**
* Laying the foundation for persistent storage and analytics

---

## 🏗️ System Architecture

```
User Upload (JPG / PNG / PDF)
        ↓
Ingestion Layer
        ↓
Preprocessing Layer
        ↓
OCR & Structured Extraction (Gemini AI)
        ↓
Session State Cache
        ↓
Streamlit UI (Results, Dashboard, History)
        ↓
MySQL Database (Bills & Line Items)
```

---

## 🧩 Core Modules

### 1️⃣ Ingestion Module

**Purpose:**
Safely converts uploaded files into standardized image inputs.

**Key Features:**

* Supports images and multi-page PDFs
* Converts PDFs to page-wise images
* Generates SHA-256 file hash to detect duplicate uploads
* Enforces security limits (page limits, image size checks)

**Output:**
A list of normalized PIL Image objects + metadata.

---

### 2️⃣ Preprocessing Module

**Purpose:**
Enhances image quality to improve OCR accuracy.

**Processing Steps:**

* EXIF-based orientation correction
* Transparency removal (white background normalization)
* Grayscale conversion
* Contrast enhancement
* Otsu binarization
* Noise removal (median filtering)
* Large image resizing for performance

**Result:**
Clean, binarized, OCR-ready images.

---

### 3️⃣ OCR & Extraction Module (Gemini AI)

**Purpose:**
Performs OCR and structured extraction in a **single AI call**.

**Key Design Choices:**

* One-call OCR + extraction (reduces latency & API cost)
* Strict prompt enforcing JSON-only output
* Extracts:

  * Vendor details
  * Purchase date & time
  * Currency
  * Line items (quantity, price, totals)
  * Tax and total amount
  * Payment method
  * Raw OCR text

**Failure Handling:**
Invalid JSON or missing data triggers controlled errors without crashing the app.

---

### 4️⃣ Validation Module

**Purpose:**
Ensures numerical consistency of extracted data.

**Validation Logic:**

* Calculates subtotal from line items
* Compares extracted totals with calculated values
* Allows marginal tolerance to handle rounding/OCR variations
* Flags mismatches as warnings (does not block storage)

---

### 5️⃣ Database Module (MySQL)

**Purpose:**
Provides persistent storage for digitized bills.

**Schema Design:**

* `users` – user metadata
* `bills` – bill/invoice headers
* `lineitems` – itemized bill details

**Key Characteristics:**

* Relational design with foreign keys
* Cascading deletes for integrity
* Designed for analytics and history browsing

---

### 6️⃣ Streamlit UI Module

**Purpose:**
Provides an interactive and user-friendly interface.

**Pages Implemented:**

* **Dashboard:** Spending analytics and trends
* **Upload & Process:** Upload, preview, extract, and save bills
* **History:** View all stored bills and item details

**UX Highlights:**

* Preprocessed image preview
* Single-click bill saving
* Tab-based result display
* Warning-based validation feedback

---

## 🔁 Session State Management

Streamlit reruns scripts on every interaction.
To maintain continuity, session state is used to store:

* Uploaded images
* Preprocessed outputs
* Extracted bill data
* Current navigation state
* Database save status

This prevents unnecessary reprocessing and API calls.

---

## 📊 Dashboard & Analytics

Milestone 1 dashboard provides:

* Total spending
* Monthly spending trends
* Vendor-wise expenditure
* Recent bills overview

Database queries are cached to improve performance.

---

## 🛡️ Error Handling & Reliability

* Early input validation (file size, format)
* Controlled AI failures (invalid JSON handling)
* Graceful UI warnings instead of crashes
* Database integrity enforcement via foreign keys

---

## ⚙️ Tech Stack

| Layer            | Technology       |
| ---------------- | ---------------- |
| Frontend         | Streamlit        |
| OCR & AI         | Google Gemini AI |
| Image Processing | OpenCV, PIL      |
| Backend Logic    | Python           |
| Database         | MySQL            |
| Data Handling    | Pandas           |
| Visualization    | Plotly           |

---

## 🚀 How to Run

```bash
# Create virtual environment
conda create -n ridvenv python=3.12
conda activate ridvenv

# Install dependencies
pip install -r requirements.txt

# Run Streamlit app
streamlit run app.py
```

---

## 📌 Milestone 1 Deliverables

✅ Document ingestion (images & PDFs)
✅ Automatic image preprocessing
✅ Single-call AI-based OCR & extraction
✅ Structured JSON output
✅ MySQL persistent storage
✅ Dashboard & history UI
✅ Error-resilient workflow

---

## 🔮 Future Enhancements (Next Milestones)

* User authentication & access control
* Advanced data validation & fraud detection
* Export to CSV/Excel/PDF
* Cloud deployment
* AI confidence scoring
* Category-wise expense analytics

---

## 🏁 Summary

The **Receipt & Invoice Digitizer** (Milestone 1) delivers a **production-ready digitization pipeline** with:

* Modular architecture
* AI-powered structured extraction
* Persistent storage
* Interactive analytics
* Robust error handling

The system is designed to scale seamlessly into enterprise-grade expense management and document intelligence solutions.

