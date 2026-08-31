# 🏦 FinRecon AI

> An explainable multi-agent financial reconciliation and risk intelligence platform for invoices and bank statements.

**FinRecon AI** helps finance teams reconcile invoices against one or more bank statements, identify mismatches and suspicious patterns, calculate explainable risk, and keep a human reviewer in control of the final financial decision.

![Dashboard](../screenshots/dashboard.png)

## 🎯 The Problem

Financial reconciliation is still highly manual in many teams. Finance professionals often need to:

- 📄 Read invoices one by one
- 🔍 Locate related bank transactions  
- 💰 Compare amounts and payment dates
- ⚠️ Identify partial or duplicate payments
- 🔎 Investigate unusual transactions
- 📊 Explain why a transaction is risky
- 📋 Document the final review decision

This becomes slow and error-prone when invoices and bank statements use different formats.

## ✨ The Solution

FinRecon AI converts this workflow into an evidence-aware multi-agent pipeline.

It can:

- 📋 Extract structured invoice information from PDF documents
- 🔄 Normalize different bank statement formats
- 🎯 Rank likely payment matches
- ⚡ Detect partial payment, overpayment, tax outstanding, and missing payment
- 🚨 Identify duplicate and statistically unusual transactions
- 📈 Generate a transparent 0–100 risk score
- 💡 Explain the evidence behind the decision
- ✅ Allow a human reviewer to approve, reject, or request verification
- 📊 Generate reports and an audit trail
- 🤖 Answer questions through a financial Copilot

## 🤖 Why FinRecon AI Is an AI Agent System

FinRecon AI uses specialized agents coordinated through an orchestration layer, each with a specific responsibility in the financial reconciliation workflow.

| Agent | Responsibility |
|-------|-----------------|
| **Document Intelligence Agent** | Extracts invoice number, vendor, dates, subtotal, tax, total due, line items, and currency |
| **Bank Normalization Agent** | Converts different CSV/XLSX/XLS/PDF statement formats into a common transaction schema |
| **Reconciliation Agent** | Ranks payment candidates using amount, vendor, date, and transaction direction |
| **Anomaly Agent** | Detects possible duplicate payments and statistical amount anomalies |
| **Risk Agent** | Produces an explainable financial risk score from 0–100 |
| **Explanation Agent** | Converts technical signals into human-readable reasons and recommended action |
| **Report Agent** | Produces summaries and downloadable audit outputs |
| **Copilot Agent** | Answers questions using the current reconciliation evidence; optional local Ollama support |

### System Architecture

```
                    Financial Documents
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
        Invoice PDFs            Bank Statements
                              CSV / XLSX / XLS / PDF
              │                         │
              ▼                         ▼
   Document Intelligence        Bank Normalization
          Agent                     Agent
              │                         │
              └────────────┬────────────┘
                           │
                           ▼
                  Reconciliation Agent
                           │
                 Evidence-aware matching
                 Amount + Vendor + Date
                 + Payment Direction
                           │
               ┌───────────┴───────────┐
               ▼                       ▼
          Anomaly Agent             Risk Agent
               │                       │
               └───────────┬───────────┘
                           ▼
                   Explanation Agent
                           │
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
         Reports        AI Copilot    Human Review
                                           │
                                           ▼
                                      Audit Trail
```

![Reconciliation](../screenshots/reconciliation.png)

## 🌟 Key Features

### 1. 📄 Intelligent Invoice Extraction

FinRecon AI extracts key financial fields such as:

- Invoice number & vendor/supplier
- Invoice date & payment terms
- Subtotal, tax percentage, & tax amount
- Total due & line items
- Currency & payment reference

### 2. 🔄 Format-Agnostic Bank Normalization

Supports different bank column names and formats:

- **Date Fields:** Date, Transaction Date, Value Date
- **Description:** Narration, Particulars, Reference
- **Amount:** Transaction Amount, Debit, Credit, DR, CR
- **Reference:** UTR, Transaction ID, Cheque Number

### 3. 🎯 Evidence-Aware Smart Matching

The reconciliation engine evaluates:

- Amount similarity (with tolerance thresholds)
- Vendor name matching & fuzzy logic
- Date proximity (configurable window)
- Transaction direction (inflow vs outflow)

FinRecon AI does not automatically claim a successful payment match based only on a similar amount.

### 4. ⚡ Payment Exception Detection

Possible reconciliation outcomes include:

