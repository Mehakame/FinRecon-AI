from pathlib import Path
import textwrap

import pandas as pd
import streamlit as st

from agents.orchestrator import run_finrecon
from agents.report_agent import reconciliation_frame, risk_frame, currency_summary, build_export_zip, status_label
from agents.copilot_agent import ask_finrecon
from database.database import init_db, save_review, get_reviews

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

st.set_page_config(page_title="FinRecon AI", page_icon="💠", layout="wide", initial_sidebar_state="expanded")


def html(value):
    st.markdown(textwrap.dedent(value).strip(), unsafe_allow_html=True)


def inject_css():
    html("""
    <style>
      .block-container{max-width:1500px;padding-top:1.35rem;padding-bottom:3rem}
      .hero{background:linear-gradient(135deg,#eef4ff,#fff 62%);border:1px solid #dbe6fb;border-radius:24px;padding:1.7rem 1.9rem;box-shadow:0 10px 30px rgba(42,76,130,.07);margin-bottom:1.2rem}
      .hero-kicker{display:inline-block;padding:.32rem .65rem;border-radius:999px;background:#e3edff;color:#2457c4;font-size:.76rem;font-weight:800;letter-spacing:.04em;text-transform:uppercase}
      .hero h1{margin:.55rem 0 .3rem;color:#14213d;font-size:2.35rem}.hero p{color:#697a95;max-width:900px;line-height:1.6;margin:0}
      .kpi{background:#fff;border:1px solid #dfe7f1;border-radius:18px;padding:1rem;box-shadow:0 5px 15px rgba(28,48,82,.05);min-height:112px}.kpi-label{color:#73819a;font-size:.82rem;font-weight:700}.kpi-value{font-size:1.85rem;font-weight:900;color:#17233b;margin-top:.25rem}.kpi-sub{color:#7e8ca4;font-size:.76rem;margin-top:.2rem}
      .agent-card{background:#fff;border:1px solid #e0e7f0;border-radius:16px;padding:.95rem;min-height:120px}.agent-card b{color:#17233b}.agent-card p{color:#74829a;font-size:.82rem;margin:.25rem 0 0}.agent-ok{color:#16875a;font-size:.78rem;font-weight:800}.agent-fail{color:#c94248;font-size:.78rem;font-weight:800}
      .risk-low{border-left:7px solid #1fa66a}.risk-medium{border-left:7px solid #e59b18}.risk-high,.risk-critical{border-left:7px solid #e14b50}.risk-box{background:#fff;border-top:1px solid #e0e7f0;border-right:1px solid #e0e7f0;border-bottom:1px solid #e0e7f0;border-radius:16px;padding:1rem 1.15rem;margin:.65rem 0}
      .decision{display:inline-block;padding:.3rem .6rem;border-radius:999px;background:#eef3ff;color:#275ac6;font-weight:800;font-size:.75rem}
      div[data-testid="stMetric"]{background:#fff;border:1px solid #e0e7f0;border-radius:16px;padding:.8rem 1rem}
      [data-testid="stExpander"]{background:#fff;border:1px solid #e0e7f0;border-radius:14px}
      [data-testid="stFileUploaderDropzone"]{background:#f8fbff;border:1.5px dashed #9ab9e5;border-radius:15px}
      .footer{text-align:center;color:#8190a8;border-top:1px solid #e6ebf2;margin-top:2rem;padding-top:1rem;font-size:.83rem}
    </style>
    """)


def init_state():
    st.session_state.setdefault("run", None)
    st.session_state.setdefault("last_mode", "uploads")
    init_db()


def money(value, currency=None):
    if value is None or pd.isna(value):
        return "—"
    symbol = {"INR":"₹","USD":"$","EUR":"€","GBP":"£"}.get(currency or "", "")
    return f"{symbol}{float(value):,.2f}"


def primary_currency(run):
    currencies = {x.get("currency") for x in run.get("invoices", []) if x.get("currency")}
    return next(iter(currencies)) if len(currencies) == 1 else None


