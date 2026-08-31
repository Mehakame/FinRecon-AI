# FinRecon AI — Professional Hackathon Build

FinRecon AI is a **local-first multi-agent financial reconciliation system** that converts invoices and bank statements into evidence-backed reconciliation decisions, explainable risk scores, and human review actions.

## Why it is an AI Agent system
The Orchestrator coordinates specialized agents:
1. **Document Intelligence Agent** — extracts invoice number, vendor, dates, subtotal, tax, total due, line items, currency.
2. **Bank Normalization Agent** — understands different CSV/XLSX/XLS/PDF statement formats and maps them to one schema.
3. **Reconciliation Agent** — ranks payment candidates using amount, vendor, date, and transaction direction.
4. **Anomaly Agent** — detects duplicate payment rows and statistical amount anomalies.
5. **Risk Agent** — builds a 0–100 explainable risk score for each invoice.
6. **Explanation Agent** — converts signals into human-readable reasoning and recommended action.
7. **Report Agent** — creates executive summaries and a downloadable audit package.
8. **Copilot Agent** — answers questions from the current evidence; optionally uses a free local Ollama model.

## Show-stopper safety feature
FinRecon **does not match an invoice just because the amount is similar**. It also checks payment direction and supporting vendor/date evidence. The bundled bank PDF contains an incoming $2,500 credit; FinRecon correctly refuses to treat that as payment for the $2,706.25 invoice.

## Demo scenarios
The Command Center includes three one-click scenarios:
- No outgoing payment found
- Subtotal paid — tax outstanding ($206.25 remains)
- Full payment matched

## Install
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Test
```powershell
python -m unittest discover -s tests -v
```

## Hackathon demo flow
1. Run **Subtotal paid — tax outstanding** demo.
2. Show the **Agent Decision Trace**.
3. Open **Documents** and show extracted subtotal/tax/total.
4. Open **Reconciliation** and show evidence/confidence.
5. Open **Risk Intelligence** and show the score breakdown.
6. Save a human review decision.
7. Open **Reports** and download the audit package.
8. Ask Copilot: `Is tax still outstanding?`
9. Run **No outgoing payment found** to show the anti-false-positive direction check.

## Responsible AI
- No automatic claim of fraud.
- Weak evidence is escalated for verification.
- Human approval remains final.
- Optional LLM is constrained to structured evidence and is not required for the core system.
