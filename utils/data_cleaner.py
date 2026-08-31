import re
from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, Optional, Tuple

import pandas as pd

from .text_utils import compact_name

ALIASES = {
    "date": {
        "date", "transactiondate", "valuedate", "postingdate", "transdate",
        "txndate", "paymentdate", "entrydate", "bookdate",
    },
    "description": {
        "description", "narration", "particulars", "details", "remarks", "memo",
        "merchant", "vendor", "vendorname", "supplier", "suppliername",
        "party", "partyname", "beneficiary", "beneficiaryname", "payee",
        "transactiondetails", "transactiondescription",
    },
    "debit": {
        "debit", "debitamount", "debitamt", "withdrawal", "withdrawals",
        "withdrawalamount", "dr", "dramount", "amountdebited", "moneyout",
        "outflow", "paid",
    },
    "credit": {
        "credit", "creditamount", "creditamt", "deposit", "deposits",
        "depositamount", "cr", "cramount", "amountcredited", "moneyin",
        "inflow", "received",
    },
    "amount": {
        "amount", "transactionamount", "txnamount", "paymentamount",
        "paidamount", "totalamount", "netamount", "transferamount",
        "transactionvalue", "value", "amt",
    },
    "balance": {
        "balance", "closingbalance", "runningbalance", "availablebalance",
        "ledgerbalance",
    },
    "reference": {
        "reference", "referenceno", "referencenumber", "transactionid",
        "txnid", "utr", "utrnumber", "chequeno", "chequenumber", "refno",
    },
}


def parse_money(value: Any) -> float:
    if value is None or pd.isna(value):
        return 0.0
    text = str(value).strip()
    parenthesis_negative = text.startswith("(") and text.endswith(")")
    text = text.replace("₹", "").replace("$", "").replace("€", "").replace("£", "")
    text = re.sub(r"\b(INR|USD|EUR|GBP)\b", "", text, flags=re.I)
    text = text.replace(",", "")
    text = re.sub(r"[^0-9.\-]", "", text)
    if text in {"", "-", "."}:
        return 0.0
    try:
        amount = float(text)
        return -abs(amount) if parenthesis_negative else amount
    except ValueError:
        return 0.0


def find_column(columns: Iterable[Any], field: str) -> Optional[str]:
    aliases = {compact_name(x) for x in ALIASES[field]}
    for col in columns:
        if compact_name(col) in aliases:
            return str(col)
    for col in columns:
        cleaned = compact_name(col)
        if not cleaned:
            continue
        for alias in aliases:
            if len(alias) >= 4 and (alias in cleaned or cleaned in alias):
                return str(col)
    best, best_score = None, 0.0
    for col in columns:
        cleaned = compact_name(col)
        if not cleaned:
            continue
        for alias in aliases:
            score = SequenceMatcher(None, cleaned, alias).ratio()
            if score > best_score:
                best, best_score = str(col), score
    return best if best_score >= 0.82 else None


def header_score(df: pd.DataFrame) -> int:
    return sum(bool(find_column(df.columns, field)) for field in ALIASES)


def detect_numeric_amount_column(df: pd.DataFrame) -> Optional[str]:
    candidates = []
    for col in df.columns:
        name = compact_name(col)
        if any(x in name for x in ["id", "reference", "utr", "account", "balance", "date", "phone"]):
            continue
        values = df[col].apply(parse_money)
        ratio = values.ne(0).mean()
        if ratio >= 0.50:
            spread = float(values.abs().std()) if len(values) > 1 else 0.0
            candidates.append((str(col), ratio, spread))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
    return candidates[0][0]


def normalize_transactions(df: pd.DataFrame, source_name: str = "bank_statement") -> Tuple[pd.DataFrame, Dict[str, Optional[str]]]:
    if df is None or df.empty:
        raise ValueError(f"{source_name}: no transaction rows found")

    frame = df.dropna(axis=1, how="all").copy()
    frame.columns = [str(c).strip() for c in frame.columns]
    mapping = {field: find_column(frame.columns, field) for field in ALIASES}

    if not any(mapping[x] for x in ["amount", "debit", "credit"]):
        mapping["amount"] = detect_numeric_amount_column(frame)

    # A generic `Amount` column must not be reused as both Debit and Credit.
    # Fuzzy matching can otherwise map the same source column to all three fields.
    if mapping.get("amount"):
        if mapping.get("debit") == mapping["amount"]:
            mapping["debit"] = None
        if mapping.get("credit") == mapping["amount"]:
            mapping["credit"] = None

    if not any(mapping[x] for x in ["amount", "debit", "credit"]):
        raise ValueError(
            f"{source_name}: Amount/Debit/Credit could not be detected. "
            f"Columns: {', '.join(map(str, frame.columns))}"
        )

    out = pd.DataFrame(index=frame.index)
    out["date"] = (
        pd.to_datetime(frame[mapping["date"]], errors="coerce", dayfirst=True, format="mixed")
        if mapping["date"] else pd.NaT
    )
    out["vendor"] = (
        frame[mapping["description"]].fillna("Transaction").astype(str).str.strip()
        if mapping["description"] else "Transaction"
    )

    debit = frame[mapping["debit"]].apply(parse_money).abs() if mapping["debit"] else pd.Series(0.0, index=frame.index)
    credit = frame[mapping["credit"]].apply(parse_money).abs() if mapping["credit"] else pd.Series(0.0, index=frame.index)

    if mapping["amount"]:
        raw_amount = frame[mapping["amount"]].apply(parse_money)
        out["amount"] = raw_amount
        out["debit"] = debit.where(debit.ne(0), raw_amount.where(raw_amount.lt(0), 0).abs())
        out["credit"] = credit.where(credit.ne(0), raw_amount.where(raw_amount.gt(0), 0))
    else:
        out["debit"] = debit
        out["credit"] = credit
        out["amount"] = credit - debit

    out["balance"] = frame[mapping["balance"]].apply(parse_money) if mapping["balance"] else pd.NA
    out["transaction_id"] = frame[mapping["reference"]].fillna("").astype(str) if mapping["reference"] else ""
    out["source_bank"] = source_name
    out["source_row"] = range(1, len(out) + 1)
    out["transaction_key"] = out["source_bank"].astype(str) + "::" + out["source_row"].astype(str)
    out["absolute_amount"] = out["amount"].abs()

    def direction(row):
        if float(row.get("debit", 0) or 0) > 0 or float(row.get("amount", 0) or 0) < 0:
            return "OUT"
        if float(row.get("credit", 0) or 0) > 0 or float(row.get("amount", 0) or 0) > 0:
            return "IN"
        return "UNKNOWN"

    out["direction"] = out.apply(direction, axis=1)
    return out.reset_index(drop=True), mapping


def validate_transactions(df: pd.DataFrame) -> list[str]:
    errors = []
    if df is None or df.empty:
        return ["No transactions found"]
    if "amount" not in df.columns:
        errors.append("Amount column is missing after normalization")
    elif pd.to_numeric(df["amount"], errors="coerce").fillna(0).abs().sum() == 0:
        errors.append("No usable transaction amounts were detected")
    return errors