def sidebar():
    with st.sidebar:
        st.markdown("## 💠 FinRecon AI")
        st.caption("Agentic Financial Reconciliation & Risk Intelligence")
        page = st.radio("Workspace", ["Command Center", "Documents", "Reconciliation", "Risk Intelligence", "Reports", "Copilot", "Audit Log"], label_visibility="collapsed")
        st.divider()
        run = st.session_state.run
        if run and run.get("success"):
            s = run["summary"]
            st.success(f"Analysis ready · {s['invoice_count']} invoice(s)")
            st.caption(f"Match rate {s['match_rate']}% · Max risk {s['max_risk']}/100")
        else:
            st.info("Upload files or run a demo scenario.")
        if st.button("Clear current analysis", use_container_width=True):
            st.session_state.run = None
            st.rerun()
        st.caption("Free/local-first. Human review remains the final decision authority.")
    return page


def run_sources(invoice_sources, bank_sources, mode):
    with st.spinner("FinRecon agents are working..."):
        result = run_finrecon(invoice_sources, bank_sources)
    st.session_state.run = result
    st.session_state.last_mode = mode
    if not result.get("success"):
        st.error(result.get("error", "Analysis failed"))
    else:
        st.success("Multi-agent analysis completed.")
        st.rerun()


def upload_panel():
    st.markdown("### Start an analysis")
    tabs = st.tabs(["Upload your files", "Hackathon demo scenarios"])
    with tabs[0]:
        c1, c2 = st.columns(2)
        with c1:
            invoices = st.file_uploader("Invoice PDFs", type=["pdf"], accept_multiple_files=True, key="invoice_uploader")
        with c2:
            banks = st.file_uploader("Bank statements", type=["csv","xlsx","xls","pdf"], accept_multiple_files=True, key="bank_uploader")
        st.caption("Multiple invoices + multiple banks supported. Text-based bank PDFs are supported; CSV/XLSX is recommended for complex statements.")
        if st.button("🚀 Run FinRecon Agents", type="primary", use_container_width=True):
            if not invoices or not banks:
                st.warning("Upload at least one invoice and one bank statement.")
            else:
                run_sources(invoices, banks, "uploads")
    with tabs[1]:
        scenario = st.selectbox("Scenario", ["No outgoing payment found", "Subtotal paid — tax outstanding", "Full payment matched"])
        descriptions = {
            "No outgoing payment found": "Uses the bundled bank PDF. It contains an incoming $2,500 credit, so FinRecon should NOT falsely treat it as payment.",
            "Subtotal paid — tax outstanding": "Finds a $2,500 outgoing payment against a $2,706.25 invoice and identifies $206.25 outstanding.",
            "Full payment matched": "Finds the exact $2,706.25 outgoing payment and auto-clears the low-risk case.",
        }
        st.info(descriptions[scenario])
        if st.button("▶ Run selected demo", use_container_width=True):
            invoice = DATA_DIR / "sample_invoice.pdf"
            bank = {
                "No outgoing payment found": DATA_DIR / "sample_bank_statement.pdf",
                "Subtotal paid — tax outstanding": DATA_DIR / "demo_tax_outstanding.csv",
                "Full payment matched": DATA_DIR / "demo_full_payment.csv",
            }[scenario]
            run_sources([invoice], [bank], f"demo:{scenario}")


