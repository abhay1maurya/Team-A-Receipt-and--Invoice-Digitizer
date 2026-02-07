"""Export utilities for bills and line items."""

from io import BytesIO
import pandas as pd
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors


def export_csv(bills_df):
	"""Export the bills dataframe to CSV bytes.

	Args:
		bills_df: DataFrame containing bill records.

	Returns:
		UTF-8 encoded CSV bytes for download.
	"""
	# CSV export is used by the summary download action.
	return bills_df.to_csv(index=False).encode("utf-8")


def export_excel(bills_df):
	"""Export the bills dataframe to an Excel workbook.

	Args:
		bills_df: DataFrame containing bill records.

	Returns:
		Excel file bytes with a single "Bills" worksheet.
	"""
	output = BytesIO()
	# Single-sheet export for the summary bills table.
	with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
		bills_df.to_excel(writer, index=False, sheet_name="Bills")
	return output.getvalue()


def export_pdf(bills_df):
	"""Export the bills dataframe to a simple PDF table.

	Args:
		bills_df: DataFrame containing bill records.

	Returns:
		PDF bytes containing a landscape table of selected bill fields.
	"""
	pdf_buffer = BytesIO()

	doc = SimpleDocTemplate(
		pdf_buffer,
		pagesize=landscape(letter),
		rightMargin=0.25 * inch,
		leftMargin=0.25 * inch,
		topMargin=0.25 * inch,
		bottomMargin=0.25 * inch,
		title="Bills Export",
	)

	# Keep a fixed column order for the PDF export.
	field_map = [
		("id", "ID"),
		("invoice_number", "Invoice Number"),
		("vendor_name", "Vendor Name"),
		("purchase_date", "Date"),
		("tax_amount", "Tax"),
		("total_amount", "Total"),
		("currency", "Currency"),
		("payment_method", "Payment Method"),
	]

	# Build the table header and rows.
	headers = [label for _, label in field_map]
	table_data = [headers]
	for _, row in bills_df.iterrows():
		table_data.append([str(row.get(key, "")) for key, _ in field_map])

	# Minimal styling for readability in the PDF table.
	table = Table(table_data, repeatRows=1)
	table.setStyle(
		TableStyle(
			[
				("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
				("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
				("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
				("FONTSIZE", (0, 0), (-1, -1), 8),
				("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
			]
		)
	)

	doc.build([table])
	return pdf_buffer.getvalue()


def export_detailed_csv(bills_df, items_df):
	"""Export detailed bills with line items to CSV bytes.

	Args:
		bills_df: DataFrame containing bill records.
		items_df: DataFrame containing line items with a bill_id column.

	Returns:
		UTF-8 encoded CSV bytes with one row per line item.
	"""
	# Build a flattened table where each line item becomes a row.
	detailed_data = []
	for _, bill in bills_df.iterrows():
		bill_id = bill.get("id")
		# Pull all line items that match the current bill.
		bill_items = (
			items_df[items_df["bill_id"] == bill_id]
			if "bill_id" in items_df.columns
			else []
		)

		# Add one row per line item, or a placeholder when none exist.
		if len(bill_items) > 0:
			for _, item in bill_items.iterrows():
				detailed_data.append(
					{
						"Bill_ID": bill_id,
						"Invoice_Number": bill.get("invoice_number", ""),
						"Vendor_Name": bill.get("vendor_name", ""),
						"Purchase_Date": bill.get("purchase_date", ""),
						"Purchase_Time": bill.get("purchase_time", ""),
						"Payment_Method": bill.get("payment_method", ""),
						"Bill_Subtotal": bill.get("subtotal", ""),
						"Bill_Tax": bill.get("tax_amount", ""),
						"Bill_Total": bill.get("total_amount", ""),
						"Currency": bill.get("currency", ""),
						"Item_SNo": item.get("s_no", ""),
						"Item_Name": item.get("item_name", ""),
						"Item_Quantity": item.get("quantity", ""),
						"Item_Unit_Price": item.get("unit_price", ""),
						"Item_Total": item.get("item_total", ""),
					}
				)
		else:
			detailed_data.append(
				{
					"Bill_ID": bill_id,
					"Invoice_Number": bill.get("invoice_number", ""),
					"Vendor_Name": bill.get("vendor_name", ""),
					"Purchase_Date": bill.get("purchase_date", ""),
					"Purchase_Time": bill.get("purchase_time", ""),
					"Payment_Method": bill.get("payment_method", ""),
					"Bill_Subtotal": bill.get("subtotal", ""),
					"Bill_Tax": bill.get("tax_amount", ""),
					"Bill_Total": bill.get("total_amount", ""),
					"Currency": bill.get("currency", ""),
					"Item_SNo": "",
					"Item_Name": "No line items",
					"Item_Quantity": "",
					"Item_Unit_Price": "",
					"Item_Total": "",
				}
			)

	detailed_df = pd.DataFrame(detailed_data)
	return detailed_df.to_csv(index=False).encode("utf-8")


def export_detailed_excel(bills_df, items_df):
	"""Export detailed bills with line items to an Excel workbook.

	Args:
		bills_df: DataFrame containing bill records.
		items_df: DataFrame containing line items with a bill_id column.

	Returns:
		Excel file bytes with a "Detailed View" worksheet.
	"""
	output = BytesIO()

	with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
		# Keep Excel columns aligned with the detailed CSV export.
		detailed_data = []
		for _, bill in bills_df.iterrows():
			bill_id = bill.get("id")
			# Match line items to the current bill for the detailed view.
			bill_items = (
				items_df[items_df["bill_id"] == bill_id]
				if "bill_id" in items_df.columns
				else []
			)

			# Add one row per line item, or a placeholder when none exist.
			if len(bill_items) > 0:
				for _, item in bill_items.iterrows():
					detailed_data.append(
						{
							"Bill_ID": bill_id,
							"Invoice_Number": bill.get("invoice_number", ""),
							"Vendor_Name": bill.get("vendor_name", ""),
							"Purchase_Date": bill.get("purchase_date", ""),
							"Purchase_Time": bill.get("purchase_time", ""),
							"Payment_Method": bill.get("payment_method", ""),
							"Bill_Subtotal": bill.get("subtotal", ""),
							"Bill_Tax": bill.get("tax_amount", ""),
							"Bill_Total": bill.get("total_amount", ""),
							"Currency": bill.get("currency", ""),
							"Item_SNo": item.get("s_no", ""),
							"Item_Name": item.get("item_name", ""),
							"Item_Quantity": item.get("quantity", ""),
							"Item_Unit_Price": item.get("unit_price", ""),
							"Item_Total": item.get("item_total", ""),
						}
					)
			else:
				detailed_data.append(
					{
						"Bill_ID": bill_id,
						"Invoice_Number": bill.get("invoice_number", ""),
						"Vendor_Name": bill.get("vendor_name", ""),
						"Purchase_Date": bill.get("purchase_date", ""),
						"Purchase_Time": bill.get("purchase_time", ""),
						"Payment_Method": bill.get("payment_method", ""),
						"Bill_Subtotal": bill.get("subtotal", ""),
						"Bill_Tax": bill.get("tax_amount", ""),
						"Bill_Total": bill.get("total_amount", ""),
						"Currency": bill.get("currency", ""),
						"Item_SNo": "",
						"Item_Name": "No line items",
						"Item_Quantity": "",
						"Item_Unit_Price": "",
						"Item_Total": "",
					}
				)

		# Convert the flattened rows to a DataFrame for Excel output.
		detailed_df = pd.DataFrame(detailed_data)
		# Write the detailed data as a single worksheet.
		detailed_df.to_excel(writer, index=False, sheet_name="Detailed View")

	return output.getvalue()


def export_detailed_pdf(bills_df, items_df):
	"""Export detailed bills with line items to a simple PDF table.

	Args:
		bills_df: DataFrame containing bill records.
		items_df: DataFrame containing line items with a bill_id column.

	Returns:
		PDF bytes containing a landscape table of bill and item fields.
	"""
	pdf_buffer = BytesIO()

	doc = SimpleDocTemplate(
		pdf_buffer,
		pagesize=landscape(letter),
		rightMargin=0.25 * inch,
		leftMargin=0.25 * inch,
		topMargin=0.25 * inch,
		bottomMargin=0.25 * inch,
		title="Detailed Bills Export",
	)

	# Fixed columns for the detailed PDF export.
	columns = [
		("bill_id", "Bill ID"),
		("invoice_number", "Invoice Number"),
		("vendor_name", "Vendor Name"),
		("purchase_date", "Date"),
		("s_no", "S.No"),
		("item_name", "Item Name"),
		("quantity", "Qty"),
		("unit_price", "Unit Price"),
		("item_total", "Item Total"),
	]

	# Build the table header and rows.
	headers = [label for _, label in columns]
	table_data = [headers]

	for _, bill in bills_df.iterrows():
		bill_id = bill.get("id")
		bill_items = (
			items_df[items_df["bill_id"] == bill_id]
			if "bill_id" in items_df.columns
			else pd.DataFrame()
		)

		# Add a placeholder row when no line items exist.
		if bill_items.empty:
			row = {
				"bill_id": bill_id,
				"invoice_number": bill.get("invoice_number", ""),
				"vendor_name": bill.get("vendor_name", ""),
				"purchase_date": bill.get("purchase_date", ""),
				"s_no": "",
				"item_name": "No line items",
				"quantity": "",
				"unit_price": "",
				"item_total": "",
			}
			table_data.append([str(row.get(key, "")) for key, _ in columns])
			continue

		for _, item in bill_items.iterrows():
			row = {
				"bill_id": bill_id,
				"invoice_number": bill.get("invoice_number", ""),
				"vendor_name": bill.get("vendor_name", ""),
				"purchase_date": bill.get("purchase_date", ""),
				"s_no": item.get("s_no", ""),
				"item_name": item.get("item_name", ""),
				"quantity": item.get("quantity", ""),
				"unit_price": item.get("unit_price", ""),
				"item_total": item.get("item_total", ""),
			}
			table_data.append([str(row.get(key, "")) for key, _ in columns])

	# Minimal styling for readability in the PDF table.
	table = Table(table_data, repeatRows=1)
	table.setStyle(
		TableStyle(
			[
				("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
				("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
				("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
				("FONTSIZE", (0, 0), (-1, -1), 8),
				("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
			]
		)
	)

	doc.build([table])
	return pdf_buffer.getvalue()
