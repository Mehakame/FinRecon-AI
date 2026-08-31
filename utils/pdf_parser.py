import re
from typing import Any, Dict, List

import fitz
import pandas as pd

from .common import source_bytes, source_name
from .data_cleaner import parse_money


def pdf_text(source: Any) -> str:
    data = source_bytes(source)
    document = fitz.open(stream=data, filetype="pdf")
    try:
        return "\n".join(page.get_text("text") or "" for page in document)
    finally:
        document.close()


def parse_bank_pdf(source: Any) -> pd.DataFrame:
    """Best-effort parser for text-based bank statement PDFs."""
    text = pdf_text(source)
    pattern = re.compile(
        r"([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})\s*\n"
        r"([^\n]+)\s*\n"
        r"(-?[₹$€£]?[\d,]+\.\d{2})\s*\n"
        r"([₹$€£]?[\d,]+\.\d{2})",
        re.M,
    )
    rows: List[Dict[str, Any]] = []
    for idx, match in enumerate(pattern.finditer(text), start=1):
        date_text, description, amount_text, balance_text = match.groups()
        amount = parse_money(amount_text)
        rows.append({
            "Date": date_text,
            "Description": description.strip(),
            "Amount": amount,
            "Balance": parse_money(balance_text),
            "Reference": f"PDF-{idx:04d}",
        })
    if not rows:
        raise ValueError(
            f"{source_name(source)}: no transaction table could be extracted from the PDF. "
            "Use CSV/XLSX for scanned or complex statements."
        )
    return pd.DataFrame(rows)
