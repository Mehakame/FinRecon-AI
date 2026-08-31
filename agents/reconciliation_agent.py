from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from utils.text_utils import vendor_similarity


def amount_similarity(total_due: Optional[float], subtotal: Optional[float], payment_abs: float) -> Tuple[float, str, Optional[float]]:
    choices = []
    for label, target in [("TOTAL_DUE", total_due), ("SUBTOTAL", subtotal)]:
        if target is None or target <= 0:
            continue
        pct = abs(payment_abs - target) / target * 100
        if pct == 0:
            score = 100.0
        elif pct <= 1:
            score = 98.0
        elif pct <= 3:
            score = 92.0
        elif pct <= 5:
            score = 82.0
        elif pct <= 10:
            score = 65.0
        elif pct <= 25:
            score = 40.0
        else:
            score = max(0.0, 25.0 - pct / 4)
        if label == "SUBTOTAL" and score == 100.0:
            score = 99.0
        choices.append((score, label, target))
    if not choices:
        return 0.0, "UNKNOWN", None
    return sorted(choices, key=lambda x: x[0], reverse=True)[0]


def date_similarity(invoice_date: Any, transaction_date: Any) -> Tuple[float, Optional[int], bool]:
    if not invoice_date or pd.isna(transaction_date):
        return 0.0, None, False
    inv = pd.to_datetime(invoice_date, errors="coerce", dayfirst=True, format="mixed")
    txn = pd.to_datetime(transaction_date, errors="coerce", dayfirst=True, format="mixed")
    if pd.isna(inv) or pd.isna(txn):
        return 0.0, None, False
    days = abs((txn - inv).days)
    if days == 0: return 100.0, 0, True
    if days <= 3: return 95.0, days, True
    if days <= 7: return 88.0, days, True
    if days <= 15: return 72.0, days, True
    if days <= 30: return 50.0, days, True
    return 15.0, days, True


def direction_score(direction: str) -> float:
    return {"OUT": 100.0, "UNKNOWN": 55.0, "IN": 0.0}.get(str(direction).upper(), 55.0)


def _weighted_confidence(amount_score, vendor_score, vendor_available, date_score, date_available, dir_score):
    parts = [(amount_score, 0.55), (dir_score, 0.20)]
    if vendor_available:
        parts.append((vendor_score, 0.18))
    if date_available:
        parts.append((date_score, 0.07))
    denominator = sum(weight for _, weight in parts)
    return round(sum(score * weight for score, weight in parts) / denominator, 2)


def _candidate(invoice: Dict[str, Any], txn: pd.Series) -> Dict[str, Any]:
    payment = abs(float(txn.get("amount", 0) or 0))
    amount_score, basis, target = amount_similarity(invoice.get("total_due"), invoice.get("subtotal"), payment)
    vendor_score, vendor_available = vendor_similarity(invoice.get("vendor"), txn.get("vendor"))
    date_score, days, date_available = date_similarity(invoice.get("date"), txn.get("date"))
    dir_score = direction_score(txn.get("direction"))
    confidence = _weighted_confidence(amount_score, vendor_score, vendor_available, date_score, date_available, dir_score)
    return {
        "transaction_key": txn.get("transaction_key"),
        "transaction_id": txn.get("transaction_id"),
        "source_bank": txn.get("source_bank"),
        "vendor": txn.get("vendor"),
        "date": txn.get("date"),
        "amount": float(txn.get("amount", 0) or 0),
        "payment_abs": payment,
        "direction": txn.get("direction"),
        "amount_similarity": round(amount_score, 1),
        "vendor_similarity": round(vendor_score, 1) if vendor_available else None,
        "date_similarity": round(date_score, 1) if date_available else None,
        "days_difference": days,
        "direction_score": dir_score,
        "match_basis": basis,
        "target_amount": target,
        "confidence": confidence,
        "evidence_count": 1 + int(vendor_available) + int(date_available) + int(str(txn.get("direction")).upper() != "UNKNOWN"),
    }