- ✅ **MATCH** — Full invoice payment found
- 🟡 **PARTIAL PAYMENT** — Only part of invoice paid
- 🔴 **OVERPAYMENT** — Amount exceeds invoice total
- ⚠️ **MISSING PAYMENT** — Expected payment not found
- 📋 **SUBTOTAL PAID / TAX OUTSTANDING** — Common scenario
- 🔍 **POSSIBLE MATCH — VERIFY** — Requires human review

### 5. 🚨 Duplicate Payment Detection

Flags repeated transactions with suspiciously similar:

- Vendor name & payment reference
- Amount & transaction date
- Narration & context

### 6. 📊 Financial Anomaly Detection

Detects statistically unusual transaction amounts and surfaces them for human review based on vendor-specific patterns.

### 7. 🎓 Explainable Risk Scoring

Each reconciled invoice receives:

- **Risk Score:** 0–100 scale
- **Risk Level:** LOW, MEDIUM, HIGH, CRITICAL
- **Evidence:** Specific reasons for the score

Example risk reasons:

- Partial payment detected
- Amount difference exceeds 10%
- Low smart-match confidence
- Possible duplicate payment
- Unusual transaction amount
- Payment date significantly delayed

![Risk Intelligence](../screenshots/risk-intelligence.png)

### 8. 👤 Human-in-the-Loop Review

AI recommendations remain advisory. A reviewer can:

- ✅ **Approve** — Accept the reconciliation
- ❌ **Reject** — Dispute the match
- 🔍 **Request Verification** — Escalate for investigation
- 📝 Add reviewer notes & tags
- 📋 Preserve all actions in audit trail

### 9. 📊 Reports & Analytics

The dashboard includes:

- Executive reconciliation summary & cash flow overview
- Outstanding amount & match rate metrics
- Risk distribution & priority review queue
- Bank-wise & vendor-wise analytics
- Downloadable audit-ready outputs

![Reports](../screenshots/reports.png)

### 10. 🤖 FinRecon Copilot

Ask questions naturally using the Copilot:

- "How much is still outstanding?"
- "Which invoice has the highest risk?"
- "Are there possible duplicate payments?"
- "Is tax still outstanding?"
- "How many invoices were successfully matched?"

Core reconciliation does not require a paid LLM API. Optional local Ollama support can be used for richer natural-language answers.

![Copilot](../screenshots/copilot.png)

## 💡 Show-Stopper Scenario

Consider a real-world invoice with partial payment:

```
Subtotal      $2,500.00
Tax             $206.25
Total Due     $2,706.25
```

Incoming bank transaction:

```
ABC Cloud Services      -$2,500.00
```

**Traditional systems** might incorrectly mark the entire invoice as paid (false positive).

**FinRecon AI correctly identifies:**

- **Status:** SUBTOTAL PAID / TAX OUTSTANDING
- **Outstanding:** $206.25
- **Risk Level:** MEDIUM
- **Reason:** Tax payment still expected

Another important safeguard: an incoming $2,500 credit should not automatically be treated as payment for the invoice simply because the amount is similar. FinRecon AI considers vendor name, payment direction, and temporal proximity.

## 📁 Project Structure

