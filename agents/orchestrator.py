from time import perf_counter
from typing import Any, Dict, List

from .document_agent import extract_invoice_data
from .bank_agent import ingest_bank_statements
from .reconciliation_agent import reconcile_all
from .anomaly_agent import analyze_transactions
from .risk_agent import calculate_all_risks
from .explanation_agent import generate_explanation
from .report_agent import build_executive_summary


def _trace(trace, name, started, detail, status="complete"):
    trace.append({"agent": name, "status": status, "duration_ms": round((perf_counter()-started)*1000, 1), "detail": detail})


def run_finrecon(invoice_sources: List[Any], bank_sources: List[Any]) -> Dict[str, Any]:
    trace = []
    try:
        started = perf_counter()
        invoices = [extract_invoice_data(source) for source in invoice_sources]
        _trace(trace, "Document Intelligence Agent", started, f"Extracted {len(invoices)} invoice(s)")

        started = perf_counter()
        bank_result = ingest_bank_statements(bank_sources)
        transactions = bank_result["transactions"]
        _trace(trace, "Bank Normalization Agent", started, f"Normalized {len(transactions)} transaction(s) from {len(bank_sources)} source(s)")

        started = perf_counter()
        reconciliation = reconcile_all(invoices, transactions)
        _trace(trace, "Reconciliation Agent", started, f"Scored {len(reconciliation)} invoice-to-payment case(s)")

        started = perf_counter()
        anomaly = analyze_transactions(transactions)
        _trace(trace, "Anomaly Agent", started, f"Found {anomaly['duplicate_count']} duplicate row(s) and {anomaly['anomaly_count']} anomaly row(s)")

        started = perf_counter()
        risks = calculate_all_risks(reconciliation, anomaly)
        _trace(trace, "Risk Agent", started, f"Generated explainable risk scores for {len(risks)} case(s)")

        started = perf_counter()
        explanations = [generate_explanation(rec, risk) for rec, risk in zip(reconciliation, risks)]
        _trace(trace, "Explanation Agent", started, "Generated human-readable evidence explanations")

        run = {
            "success": True,
            "invoices": invoices,
            "transactions": transactions,
            "mappings": bank_result["mappings"],
            "bank_errors": bank_result["errors"],
            "reconciliation": reconciliation,
            "anomaly_analysis": anomaly,
            "risk": risks,
            "explanations": explanations,
            "agent_trace": trace,
        }
        run["summary"] = build_executive_summary(run)
        return run
    except Exception as exc:
        trace.append({"agent": "Orchestrator", "status": "failed", "duration_ms": 0, "detail": str(exc)})
        return {"success": False, "error": str(exc), "agent_trace": trace}


# Backward-compatible single-invoice API used by the user's earlier tests.
def run_finpilot(invoice_pdf_path, transactions_df):
    from .document_agent import extract_invoice_data
    from .reconciliation_agent import reconcile_invoice
    from .anomaly_agent import analyze_transactions
    from .risk_agent import calculate_risk
    from .explanation_agent import generate_explanation

    invoice = extract_invoice_data(invoice_pdf_path)
    transactions_df = transactions_df.copy()
    if "transaction_key" not in transactions_df.columns:
        transactions_df["transaction_key"] = [f"legacy::{i+1}" for i in range(len(transactions_df))]
    if "source_bank" not in transactions_df.columns:
        transactions_df["source_bank"] = "legacy_dataframe"
    if "absolute_amount" not in transactions_df.columns and "amount" in transactions_df.columns:
        transactions_df["absolute_amount"] = transactions_df["amount"].abs()
    if "direction" not in transactions_df.columns:
        transactions_df["direction"] = transactions_df["amount"].apply(lambda x: "OUT" if float(x) < 0 else "UNKNOWN")
    if "debit" not in transactions_df.columns:
        transactions_df["debit"] = transactions_df["amount"].apply(lambda x: abs(float(x)) if float(x) < 0 else 0.0)
    if "credit" not in transactions_df.columns:
        transactions_df["credit"] = transactions_df["amount"].apply(lambda x: float(x) if float(x) > 0 else 0.0)
    rec = reconcile_invoice(invoice, transactions_df)
    anomaly = analyze_transactions(transactions_df)
    txn = rec.get("matched_transaction") or {}
    key = str(txn.get("transaction_key") or "")
    dup = anomaly["duplicates"]
    anom = anomaly["anomalies"]
    dup_keys = set(dup["transaction_key"].astype(str)) if not dup.empty else set()
    anom_keys = set(anom["transaction_key"].astype(str)) if not anom.empty else set()
    risk = calculate_risk(rec, key in dup_keys, key in anom_keys)
    explanation = generate_explanation(rec, risk)
    return {"success": True, "invoice": invoice, "reconciliation": rec, "anomaly_analysis": anomaly, "risk": risk, "explanation": explanation}