def command_center():
    html("""
    <div class="hero"><span class="hero-kicker">Multi-Agent Finance AI</span><h1>FinRecon AI Command Center</h1><p>Turn invoices and bank statements into evidence-backed reconciliation decisions. FinRecon coordinates document intelligence, bank normalization, payment matching, anomaly detection, explainable risk scoring and human review — without requiring a paid API.</p></div>
    """)
    run = st.session_state.run
    if run and run.get("success"):
        s = run["summary"]
        currency = primary_currency(run)
        rec = reconciliation_frame(run["reconciliation"])
        outstanding = rec["Outstanding"].fillna(0).sum() if not rec.empty else 0
        cards = [
            (s["invoice_count"], "Invoices", "Documents processed"),
            (s["transaction_count"], "Transactions", "Across all bank sources"),
            (f"{s['match_rate']}%", "Full match rate", f"{s['matched_count']} fully matched"),
            (money(outstanding, currency), "Outstanding", "Requires follow-up"),
            (s["duplicate_rows"], "Duplicate rows", "Potential repeat payments"),
            (f"{s['max_risk']}/100", "Max risk", f"{s['high_critical_cases']} high/critical"),
        ]
        cols = st.columns(6)
        for col, (value, label, sub) in zip(cols, cards):
            with col:
                html(f'<div class="kpi"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div><div class="kpi-sub">{sub}</div></div>')

        st.markdown("### Agent decision trace")
        cols = st.columns(len(run["agent_trace"]))
        for col, agent in zip(cols, run["agent_trace"]):
            with col:
                status_cls = "agent-ok" if agent["status"] == "complete" else "agent-fail"
                html(f'<div class="agent-card"><div class="{status_cls}">● {agent["status"].upper()}</div><b>{agent["agent"]}</b><p>{agent["detail"]}<br>{agent["duration_ms"]} ms</p></div>')

        st.markdown("### Priority cases")
        riskdf = risk_frame(run["risk"]).sort_values("Risk score", ascending=False)
        st.dataframe(riskdf.head(8), use_container_width=True, hide_index=True)
        if run.get("bank_errors"):
            st.warning(f"Some bank files were skipped: {run['bank_errors']}")
    upload_panel()


def documents_page():
    run = st.session_state.run
    st.title("Document Intelligence")
    if not run or not run.get("success"):
        st.info("Run an analysis first.")
        return
    inv_rows = []
    for inv in run["invoices"]:
        inv_rows.append({
            "File": inv.get("file"), "Invoice no.": inv.get("invoice_number"), "Vendor": inv.get("vendor"), "Invoice date": inv.get("date"), "Due date": inv.get("due_date"),
            "Currency": inv.get("currency"), "Subtotal": inv.get("subtotal"), "Tax rate %": inv.get("tax_rate"), "Tax": inv.get("tax_amount"), "Total due": inv.get("total_due"),
            "Extraction confidence": inv.get("document_confidence"), "Warnings": " | ".join(inv.get("warnings", [])),
        })
    st.dataframe(pd.DataFrame(inv_rows), use_container_width=True, hide_index=True)
    for inv in run["invoices"]:
        if inv.get("line_items"):
            with st.expander(f"Line items · {inv.get('file')}"):
                st.dataframe(pd.DataFrame(inv["line_items"]), use_container_width=True, hide_index=True)
    st.markdown("### Bank normalization map")
    st.dataframe(pd.DataFrame(run["mappings"]), use_container_width=True, hide_index=True)
    with st.expander("Normalized transactions"):
        st.dataframe(run["transactions"], use_container_width=True, hide_index=True)


def reconciliation_page():
    run = st.session_state.run
    st.title("Evidence-Aware Reconciliation")
    if not run or not run.get("success"):
        st.info("Run an analysis first.")
        return
    df = reconciliation_frame(run["reconciliation"])
    statuses = df["Status"].dropna().unique().tolist()
    selected = st.multiselect("Status filter", statuses, default=statuses)
    query = st.text_input("Search vendor / invoice / bank transaction", placeholder="e.g. Acme")
    view = df[df["Status"].isin(selected)].copy()
    if query:
        mask = view.astype(str).apply(lambda col: col.str.contains(query, case=False, na=False)).any(axis=1)
        view = view[mask]
    st.dataframe(view, use_container_width=True, hide_index=True)
    selected_invoice = st.selectbox("Inspect evidence", df["Invoice"].tolist())
    idx = df.index[df["Invoice"] == selected_invoice][0]
    rec = run["reconciliation"][idx]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Confidence", f"{rec.get('confidence',0):.1f}%")
    c2.metric("Amount similarity", f"{rec.get('amount_similarity',0):.1f}%")
    c3.metric("Vendor similarity", f"{rec.get('vendor_similarity',0):.1f}%")
    c4.metric("Date similarity", f"{rec.get('date_similarity',0):.1f}%")
    st.info(rec.get("evidence") or rec.get("message") or "No additional evidence")
    if rec.get("top_candidates"):
        with st.expander("Top candidate transactions"):
            st.dataframe(pd.DataFrame(rec["top_candidates"]), use_container_width=True, hide_index=True)


