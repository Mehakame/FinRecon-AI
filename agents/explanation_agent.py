from typing import Any, Dict


def generate_explanation(reconciliation_result: Dict[str, Any], risk_result: Dict[str, Any]) -> Dict[str, Any]:
    status = reconciliation_result.get("status", "NEEDS_REVIEW")
    inv = float(reconciliation_result.get("invoice_amount") or 0)
    payment = float(reconciliation_result.get("payment_amount") or 0)
    outstanding = float(reconciliation_result.get("outstanding") or 0)
    confidence = float(reconciliation_result.get("confidence") or 0)

    if status == "MATCH":
        explanation = f"An outgoing bank transaction reconciles the invoice at {confidence:.1f}% confidence. Invoice value {inv:,.2f}; payment {payment:,.2f}."
    elif status == "SUBTOTAL_PAID_TAX_OUTSTANDING":
        explanation = f"The bank payment aligns with the invoice subtotal, but the full payable total is not covered. Outstanding tax/final balance: {outstanding:,.2f}."
    elif status == "PARTIAL_PAYMENT":
        explanation = f"A likely outgoing payment was found, but it covers only part of the invoice. Outstanding amount: {outstanding:,.2f}."
    elif status == "OVERPAYMENT":
        explanation = f"A likely payment was found, but it exceeds the invoice payable amount by {abs(inv-payment):,.2f}."
    elif status == "POSSIBLE_MATCH":
        explanation = "A transaction has a strong amount signal but not enough independent evidence to confirm it automatically."
    elif status == "MISSING_PAYMENT":
        explanation = "No outgoing bank transaction had enough combined amount/vendor/date evidence to safely confirm payment."
    else:
        explanation = "The invoice could not be fully interpreted and requires human review."

    return {
        "explanation": explanation,
        "recommendation": risk_result.get("recommended_action", "Review source evidence"),
        "risk_score": risk_result.get("risk_score", 0),
        "risk_level": risk_result.get("risk_level", "UNKNOWN"),
        "reasons": risk_result.get("reasons", []),
    }
