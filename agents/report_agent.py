import io
import json
import zipfile
from typing import Any, Dict

import pandas as pd


def status_label(status: str) -> str:
    return {
        "MATCH": "Matched",
        "POSSIBLE_MATCH": "Possible match — verify",
        "SUBTOTAL_PAID_TAX_OUTSTANDING": "Subtotal paid / tax outstanding",
        "PARTIAL_PAYMENT": "Partial payment",
        "OVERPAYMENT": "Overpayment",
        "MISSING_PAYMENT": "Missing payment",
        "NEEDS_REVIEW": "Needs review",
    }.get(status, status)


def reconciliation_frame(results: list[dict]) -> pd.DataFrame:
    rows = []
    for rec in results:
        inv = rec.get("invoice", {})
        txn = rec.get("matched_transaction") or {}
        rows.append({
            "Invoice": inv.get("file"),
            "Invoice no.": inv.get("invoice_number"),
            "Vendor": inv.get("vendor"),
            "Currency": inv.get("currency"),
            "Subtotal": inv.get("subtotal"),
            "Tax": inv.get("tax_amount"),
            "Total due": inv.get("total_due") or inv.get("amount"),
            "Bank": txn.get("source_bank"),
            "Bank transaction": txn.get("vendor"),
            "Bank amount": rec.get("payment_amount"),
            "Outstanding": rec.get("outstanding"),
            "Status": status_label(rec.get("status")),
            "Confidence": rec.get("confidence"),
            "Evidence": rec.get("evidence") or rec.get("message"),
        })
    return pd.DataFrame(rows)


def risk_frame(risks: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([{
        "Invoice": x.get("invoice_file"), "Vendor": x.get("vendor"), "Status": status_label(x.get("status")),
        "Outstanding": x.get("outstanding"), "Confidence": x.get("confidence"), "Risk score": x.get("risk_score"),
        "Risk level": x.get("risk_level"), "Decision": x.get("decision"),
        "Reasons": " | ".join(x.get("reasons", [])), "Recommended action": x.get("recommended_action"),
    } for x in risks])


def currency_summary(invoices: list[dict], reconciliations: list[dict]) -> pd.DataFrame:
    rows = []
    currencies = sorted({inv.get("currency") or "UNKNOWN" for inv in invoices})
    for currency in currencies:
        indexes = [i for i, inv in enumerate(invoices) if (inv.get("currency") or "UNKNOWN") == currency]
        total = sum(float(invoices[i].get("total_due") or invoices[i].get("amount") or 0) for i in indexes)
        outstanding = sum(float(reconciliations[i].get("outstanding") or 0) for i in indexes)
        rows.append({"Currency": currency, "Invoice total": total, "Outstanding": outstanding, "Invoices": len(indexes)})
    return pd.DataFrame(rows)


def build_executive_summary(run: Dict[str, Any]) -> Dict[str, Any]:
    rec = run["reconciliation"]
    risks = run["risk"]
    transactions = run["transactions"]
    matched = sum(x.get("status") == "MATCH" for x in rec)
    high = sum(x.get("risk_level") in {"HIGH", "CRITICAL"} for x in risks)
    return {
        "invoice_count": len(run["invoices"]),
        "transaction_count": len(transactions),
        "matched_count": matched,
        "review_count": len(rec) - matched,
        "match_rate": round(matched / len(rec) * 100, 1) if rec else 0.0,
        "duplicate_rows": run["anomaly_analysis"]["duplicate_count"],
        "anomaly_rows": run["anomaly_analysis"]["anomaly_count"],
        "high_critical_cases": high,
        "max_risk": max((x.get("risk_score", 0) for x in risks), default=0),
    }


def build_export_zip(run: Dict[str, Any], audit_log: pd.DataFrame | None = None) -> bytes:
    rec_df = reconciliation_frame(run["reconciliation"])
    risk_df = risk_frame(run["risk"])
    dup = run["anomaly_analysis"]["duplicates"]
    anom = run["anomaly_analysis"]["anomalies"]
    summary = build_executive_summary(run)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("executive_summary.json", json.dumps(summary, indent=2))
        z.writestr("reconciliation.csv", rec_df.to_csv(index=False))
        z.writestr("risk_report.csv", risk_df.to_csv(index=False))
        z.writestr("normalized_transactions.csv", run["transactions"].to_csv(index=False))
        z.writestr("duplicates.csv", dup.to_csv(index=False) if not dup.empty else "")
        z.writestr("anomalies.csv", anom.to_csv(index=False) if not anom.empty else "")
        if audit_log is not None and not audit_log.empty:
            z.writestr("audit_log.csv", audit_log.to_csv(index=False))
    return buffer.getvalue()
