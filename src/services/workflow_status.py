from __future__ import annotations

from sqlmodel import Session, select

from ..models import Invoice, InvoiceDocument


WORKFLOW_ONLY_STATUSES = {"INCOMPLET", "BC_RECU", "BR_RECU"}
PAYMENT_STATUSES = {"A_PAYER", "PARTIEL", "PAYEE"}
PRESERVED_STATUSES = {"ANNULEE", "LITIGE"}


def _has_doc_type(session: Session, inv: Invoice, doc_type: str) -> bool:
    if not getattr(inv, "id", None):
        return False
    row = session.exec(
        select(InvoiceDocument.id).where(
            InvoiceDocument.invoice_id == inv.id,
            InvoiceDocument.doc_type == doc_type,
        )
    ).first()
    return row is not None


def resolve_workflow_status(session: Session, inv: Invoice) -> str:
    """Détermine le statut documentaire / achat de la facture.

    Ne gère pas les statuts de paiement déjà calculés (A_PAYER/PARTIEL/PAYEE).
    Cette fonction est utile surtout pour les dossiers BC/BR sans facture.
    """
    current = (getattr(inv, "status", "") or "").upper()
    if current in PRESERVED_STATUSES:
        return current

    has_invoice = bool(getattr(inv, "invoice_no", None)) or _has_doc_type(session, inv, "FACTURE")
    has_br = bool(getattr(inv, "br_no", None)) or _has_doc_type(session, inv, "BR")
    has_bc = bool(getattr(inv, "bc_no", None)) or _has_doc_type(session, inv, "BC")

    if has_invoice:
        if current in PAYMENT_STATUSES:
            return current
        return "A_PAYER"
    if has_br:
        return "BR_RECU"
    if has_bc:
        return "BC_RECU"
    return "INCOMPLET"


def apply_workflow_status(session: Session, inv: Invoice) -> Invoice:
    inv.status = resolve_workflow_status(session, inv)
    return inv
