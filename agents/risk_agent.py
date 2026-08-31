from typing import Any, Dict


def _add(components, points, signal, detail):
    if points > 0:
        components.append({"points": int(points), "signal": signal, "detail": detail})
    return points


def calculate_risk(reconciliation_result: Dict[str, Any], duplicate_detected: bool = False, anomaly_detected: bool = False) -> Dict[str, Any]:
    status = reconciliation_result.get("status", "NEEDS_REVIEW")
    invoice_amount = float(reconciliation_result.get("invoice_amount") or 0)
    difference = abs(float(reconciliation_result.get("difference") or 0))
    confidence = float(reconciliation_result.get("confidence") or 0)
    days = reconciliation_result.get("days_difference")
    components = []
    score = 0

    status_points = {
        "MATCH": 3,
        "POSSIBLE_MATCH": 28,
        "SUBTOTAL_PAID_TAX_OUTSTANDING": 35,
        "PARTIAL_PAYMENT": 38,
        "OVERPAYMENT": 32,
        "MISSING_PAYMENT": 58,
        "NEEDS_REVIEW": 30,
    }.get(status, 30)
    status_detail = {
        "MATCH": "Payment evidence is consistent with the invoice",
        "POSSIBLE_MATCH": "Candidate exists but supporting evidence is incomplete",
        "SUBTOTAL_PAID_TAX_OUTSTANDING": "Subtotal appears paid but tax/final balance remains outstanding",
        "PARTIAL_PAYMENT": "Payment is lower than the invoice payable amount",
        "OVERPAYMENT": "Payment is higher than the invoice payable amount",
        "MISSING_PAYMENT": "No reliable outgoing payment could be confirmed",
        "NEEDS_REVIEW": "Invoice could not be fully interpreted",
    }.get(status, "Manual review is required")
    score += _add(components, status_points, "reconciliation_status", status_detail)

    if invoice_amount > 0 and difference > 0:
        pct = difference / invoice_amount * 100
        points = 25 if pct >= 50 else 18 if pct >= 25 else 12 if pct >= 10 else 6 if pct >= 3 else 2
        score += _add(components, points, "amount_difference", f"Difference is {pct:.1f}% of invoice value")

    if confidence < 45:
        score += _add(components, 18, "match_confidence", "Very low match confidence")
    elif confidence < 65:
        score += _add(components, 10, "match_confidence", "Low match confidence")
    elif confidence < 80:
        score += _add(components, 5, "match_confidence", "Match should still be verified")

    if days is not None:
        try:
            days_int = int(days)
            if days_int > 30:
                score += _add(components, 12, "date_gap", f"Invoice/payment date gap is {days_int} days")
            elif days_int > 15:
                score += _add(components, 7, "date_gap", f"Invoice/payment date gap is {days_int} days")
        except (TypeError, ValueError):
            pass

    if duplicate_detected:
        score += _add(components, 25, "duplicate", "Matched transaction is part of a potential duplicate set")
    if anomaly_detected:
        score += _add(components, 20, "anomaly", "Matched transaction amount is statistically unusual")
    if invoice_amount >= 500000:
        score += _add(components, 15, "high_value", "Very high-value invoice")
    elif invoice_amount >= 100000:
        score += _add(components, 8, "high_value", "High-value invoice")

    score = min(int(round(score)), 100)
    if score <= 25:
        level, action = "LOW", "Auto-clear is possible after normal verification"
    elif score <= 50:
        level, action = "MEDIUM", "Reviewer should verify invoice and payment evidence"
    elif score <= 75:
        level, action = "HIGH", "Manual financial verification is required before approval"
    else:
        level, action = "CRITICAL", "Hold the case and perform immediate manual verification"

    return {
        "risk_score": score,
        "risk_level": level,
        "reasons": [x["detail"] for x in components],
        "components": components,
        "recommended_action": action,
        "decision": "AUTO_CLEAR" if level == "LOW" and status == "MATCH" and confidence >= 85 else "HUMAN_REVIEW",
    }


def calculate_all_risks(reconciliation_results: list[dict], anomaly_analysis: dict) -> list[dict]:
    dup_df = anomaly_analysis.get("duplicates")
    anom_df = anomaly_analysis.get("anomalies")
    dup_keys = set(dup_df["transaction_key"].astype(str)) if dup_df is not None and not dup_df.empty else set()
    anom_keys = set(anom_df["transaction_key"].astype(str)) if anom_df is not None and not anom_df.empty else set()
    output = []
    for rec in reconciliation_results:
        txn = rec.get("matched_transaction") or {}
        key = str(txn.get("transaction_key") or "")
        risk = calculate_risk(rec, duplicate_detected=key in dup_keys, anomaly_detected=key in anom_keys)
        risk["invoice_file"] = rec.get("invoice", {}).get("file")
        risk["vendor"] = rec.get("invoice", {}).get("vendor")
        risk["status"] = rec.get("status")
        risk["outstanding"] = rec.get("outstanding")
        risk["confidence"] = rec.get("confidence")
        output.append(risk)
    return output
