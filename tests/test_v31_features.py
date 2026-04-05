import importlib
import os
import tempfile
import unittest
from datetime import datetime

from fastapi.testclient import TestClient
from sqlmodel import Session, select


class AppV31FeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(cls.tmpdir.name, "test_v31.db")
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
        os.environ["COOKIE_SECURE"] = "0"
        os.environ["BOOTSTRAP_USER1"] = "admin"
        os.environ["BOOTSTRAP_PASS1"] = "admin123"
        import src.main as main
        cls.main = importlib.reload(main)
        cls.client = TestClient(cls.main.app)
        cls.client.__enter__()
        login = cls.client.post("/login", data={"username": "admin", "password": "admin123"}, follow_redirects=False)
        assert login.status_code == 303

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)
        cls.tmpdir.cleanup()

    def test_create_reglement_with_payment_type_and_reference(self):
        with Session(self.main.engine) as session:
            acc = self.main.CompanyBankAccount(bank_name="BOA", account_no="001122", is_active=True)
            session.add(acc)
            session.commit()
            session.refresh(acc)
            acc_id = acc.id

        response = self.client.post(
            "/reglements/create",
            data={
                "account_id": str(acc_id),
                "payment_date": "2026-03-15",
                "payment_type": "CHEQUE",
                "instrument_ref": "CHQ-7788",
                "note": "Paiement exceptionnel",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)

        with Session(self.main.engine) as session:
            batch = session.exec(select(self.main.PaymentBatch).order_by(self.main.PaymentBatch.id.desc())).first()
            self.assertIsNotNone(batch)
            self.assertEqual(batch.payment_type, "CHEQUE")
            self.assertEqual(batch.instrument_ref, "CHQ-7788")
            self.assertEqual(batch.note, "Paiement exceptionnel")

    def test_auto_qualification_qualifies_obvious_bank_fees(self):
        with Session(self.main.engine) as session:
            rub = self.main.CashflowRubrique(rubrique="Frais bancaires", nature_flux="DECAISSEMENT")
            txn = self.main.BankTxn(
                date=datetime(2026, 3, 1),
                value_date=datetime(2026, 3, 1),
                label="Commission bancaire mars",
                label_norm="COMMISSION BANCAIRE MARS",
                debit=45.0,
                credit=0.0,
                dedup_key="v31-fees-1",
                processing_status="HORS_FACTURE",
            )
            session.add(rub)
            session.add(txn)
            session.commit()
            session.refresh(txn)
            txn_id = txn.id

        response = self.client.post("/qualification/auto_apply", data={"limit": "20"}, follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertIn("auto_qualified_", response.headers.get("location", ""))

        with Session(self.main.engine) as session:
            txn = session.get(self.main.BankTxn, txn_id)
            cf = session.exec(select(self.main.CashflowActual).where(self.main.CashflowActual.banktxn_id == txn_id)).first()
            self.assertEqual(txn.processing_status, "QUALIFIEE")
            self.assertIsNotNone(cf)


if __name__ == "__main__":
    unittest.main()
