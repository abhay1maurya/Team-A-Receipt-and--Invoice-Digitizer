

# 📄 Receipt & Invoice Digitizer — Milestone 2

### *Validation, Normalization & Intelligence Layer*

> ⚠️ **Important Note**
> This repository contains **only Milestone 2** of the *Receipt & Invoice Digitizer* project.
>
> 🔗 **Main Project Repository (Milestone 1 + Milestone 2):**
> [https://github.com/abhay1maurya/Receipt-and-Invoice-Digitizer](https://github.com/abhay1maurya/Receipt-and-Invoice-Digitizer)
>
> Milestone 1 covers ingestion, preprocessing, OCR, UI, and base persistence.
> This repository focuses **exclusively on post-OCR intelligence and data reliability.**

---

## 📌 Milestone 2 Overview

Milestone 2 extends the OCR-based digitization pipeline into a **reliable, analytics-ready financial data processing system**.
The focus is **not extraction**, but **correctness, consistency, validation, and de-duplication** of extracted receipt and invoice data.

This milestone assumes OCR output is already available and operates **after AI extraction**.

---

## 🎯 Objectives of Milestone 2

* Recover missing or weak fields from OCR output
* Normalize extracted data into database-safe formats
* Support multi-currency receipts with USD standardization
* Validate financial correctness across pricing models
* Detect logical duplicate bills
* Prepare data for persistent storage and analytics

---

## 🧠 High-Level Scope (Milestone 2 Only)

```
OCR Output
   ↓
Regex & NLP Fallback
   ↓
Normalization
   ↓
Currency Conversion
   ↓
Validation
   ↓
Duplicate Detection
   ↓
Database-Ready Data
```

---

## 🧩 Modules Implemented

### 1️⃣ Regex & NLP Fallback Extraction

**Purpose:** Recover critical fields when AI extraction is incomplete.

**Techniques Used:**

* Regex-based deterministic parsing:

  * Invoice / receipt number
  * Dates
  * Subtotal, tax, total
  * Currency
  * Payment method
* spaCy Named Entity Recognition:

  * ORG entities only
  * Used **only if vendor name is missing or weak**

**Design Rule:**

* Strong AI-extracted fields are **never overridden**
* Fallback triggers only for weak or null fields


---

### 2️⃣ Data Normalization Layer

**Purpose:** Standardize extracted data for storage and querying.

**Normalization Includes:**

* Uppercase standardization for text fields
* ISO-compliant date and time formatting
* Safe numeric conversion (floats, decimals)
* Length constraints enforcement
* Default value handling
* Line-item structure normalization

---

### 3️⃣ Currency Conversion Layer

**Purpose:** Enable unified analytics across receipts in different currencies.

**Features:**

* Detects non-USD currencies
* Converts all monetary values to USD
* Preserves:

  * Original currency
  * Original amounts
  * Exchange rate used

**Design Principle:**

* Analytics consistency without loss of audit transparency

---

### 4️⃣ Validation Layer

**Purpose:** Ensure financial correctness of extracted bills.

**Validation Models Supported:**

* **Tax-Inclusive Model**

  ```
  sum(line_items) ≈ total_amount
  ```
* **Tax-Exclusive Model**

  ```
  sum(line_items) + tax_amount ≈ total_amount
  ```

**Key Characteristics:**

* Tolerance-based validation (±0.02)
* OCR rounding errors are tolerated
* Validation is **warning-driven**, not destructive
* Incorrect totals are corrected and re-validated

---

### 5️⃣ Logical Duplicate Detection

**Purpose:** Prevent duplicate bills from being stored.

**Hard Duplicate (Blocking):**

* Invoice number
* Vendor name
* Purchase date
* Total amount (within tolerance)

**Soft Duplicate (Warning):**

* Vendor name
* Purchase date
* Total amount
  *(Used when invoice number is missing)*

**Important:**

* Duplicate detection is **independent of file hash**
* Operates on **business logic**, not file metadata

---

## 🗄️ Database Compatibility

Milestone 2 produces **fully normalized, validated, and duplicate-checked data** compatible with:

* Relational databases (SQLite, PostgreSQL)
* Analytics engines
* Reporting dashboards

**Schema Used:**

* `bills` (header-level data)
* `lineitems` (item-level data)

---

## 🧪 Error Handling Philosophy

* No silent failures
* No application crashes
* Clear warnings instead of hard stops (where possible)
* User remains in control of final persistence decision

---

## 🚫 Explicitly Out of Scope

The following are **not part of Milestone 2**:

* File upload handling
* Image preprocessing
* OCR or AI model training
* UI design or navigation
* Authentication or multi-user access
* Advanced analytics dashboards

(All of the above belong to the main repository.)

---

## 📈 Outcome of Milestone 2

By completing Milestone 2, the system evolves from **OCR-based digitization** to a **trustworthy financial data processing pipeline** where:

* Extracted data is deterministic and consistent
* Monetary values are validated and corrected
* Duplicate records are prevented
* Stored data is analytics-ready

---

## 🎓 Academic Positioning

This milestone demonstrates:

* Practical data validation strategies
* Robust post-OCR processing
* Real-world handling of imperfect AI outputs
* Production-aligned system design