```
finReconAI/
│
├── app.py                          # Main Streamlit application
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── LICENSE                         # Project license
├── .gitignore                      # Git ignore rules
│
├── agents/                         # Multi-agent orchestration
│   ├── __init__.py
│   ├── orchestrator.py             # Coordinates all agents
│   ├── document_agent.py           # Invoice extraction
│   ├── bank_agent.py               # Statement normalization
│   ├── reconciliation_agent.py     # Payment matching
│   ├── anomaly_agent.py            # Duplicate & anomaly detection
│   ├── risk_agent.py               # Risk scoring engine
│   ├── explanation_agent.py        # Generate explanations
│   ├── report_agent.py             # Reports & analytics
│   └── copilot_agent.py            # Question-answering copilot
│
├── database/                       # Data persistence
│   ├── __init__.py
│   └── database.py                 # Local audit trail storage
│
├── utils/                          # Utility functions
│   ├── __init__.py
│   ├── common.py                   # Shared utilities
│   ├── data_cleaner.py             # Data normalization
│   ├── pdf_parser.py               # PDF extraction
│   └── text_utils.py               # Text processing
│
├── data/                           # Demo datasets
│   ├── demo_tax_outstanding.csv    # Test scenario
│   ├── demo_full_payment.csv       # Test scenario
│   └── demo_duplicate_risk.csv     # Test scenario
│
└── tests/                          # Unit tests
    └── test_pipeline.py            # Pipeline tests
```

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/FinRecon-AI.git
cd FinRecon-AI/finReconAI
```

### 2. Create a Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run FinRecon AI

```bash
streamlit run app.py
```

The application will usually open at: **http://localhost:8501**

### 5. Run Tests (Optional)

```bash
python -m unittest discover -s tests -v
```

## 🎬 Hackathon Demo Flow

For a quick demonstration of FinRecon AI capabilities:

1. **Open the Command Center / Overview** → View dashboard summary
2. **Run the "Subtotal Paid — Tax Outstanding" scenario** → Demonstrate edge case handling
3. **Show Extracted Invoice Fields** → Navigate to Documents tab
4. **Open Reconciliation Tab** → Explain the matching evidence and confidence scores
5. **Open Risk Intelligence** → Show the risk score breakdown and reasoning
6. **Save a Human Review Decision** → Demonstrate approval/rejection workflow
7. **Open Reports & Analytics** → Show audit-ready compliance outputs
8. **Ask the Copilot Questions:**
   - "Is tax still outstanding?"
   - "Which invoices have high risk?"
   - "How many matches are successful?"
9. **Demonstrate Anti-False-Positive Safeguard** → Show payment direction validation preventing incorrect matches

## 🛡️ Responsible AI Design

FinRecon AI is designed as a **decision-support system**, not an autonomous payment authority.

### Core Principles:

- ✅ **No automatic fraud claims** — All findings are advisory
- ⚠️ **Weak matches escalated** — Uncertain results require verification
- 📊 **Transparency first** — Evidence shown alongside confidence scores
- 👤 **Human authority** — Final financial decisions remain with authorized personnel
- 🔒 **Evidence-constrained** — Optional LLM output bounded by structured reconciliation data
- 🚫 **Sensitive data protection** — Financial data should not be committed to public repositories

## 🔐 Privacy & Security

For local use, financial files are processed within the application workflow only.

### Best Practices:

- ❌ Do not commit real customer invoices
- ❌ Do not commit real bank statements
- ❌ Do not commit API keys or secrets
- ❌ Do not commit `.env` or Streamlit secrets files
- ✅ Use synthetic/demo files for public examples
- ✅ Review `.gitignore` before committing

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Language** | Python 3.9+ |
| **UI Framework** | Streamlit |
| **Data Processing** | Pandas |
| **PDF Processing** | PyMuPDF |
| **Excel Support** | OpenPyXL / xlrd |
| **Matching Engine** | Similarity scoring + financial rules |
| **Risk Engine** | Explainable rule-based system |
| **Anomaly Detection** | Statistical analysis |
| **Audit Trail** | Local database layer |
| **Optional Local LLM** | Ollama |

## 🚀 Future Roadmap

- 🔍 OCR for scanned invoices and bank PDFs
- 🌍 Semantic vendor/entity resolution across different name variations
- 💱 Multi-currency reconciliation and exchange rate handling
- ⚙️ Configurable organization-specific risk policies
- 📋 Invoice-to-PO-to-payment three-way matching
- 👥 Recurring vendor behavior profiles & spending patterns
- 📈 Graph-based payment risk analysis
- 🔑 Role-based access control (RBAC)
- ☁️ Cloud deployment & enterprise connector integrations
- 🔌 REST API for ERP/accounting system integration
- 📊 Advanced reporting & business intelligence features

## 🤝 Contributing

Contributions are welcome! We appreciate your interest in improving FinRecon AI.

### How to Contribute:

1. **Fork the repository**
2. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Commit your changes:**
   ```bash
   git commit -m "Add your feature description"
   ```
4. **Push to the branch:**
   ```bash
   git push origin feature/your-feature-name
   ```
5. **Open a Pull Request**

### Guidelines:

- Please avoid submitting real or sensitive financial data
- Follow the existing code style and patterns
- Include tests for new features
- Update documentation as needed
- Reference issues in your commit messages

## ⚖️ Disclaimer

**FinRecon AI** is a prototype and decision-support project. It does **not** provide financial, accounting, legal, or fraud-investigation advice. 

Results should be reviewed by an **authorized human** before any financial action is taken. The system is designed to augment human decision-making, not replace it.

## 📄 License

This project is licensed under the terms specified in the [LICENSE](../LICENCE) file. Please review the license before using this software.

---

**Built with ❤️ for smarter financial reconciliation**

This project is released under the MIT License. See LICENSE for details.

Support the Project

If you find FinRecon AI useful:

⭐ Star the repository

🍴 Fork it

🐛 Open an issue

💡 Suggest a feature

🤝 Submit a pull request

FinRecon AI — Evidence-aware financial reconciliation with explainable risk and human control.