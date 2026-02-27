"""Vendor template parsing utilities for OCR text.

This module loads vendor-specific templates from JSON files and applies them
to OCR text as a structured fallback. Templates can define:
- Static fields (fixed vendor name)
- Field patterns (regex for invoice/date/time)
- Label-based amounts (subtotal/total near a label)
- Line item parsing with start/end markers
"""

import json
import os
import re
from typing import Dict, List, Optional, Any

from .regex_patterns import AMOUNT_PATTERN

_TEMPLATES: Dict[str, Dict[str, Any]] = {}
_TEMPLATE_ALIASES: Dict[str, str] = {}
_TEMPLATES_LOADED = False


def _normalize_vendor_key(value: str) -> str:
    """Normalize vendor labels into a lookup key.

    Strips non-alphanumerics and uppercases the input so aliases like
    "WAL-MART" and "Walmart" resolve to the same template.
    """
    if not value:
        return ""
    return re.sub(r"[^A-Z0-9]+", "", value.upper())


def _load_templates() -> None:
    """Load template JSON files and build alias lookup maps.

    Runs once per process and caches templates in memory.
    """
    global _TEMPLATES_LOADED

    if _TEMPLATES_LOADED:
        return

    # Load all JSON templates once and build alias lookup.
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    if not os.path.isdir(template_dir):
        _TEMPLATES_LOADED = True
        return

    for filename in os.listdir(template_dir):
        if not filename.lower().endswith(".json"):
            continue

        file_path = os.path.join(template_dir, filename)
        try:
            with open(file_path, "r", encoding="utf-8") as handle:
                template = json.load(handle)
        except Exception:
            continue

        vendor_key = template.get("vendor_key")
        if not vendor_key:
            continue

        _TEMPLATES[vendor_key] = template

        aliases = list(template.get("aliases", []))
        aliases.append(vendor_key)
        for alias in aliases:
            normalized = _normalize_vendor_key(alias)
            if normalized:
                _TEMPLATE_ALIASES[normalized] = vendor_key

    _TEMPLATES_LOADED = True


def find_template_for_vendor(vendor_name: Optional[str]) -> Optional[Dict[str, Any]]:
    """Find the best matching template for a vendor name.

    Args:
        vendor_name: Vendor name extracted from OCR or spaCy.

    Returns:
        Template dict if matched, otherwise None.
    """
    _load_templates()
    if not vendor_name:
        return None

    normalized = _normalize_vendor_key(vendor_name)
    if not normalized:
        return None

    vendor_key = _TEMPLATE_ALIASES.get(normalized)
    if not vendor_key:
        return None

    return _TEMPLATES.get(vendor_key)


def _find_first(patterns: List[str], text: str) -> str:
    """Return the first regex capture match from a list of patterns."""
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return ""


def _find_amount_after_label(label_patterns: List[str], text: str) -> float:
    """Find a currency amount that follows any of the given label patterns."""
    for label in label_patterns:
        regex = rf"{label}\s*[:\-]?\s*({AMOUNT_PATTERN})"
        match = re.search(regex, text, re.IGNORECASE)
        if match:
            return float(match.group(1).replace(",", ""))
    return 0.0


def _slice_lines_by_markers(lines: List[str], start_markers: List[str], end_markers: List[str]) -> List[str]:
    """Slice OCR lines between start and end markers for line items."""
    start_index = 0
    end_index = len(lines)

    # Prefer content between header/footer markers to avoid totals or store info.
    if start_markers:
        for idx, line in enumerate(lines):
            if any(re.search(marker, line, re.IGNORECASE) for marker in start_markers):
                start_index = idx + 1
                break

    if end_markers:
        for idx in range(start_index, len(lines)):
            if any(re.search(marker, lines[idx], re.IGNORECASE) for marker in end_markers):
                end_index = idx
                break

    return lines[start_index:end_index]


def _parse_line_items(lines: List[str], line_pattern: str, line_groups: Optional[Dict[str, int]] = None) -> List[Dict[str, Any]]:
    """Parse line items from scoped OCR lines using a template pattern.

    Supports either named capture groups or index-based group mapping.
    """
    items: List[Dict[str, Any]] = []

    for line in lines:
        match = re.search(line_pattern, line, re.IGNORECASE)
        if not match:
            continue

        groups = match.groupdict() if match.groupdict() else {}
        if groups:
            name = groups.get("item_name") or groups.get("name")
            qty = groups.get("quantity") or groups.get("qty")
            unit_price = groups.get("unit_price") or groups.get("price")
            item_total = groups.get("item_total") or groups.get("total")
        else:
            name = None
            qty = None
            unit_price = None
            item_total = None
            if line_groups:
                if "item_name" in line_groups:
                    name = match.group(line_groups["item_name"])
                if "quantity" in line_groups:
                    qty = match.group(line_groups["quantity"])
                if "unit_price" in line_groups:
                    unit_price = match.group(line_groups["unit_price"])
                if "item_total" in line_groups:
                    item_total = match.group(line_groups["item_total"])

        if not name:
            continue

        try:
            qty_val = float(qty) if qty is not None else 1.0
        except Exception:
            qty_val = 1.0

        try:
            unit_val = float(unit_price) if unit_price is not None else 0.0
        except Exception:
            unit_val = 0.0

        try:
            total_val = float(item_total) if item_total is not None else qty_val * unit_val
        except Exception:
            total_val = qty_val * unit_val

        items.append({
            "s_no": len(items) + 1,
            "item_name": str(name).strip(),
            "quantity": qty_val,
            "unit_price": unit_val,
            "item_total": round(total_val, 2),
        })

    return items


def parse_with_template(ocr_text: str, template: Dict[str, Any]) -> Dict[str, Any]:
    """Apply a vendor template to OCR text and return extracted fields.

    Returns a partial result containing only fields the template is able to
    detect (plus optional line items). Missing fields are omitted.
    """
    extracted: Dict[str, Any] = {}

    # Static fields allow template authors to pin vendor labels or defaults.
    static_fields = template.get("static_fields", {})
    if isinstance(static_fields, dict):
        extracted.update(static_fields)

    # Per-field rules support either patterns or label-based amount detection.
    fields = template.get("fields", {})
    for field_name, config in fields.items():
        if not isinstance(config, dict):
            continue

        patterns = config.get("patterns") or []
        label_patterns = config.get("label_patterns") or []

        if patterns:
            extracted[field_name] = _find_first(patterns, ocr_text)
        elif label_patterns:
            extracted[field_name] = _find_amount_after_label(label_patterns, ocr_text)

    # Line item parsing runs only when a vendor supplies a line pattern.
    line_items_config = template.get("line_items") or {}
    line_pattern = line_items_config.get("line_pattern")
    if line_pattern:
        lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]
        start_markers = line_items_config.get("start_markers") or []
        end_markers = line_items_config.get("end_markers") or []
        scoped_lines = _slice_lines_by_markers(lines, start_markers, end_markers)
        line_groups = line_items_config.get("line_groups")
        extracted["items"] = _parse_line_items(scoped_lines, line_pattern, line_groups)

    return extracted