def risk_page():
    run = st.session_state.run
    st.title("Explainable Risk Intelligence")
    if not run or not run.get("success"):
        st.info("Run an analysis first.")
        return
    df = risk_frame(run["risk"])
    st.dataframe(df, use_container_width=True, hide_index=True)
    selected = st.selectbox("Review case", df["Invoice"].tolist())
    idx = df.index[df["Invoice"] == selected][0]
    risk = run["risk"][idx]
    explanation = run["explanations"][idx]
    level = risk["risk_level"]
    html(f'<div class="risk-box risk-{level.lower()}"><span class="decision">{risk["decision"]}</span><h2>{risk["risk_score"]}/100 · {level} RISK</h2><p>{explanation["explanation"]}</p><b>Recommended action:</b> {risk["recommended_action"]}</div>')
    st.progress(risk["risk_score"] / 100)
    st.markdown("#### Risk score breakdown")
    comp = pd.DataFrame(risk["components"])
    st.dataframe(comp, use_container_width=True, hide_index=True)

    with st.form("review_form"):
        decision = st.radio("Human decision", ["Approve", "Request verification", "Reject"], horizontal=True)
        note = st.text_area("Reviewer note", placeholder="What did you verify?")
        submitted = st.form_submit_button("Save audit decision", type="primary")
        if submitted:
            save_review(selected, decision, note or "No note provided", risk["risk_score"], risk["risk_level"])
            st.success("Review saved to the audit database.")

    anomaly = run["anomaly_analysis"]
    c1, c2 = st.columns(2)
    with c1:
        with st.expander(f"Potential duplicate rows ({anomaly['duplicate_count']})"):
            st.dataframe(anomaly["duplicates"], use_container_width=True, hide_index=True)
    with c2:
        with st.expander(f"Amount anomalies ({anomaly['anomaly_count']})"):
            st.dataframe(anomaly["anomalies"], use_container_width=True, hide_index=True)


