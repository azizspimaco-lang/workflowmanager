import importlib
import os
import tempfile
import unittest
import uuid
from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select

from src.models import BankTxn, Invoice, InvoicePaymentMatch
from src.services.matching import apply_invoice_payment_match


class PartialPaymentServiceTests(unittest.TestCase):
    def test_partial_then_full_payment_updates_status_and_amount_paid(self):
        engine = create_engine("sqlite://")
        SQLModel.metadata.create_all(engine)

        with Session(engine) as session:
            inv = Invoice(
                supplier_name="ACME",
                invoice_no="FAC-PART-1",
                amount_ttc=300.0,
                amount=300.0,
                status="A_PAYER",
                dedup_key="inv-part-1",
            )
            txn1 = BankTxn(date=datetime(2026, 2, 1), value_date=datetime(2026, 2, 2), label="VIR 1", debit=100.0, credit=0.0)
            txn2 = BankTxn(date=datetime(2026, 2, 10), value_date=datetime(2026, 2, 11), label="VIR 2", debit=200.0, credit=0.0)
            session.add(inv)
            session.add(txn1)
            session.add(txn2)
            session.commit()
            session.refresh(inv)
            session.refresh(txn1)
            session.refresh(txn2)

            apply_invoice_payment_match(session, txn=txn1, inv=inv, matched_amount=100.0, method="MANUAL")
            inv1 = session.get(Invoice, inv.id)
            self.assertEqual(inv1.status, "PARTIEL")
            self.assertEqual(float(inv1.amount_paid or 0.0), 100.0)
            self.assertEqual(inv1.payment_date.date().isoformat(), "2026-02-02")

            apply_invoice_payment_match(session, txn=txn2, inv=inv, matched_amount=200.0, method="MANUAL")
            inv2 = session.get(Invoice, inv.id)
            self.assertEqual(inv2.status, "PAYEE")
            self.assertEqual(float(inv2.amount_paid or 0.0), 300.0)
            self.assertEqual(inv2.payment_date.date().isoformat(), "2026-02-11")
            matches = session.exec(select(InvoicePaymentMatch).where(InvoicePaymentMatch.invoice_id == inv.id)).all()
            self.assertEqual(len(matches), 2)

    def test_partial_overpayment_is_blocked(self):
        engine = create_engine("sqlite://")
        SQLModel.metadata.create_all(engine)

        with Session(engine) as session:
            inv = Invoice(supplier_name="ACME", invoice_no="FAC-PART-2", amount_ttc=300.0, status="A_PAYER", dedup_key="inv-part-2")
            txn1 = BankTxn(date=datetime(2026, 2, 1), value_date=datetime(2026, 2, 2), label="VIR 1", debit=250.0, credit=0.0)
            txn2 = BankTxn(date=datetime(2026, 2, 10), value_date=datetime(2026, 2, 11), label="VIR 2", debit=100.0, credit=0.0)
            session.add(inv)
            session.add(txn1)
            session.add(txn2)
            session.commit()
            session.refresh(inv)
            session.refresh(txn1)
            session.refresh(txn2)

            apply_invoice_payment_match(session, txn=txn1, inv=inv, matched_amount=250.0, method="MANUAL")
            with self.assertRaises(ValueError):
                apply_invoice_payment_match(session, txn=txn2, inv=inv, matched_amount=100.0, method="MANUAL")


class AppV5PartialAndPlanningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(cls.tmpdir.name, "test_v5.db")
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
        os.environ["COOKIE_SECURE"] = "0"
        os.environ["BOOTSTRAP_USER1"] = "admin"
        os.environ["BOOTSTRAP_PASS1"] = "admin123"
        import src.main as main
        cls.main = importlib.reload(main)
        cls.client = TestClient(cls.main.app)
        cls.client.__enter__()
        login = cls.client.post(
            "/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=False,
        )
        assert login.status_code == 303

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)
        cls.tmpdir.cleanup()

    def _uniq(self, prefix: str) -> str:
        return f"{prefix}-{uuid.uuid4().hex[:8]}"

    def test_auto_apply_can_finish_partially_paid_invoice_using_outstanding_amount(self):
        with Session(self.main.engine) as session:
            inv = self.main.Invoice(
                supplier_name="ACME SARL",
                invoice_no="F-PART-AUTO",
                amount_ttc=300.0,
                amount=300.0,
                status="PARTIEL",
                amount_paid=100.0,
                dedup_key=self._uniq("inv"),
                invoice_date=datetime(2026, 2, 1),
                due_date=datetime(2026, 2, 20),
            )
            txn_old = self.main.BankTxn(
                date=datetime(2026, 2, 3),
                value_date=datetime(2026, 2, 4),
                label="VIR ACME ACOMPTE",
                label_norm="VIR ACME ACOMPTE",
                debit=100.0,
                credit=0.0,
                dedup_key=self._uniq("txn"),
            )
            txn_new = self.main.BankTxn(
                date=datetime(2026, 2, 20),
                value_date=datetime(2026, 2, 20),
                label="VIR ACME FACTURE F-PART-AUTO",
                label_norm="VIR ACME FACTURE F-PART-AUTO",
                debit=200.0,
                credit=0.0,
                dedup_key=self._uniq("txn"),
            )
            session.add(inv)
            session.add(txn_old)
            session.add(txn_new)
            session.commit()
            session.refresh(inv)
            session.refresh(txn_old)
            session.refresh(txn_new)
            session.add(self.main.InvoicePaymentMatch(invoice_id=inv.id, banktxn_id=txn_old.id, matched_amount=100.0, method="MANUAL"))
            session.commit()
            inv_id = inv.id
            txn_new_id = txn_new.id

        response = self.client.post("/matching/auto_apply", data={"limit": "5"}, follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertIn("auto_applied_", response.headers.get("location", ""))

        with Session(self.main.engine) as session:
            inv = session.get(self.main.Invoice, inv_id)
            matches = session.exec(select(self.main.InvoicePaymentMatch).where(self.main.InvoicePaymentMatch.invoice_id == inv_id)).all()
            self.assertEqual(len(matches), 2)
            self.assertEqual(inv.status, "PAYEE")
            self.assertEqual(float(inv.amount_paid or 0.0), 300.0)
            self.assertTrue(any(m.banktxn_id == txn_new_id and float(m.matched_amount or 0.0) == 200.0 for m in matches))

    def test_planning_page_shows_outstanding_amount_for_partial_invoice(self):
        today = date.today()
        with Session(self.main.engine) as session:
            acc = self.main.CompanyBankAccount(
                bank_name="BANK TEST",
                account_no=self._uniq("ACC"),
                iban=None,
                swift=None,
                is_active=True,
            )
            inv = self.main.Invoice(
                supplier_name="FOURNISSEUR PARTIEL",
                invoice_no="FAC-PLAN-PART",
                amount_ttc=500.0,
                amount=500.0,
                amount_paid=200.0,
                status="PARTIEL",
                dedup_key=self._uniq("inv"),
                legal_due_date=datetime.combine(today + timedelta(days=5), datetime.min.time()),
            )
            session.add(acc)
            session.add(inv)
            session.commit()

        response = self.client.get("/planning")
        self.assertEqual(response.status_code, 200)
        self.assertIn("FAC-PLAN-PART", response.text)
        self.assertIn("300.00 MAD", response.text)
        self.assertIn("Payé 200.00 / Total 500.00", response.text)


if __name__ == "__main__":
    unittest.main()
