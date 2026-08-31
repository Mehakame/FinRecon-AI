import re
from typing import Any, Dict, List, Optional

from utils.pdf_parser import pdf_text
from utils.common import source_name


def _first_amount(text: str, patterns: List[str]) -> Optional[float]:
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            try:
                return float(match.group(1).replace(",", ""))
            except ValueError:
                pass
    return None


def _infer_vendor(text: str) -> Optional[str]:
    explicit = re.search(
        r"(?:vendor|supplier|billed\s*by|seller|from)\s*[:.-]?\s*([^\n]{2,80})",
        text,
        re.I,
    )
    if explicit:
        return explicit.group(1).strip()

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    try:
        invoice_idx = next(i for i, line in enumerate(lines) if line.upper() == "INVOICE")
        preamble = lines[:invoice_idx]
    except StopIteration:
        preamble = lines[:6]

    for line in preamble:
        if "@" in line or re.search(r"\d{3,}", line):
            continue
        if len(line) >= 3 and re.search(r"[A-Za-z]", line):
            return line[:80]
    return None


def _extract_line_items(text: str) -> list[dict]:
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    try:
        start = lines.index("Amount") + 1
    except ValueError:
        return []
    items = []
    i = start
    while i + 3 < len(lines):
        if lines[i].lower().startswith("subtotal"):
            break
        desc, qty, unit, amount = lines[i:i+4]
        if re.fullmatch(r"\d+(?:\.\d+)?", qty) and re.search(r"[₹$€£]?[\d,]+\.\d{2}", unit) and re.search(r"[₹$€£]?[\d,]+\.\d{2}", amount):
            def money(s):
                return float(re.sub(r"[^0-9.]", "", s.replace(",", "")))
            items.append({
                "description": desc,
                "quantity": float(qty),
                "unit_price": money(unit),
                "amount": money(amount),
            })
            i += 4
        else:
            i += 1
    return items


def extract_invoice_data(source: Any) -> Dict[str, Any]:
    text = pdf_text(source)
    result: Dict[str, Any] = {
        "file": source_name(source),
        "invoice_number": None,
        "vendor": None,
        "date": None,
        "due_date": None,
        "subtotal": None,
        "tax_rate": None,
        "tax_amount": None,
        "total_due": None,
        "amount": None,
        "currency": None,
        "line_items": [],
        "raw_text": text,
        "document_confidence": 0,
        "warnings": [],
    }

    if not text.strip():
        result["warnings"].append("No text extracted; PDF may be scanned/image-only")
        return result

    if "₹" in text or re.search(r"\bINR\b", text, re.I):
        result["currency"] = "INR"
    elif "$" in text or re.search(r"\bUSD\b", text, re.I):
        result["currency"] = "USD"
    elif "€" in text or re.search(r"\bEUR\b", text, re.I):
        result["currency"] = "EUR"
    elif "£" in text or re.search(r"\bGBP\b", text, re.I):
        result["currency"] = "GBP"

    invoice_patterns = [
        r"(?im)^\s*invoice\s*(?:no\.?|number|#)\s*[:.-]?\s*([A-Z0-9/-]{3,})\s*$",
        r"(?im)^\s*invoice\s*[:.-]\s*([A-Z0-9/-]{3,})\s*$",
    ]
    for pattern in invoice_patterns:
        match = re.search(pattern, text, re.I)
        if match:
            result["invoice_number"] = match.group(1).strip()
            break

    result["vendor"] = _infer_vendor(text)

    for key, patterns in {
        "date": [
            r"(?:invoice\s*date|date)\s*[:.-]?\s*([A-Z][a-z]+\s+\d{1,2},\s+\d{4})",
            r"(?:invoice\s*date|date)\s*[:.-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"(?:invoice\s*date|date)\s*[:.-]?\s*(\d{4}[/-]\d{1,2}[/-]\d{1,2})",
        ],
        "due_date": [
            r"(?:due\s*date)\s*[:.-]?\s*([A-Z][a-z]+\s+\d{1,2},\s+\d{4})",
            r"(?:due\s*date)\s*[:.-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        ],
    }.items():
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                result[key] = match.group(1).strip()
                break

    result["subtotal"] = _first_amount(text, [
        r"\bsubtotal\b\D{0,25}([\d,]+(?:\.\d{1,2})?)",
        r"\bsub\s*total\b\D{0,25}([\d,]+(?:\.\d{1,2})?)",
    ])

    tax_rate_match = re.search(r"(?:tax|gst|vat)\s*\(?\s*(\d+(?:\.\d+)?)\s*%", text, re.I)
    if tax_rate_match:
        result["tax_rate"] = float(tax_rate_match.group(1))

    result["tax_amount"] = _first_amount(text, [
        r"(?:tax|gst|vat)(?:\s*\([^)]*\))?\s*[:.-]?\s*[₹$€£]?\s*([\d,]+(?:\.\d{1,2})?)",
    ])

    result["total_due"] = _first_amount(text, [
        r"(?:total\s*due|amount\s*due|grand\s*total|amount\s*payable|invoice\s*total)\s*[:.-]?\s*[₹$€£]?\s*([\d,]+(?:\.\d{1,2})?)",
    ])

    if result["total_due"] is None and result["subtotal"] is not None and result["tax_amount"] is not None:
        result["total_due"] = result["subtotal"] + result["tax_amount"]
    if result["tax_amount"] is None and result["total_due"] is not None and result["subtotal"] is not None:
        if result["total_due"] >= result["subtotal"]:
            result["tax_amount"] = result["total_due"] - result["subtotal"]

    result["amount"] = result["total_due"] or result["subtotal"]
    result["line_items"] = _extract_line_items(text)

    core_fields = ["invoice_number", "vendor", "date", "amount"]
    result["document_confidence"] = round(sum(bool(result[x]) for x in core_fields) / len(core_fields) * 100, 1)
    if result["amount"] is None:
        result["warnings"].append("Invoice payable amount could not be extracted")
    if result["vendor"] is None:
        result["warnings"].append("Vendor could not be confidently extracted")
    return result