def reports_page():
    run = st.session_state.run
    st.title("Executive Reports")
    if not run or not run.get("success"):
        st.info("Run an analysis first.")
        return
    rec = reconciliation_frame(run["reconciliation"])
    risk = risk_frame(run["risk"])
    tx = run["transactions"].copy()
    summary = run["summary"]
    tabs = st.tabs(["Executive", "Cash Flow", "Risk & Exceptions", "Bank-wise", "Vendor-wise", "Export"])
    with tabs[0]:
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Invoices", summary["invoice_count"])
        c2.metric("Match rate", f"{summary['match_rate']}%")
        c3.metric("High/Critical", summary["high_critical_cases"])
        c4.metric("Max risk", f"{summary['max_risk']}/100")
        st.markdown("#### Currency summary")
        st.dataframe(currency_summary(run["invoices"], run["reconciliation"]), use_container_width=True, hide_index=True)
        st.markdown("#### Reconciliation status")
        st.bar_chart(rec["Status"].value_counts())
    with tabs[1]:
        money_in = tx.loc[tx["amount"] > 0, "amount"].sum()
        money_out = tx.loc[tx["amount"] < 0, "amount"].abs().sum()
        a,b,c = st.columns(3); a.metric("Money In", f"{money_in:,.2f}"); b.metric("Money Out", f"{money_out:,.2f}"); c.metric("Net", f"{money_in-money_out:,.2f}")
        dated = tx.dropna(subset=["date"]).copy()
        if not dated.empty:
            daily = dated.assign(Money_In=dated["amount"].where(dated["amount"]>0,0), Money_Out=dated["amount"].where(dated["amount"]<0,0).abs()).groupby("date")[["Money_In","Money_Out"]].sum().sort_index()
            st.line_chart(daily)
    with tabs[2]:
        st.bar_chart(risk["Risk level"].value_counts())
        st.dataframe(risk.sort_values("Risk score", ascending=False), use_container_width=True, hide_index=True)
    with tabs[3]:
        rows=[]
        for name, group in tx.groupby("source_bank"):
            rows.append({"Bank":name,"Transactions":len(group),"Money In":group.loc[group.amount>0,"amount"].sum(),"Money Out":group.loc[group.amount<0,"amount"].abs().sum()})
        bankdf=pd.DataFrame(rows)
        st.dataframe(bankdf,use_container_width=True,hide_index=True)
        if not bankdf.empty: st.bar_chart(bankdf.set_index("Bank")[["Money In","Money Out"]])
    with tabs[4]:
        vendor = rec.groupby("Vendor", dropna=False).agg(Invoices=("Invoice","count"), Total_Due=("Total due","sum"), Outstanding=("Outstanding","sum"), Avg_Confidence=("Confidence","mean")).sort_values("Outstanding", ascending=False)
        st.dataframe(vendor, use_container_width=True)
        if not vendor.empty: st.bar_chart(vendor["Outstanding"].head(10))
    with tabs[5]:
        audit = get_reviews()
        package = build_export_zip(run, audit)
        st.download_button("⬇ Download complete audit package (.zip)", package, file_name="finrecon_audit_package.zip", mime="application/zip", use_container_width=True)
        st.download_button("Download reconciliation CSV", rec.to_csv(index=False).encode(), file_name="reconciliation.csv", mime="text/csv", use_container_width=True)
        st.download_button("Download risk CSV", risk.to_csv(index=False).encode(), file_name="risk_report.csv", mime="text/csv", use_container_width=True)


def copilot_page():
    run = st.session_state.run
    st.title("FinRecon Copilot")
    if not run or not run.get("success"):
        st.info("Run an analysis first.")
        return
    use_ollama = st.toggle("Use local Ollama AI", value=False, help="Optional and free. If Ollama is unavailable, FinRecon automatically uses deterministic evidence mode.")
    model = st.text_input("Ollama model", value="llama3.2:3b", disabled=not use_ollama)
    suggestions = ["Why is the highest-risk invoice flagged?", "How much is outstanding?", "Any duplicate payments?", "Is tax still outstanding?", "How many invoices matched?"]
    st.caption("Try: " + " · ".join(suggestions))
    q = st.text_input("Ask FinRecon", placeholder="Why is this transaction risky?")
    if q:
        answer = ask_finrecon(q, run, use_ollama=use_ollama, model=model)
        st.info(answer["answer"])
        st.caption(f"Response mode: {answer['mode']}")


def audit_page():
    st.title("Human Review Audit Log")
    reviews = get_reviews()
    if reviews.empty:
        st.info("No review decisions saved yet.")
    else:
        st.dataframe(reviews, use_container_width=True, hide_index=True)
        st.download_button("Download audit log", reviews.to_csv(index=False).encode(), file_name="audit_log.csv", mime="text/csv")


def main():
    inject_css(); init_state(); page = sidebar()
    pages = {"Command Center":command_center,"Documents":documents_page,"Reconciliation":reconciliation_page,"Risk Intelligence":risk_page,"Reports":reports_page,"Copilot":copilot_page,"Audit Log":audit_page}
    pages[page]()
    html('<div class="footer">FinRecon AI · Evidence-aware multi-agent reconciliation · Explainable risk · Human-in-the-loop</div>')

if __name__ == "__main__":
    main()
