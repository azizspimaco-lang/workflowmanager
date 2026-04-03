import unittest
from datetime import datetime

from sqlmodel import Session, SQLModel, create_engine, select

from src.models import BankTxn, Invoice, InvoicePaymentMatch
from src.services.matching import (
    apply_invoice_payment_match,
    candidate_invoices_for_txn,
    score_match,
    txn_amount,
)


class MatchingServiceTests(unittest.TestCase):
    def test_txn_amount_prefers_debit_then_credit(self):
        self.assertEqual(txn_amount(BankTxn(date=datetime(2026, 1, 1), label="A", debit=120.0, credit=0.0)), 120.0)
        self.assertEqual(txn_amount(BankTxn(date=datetime(2026, 1, 1), label="A", debit=0.0, credit=80.0)), 80.0)
        self.assertEqual(txn_amount(BankTxn(date=datetime(2026, 1, 1), label="A", debit=0.0, credit=0.0)), 0.0)

    def test_candidate_invoices_uses_amount_ttc_priority(self):
        txn = BankTxn(date=datetime(2026, 1, 10), label="VIR ACME", debit=118.0, credit=0.0)
        bad_amount_invoice = Invoice(
            supplier_name="ACME",
            invoice_no="F001",
            amount=100.0,
            amount_ttc=118.0,
            status="A_PAYER",
            dedup_key="inv-1",
        )
        matches = candidate_invoices_for_txn(txn, [bad_amount_invoice], invoice_amount=lambda inv: float(inv.amount_ttc or inv.amount or 0.0))
        self.assertEqual(len(matches), 1)

    def test_score_match_uses_invoice_number_and_supplier(self):
        txn = BankTxn(
            date=datetime(2026, 1, 10),
            value_date=datetime(2026, 1, 11),
            label="VIR ACME FACTURE F001",
            label_norm="VIR ACME FACTURE F001",
            debit=118.0,
            credit=0.0,
        )
        inv = Invoice(
            supplier_name="ACME SARL",
            invoice_no="F001",
            invoice_date=datetime(2026, 1, 10),
            amount_ttc=118.0,
            amount=100.0,
            status="A_PAYER",
            dedup_key="inv-2",
        )
        score = score_match(
            txn,
            inv,
            normalize_label=lambda s: s.upper(),
            invoice_amount=lambda invoice: float(invoice.amount_ttc or invoice.amount or 0.0),
        )
        self.assertGreaterEqual(score, 90)

    def test_apply_invoice_payment_match_updates_status_and_date(self):
        engine = create_engine("sqlite://")
        SQLModel.metadata.create_all(engine)

        with Session(engine) as session:
            txn = BankTxn(date=datetime(2026, 1, 10), value_date=datetime(2026, 1, 12), label="VIR", debit=250.0, credit=0.0)
            inv = Invoice(supplier_name="ACME", invoice_no="F003", amount_ttc=250.0, status="A_PAYER", dedup_key="inv-3")
            session.add(txn)
            session.add(inv)
            session.commit()
            session.refresh(txn)
            session.refresh(inv)

            match = apply_invoice_payment_match(
                session,
                txn=txn,
                inv=inv,
                matched_amount=250.0,
                method="MANUAL",
            )

            refreshed_inv = session.get(Invoice, inv.id)
            matches = session.exec(select(InvoicePaymentMatch)).all()
            self.assertEqual(match.method, "MANUAL")
            self.assertEqual(len(matches), 1)
            self.assertEqual(refreshed_inv.status, "PAYEE")
            self.assertEqual(refreshed_inv.payment_date.date().isoformat(), "2026-01-12")


if __name__ == "__main__":
    unittest.main()
