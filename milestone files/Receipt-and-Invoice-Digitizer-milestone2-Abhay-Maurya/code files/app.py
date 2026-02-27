# Main application file for Receipt and Invoice Digitizer

import streamlit as st
import sys
import os
import time
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from dashboard import page_dashboard

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
try:
    from src.preprocessing import preprocess_image
    from src.ocr import run_ocr_and_extract_bill  # Internally uses normalizer
    from src.ingestion import ingest_document, generate_file_hash
    from src.database import init_db, insert_bill, get_all_bills, get_bill_items, get_bill_details
    from src.validation import validate_bill_complete
except ImportError as e:
    st.warning(f"⚠️ Module Import Warning: {e}")


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

# Dialog function to display uploaded image in a modal popup
@st.dialog("📷 Uploaded Image")
def show_uploaded_image_dialog(image, caption):
    """Display uploaded image in a modal dialog popup.
    Args:
        image: PIL Image object (original uploaded image)
        caption: Title/caption for the image"""
    st.image(image, caption=caption, width="stretch")
    st.info("Click outside the dialog to close.")


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
            # Warn user if the uploaded file hasn't changed from the last one
            if not file_changed:
                st.warning("⚠️ No changes detected. The uploaded file matches the last processed file.")
            
            
            # Reset all processing state when a new file is uploaded
            # This prevents stale data from previous file being displayed
            if file_changed:
                st.session_state.file_type = None
                st.session_state.images = None
                st.session_state.metadata = None
                st.session_state.ingestion_done = False
                st.session_state.current_page_index = 0
                st.session_state.processed_pages = []
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
                        
                        with st.spinner("Extracting and saving bill..."):
                            # GEMINI OCR - Extract structured data with normalization
                            bill_data = run_ocr_and_extract_bill(target_img, st.session_state.api_key)

                            save_allowed = True
                            duplicate_detected = False

                            # Check for OCR extraction errors first
                            if "error" in bill_data:
                                st.error(f"❌ Extraction failed: {bill_data['error']}")
                                save_allowed = False
                            else:
                                time.sleep(6)
                                st.success("✅ Data extraction and normalization completed")
                            
                            #  VALIDATE - Unified validation: checks amounts AND duplicates
                            if save_allowed:
                                validation_result = validate_bill_complete(bill_data, user_id=1)
                                amount_validation = validation_result["amount_validation"]

                                # Check amount validation; if it fails, save using calculated amounts
                                if not amount_validation["is_valid"]:
                                    time.sleep(5)
                                    st.warning(
                                        "⚠ Bill amount validation failed. Using calculated subtotal, tax, and total for save."
                                    )
                                    bill_data["subtotal"] = amount_validation["items_sum"]
                                    bill_data["tax_amount"] = amount_validation["tax_amount"]
                                    bill_data["total_amount"] = round(
                                        amount_validation["items_sum"] + amount_validation["tax_amount"], 2
                                    )
                                    
                                    # RE-RUN DUPLICATE CHECK after modifying amounts
                                    # This ensures duplicate detection uses the corrected total_amount
                                    validation_result = validate_bill_complete(bill_data, user_id=1)
                                else:
                                    time.sleep(5)
                                    st.success("✅ Amount validation passed")
                                
                                # Duplicate detection (hard or soft) blocks save per requirement
                                dup_check = validation_result["duplicate_check"]
                                time.sleep(4)
                                if dup_check.get("duplicate") or dup_check.get("soft_duplicate"):
                                    reason = dup_check.get("reason", "Unknown reason")
                                    time.sleep(4)
                                    st.warning(
                                        f"⚠️ Duplicate bill detected. Reason: {reason}. Bill not saved."
                                    )
                                    save_allowed = False
                                    duplicate_detected = True
                                else:
                                    time.sleep(4)
                                    st.success("✅ No duplicate detected")
                            
                            # STORE - Save to session state and database
                            if save_allowed:
                                st.session_state.final_document_text = ""
                                st.session_state.extracted_bill_data = bill_data
                                
                                # Insert into database (persistent storage)
                                bill_id = insert_bill(bill_data)
                                st.session_state.bill_saved = True
                                time.sleep(1)
                                st.success(f"✅ Bill saved successfully to database! (ID: {bill_id})")
                                
                                time.sleep(3)
                            
                            # DISPLAY - Rerun to show updated results and database tables
                            if save_allowed:
                                st.rerun()
                            else:
                                st.stop()

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
                        # WORKFLOW: Upload → Ingest → Preprocess → User Trigger (this button)
                        target_img = processed_image or current_image
                        
                        with st.spinner(f"Processing page {current_idx + 1}..."):
                            # OCR + Normalize - Extract and standardize bill data
                            bill_data = run_ocr_and_extract_bill(target_img, st.session_state.api_key)

                            save_allowed = True
                            duplicate_detected = False
                            
                            # Check for OCR extraction errors first
                            if "error" in bill_data:
                                st.error(f"❌ Extraction failed: {bill_data['error']}")
                                save_allowed = False
                            else:
                                time.sleep(6)
                                st.success("✅ Data extraction and normalization completed")
                            
                            # Validate - Unified validation: checks amounts AND duplicates
                            if save_allowed:
                                validation_result = validate_bill_complete(bill_data, user_id=1)
                                amount_validation = validation_result["amount_validation"]

                                # Check amount validation; warn only and use calculated amounts if needed
                                if not amount_validation["is_valid"]:
                                    time.sleep(5)
                                    st.warning(
                                        "⚠ Validation warning: Amounts may not align perfectly. Using calculated subtotal, tax, and total for save."
                                    )
                                    bill_data["subtotal"] = amount_validation["items_sum"]
                                    bill_data["tax_amount"] = amount_validation["tax_amount"]
                                    bill_data["total_amount"] = round(
                                        amount_validation["items_sum"] + amount_validation["tax_amount"], 2
                                    )
                                    
                                    # RE-RUN DUPLICATE CHECK after modifying amounts
                                    # This ensures duplicate detection uses the corrected total_amount
                                    validation_result = validate_bill_complete(bill_data, user_id=1)
                                else:
                                    time.sleep(5)
                                    st.success("✅ Amount validation passed")
                                
                                # Duplicate detection (hard or soft) blocks save per requirement
                                dup_check = validation_result["duplicate_check"]
                                time.sleep(5)
                                if dup_check.get("duplicate") or dup_check.get("soft_duplicate"):
                                    reason = dup_check.get("reason", "Unknown reason")
                                    time.sleep(4)
                                    st.warning(
                                        f"⚠️ Duplicate bill detected. Reason: {reason}. Bill not saved."
                                    )
                                    save_allowed = False
                                    duplicate_detected = True
                                else:
                                    time.sleep(4)
                                    st.success("✅ No duplicate detected")
                            
                            # Store - Save to database and update session state
                            if save_allowed:
                                st.session_state.final_document_text = ""
                                st.session_state.extracted_bill_data = bill_data
                                bill_id = insert_bill(bill_data)
                                st.session_state.bill_saved = True
                                time.sleep(1)
                                st.success(f"✅ Bill saved successfully to database! (ID: {bill_id})")
                                time.sleep(3)
                            
                            # Rerun to show updated results
                            if save_allowed:
                                st.rerun()
                            else:
                                st.stop()

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
                                'original_total_amount',
                                'original_currency',
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
            'original_total_amount',
            'original_currency',
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