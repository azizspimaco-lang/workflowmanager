import importlib
import io
import os
import tempfile
import unittest
import uuid
from datetime import datetime

from fastapi.testclient import TestClient
from sqlmodel import Session, select


class AppRegressionV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(cls.tmpdir.name, "test_v3.db")
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

    def _create_account(self):
        with Session(self.main.engine) as session:
            acc = self.main.CompanyBankAccount(
                bank_name=self._uniq("BANK"),
                account_no=self._uniq("ACC"),
                iban=None,
                swift=None,
                is_active=True,
            )
            session.add(acc)
            session.commit()
            session.refresh(acc)
            return acc.id, acc.bank_name, acc.account_no

    def _create_txn(self, **kwargs):
        with Session(self.main.engine) as session:
            txn = self.main.BankTxn(
                date=kwargs.get("date", datetime(2026, 1, 15)),
                value_date=kwargs.get("value_date", datetime(2026, 1, 16)),
                label=kwargs.get("label", self._uniq("VIR TEST")),
                label_norm=kwargs.get("label_norm", kwargs.get("label", "") or self._uniq("VIR TEST")),
                debit=kwargs.get("debit", 100.0),
                credit=kwargs.get("credit", 0.0),
                dedup_key=kwargs.get("dedup_key", self._uniq("txn")),
                bank_name=kwargs.get("bank_name"),
                account_no=kwargs.get("account_no"),
                currency=kwargs.get("currency", "MAD"),
            )
            session.add(txn)
            session.commit()
            session.refresh(txn)
            return txn.id

    def _create_invoice(self, **kwargs):
        with Session(self.main.engine) as session:
            inv = self.main.Invoice(
                supplier_name=kwargs.get("supplier_name", self._uniq("FOURNISSEUR")),
                invoice_no=kwargs.get("invoice_no", self._uniq("FAC")),
                amount_ttc=kwargs.get("amount_ttc", 100.0),
                amount=kwargs.get("amount", kwargs.get("amount_ttc", 100.0)),
                status=kwargs.get("status", "A_PAYER"),
                dedup_key=kwargs.get("dedup_key", self._uniq("inv")),
                invoice_date=kwargs.get("invoice_date"),
                due_date=kwargs.get("due_date"),
            )
            session.add(inv)
            session.commit()
            session.refresh(inv)
            return inv.id

    def test_manual_matching_without_invoice_id_redirects_instead_of_422(self):
        txn_id = self._create_txn(debit=150.0)
        response = self.client.post(
            "/matching/manual",
            data={"banktxn_id": str(txn_id)},
            headers={"referer": "http://testserver/matching"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertIn("missing_invoice", response.headers.get("location", ""))

    def test_delete_selected_removes_multiple_unmatched_rows(self):
        txn1 = self._create_txn(label=self._uniq("FRAIS TENUE"), debit=10.0)
        txn2 = self._create_txn(label=self._uniq("COMMISSION"), debit=20.0)

        response = self.client.post(
            "/releves/delete-selected",
            content=f"txn_ids={txn1}&txn_ids={txn2}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertIn("msg=delete_ok", response.headers.get("location", ""))

        with Session(self.main.engine) as session:
            self.assertIsNone(session.get(self.main.BankTxn, txn1))
            self.assertIsNone(session.get(self.main.BankTxn, txn2))

    def test_auto_apply_matches_high_confidence_pair(self):
        txn_id = self._create_txn(
            label="VIR ACME FACTURE F900",
            label_norm="VIR ACME FACTURE F900",
            debit=118.0,
            value_date=datetime(2026, 1, 20),
        )
        inv_id = self._create_invoice(
            supplier_name="ACME SARL",
            invoice_no="F900",
            amount_ttc=118.0,
            amount=100.0,
            invoice_date=datetime(2026, 1, 19),
            due_date=datetime(2026, 1, 20),
        )

        response = self.client.post(
            "/matching/auto_apply",
            data={"limit": "not-a-number"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertIn("auto_applied_", response.headers.get("location", ""))

        with Session(self.main.engine) as session:
            inv = session.get(self.main.Invoice, inv_id)
            matches = session.exec(
                select(self.main.InvoicePaymentMatch).where(
                    self.main.InvoicePaymentMatch.invoice_id == inv_id,
                    self.main.InvoicePaymentMatch.banktxn_id == txn_id,
                )
            ).all()
            self.assertEqual(len(matches), 1)
            self.assertEqual(inv.status, "PAYEE")
            self.assertEqual(inv.payment_date.date().isoformat(), "2026-01-20")

    def test_releves_import_deduplicates_same_file(self):
        account_id, bank_name, account_no = self._create_account()
        csv_content = (
            "Date;Date valeur;Libellé;Débit;Crédit;Solde\n"
            "2026-02-01;2026-02-02;VIR FOURNISSEUR A;1500,00;;10000,00\n"
            "2026-02-03;2026-02-03;COMMISSION BANCAIRE;12,50;;9987,50\n"
        ).encode("utf-8")

        for _ in range(2):
            response = self.client.post(
                "/releves/import",
                data={"company_bank_account_id": str(account_id), "currency": "MAD"},
                files={"file": ("releve.csv", io.BytesIO(csv_content), "text/csv")},
                follow_redirects=False,
            )
            self.assertEqual(response.status_code, 303)
            self.assertIn("msg=import_ok", response.headers.get("location", ""))

        with Session(self.main.engine) as session:
            rows = session.exec(
                select(self.main.BankTxn).where(
                    self.main.BankTxn.bank_name == bank_name,
                    self.main.BankTxn.account_no == account_no,
                )
            ).all()
            self.assertEqual(len(rows), 2)


if __name__ == "__main__":
    unittest.main()
