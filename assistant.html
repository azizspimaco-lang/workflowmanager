from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Optional

from sqlmodel import Session, select

from ..models import BankTxn, Invoice, InvoicePaymentMatch
from .payment_status import invoice_outstanding_amount, recompute_invoice_payment_status


NormalizeLabel = Callable[[str], str]
InvoiceAmount = Callable[[Invoice], float]


@dataclass
class MatchSuggestion:
    inv: Invoice
    score: int


def txn_amount(txn: BankTxn) -> float:
    """Retourne le montant positif d'un mouvement (débit sinon crédit)."""
    debit = float(txn.debit or 0.0)
    credit = float(txn.credit or 0.0)
    if debit > 0:
        return debit
    if credit > 0:
        return credit
    return 0.0


def candidate_invoices_for_txn(
    txn: BankTxn,
    open_invoices: Iterable[Invoice],
    invoice_amount: InvoiceAmount,
    tolerance_exact: float = 0.01,
    tolerance_loose: float = 5.0,
) -> list[Invoice]:
    txn_amt = round(txn_amount(txn), 2)
    candidates: list[Invoice] = []
    if txn_amt <= 0:
        return candidates
    for inv in open_invoices:
        inv_amt = round(invoice_amount(inv), 2)
        if inv_amt <= 0:
            continue
        gap = abs(inv_amt - txn_amt)
        if gap <= tolerance_exact or gap <= tolerance_loose:
            candidates.append(inv)
    return candidates


def score_match(
    txn: BankTxn,
    inv: Invoice,
    normalize_label: NormalizeLabel,
    invoice_amount: InvoiceAmount,
) -> int:
    """Score simple (0..100) pour proposer un match 1:1."""
    txn_amt = txn_amount(txn)
    inv_amt = float(invoice_amount(inv) or 0.0)
    if txn_amt <= 0 or inv_amt <= 0:
        return 0

    if abs(txn_amt - inv_amt) > 0.01:
        return 0
    score = 70

    txn_date = (txn.value_date or txn.date).date()
    target_date = None
    for cand in (inv.due_date_planned, inv.due_date, inv.invoice_date):
        if cand:
            target_date = cand.date()
            break
    if target_date:
        delta = abs((txn_date - target_date).days)
        if delta <= 3:
            score += 20
        elif delta <= 7:
            score += 10

    label = txn.label_norm or normalize_label(txn.label or "")
    if inv.invoice_no:
        invoice_no = normalize_label(inv.invoice_no)
        if invoice_no and invoice_no in label:
            score += 10
    if inv.supplier_name:
        supplier = normalize_label(inv.supplier_name)
        token = next((part for part in supplier.split() if len(part) >= 5), "")
        if token and token in label:
            score += 10

    return int(score)


def suggest_for_txn(
    txn: BankTxn,
    invoices: Iterable[Invoice],
    normalize_label: NormalizeLabel,
    invoice_amount: InvoiceAmount,
    limit: int = 5,
) -> list[dict]:
    suggestions: list[dict] = []
    for inv in invoices:
        if (inv.status or "").upper() in ("PAYEE", "ANNULEE"):
            continue
        score = score_match(txn, inv, normalize_label=normalize_label, invoice_amount=invoice_amount)
        if score > 0:
            suggestions.append({"inv": inv, "score": score})
    suggestions.sort(key=lambda item: item["score"], reverse=True)
    return suggestions[:limit]


def apply_invoice_payment_match(
    session: Session,
    *,
    txn: BankTxn,
    inv: Invoice,
    matched_amount: float,
    method: str,
    ensure_cashflow: Optional[Callable[[Session, InvoicePaymentMatch], None]] = None,
) -> InvoicePaymentMatch:
    """Applique un rapprochement 1:1 de façon centralisée et cohérente."""
    other_for_txn = session.exec(
        select(InvoicePaymentMatch).where(
            InvoicePaymentMatch.banktxn_id == txn.id,
            InvoicePaymentMatch.invoice_id != inv.id,
        )
    ).first()
    if other_for_txn:
        raise ValueError("txn_already_matched")

    existing_matches = session.exec(
        select(InvoicePaymentMatch).where(InvoicePaymentMatch.invoice_id == inv.id)
    ).all()

    amount = float(matched_amount or 0.0)
    if amount <= 0:
        amount = txn_amount(txn)
    if amount <= 0:
        raise ValueError("invalid_amount")

    match = session.exec(
        select(InvoicePaymentMatch).where(
            InvoicePaymentMatch.banktxn_id == txn.id,
            InvoicePaymentMatch.invoice_id == inv.id,
        )
    ).first()

    prior_amount = 0.0
    if match:
        prior_amount = float(match.matched_amount or 0.0)

    other_paid = 0.0
    for row in existing_matches:
        if match and row.id == match.id:
            continue
        try:
            other_paid += float(row.matched_amount or 0.0)
        except Exception:
            pass

    inv_total = 0.0
    try:
        inv_total = float(getattr(inv, "amount_ttc", None) or getattr(inv, "amount", 0.0) or 0.0)
    except Exception:
        inv_total = 0.0

    if inv_total > 0 and other_paid + amount > inv_total + 0.01:
        raise ValueError("amount_exceeds_invoice")

    if match:
        match.matched_amount = amount
        match.method = method
    else:
        match = InvoicePaymentMatch(
            invoice_id=inv.id,
            banktxn_id=txn.id,
            matched_amount=amount,
            method=method,
        )
        session.add(match)

    session.flush()
    recompute_invoice_payment_status(session, inv)
    session.add(inv)
    session.commit()
    session.refresh(match)

    if ensure_cashflow:
        try:
            ensure_cashflow(session, match)
        except Exception:
            session.rollback()

    return match