def reconcile_invoice(invoice: Dict[str, Any], transactions_df: pd.DataFrame, used_keys: Optional[set] = None, tolerance_pct: float = 0.01) -> Dict[str, Any]:
    used_keys = used_keys if used_keys is not None else set()
    invoice_amount = invoice.get("total_due") or invoice.get("amount") or invoice.get("subtotal")
    if invoice_amount is None:
        return {
            "status": "NEEDS_REVIEW", "invoice_amount": None, "payment_amount": None,
            "difference": None, "outstanding": None, "confidence": 0.0,
            "message": "Invoice payable amount could not be extracted", "matched_transaction": None,
            "top_candidates": [],
        }
    available = transactions_df[~transactions_df["transaction_key"].isin(used_keys)].copy()
    if available.empty:
        return {
            "status": "MISSING_PAYMENT", "invoice_amount": float(invoice_amount), "payment_amount": 0.0,
            "difference": float(invoice_amount), "outstanding": float(invoice_amount), "confidence": 0.0,
            "message": "No unused bank transactions are available", "matched_transaction": None,
            "top_candidates": [],
        }

    candidates = sorted((_candidate(invoice, row) for _, row in available.iterrows()), key=lambda x: x["confidence"], reverse=True)
    best = candidates[0]

    # Safety gate: incoming money cannot be auto-reconciled as an invoice payment.
    if best["direction"] == "IN":
        reliable = False
    else:
        reliable = best["amount_similarity"] >= 60 and best["confidence"] >= 58

    if not reliable:
        return {
            "status": "MISSING_PAYMENT", "invoice_amount": float(invoice_amount), "payment_amount": 0.0,
            "difference": float(invoice_amount), "outstanding": float(invoice_amount), "confidence": round(best["confidence"], 1),
            "message": "No transaction had enough evidence to safely confirm payment",
            "matched_transaction": None, "top_candidates": candidates[:3],
            "vendor_similarity": best["vendor_similarity"] or 0.0,
            "amount_similarity": best["amount_similarity"], "date_similarity": best["date_similarity"] or 0.0,
            "days_difference": best["days_difference"], "match_basis": best["match_basis"],
        }

    payment = best["payment_abs"]
    total_due = invoice.get("total_due")
    subtotal = invoice.get("subtotal")
    tolerance = max(1.0, float(invoice_amount) * tolerance_pct)

    # If only amount evidence is available, do not auto-confirm.
    if best["evidence_count"] <= 2 and best["direction"] == "UNKNOWN":
        status = "POSSIBLE_MATCH"
    elif total_due is not None and abs(payment - float(total_due)) <= max(1.0, float(total_due) * tolerance_pct):
        status = "MATCH"
    elif subtotal is not None and total_due is not None and total_due >= subtotal and abs(payment - float(subtotal)) <= max(1.0, float(subtotal) * tolerance_pct):
        status = "SUBTOTAL_PAID_TAX_OUTSTANDING"
    elif payment < float(invoice_amount):
        status = "PARTIAL_PAYMENT"
    else:
        status = "OVERPAYMENT"

    difference = float(invoice_amount) - payment
    outstanding = max(difference, 0.0)
    evidence = [f"amount {best['amount_similarity']:.0f}%", f"direction {best['direction']}"]
    if best["vendor_similarity"] is not None:
        evidence.append(f"vendor {best['vendor_similarity']:.0f}%")
    if best["date_similarity"] is not None:
        evidence.append(f"date {best['date_similarity']:.0f}%")

    return {
        "status": status,
        "invoice_amount": float(invoice_amount),
        "payment_amount": payment,
        "difference": difference,
        "outstanding": outstanding,
        "confidence": round(best["confidence"], 1),
        "vendor_similarity": best["vendor_similarity"] or 0.0,
        "amount_similarity": best["amount_similarity"],
        "date_similarity": best["date_similarity"] or 0.0,
        "days_difference": best["days_difference"],
        "match_basis": best["match_basis"],
        "evidence": ", ".join(evidence),
        "matched_transaction": best,
        "top_candidates": candidates[:3],
    }


def reconcile_all(invoices: List[Dict[str, Any]], transactions_df: pd.DataFrame) -> List[Dict[str, Any]]:
    results, used = [], set()
    for invoice in invoices:
        result = reconcile_invoice(invoice, transactions_df, used_keys=used)
        result["invoice"] = invoice
        txn = result.get("matched_transaction")
        if txn and result["status"] not in {"POSSIBLE_MATCH"}:
            used.add(txn.get("transaction_key"))
        results.append(result)
    return results
