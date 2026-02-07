"""Admin page for system monitoring and maintenance."""

import streamlit as st
import pandas as pd

from src.database import get_all_bills, get_bill_items, delete_bill
from src.dashboard.exports import (
    export_csv,
    export_excel,
    export_pdf,
    export_detailed_csv,
    export_detailed_excel,
    export_detailed_pdf,
)


def page_admin():
    """Render the admin dashboard with metrics, bill details, exports, and maintenance.

    Shows high-level KPIs, a recent bills preview, detailed bill metadata with line
    items, export tools for summary and detailed data, and safe deletion options.
    """
    # Page header and introduction.
    st.title("🛠️ Admin")
    st.markdown("System overview and maintenance tools.")
    st.divider()

    try:
        # Load all bills once for summaries, details, and exports.
        bills = get_all_bills() or []
    except Exception as exc:
        st.error(f"Failed to load bills: {exc}")
        bills = []

    # Top-level KPI metrics.
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Bills", len(bills))
    with col2:
        # Aggregate totals for quick admin visibility.
        total_spent = sum(bill.get("total_amount", 0) for bill in bills)
        st.metric("Total Spend", f"${total_spent:,.2f}")
    with col3:
        # Count distinct vendors to indicate dataset breadth.
        vendors = {bill.get("vendor_name") for bill in bills if bill.get("vendor_name")}
        st.metric("Unique Vendors", len(vendors))

    st.divider()
    # Recent bills preview for quick inspection.
    st.subheader("🧾 Recent Bills")
    if bills:
        bills_df = pd.DataFrame(bills)
        # Show a quick snapshot to keep the admin page lightweight.
        recent_df = bills_df.head(10)
        st.dataframe(recent_df, width="stretch", hide_index=True)
    else:
        st.info("No bills available to preview.")
        return

    st.divider()

    # Bill detail viewer with metadata and line items.
    st.subheader("🔎 Bill Details")
    # Build readable option labels for the bill selector.
    options_df = bills_df.loc[:, ["id", "vendor_name", "purchase_date", "total_amount"]].copy()
    options_df["total_amount"] = pd.to_numeric(
        options_df["total_amount"], errors="coerce"
    ).fillna(0.0)

    option_labels = {
        int(row["id"]): (
            f"Bill #{int(row['id'])} • {row['vendor_name']} • "
            f"{row['purchase_date']} • ${row['total_amount']:.2f}"
        )
        for _, row in options_df.iterrows()
    }
    # Bill picker based on readable labels.
    selected_bill_id = st.selectbox(
        "Select a bill to view details:",
        options=list(option_labels.keys()),
        format_func=lambda x: option_labels.get(int(x), str(x)),
        key="admin_bill_details_selector",
    )

    bill_row = bills_df[bills_df["id"] == selected_bill_id]
    # Only render details if the bill exists in the current dataset.
    if not bill_row.empty:
        bill = bill_row.iloc[0].to_dict()

        # Two-column layout for summary and monetary fields.
        meta_col1, meta_col2 = st.columns(2)
        with meta_col1:
            st.markdown("#### Bill Summary")
            # Core bill metadata.
            st.write(f"Vendor: {bill.get('vendor_name', '-')}")
            st.write(f"Invoice #: {bill.get('invoice_number', '-')}")
            st.write(f"Date: {bill.get('purchase_date', '-')}")
            st.write(f"Time: {bill.get('purchase_time', '-')}")
            st.write(f"Payment: {bill.get('payment_method', '-')}")
            st.write(f"Currency: {bill.get('currency', '-')}")

        with meta_col2:
            st.markdown("#### Amounts")
            # Derive subtotal if the stored value is missing.
            subtotal = (
                bill.get("subtotal")
                if bill.get("subtotal") is not None
                else bill.get("total_amount", 0) - bill.get("tax_amount", 0)
            )
            st.write(f"Subtotal: ${float(subtotal or 0):,.2f}")
            st.write(f"Tax: ${float(bill.get('tax_amount', 0) or 0):,.2f}")
            st.write(
                f"Total: ${float(bill.get('total_amount', 0) or 0):,.2f}"
            )

            if bill.get("original_currency") and bill.get("original_currency") != bill.get(
                "currency"
            ):
                st.divider()
                st.markdown("#### Original Currency")
                st.write(f"Currency: {bill.get('original_currency', '-')}")
                if bill.get("original_total_amount") is not None:
                    orig_total = float(bill.get("original_total_amount"))
                    st.write(
                        f"Original Total: {orig_total:,.2f} "
                        f"{bill.get('original_currency', '')}"
                    )
                if bill.get("exchange_rate") is not None:
                    st.write(f"Exchange Rate: {float(bill.get('exchange_rate')):,.6f}")

        # Fetch and render line items for the selected bill.
        try:
            # Load line items for the selected bill only.
            line_items = get_bill_items(selected_bill_id) or []
        except Exception:
            line_items = []

        st.markdown("#### Line Items")
        if line_items:
            items_detail = pd.DataFrame(line_items)
            # Ensure numeric columns are coerced for consistent formatting.
            for col in ["item_total", "unit_price", "quantity"]:
                if col in items_detail.columns:
                    items_detail[col] = pd.to_numeric(
                        items_detail[col], errors="coerce"
                    ).fillna(0)
            if "unit_price" in items_detail.columns:
                items_detail["unit_price"] = items_detail["unit_price"].apply(
                    lambda x: f"${x:.2f}"
                )
            if "item_total" in items_detail.columns:
                items_detail["item_total"] = items_detail["item_total"].apply(
                    lambda x: f"${x:.2f}"
                )
            st.dataframe(items_detail, width="stretch", hide_index=True)
        else:
            st.info("No line items found for this bill.")

    st.divider()

    # Export section for summary and detailed outputs.
    st.subheader("📥 Export Bills")

    # Layout export controls and action button.
    export_col1, export_col2, export_col3, export_col4 = st.columns([2, 1, 1, 1])

    # Export file format selection.
    with export_col1:
        export_format = st.selectbox(
            "Select export format:",
            options=["CSV", "Excel", "PDF"],
            key="admin_export_format_selector",
            help="Choose the format to export bills",
        )

    # Export type selection (summary vs detailed).
    with export_col2:
        export_type = st.selectbox(
            "Export type:",
            options=["Summary", "Detailed"],
            key="admin_export_type_selector",
            help="Summary: Bills only | Detailed: Bills with line items",
        )

    # Spacer column for layout balance.
    with export_col3:
        st.markdown("")

    # Export action and file generation.
    with export_col4:
        try:
            # Normalize numeric fields before export to avoid mixed types.
            export_df = bills_df.copy()
            numeric_columns = export_df.select_dtypes(include=["float64", "int64"]).columns
            for col in numeric_columns:
                export_df[col] = pd.to_numeric(export_df[col], errors="coerce")

            # Flatten all line items with bill IDs for detailed exports.
            all_items = []
            for bill in bills:
                bill_id = bill.get("id")
                for item in get_bill_items(bill_id) or []:
                    all_items.append({**item, "bill_id": bill_id})
            items_df = pd.DataFrame(all_items)

            # Switch between detailed and summary exports.
            if export_type == "Detailed":
                if export_format == "CSV":
                    file_data = export_detailed_csv(export_df, items_df)
                    file_name = "bills_detailed_export.csv"
                    mime_type = "text/csv"
                elif export_format == "Excel":
                    file_data = export_detailed_excel(export_df, items_df)
                    file_name = "bills_detailed_export.xlsx"
                    mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                else:
                    file_data = export_detailed_pdf(export_df, items_df)
                    file_name = "bills_detailed_export.pdf"
                    mime_type = "application/pdf"
            else:
                if export_format == "CSV":
                    file_data = export_csv(export_df)
                    file_name = "bills_export.csv"
                    mime_type = "text/csv"
                elif export_format == "Excel":
                    file_data = export_excel(export_df)
                    file_name = "bills_export.xlsx"
                    mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                else:
                    file_data = export_pdf(export_df)
                    file_name = "bills_export.pdf"
                    mime_type = "application/pdf"

            # Button label and download payload.
            export_label = f"📥 Export {export_type} {export_format}"
            st.download_button(
                label=export_label,
                data=file_data,
                file_name=file_name,
                mime=mime_type,
                type="primary",
                use_container_width=True,
                key="admin_export_download_button",
            )
        except Exception as exc:
            st.error(f"❌ Error preparing export: {str(exc)}")

    st.divider()

    # Destructive action for bill deletion.
    st.subheader("🗑️ Delete Bill")
    st.warning(
        "⚠️ Deleting a bill will permanently remove it and all associated line items."
    )

    # Build delete dropdown labels.
    delete_options = {
        int(row["id"]): f"Bill #{int(row['id'])} • {row['vendor_name']} • {row['purchase_date']}"
        for _, row in bills_df.iterrows()
    }
    # Delete selection and confirmation toggle.
    selected_delete_id = st.selectbox(
        "Select bill to delete",
        options=list(delete_options.keys()),
        format_func=lambda x: delete_options.get(int(x), str(x)),
        key="admin_delete_bill_selector",
    )
    confirm_delete = st.checkbox("Confirm deletion", key="admin_confirm_delete")

    # Execute deletion only when confirmed.
    if st.button(
        "Delete Bill",
        type="primary",
        disabled=not confirm_delete,
        key="admin_delete_bill_button",
    ):
        try:
            # Delete from storage and refresh the UI state.
            success = delete_bill(selected_delete_id)
            if success:
                # Clear cached data so the UI refreshes with the new state.
                st.success(f"Bill #{selected_delete_id} deleted successfully.")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Selected bill was not found.")
        except Exception as exc:
            st.error(f"Failed to delete bill: {exc}")

    st.divider()

    # Raw data explorer for bills and line items.
    st.subheader("🗂️ Database Explorer")
    tabs = st.tabs(["Bills", "Line Items"])

    # Bills table tab.
    with tabs[0]:
        st.markdown("#### All Bills (Raw)")
        # Enforce a consistent column order in the raw bills view.
        bills_full_cols = [
            "id",
            "invoice_number",
            "vendor_name",
            "purchase_date",
            "purchase_time",
            "subtotal",
            "tax_amount",
            "total_amount",
            "currency",
            "original_currency",
            "original_total_amount",
            "exchange_rate",
            "payment_method",
        ]
        bills_full = bills_df.copy()
        for col in bills_full_cols:
            if col not in bills_full.columns:
                bills_full[col] = None
        bills_full = bills_full[bills_full_cols]

        # Format numeric fields consistently.
        for col in ["subtotal", "tax_amount", "total_amount", "original_total_amount"]:
            bills_full[col] = pd.to_numeric(bills_full[col], errors="coerce")
            bills_full[col] = bills_full[col].apply(
                lambda x: f"${x:.2f}" if pd.notna(x) else "-"
            )
        bills_full["exchange_rate"] = bills_full["exchange_rate"].apply(
            lambda x: f"{float(x):.6f}" if pd.notna(x) else "-"
        )

        st.dataframe(bills_full, hide_index=True, width="stretch")

    # Line items table tab.
    with tabs[1]:
        st.markdown("#### All Line Items (Raw)")
        # Collect all line items across bills for inspection.
        all_items = []
        for bill in bills:
            bill_id = bill.get("id")
            for item in get_bill_items(bill_id) or []:
                all_items.append({**item, "bill_id": bill_id})

        # Normalize and format line item numbers before display.
        if all_items:
            items_all_df = pd.DataFrame(all_items)
            for col in ["quantity", "unit_price", "item_total"]:
                if col in items_all_df.columns:
                    items_all_df[col] = pd.to_numeric(
                        items_all_df[col], errors="coerce"
                    ).fillna(0)
            if "unit_price" in items_all_df.columns:
                items_all_df["unit_price"] = items_all_df["unit_price"].apply(
                    lambda x: f"${x:.2f}"
                )
            if "item_total" in items_all_df.columns:
                items_all_df["item_total"] = items_all_df["item_total"].apply(
                    lambda x: f"${x:.2f}"
                )

            preferred_cols = [
                "s_no",
                "bill_id",
                "item_name",
                "quantity",
                "unit_price",
                "item_total",
            ]
            ordered_cols = [c for c in preferred_cols if c in items_all_df.columns]
            remaining_cols = [c for c in items_all_df.columns if c not in ordered_cols]
            items_all_df = items_all_df[ordered_cols + remaining_cols]

            st.dataframe(items_all_df, hide_index=True, width="stretch")
        else:
            st.info("No line items available in the database.")
