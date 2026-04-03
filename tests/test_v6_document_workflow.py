import base64
import importlib
import json
import os
import tempfile
import unittest
import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session, select


class AppV6DocumentWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(cls.tmpdir.name, "test_v6.db")
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

    def _b64(self, obj: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(obj).encode("utf-8")).decode("utf-8")

    def test_scan_bundle_commit_with_bc_and_br_sets_status_br_recu(self):
        with Session(self.main.engine) as session:
            inv = self.main.Invoice(
                supplier_name="A_COMPLETER",
                invoice_no=None,
                status="INCOMPLET",
                dedup_key=self._uniq("bundle"),
                currency="MAD",
                amount=0.0,
            )
            session.add(inv)
            session.commit()
            session.refresh(inv)
            invoice_id = inv.id

        payload = self._b64(
            {
                "invoice_id": invoice_id,
                "items": [
                    {
                        "stored": "tmp_bc.pdf",
                        "filename": "piece_bc.pdf",
                        "doc_type": "BC",
                        "ref_no": self._uniq("BC"),
                        "ref_date": "2026-03-01T00:00:00",
                        "data": {
                            "doc_type": "BC",
                            "supplier_name": "Atlas Fournitures",
                            "bc_no": self._uniq("BCREF"),
                            "bc_date": "2026-03-01",
                        },
                    },
                    {
                        "stored": "tmp_br.pdf",
                        "filename": "piece_br.pdf",
                        "doc_type": "BR",
                        "ref_no": self._uniq("BR"),
                        "ref_date": "2026-03-05T00:00:00",
                        "data": {
                            "doc_type": "BR",
                            "supplier_name": "Atlas Fournitures",
                            "br_no": self._uniq("BRREF"),
                            "br_date": "2026-03-05",
                            "service_date": "2026-03-05",
                        },
                    },
                ],
            }
        )

        response = self.client.post(
            "/factures/scan_bundle_commit",
            data={"payload": payload, "force": "1"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers.get("location"), f"/factures/{invoice_id}")

        with Session(self.main.engine) as session:
            inv = session.get(self.main.Invoice, invoice_id)
            self.assertEqual(inv.status, "BR_RECU")
            self.assertTrue(inv.bc_no)
            self.assertTrue(inv.br_no)
            docs = session.exec(select(self.main.InvoiceDocument).where(self.main.InvoiceDocument.invoice_id == invoice_id)).all()
            self.assertEqual(sorted(d.doc_type for d in docs), ["BC", "BR"])

    def test_add_docs_commit_with_bc_upgrades_incomplete_invoice_to_bc_recu(self):
        with Session(self.main.engine) as session:
            inv = self.main.Invoice(
                supplier_name="A_COMPLETER",
                invoice_no=None,
                status="INCOMPLET",
                dedup_key=self._uniq("inv"),
                currency="MAD",
                amount=0.0,
            )
            session.add(inv)
            session.commit()
            session.refresh(inv)
            invoice_id = inv.id

        bc_ref = self._uniq("BC")
        payload = self._b64(
            {
                "items": [
                    {
                        "stored": "tmp_bc_only.pdf",
                        "filename": "bc_only.pdf",
                        "doc_type": "BC",
                        "ref_no": bc_ref,
                        "ref_date": "2026-03-10T00:00:00",
                        "data": {
                            "doc_type": "BC",
                            "supplier_name": "Atlas Fournitures",
                            "bc_no": bc_ref,
                            "bc_date": "2026-03-10",
                        },
                    }
                ]
            }
        )

        response = self.client.post(
            f"/factures/{invoice_id}/add_docs_commit",
            data={"payload": payload, "force": "1"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers.get("location"), f"/factures/{invoice_id}")

        with Session(self.main.engine) as session:
            inv = session.get(self.main.Invoice, invoice_id)
            self.assertEqual(inv.status, "BC_RECU")
            self.assertEqual(inv.bc_no, bc_ref)
            docs = session.exec(select(self.main.InvoiceDocument).where(self.main.InvoiceDocument.invoice_id == invoice_id)).all()
            self.assertEqual(len(docs), 1)
            self.assertEqual(docs[0].doc_type, "BC")


if __name__ == "__main__":
    unittest.main()
