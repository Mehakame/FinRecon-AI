import unittest
from pathlib import Path

from agents.document_agent import extract_invoice_data
from agents.bank_agent import ingest_bank_statements
from agents.orchestrator import run_finrecon

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


class FinReconPipelineTests(unittest.TestCase):
    def test_invoice_breakdown(self):
        invoice = extract_invoice_data(DATA / "sample_invoice.pdf")
        self.assertEqual(invoice["vendor"], "Acme Corporation")
        self.assertAlmostEqual(invoice["subtotal"], 2500.00, places=2)
        self.assertAlmostEqual(invoice["tax_amount"], 206.25, places=2)
        self.assertAlmostEqual(invoice["total_due"], 2706.25, places=2)
        self.assertEqual(invoice["currency"], "USD")

    def test_bank_pdf_direction(self):
        result = ingest_bank_statements([DATA / "sample_bank_statement.pdf"])
        tx = result["transactions"]
        self.assertEqual(len(tx), 6)
        self.assertEqual(tx.iloc[0]["direction"], "IN")
        self.assertAlmostEqual(float(tx.iloc[0]["amount"]), 2500.00, places=2)

    def test_incoming_credit_not_false_payment(self):
        run = run_finrecon([DATA / "sample_invoice.pdf"], [DATA / "sample_bank_statement.pdf"])
        self.assertTrue(run["success"])
        self.assertEqual(run["reconciliation"][0]["status"], "MISSING_PAYMENT")

    def test_tax_outstanding(self):
        run = run_finrecon([DATA / "sample_invoice.pdf"], [DATA / "demo_tax_outstanding.csv"])
        self.assertTrue(run["success"])
        rec = run["reconciliation"][0]
        self.assertEqual(rec["status"], "SUBTOTAL_PAID_TAX_OUTSTANDING")
        self.assertAlmostEqual(rec["outstanding"], 206.25, places=2)

    def test_full_match(self):
        run = run_finrecon([DATA / "sample_invoice.pdf"], [DATA / "demo_full_payment.csv"])
        self.assertTrue(run["success"])
        rec = run["reconciliation"][0]
        self.assertEqual(rec["status"], "MATCH")
        self.assertAlmostEqual(rec["outstanding"], 0.0, places=2)
        self.assertEqual(run["risk"][0]["risk_level"], "LOW")


if __name__ == "__main__":
    unittest.main()
