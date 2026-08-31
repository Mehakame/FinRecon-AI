import json
import urllib.request
from typing import Any, Dict


def _rule_based(question: str, run: Dict[str, Any]) -> str:
    q = question.lower().strip()
    rec = run["reconciliation"]
    risks = run["risk"]
    anomaly = run["anomaly_analysis"]
    if "outstanding" in q or "unpaid" in q:
        total = sum(float(x.get("outstanding") or 0) for x in rec)
        return f"Total outstanding across the current case set is {total:,.2f}."
    if "duplicate" in q:
        return f"I found {anomaly['duplicate_count']} transaction row(s) involved in potential duplicates."
    if "anomal" in q or "unusual" in q or "suspicious" in q:
        return f"I found {anomaly['anomaly_count']} statistically unusual transaction amount(s)."
    if "risk" in q:
        if not risks:
            return "No risk results are available."
        item = sorted(risks, key=lambda x: x.get("risk_score", 0), reverse=True)[0]
        return f"Highest risk case is {item.get('invoice_file')} at {item.get('risk_score')}/100 ({item.get('risk_level')}). " + "; ".join(item.get("reasons", [])[:3])
    if "tax" in q:
        cases = [x for x in rec if x.get("status") == "SUBTOTAL_PAID_TAX_OUTSTANDING"]
        if not cases:
            return "No subtotal-paid / tax-outstanding case was detected."
        total = sum(float(x.get("outstanding") or 0) for x in cases)
        return f"{len(cases)} invoice(s) have subtotal payment evidence but tax/final balance remains outstanding. Total: {total:,.2f}."
    if "match" in q or "recon" in q:
        matched = sum(x.get("status") == "MATCH" for x in rec)
        return f"{matched} of {len(rec)} invoice(s) are fully matched. {len(rec)-matched} require review."
    if "why" in q:
        flagged = [x for x in risks if x.get("risk_level") in {"HIGH", "CRITICAL"}]
        if flagged:
            item = flagged[0]
            return f"{item.get('invoice_file')} is flagged because: " + "; ".join(item.get("reasons", [])[:4])
    return "Ask about outstanding amount, tax, duplicates, anomalies, reconciliation, or highest risk."


def _ollama(question: str, run: Dict[str, Any], model: str) -> str | None:
    context = {
        "reconciliation": [{k: v for k, v in x.items() if k not in {"top_candidates", "invoice"}} for x in run["reconciliation"]],
        "risk": run["risk"],
        "summary": run["summary"],
    }
    prompt = (
        "You are FinRecon AI, an explainable financial reconciliation agent. Use ONLY the JSON evidence below. "
        "Never invent a payment or claim fraud. If evidence is weak, say verification is required.\n\n"
        + json.dumps(context, default=str) + f"\n\nQuestion: {question}"
    )
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
    req = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            return json.loads(response.read().decode("utf-8")).get("response")
    except Exception:
        return None


def ask_finrecon(question: str, run: Dict[str, Any], use_ollama: bool = False, model: str = "llama3.2:3b") -> Dict[str, Any]:
    if use_ollama:
        answer = _ollama(question, run, model)
        if answer:
            return {"answer": answer, "mode": f"Local Ollama · {model}"}
    return {"answer": _rule_based(question, run), "mode": "Deterministic evidence mode"}
