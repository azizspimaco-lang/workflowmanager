import importlib
import os
import tempfile
import unittest
from datetime import datetime

from fastapi.testclient import TestClient
from sqlmodel import Session


class AppSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(cls.tmpdir.name, "test_app.db")
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
        os.environ["COOKIE_SECURE"] = "0"
        os.environ["BOOTSTRAP_USER1"] = "admin"
        os.environ["BOOTSTRAP_PASS1"] = "admin123"
        import src.main as main
        cls.main = importlib.reload(main)
        cls.client = TestClient(cls.main.app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)
        cls.tmpdir.cleanup()

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertIn("ok", response.text.lower())

    def test_matching_manual_route_marks_invoice_paid(self):
        login = self.client.post(
            "/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=False,
        )
        self.assertEqual(login.status_code, 303)

        with Session(self.main.engine) as session:
            txn = self.main.BankTxn(
                date=datetime(2026, 1, 15),
                value_date=datetime(2026, 1, 16),
                label="VIR TEST FACTURE F100",
                label_norm="VIR TEST FACTURE F100",
                debit=321.0,
                credit=0.0,
                dedup_key="txn-smoke-1",
            )
            inv = self.main.Invoice(
                supplier_name="TEST FOURNISSEUR",
                invoice_no="F100",
                amount_ttc=321.0,
                amount=321.0,
                status="A_PAYER",
                dedup_key="inv-smoke-1",
            )
            session.add(txn)
            session.add(inv)
            session.commit()
            session.refresh(txn)
            session.refresh(inv)
            txn_id = txn.id
            inv_id = inv.id

        response = self.client.post(
            "/matching/manual",
            data={"banktxn_id": str(txn_id), "invoice_id": str(inv_id), "matched_amount": "321"},
            headers={"referer": "http://testserver/matching"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertIn("match_ok", response.headers.get("location", ""))

        with Session(self.main.engine) as session:
            inv = session.get(self.main.Invoice, inv_id)
            self.assertEqual(inv.status, "PAYEE")
            self.assertEqual(inv.payment_date.date().isoformat(), "2026-01-16")


if __name__ == "__main__":
    unittest.main()
