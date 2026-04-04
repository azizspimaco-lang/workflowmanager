from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from ..models import Invoice, InvoicePaymentMatch, BankTxn


def invoice_total_amount(inv: Invoice) -> float:
    for cand in (getattr(inv, 'amount_ttc', None), getattr(inv, 'amount', None)):
        try:
            if cand is not None:
                return float(cand or 0.0)
        except Exception:
            pass
    return 0.0


def invoice_paid_amount(session: Session, inv: Invoice) -> float:
    rows = session.exec(
        select(InvoicePaymentMatch).where(InvoicePaymentMatch.invoice_id == inv.id)
    ).all()
    total = 0.0
    for row in rows:
        try:
            total += float(row.matched_amount or 0.0)
        except Exception:
            pass
    if total <= 0.0001:
        try:
            total = float(getattr(inv, "amount_paid", 0.0) or 0.0)
        except Exception:
            total = 0.0
    return round(total, 2)


def invoice_outstanding_amount(session: Session, inv: Invoice) -> float:
    total = invoice_total_amount(inv)
    paid = max(0.0, invoice_paid_amount(session, inv))
    return round(max(0.0, total - paid), 2)


def recompute_invoice_payment_status(session: Session, inv: Invoice) -> Invoice:
    total = invoice_total_amount(inv)
    paid = invoice_paid_amount(session, inv)
    inv.amount_paid = paid

    latest_dt: Optional[object] = None
    rows = session.exec(
        select(InvoicePaymentMatch).where(InvoicePaymentMatch.invoice_id == inv.id)
    ).all()
    for row in rows:
        txn = session.get(BankTxn, row.banktxn_id)
        if not txn:
            continue
        dt = txn.value_date or txn.date
        if latest_dt is None or (dt and dt > latest_dt):
            latest_dt = dt
    inv.payment_date = latest_dt

    current_status = (getattr(inv, 'status', '') or '').upper()
    if current_status == 'ANNULEE':
        return inv

    if total <= 0:
        if paid > 0:
            inv.status = 'PAYEE'
        elif current_status not in ('LITIGE',):
            inv.status = 'A_PAYER'
        return inv

    if paid <= 0.0001:
        if current_status not in ('LITIGE',):
            inv.status = 'A_PAYER'
            inv.payment_date = None
    elif paid >= total - 0.0001:
        inv.status = 'PAYEE'
    else:
        inv.status = 'PARTIEL'

    return inv
