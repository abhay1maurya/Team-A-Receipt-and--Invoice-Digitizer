# Main application file for Receipt and Invoice Digitizer
# This Streamlit app provides a multi-page interface for:
# - Dashboard: View spending analytics and charts from saved bills
# - Upload & Process: Upload and digitize receipts/invoices using Gemini OCR
# - History: Browse all previously saved bills and line items

import streamlit as st
import sys
import os
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# PAGE CONFIGURATION - Sets up browser tab title, icon, and layout
st.set_page_config(
    page_title="DigitizeBills | Receipt & Invoice Digitizer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add root directory to path so we can import 'src' modules
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Import core functionality from src package
# - preprocessing: Image enhancement for better OCR accuracy
# - ocr: Gemini API integration for text extraction and structured data parsing
# - ingestion: File upload handling (images, PDFs) and hash generation for change detection
# - database: MySQL persistence layer for invoices and line items
try:
    from src.preprocessing import preprocess_image
    from src.ocr import run_ocr_and_extract_bill
    from src.ingestion import ingest_document, generate_file_hash
    from src.database import init_db, insert_bill, get_all_bills, get_bill_items, get_bill_details
    from src.validation import validate_bill_amounts
except ImportError as e:
    st.warning(f"⚠️ Module Import Warning: {e}")

# SESSION STATE SETUP - Streamlit reruns the script on every interaction
# Session state preserves variables across reruns to maintain application state

# Navigation state - tracks which page user is viewing
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Dashboard"  # Default landing page
if 'api_key' not in st.session_state:
    st.session_state.api_key = None  # Gemini API key for OCR operations

# Document Processing State - tracks uploaded file and ingestion status
if 'file_type' not in st.session_state:
    st.session_state.file_type = None  # 'image' or 'pdf' - determines processing workflow
if 'images' not in st.session_state:
    st.session_state.images = None  # List of PIL Image objects (one per page)
if 'metadata' not in st.session_state:
    st.session_state.metadata = None  # File metadata from ingestion (size, format, etc.)
if 'ingestion_done' not in st.session_state:
    st.session_state.ingestion_done = False  # Flag to prevent re-ingesting same file
if 'last_file_hash' not in st.session_state:
    st.session_state.last_file_hash = None  # Hash of last uploaded file for change detection

# Page-by-page Processing State - for multi-page PDFs
if 'current_page_index' not in st.session_state:
    st.session_state.current_page_index = 0  # Index of currently viewed page in multi-page PDF
if 'processed_pages' not in st.session_state:
    st.session_state.processed_pages = []  # Boolean list tracking which pages have been OCR'd
if 'page_texts' not in st.session_state:
    st.session_state.page_texts = []  # List of extracted text per page (for future multi-page merge)
if 'processed_images' not in st.session_state:
    st.session_state.processed_images = []  # List of preprocessed PIL images per page

# Document-level State - tracks overall extraction and save status
if 'document_processed' not in st.session_state:
    st.session_state.document_processed = False  # Flag indicating file is ready for results display
if 'final_document_text' not in st.session_state:
    st.session_state.final_document_text = ""  # Complete OCR text from processed document
if 'extracted_bill_data' not in st.session_state:
    st.session_state.extracted_bill_data = None  # Structured JSON data from Gemini extraction
if 'bill_saved' not in st.session_state:
    st.session_state.bill_saved = False  # Flag indicating bill has been saved to database

# Initialize database on app start - creates tables if they don't exist
try:
    init_db()
except Exception as e:
    st.warning(f"Database initialization warning: {e}")


# SIDEBAR NAVIGATION - persistent sidebar for API key entry and page navigation
with st.sidebar:
    st.title("Digitizer")
    st.caption("Receipt & Invoice Digitizer")
    st.divider()
    
    # API key input - stored as password field for security
    # Uses temporary variable to avoid clearing on rerun
    st.subheader("🔑 API Configuration")
    input_key = st.text_input(
        "Enter Gemini API Key",
        type="password",
        placeholder="Paste your API key here"
    )

    # Save API key to session state only if user provides input
    if input_key:
        st.session_state.api_key = input_key

    # Display status based on session state (not input box)
    # This ensures status persists across reruns
    if st.session_state.api_key:
        st.success("✅ API Key Loaded")
    else:
        st.warning("⚠️ API Key Required for OCR")

    st.divider()
    
    st.subheader("Navigation")
    
    # Page selection buttons - update session state and trigger rerun
    # Each button sets current_page and forces app to re-render with new page
    if st.button("📊 Dashboard", key="nav_dashboard", width="stretch"):
        st.session_state.current_page = "Dashboard"
        st.rerun()  # Force immediate re-render to show new page
    
    if st.button("🧾 Upload & Process", key="nav_upload", width="stretch"):
        st.session_state.current_page = "Upload & Process"
        st.rerun()
    
    if st.button("🕒 History", key="nav_history", width="stretch"):
        st.session_state.current_page = "History"
        st.rerun()
    
    st.divider()
    st.subheader("System")
    st.link_button(label="Repo", url="https://github.com/abhay1maurya/Receipt-and-Invoice-Digitizer")
    st.info("ℹ️ v1.0.0-beta")

# Cached data loaders to avoid repeat database queries on every rerun
# Cache expires after 60 seconds to balance performance vs data freshness
# These functions are called multiple times across dashboard/upload/history pages

@st.cache_data(ttl=60, show_spinner=False)
def _cached_bills():
    """Fetch all bills from database with 60s cache.
    Returns empty list on error to prevent page crashes."""
    try:
        return get_all_bills() or []
    except Exception as e:
        st.warning(f"Could not load bills: {e}")
        return []


@st.cache_data(ttl=60, show_spinner=False)
def _cached_items(bills):
    """Fetch all line items for given bills and enrich with bill metadata.
    Returns flattened list of items with vendor_name and purchase_date attached."""
    items = []
    for bill in bills:
        try:
            bill_items = get_bill_items(bill.get("id"))
        except Exception:
            bill_items = []
        # Enrich each item with parent bill information for easier analysis
        for item in bill_items:
            items.append(
                {
                    **item,
                    "bill_id": bill.get("id"),
                    "vendor_name": bill.get("vendor_name"),
                    "purchase_date": bill.get("purchase_date"),
                }
            )
    return items


# Dialog function to display uploaded image in a modal popup
@st.dialog("📷 Uploaded Image")
def show_uploaded_image_dialog(image, caption):
    """Display uploaded image in a modal dialog popup.
    Args:
        image: PIL Image object (original uploaded image)
        caption: Title/caption for the image"""
    st.image(image, caption=caption, width="stretch")
    st.info("Click outside the dialog to close.")


# PAGE: DASHBOARD - displays spending analytics, charts, and recent bills
def page_dashboard():
    st.title("My Spending Dashboard")
    st.markdown("Live view of your saved receipts and invoices.")
    st.divider()

    # Load bills from database with caching
    bills = _cached_bills()
    if not bills:
        st.info("📭 No bills saved yet. Upload and save a bill to see your dashboard populate.")
        return

    # Convert to DataFrame for pandas/plotly operations
    bills_df = pd.DataFrame(bills)
    # Parse purchase_date strings into datetime objects for time-series analysis
    bills_df["purchase_date_dt"] = pd.to_datetime(bills_df.get("purchase_date"), errors="coerce")

    # Calculate summary metrics from bills data
    total_spent = bills_df["total_amount"].sum()  # Sum of all bill totals
    months_active = bills_df["purchase_date_dt"].dt.to_period("M").nunique() or 1  # Unique months with bills
    avg_per_month = total_spent / months_active  # Average monthly spending
    vendors_count = bills_df["vendor_name"].nunique()  # Count of unique vendors
    transactions_count = len(bills_df)  # Total number of bills

    # Display metrics in 4-column layout
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Total Spent", value=f"${total_spent:,.2f}")
    with col2:
        st.metric(label="Avg. Spent/Month", value=f"${avg_per_month:,.2f}")
    with col3:
        st.metric(label="Total Vendors", value=str(vendors_count))
    with col4:
        st.metric(label="Total Transactions", value=str(transactions_count))

    st.divider()

    # Charts section - two-column layout for visualizations
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("📈 Monthly Spending Trend")
        # Group bills by month and sum total_amount for trend analysis
        monthly = (
            bills_df.dropna(subset=["purchase_date_dt"])  # Exclude bills with invalid dates
            .groupby(bills_df["purchase_date_dt"].dt.to_period("M"))["total_amount"]
            .sum()
            .reset_index()
        )
        monthly["month"] = monthly["purchase_date_dt"].dt.strftime("%Y-%m")  # Format for display
        # Create line chart with Plotly
        fig1 = go.Figure()
        fig1.add_trace(
            go.Scatter(
                x=monthly["month"],
                y=monthly["total_amount"],
                mode="lines+markers",
                name="Spending",
                line=dict(color="#3498db", width=3),
                marker=dict(size=8),
            )
        )
        fig1.update_layout(
            hovermode="x unified",
            height=350,
            margin=dict(l=0, r=0, t=20, b=0),
            yaxis_title="Amount ($)",
            xaxis_title="Month",
            showlegend=False,
        )
        st.plotly_chart(fig1, width=1200)

    with col_chart2:
        st.subheader("🏪 Spending by Vendor")
        # Aggregate spending by vendor and sort descending
        by_vendor = bills_df.groupby("vendor_name")["total_amount"].sum().sort_values(ascending=False).reset_index()
        # Create bar chart with color gradient based on amount
        fig2 = px.bar(
            by_vendor,
            x="vendor_name",
            y="total_amount",
            color="total_amount",
            color_continuous_scale="Blues",  # Darker blue for higher amounts
            height=350,
        )
        fig2.update_layout(margin=dict(l=0, r=0, t=20, b=0), yaxis_title="Amount ($)", xaxis_title="Vendor", showlegend=False)
        st.plotly_chart(fig2, width=1200)

    st.divider()

    # Top vendors and items tables - two-column layout
    col_vendors, col_items = st.columns(2)

    with col_vendors:
        st.subheader("🔝 Top Vendors (by spend)")
        # Show top 10 vendors by total spending
        top_vendors = by_vendor.head(10)
        st.dataframe(
            top_vendors.rename(columns={"vendor_name": "Vendor", "total_amount": "Spent ($)"}),
            hide_index=True,
            width="stretch",
        )

    with col_items:
        st.subheader("⭐ Top Items (by spend)")
        # Load line items from database with bill metadata
        items = _cached_items(bills)
        if items:
            items_df = pd.DataFrame(items)
            # Convert item_total to numeric, handling any malformed values
            items_df["item_total"] = pd.to_numeric(items_df.get("item_total"), errors="coerce").fillna(0)
            # Group by item name and sum totals across all bills
            top_items = (
                items_df.groupby("item_name")["item_total"]
                .sum()
                .sort_values(ascending=False)
                .reset_index()
                .head(10)  # Top 10 most expensive items
            )
            st.dataframe(
                top_items.rename(columns={"item_name": "Item", "item_total": "Spent ($)"}),
                hide_index=True,
                width="stretch",
            )
        else:
            st.info("No line items available yet.")

    st.divider()

    # Recent transactions table - shows latest 20 bills
    st.subheader("📋 Recent Bills")
    recent_cols = [
        "id",
        "invoice_number",
        "vendor_name",
        "purchase_date",
        "purchase_time",
        "payment_method",
        "total_amount",
        "tax_amount",
        "currency",
    ]
    # Sort by date descending to show most recent first
    recent = bills_df.sort_values(by="purchase_date_dt", ascending=False).head(20)
    recent_display = recent[recent_cols].copy()
    # Format currency columns for display
    recent_display["total_amount"] = recent_display["total_amount"].apply(lambda x: f"${x:.2f}")
    recent_display["tax_amount"] = recent_display["tax_amount"].apply(lambda x: f"${x:.2f}")
    st.dataframe(recent_display, hide_index=True, width="stretch")


# PAGE: UPLOAD & PROCESS - handles file upload, preprocessing, OCR, and database save
def page_upload_process():
    st.title("🧾 Document Upload")
    st.markdown("Upload receipts or invoices for automated digitization.")
    st.divider()

    # MAIN LAYOUT - two-column design: left for upload controls, right for results
    col1, col2 = st.columns([1, 2])

    # COLUMN 1: UPLOAD & PROCESSING CONTROLS
    with col1:
        st.subheader("1. Input")
        
        # Check if API key is configured before allowing uploads
        api_key_available = st.session_state.api_key and st.session_state.api_key.strip() != ""
        
        if not api_key_available:
            st.warning("⚠️ Please enter your Gemini API key in the sidebar first.")
        
        # File uploader widget - accepts images and PDFs
        uploaded_file = st.file_uploader(
            "Select File", 
            type=["jpg", "jpeg", "png", "pdf"], 
            help="Supported formats: JPG, PNG, PDF. Max size 5MB."
        )

        if uploaded_file:
            # Validate file size to prevent memory issues and long processing times
            MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB limit in bytes
            file_size = uploaded_file.size
            
            if file_size > MAX_FILE_SIZE:
                st.error(f"❌ File too large! Size: {file_size / 1024 / 1024:.2f} MB. Maximum allowed: 5 MB")
                st.stop()  # Halt execution if file exceeds size limit
            
            # Generate hash for uploaded file to detect when user uploads a different file
            try:
                current_file_hash = generate_file_hash(uploaded_file)
            except Exception as e:
                st.error(f"File hash generation failed: {e}")
                st.stop()
            
            # Compare hash to detect file changes
            file_changed = current_file_hash != st.session_state.last_file_hash
            
            # Reset all processing state when a new file is uploaded
            # This prevents stale data from previous file being displayed
            if file_changed:
                st.session_state.file_type = None
                st.session_state.images = None
                st.session_state.metadata = None
                st.session_state.ingestion_done = False
                st.session_state.current_page_index = 0
                st.session_state.processed_pages = []
                st.session_state.page_texts = []
                st.session_state.processed_images = []
                st.session_state.document_processed = False
                st.session_state.final_document_text = ""
                st.session_state.last_file_hash = None
            
            # Ingestion runs only once per file to convert upload into PIL images
            # Prevents re-processing on every Streamlit rerun
            if not st.session_state.ingestion_done:
                try:
                    # Convert uploaded file (image or PDF) into list of PIL Image objects
                    images, metadata = ingest_document(uploaded_file, filename=uploaded_file.name)
                    
                    # Determine file type from extension to control workflow
                    file_ext = uploaded_file.name.lower().split('.')[-1]
                    if file_ext in ['jpg', 'jpeg', 'png']:
                        file_type = 'image'  # Single image workflow
                    else:
                        file_type = 'pdf'  # Multi-page PDF workflow
                    
                    # Store ingestion results in session state
                    st.session_state.images = images
                    st.session_state.metadata = metadata
                    st.session_state.file_type = file_type
                    st.session_state.ingestion_done = True
                    st.session_state.last_file_hash = current_file_hash
                    # Mark document ready for results display
                    st.session_state.document_processed = True
                    
                    # Initialize per-page tracking arrays
                    num_pages = len(images)
                    st.session_state.processed_pages = [False] * num_pages
                    st.session_state.page_texts = [""] * num_pages
                    st.session_state.processed_images = [None] * num_pages
                    
                    # Automatically preprocess all images for better OCR accuracy
                    # This includes noise removal, contrast enhancement, etc.
                    with st.spinner("Preprocessing images..."):
                        for idx, img in enumerate(images):
                            try:
                                processed_img = preprocess_image(img)
                                st.session_state.processed_images[idx] = processed_img
                            except Exception as e:
                                st.warning(f"⚠️ Preprocessing failed for page {idx + 1}: {e}")
                    
                except Exception as e:
                    st.error(f"Ingestion Failed: {e}")
                    st.session_state.ingestion_done = False
                    st.session_state.last_file_hash = None
                    st.stop()
            
            # Display file info and processing controls after successful ingestion
            if st.session_state.ingestion_done and st.session_state.images:
                num_pages = len(st.session_state.images)
                file_type = st.session_state.file_type
                
                # Show appropriate message based on file type
                if file_type == 'image':
                    st.success(f"✅ Image loaded (Single page)")
                elif num_pages == 1:
                    st.success(f"✅ PDF loaded (1 page, treated as image)")
                else:
                    st.info(f"📄 PDF loaded ({num_pages} pages)")
                
                st.divider()
                
                # WORKFLOW CASE A & B: Single image or single-page PDF
                # Simplified workflow - one image, one save button
                if file_type == 'image' or num_pages == 1:
                    current_image = st.session_state.images[0]
                    processed_image = st.session_state.processed_images[0]

                    # Display preprocessed image (or original if preprocessing failed)
                    st.image(processed_image or current_image, caption="Preprocessed Image", width="stretch")

                    # Button to view original uploaded image in dialog
                    if st.button(
                        "👁️ View Uploaded Image",
                        key="view_uploaded_single",
                        width="stretch"
                    ):
                        show_uploaded_image_dialog(current_image, "Uploaded Image")

                    # Single save button - runs OCR and saves to database in one step
                    if st.button(
                        "💾 Save My Bill",
                        type="primary",
                        width="stretch",
                        disabled=not api_key_available,  # Disabled if no API key
                        key="save_single"
                    ):
                        # Use preprocessed image if available, fallback to original
                        target_img = processed_image or current_image
                        with st.spinner("Extracting and saving bill (single call)..."):
                            # Run OCR and extract structured data using Gemini API
                            bill_data = run_ocr_and_extract_bill(target_img, st.session_state.api_key)

                            # # Validation of the totals, tax and items totals
                            validation = validate_bill_amounts(bill_data)

                            if not validation["is_valid"]:
                                st.warning(
                                    "⚠ Bill amount validation failed. "
                                    "Item totals and final total do not align. Please review."
                                )


                            if "error" in bill_data:
                                st.error(f"❌ Extraction failed: {bill_data['error']}")
                            else:
                                # Store extracted data in session state
                                st.session_state.final_document_text = bill_data.get('ocr_text', '')
                                st.session_state.extracted_bill_data = bill_data
                                # Save to database and get new bill ID
                                bill_id = insert_bill(bill_data)
                                st.session_state.bill_saved = True
                                st.success(f"✅ Bill saved successfully! (ID: {bill_id})")
                                st.rerun()  # Refresh to show updated results

                # WORKFLOW CASE B: Multi-page PDF processing
                # Page-by-page navigation and individual save buttons
                else:
                    st.subheader("📄 View Pages")
                    # Create page selector buttons (limit to 10 columns to avoid layout issues)
                    num_cols = min(num_pages, 10)
                    cols = st.columns(num_cols)
                    for page_num in range(num_pages):
                        col_idx = page_num % num_cols  # Wrap to next row if more than 10 pages
                        with cols[col_idx]:
                            # Highlight currently selected page with primary button style
                            is_selected = page_num == st.session_state.current_page_index
                            button_type = "primary" if is_selected else "secondary"
                            if st.button(
                                f"Page {page_num + 1}",
                                key=f"page_selector_{page_num}",
                                type=button_type,
                                width="stretch"
                            ):
                                st.session_state.current_page_index = page_num
                                st.rerun()  # Refresh to display selected page

                    st.divider()

                    # Display currently selected page
                    current_idx = st.session_state.current_page_index
                    processed_image = st.session_state.processed_images[current_idx]
                    current_image = st.session_state.images[current_idx]

                    st.write(f"**Page: {current_idx + 1} / {num_pages}**")
                    st.image(processed_image or current_image, caption=f"Page {current_idx + 1} (Preprocessed)", width="stretch")

                    # Button to view original uploaded page in dialog
                    if st.button(
                        f"👁️ View Uploaded Page {current_idx + 1}",
                        key=f"view_uploaded_page_{current_idx}",
                        width="stretch"
                    ):
                        show_uploaded_image_dialog(current_image, f"Uploaded Page {current_idx + 1}")

                    st.divider()

                    # Per-page save button - allows saving individual pages as separate bills
                    if st.button(
                        f"💾 Save My Bill - Page {current_idx + 1}",
                        type="primary",
                        width="stretch",
                        disabled=not api_key_available,
                        key=f"save_page_{current_idx}"
                    ):
                        target_img = processed_image or current_image
                        with st.spinner(f"Extracting and saving page {current_idx + 1}..."):
                            # Run OCR on selected page only
                            bill_data = run_ocr_and_extract_bill(target_img, st.session_state.api_key)
                            if "error" in bill_data:
                                st.error(f"❌ Extraction failed: {bill_data['error']}")
                            else:
                                st.session_state.final_document_text = bill_data.get('ocr_text', '')
                                st.session_state.extracted_bill_data = bill_data
                                bill_id = insert_bill(bill_data)
                                st.session_state.bill_saved = True
                                st.success(f"✅ Bill saved successfully! (ID: {bill_id})")
                                st.rerun()

    # COLUMN 2: RESULTS DISPLAY - shows extracted data and database tables
    with col2:
        # Only show results if document has been ingested and processed
        if st.session_state.document_processed:
            st.subheader("2. Results")

            # Two tabs for organizing different types of information
            tab_results, tab_metadata = st.tabs(["📄 Results", "ℹ️ Metadata"])

            # TAB 1: RESULTS - displays extracted bill data and all saved bills
            with tab_results:

                # Display extracted bill data if OCR extraction succeeded
                if st.session_state.extracted_bill_data and "error" not in st.session_state.extracted_bill_data:
                    bill_data = st.session_state.extracted_bill_data
                    
                    st.markdown("### 📋 Extracted Bill Information")
                    # Two-table layout: list all bills + detailed view of selected bill items
                    st.markdown("### 📦 Persistent Storage")
                    try:
                        # Fetch all bills from database to show complete collection
                        all_bills = get_all_bills()
                        if all_bills:
                            bills_df = pd.DataFrame(all_bills)
                            # Format currency columns for clean display
                            bills_df['total_amount'] = bills_df['total_amount'].apply(lambda x: f"${x:.2f}")
                            bills_df['tax_amount'] = bills_df['tax_amount'].apply(lambda x: f"${x:.2f}")

                            # Define invoice schema columns to display
                            visible_cols = [
                                'id',
                                'invoice_number',
                                'vendor_name',
                                'purchase_date',
                                'purchase_time',
                                'payment_method',
                                'total_amount',
                                'tax_amount',
                                'currency',
                            ]

                            # Table 1: Overview of all saved bills
                            st.dataframe(
                                bills_df[visible_cols],
                                width="stretch",
                                hide_index=True,
                            )

                            st.markdown("### 🔍 Detailed Bill Items")

                            # Dropdown to select a bill and view its line items
                            bill_options = [b['id'] for b in all_bills]
                            bill_labels = [
                                f"Bill #{b['id']} - {b['vendor_name']} - {b['purchase_date']}"
                                for b in all_bills
                            ]
                            selected_bill_id = st.selectbox(
                                "Select ID to view items:",
                                options=bill_options,
                                format_func=lambda x: [label for bid, label in zip(bill_options, bill_labels) if bid == x][0]
                            )

                            # Fetch and display line items for selected bill
                            if selected_bill_id:
                                bill_items = get_bill_items(selected_bill_id)
                                if bill_items:
                                    items_detail_df = pd.DataFrame(bill_items)
                                    st.dataframe(items_detail_df, width="stretch", hide_index=True)
                                else:
                                    st.info("No items found for this bill")
                        else:
                            st.info("No bills saved yet")
                    except Exception as e:
                        st.warning(f"Could not load bills from database: {e}")

            # TAB 2: METADATA - displays raw file information
            with tab_metadata:
                st.json(st.session_state.get("metadata", {}))

# PAGE: HISTORY - browse all saved bills with summary metrics and table view
def page_history():
    st.title("🕒 Upload History")
    st.markdown("View previously digitized documents and export reports.")
    st.divider()

    try:
        # Load all bills from database
        all_bills = get_all_bills()
        
        if not all_bills:
            st.info("📭 No bills saved yet. Upload and process documents to get started.")
            return
        
        # Calculate summary metrics for overview
        col1, col2, col3, col4 = st.columns(4)
        
        total_spent = sum(b.get('total_amount', 0) for b in all_bills)  # Sum all bill totals
        avg_spent = total_spent / len(all_bills) if all_bills else 0  # Average per bill
        unique_vendors = len(set(b.get('vendor_name') for b in all_bills))  # Count unique vendors
        
        with col1:
            st.metric("Total Spent", f"${total_spent:.2f}")
        
        with col2:
            st.metric("Average Bill", f"${avg_spent:.2f}")
        
        with col3:
            st.metric("Total Vendors", unique_vendors)
        
        with col4:
            st.metric("Total Bills", len(all_bills))
        
        st.divider()
        
        # Main bills table showing all saved invoices
        st.subheader("📋 All Scanned Bills")
        bills_df = pd.DataFrame(all_bills)
        # Format currency for display
        bills_df['total_amount'] = bills_df['total_amount'].apply(lambda x: f"${x:.2f}")
        bills_df['tax_amount'] = bills_df['tax_amount'].apply(lambda x: f"${x:.2f}")

        # Display invoice schema columns
        visible_cols = [
            'id',
            'invoice_number',
            'vendor_name',
            'purchase_date',
            'purchase_time',
            'payment_method',
            'total_amount',
            'tax_amount',
            'currency',
        ]

        st.dataframe(
            bills_df[visible_cols],
            width="stretch",
            hide_index=True,
        )
        
        st.divider()
        
    
    except Exception as e:
        st.error(f"Error loading history: {e}")

# MAIN APP ROUTING - directs to appropriate page based on session state
# This section executes on every rerun to render the selected page
if st.session_state.current_page == "Dashboard":
    page_dashboard()
elif st.session_state.current_page == "Upload & Process":
    page_upload_process()
elif st.session_state.current_page == "History":
    page_history()