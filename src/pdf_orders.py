# src/pdf_orders.py
from __future__ import annotations

from datetime import date
from io import BytesIO
from typing import Optional, List, Dict

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm


# ---------------- Helpers format ----------------

def _fmt_date_fr(d: date) -> str:
    return f"{d.day:02d}/{d.month:02d}/{d.year}"

def _fmt_amount(amount: float) -> str:
    # 10000 -> "10 000,00"
    try:
        s = f"{float(amount):,.2f}"
        s = s.replace(",", " ").replace(".", ",")
        return s
    except Exception:
        return str(amount)

def _boxed_amount(amount: float, currency: str) -> str:
    cur = (currency or "").upper()
    amt = _fmt_amount(amount)
    if cur in ("USD", "$"):
        return f"# ${amt} #"
    if cur in ("EUR", "€"):
        return f"# €{amt} #"
    return f"# {amt} #"

def _clean(s: Optional[str], maxlen: int) -> str:
    if not s:
        return ""
    return str(s).strip()[:maxlen]

# ---------------- Amount to words (FR - simple) ----------------
# (Suffisant pour usage ordre de virement : MAD/EUR/USD)
_UNITS = ["zéro","un","deux","trois","quatre","cinq","six","sept","huit","neuf"]
_TEENS = ["dix","onze","douze","treize","quatorze","quinze","seize","dix-sept","dix-huit","dix-neuf"]
_TENS = ["","", "vingt","trente","quarante","cinquante","soixante","soixante","quatre-vingt","quatre-vingt"]

def _fr_0_99(n: int) -> str:
    if n < 10:
        return _UNITS[n]
    if 10 <= n < 20:
        return _TEENS[n-10]
    t = n // 10
    u = n % 10
    if t == 7:  # 70-79 = soixante + 10..19
        base = "soixante"
        return base + ("-" + _fr_0_99(10 + u) if u else "-dix")
    if t == 9:  # 90-99 = quatre-vingt + 10..19
        base = "quatre-vingt"
        return base + ("-" + _fr_0_99(10 + u) if u else "-dix")
    tens = _TENS[t]
    if t == 8 and u == 0:
        return "quatre-vingts"
    if u == 0:
        return tens
    if u == 1 and t in (2,3,4,5,6):
        return tens + "-et-un"
    return tens + "-" + _UNITS[u]

def _fr_0_999(n: int) -> str:
    if n < 100:
        return _fr_0_99(n)
    c = n // 100
    r = n % 100
    if c == 1:
        head = "cent"
    else:
        head = _UNITS[c] + " cent"
    if r == 0 and c > 1:
        return head + "s"
    if r == 0:
        return head
    return head + " " + _fr_0_99(r)

def number_to_words_fr(n: int) -> str:
    if n == 0:
        return "zéro"
    if n < 0:
        return "moins " + number_to_words_fr(-n)
    parts = []
    millions = n // 1_000_000
    n %= 1_000_000
    thousands = n // 1000
    rest = n % 1000

    if millions:
        if millions == 1:
            parts.append("un million")
        else:
            parts.append(number_to_words_fr(millions) + " millions")

    if thousands:
        if thousands == 1:
            parts.append("mille")
        else:
            parts.append(_fr_0_999(thousands) + " mille")

    if rest:
        parts.append(_fr_0_999(rest))

    return " ".join(parts)

def amount_to_words_fr(amount: float, currency: str) -> str:
    cur = (currency or "MAD").upper()
    major_name = {
        "MAD": "dirhams",
        "DHS": "dirhams",
        "DH": "dirhams",
        "EUR": "euros",
        "USD": "dollars",
    }.get(cur, cur.lower())

    # centimes
    a = float(amount or 0.0)
    major = int(a)
    cents = int(round((a - major) * 100))

    words_major = number_to_words_fr(major)
    if cents > 0:
        words_cents = number_to_words_fr(cents)
        return f"{words_major} {major_name} {words_cents} centimes"
    return f"{words_major} {major_name}"


# ---------------- Detection template ----------------

def _is_international(lines: List[Dict], currency: str) -> bool:
    cur = (currency or "MAD").upper()
    if cur not in ("MAD", "DH", "DHS"):
        return True
    for ln in lines:
        iban = (ln.get("beneficiary_iban") or ln.get("beneficiary_rib") or "").strip().upper()
        swift = (ln.get("beneficiary_swift") or "").strip().upper()
        if iban.startswith("IBAN") or len(iban) >= 20 or swift:
            return True
    return False


# ---------------- Rendering ----------------

def _draw_kv(c: canvas.Canvas, x: float, y: float, k: str, v: str, k_w: float = 55*mm):
    c.setFont("Helvetica", 10)
    c.drawString(x, y, k)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x + k_w, y, v)

def _render_national_bmce_like(
    c: canvas.Canvas,
    bank_name: str,
    debit_account: Optional[str],
    agency: Optional[str],
    payment_date: date,
    lines: List[Dict],
    total_amount: float,
    currency: str,
):
    # Portrait A4 (on garde de l'espace pour en-tête + pied)
    w, h = A4
    left = 16 * mm
    right = 16 * mm
    header_space = 18 * mm   # espace libre en haut (en-tête société)
    footer_space = 15 * mm   # espace libre en bas (pied de page)
    top = h - header_space
    box_w = w - left - right

    def rect(x, y, ww, hh, lw=0.8):
        c.setLineWidth(lw)
        c.rect(x, y, ww, hh)

    def label(x, y, s, size=9):
        c.setFont("Helvetica", size)
        c.drawString(x, y, s)

    def value(x, y, s, size=10):
        c.setFont("Helvetica-Bold", size)
        c.drawString(x, y, s)

    # ---------------- TITRE ----------------
    y = top - 10 * mm
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(w / 2, y, "ORDRE DE VIREMENT UNITAIRE")

    # ---------------- DATE + REF ----------------
    y -= 14 * mm
    rect(left, y - 18 * mm, box_w, 18 * mm)
    label(left + 4 * mm, y - 6 * mm, "Date :")
    value(left + 20 * mm, y - 6.2 * mm, _fmt_date_fr(payment_date))

    label(left + 4 * mm, y - 14 * mm, "Référence Opération :")
    value(left + 45 * mm, y - 14.2 * mm, "")

    # ---------------- TYPE + AGENCE ----------------
    y -= 22 * mm
    rect(left, y - 12 * mm, box_w, 12 * mm)
    label(left + 4 * mm, y - 8.5 * mm, "Type Opération :")
    value(left + 32 * mm, y - 8.8 * mm, "VRT_UNITAIRE")
    label(left + 78 * mm, y - 8.5 * mm, "Agence :")
    value(left + 95 * mm, y - 8.8 * mm, _clean(agency, 80) or "")

    # ---------------- PHRASE (ABAISSÉE) ----------------
    y -= 16 * mm
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(left + 2 * mm, y - 2 * mm, "Par le débit de notre compte, veuillez exécuter le virement en détail")
    c.setFont("Helvetica", 10)

    # ---------------- BLOC PRINCIPAL ----------------
    y -= 10 * mm
    rect(left, y - 78 * mm, box_w, 78 * mm)

    # séparateurs
    c.setLineWidth(0.6)
    for k in range(1, 7):
        c.line(left, y - k * 11 * mm, left + box_w, y - k * 11 * mm)

    # valeurs
    rs = _clean(lines[0].get("ordering_name") if lines and len(lines) == 1 else "", 80) or "—"
    rib_ord = _clean(debit_account, 80)

    ben = _clean(lines[0].get("beneficiary_name"), 200) if len(lines) == 1 else "BATCH BENEFICIAIRES"
    rib_ben = ""
    if len(lines) == 1:
        rib_ben = _clean(lines[0].get("beneficiary_rib") or lines[0].get("beneficiary_iban"), 80)

    # --- ordre demandé ---
    label(left + 4 * mm, y - 8 * mm, "Raison Sociale")
    value(left + 45 * mm, y - 8.2 * mm, rs)

    label(left + 4 * mm, y - 19 * mm, "RIB Ordonnateur")
    value(left + 45 * mm, y - 19.2 * mm, rib_ord)

    label(left + 4 * mm, y - 30 * mm, "RIB Bénéficiaire")
    value(left + 45 * mm, y - 30.2 * mm, rib_ben)

    label(left + 4 * mm, y - 41 * mm, "Nom Bénéficiaire")
    value(left + 45 * mm, y - 41.2 * mm, ben)

    label(left + 4 * mm, y - 52 * mm, "Montant Virement")
    value(left + 45 * mm, y - 52.2 * mm, f"{_fmt_amount(total_amount)}")

    label(left + 4 * mm, y - 63 * mm, "En Lettres")
    value(left + 45 * mm, y - 63.2 * mm, amount_to_words_fr(total_amount, currency).upper())

    # ---------------- LIBELLÉS (2 lignes) ----------------
    y -= 78 * mm
    rect(left, y - 24 * mm, box_w, 24 * mm)
    c.setLineWidth(0.6)
    c.line(left, y - 12 * mm, left + box_w, y - 12 * mm)

    motif = _clean(lines[0].get("motif") if lines and len(lines) == 1 else "", 80) or "PAIEMENT FACTURE"

    label(left + 4 * mm, y - 8 * mm, "Libellé Relevé Ordonnateur")
    value(left + 65 * mm, y - 8.2 * mm, motif)

    label(left + 4 * mm, y - 20 * mm, "Libellé Relevé Bénéficiaire")
    value(left + 65 * mm, y - 20.2 * mm, motif)

    # ---------------- SIGNATURES (CASE FUSIONNÉE) ----------------
    y -= 28 * mm
    rect(left, y - 55 * mm, box_w, 55 * mm)

    # ✅ texte en haut à gauche, pas centré
    c.setFont("Helvetica-Bold", 11)
    c.drawString(left + 4 * mm, y - 10 * mm, "Signatures Autorisées")
    c.setFont("Helvetica", 10)

    # ✅ pas de trait vertical au milieu
    # (donc on ne dessine plus la ligne centrale)

    # ✅ pas de pied de page "Banque: ..."
    # On laisse l'espace footer_space libre
    
def _render_international_transfer_letter(
    c: canvas.Canvas,
    bank_name: str,
    agency: Optional[str],
    city: Optional[str],
    debit_account: Optional[str],
    payment_date: date,
    lines: List[Dict],
    total_amount: float,
    currency: str,
):
    # Style lettre ordre de virement international :contentReference[oaicite:3]{index=3}
    w, h = A4
    left = 18 * mm
    top = h - 18 * mm

    # En-tête date + banque/agence
    c.setFont("Helvetica", 11)
    c.drawString(left, top, f"Casablanca, le {_fmt_date_fr(payment_date)}")

    y = top - 12*mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(left, y, bank_name or "BANQUE")

    c.setFont("Helvetica", 10)
    y -= 6*mm
    if agency:
        c.drawString(left, y, agency)
        y -= 6*mm
    if city:
        c.drawString(left, y, city)
        y -= 10*mm
    else:
        y -= 4*mm

    if debit_account:
        c.setFont("Helvetica", 10)
        c.drawString(left, y, f"Compte n° {debit_account}")
        y -= 10*mm

    c.setFont("Helvetica-Bold", 11)
    c.drawString(left, y, "Objet : Ordre de Transfert (Devise)")
    y -= 10*mm

    # Si une seule ligne, on imprime détaillé ; sinon mini-table
    if len(lines) == 1:
        ln = lines[0]
        ben = _clean(ln.get("beneficiary_name"), 200)
        adr = _clean(ln.get("beneficiary_address"), 250)
        iban = _clean(ln.get("beneficiary_iban") or ln.get("beneficiary_rib"), 80)
        swift = _clean(ln.get("beneficiary_swift"), 30)
        motif = _clean(ln.get("motif"), 200)

        c.setFont("Helvetica", 10)
        c.drawString(left, y, f"En faveur de : {ben}")
        y -= 7*mm
        if adr:
            c.drawString(left, y, f"ADRESSE : {adr}")
            y -= 7*mm
        if iban:
            c.drawString(left, y, f"IBAN N° : {iban}")
            y -= 7*mm
        if swift:
            c.drawString(left, y, f"CODE SWIFT : {swift}")
            y -= 10*mm

        c.setFont("Helvetica-Bold", 10)
        c.drawString(left, y, f"Montant ({currency.upper()}) : {_boxed_amount(total_amount, currency)}")
        y -= 10*mm

        c.setFont("Helvetica", 10)
        c.drawString(left, y, "Nous vous prions de bien vouloir effectuer par le débit de notre compte sus indiqué le transfert")
        y -= 6*mm
        c.drawString(left, y, "désigné ci-dessous :")
        y -= 10*mm

        c.setFont("Helvetica-Bold", 10)
        c.drawString(left, y, amount_to_words_fr(total_amount, currency).capitalize())
        y -= 10*mm

        if motif:
            c.setFont("Helvetica", 10)
            c.drawString(left, y, motif)
            y -= 8*mm

    else:
        c.setFont("Helvetica", 10)
        c.drawString(left, y, "Nous vous prions de bien vouloir effectuer le(s) transfert(s) suivant(s) :")
        y -= 10*mm

        c.setFont("Helvetica-Bold", 10)
        c.drawString(left, y, "Bénéficiaire")
        c.drawString(left + 95*mm, y, "IBAN")
        c.drawRightString(w - left, y, "Montant")
        y -= 5 * mm
        c.setLineWidth(0.5)
        c.line(left, y, w - left, y)
        y -= 6 * mm

        c.setFont("Helvetica", 9)
        for ln in lines[:16]:
            ben = _clean(ln.get("beneficiary_name"), 38)
            iban = _clean(ln.get("beneficiary_iban") or ln.get("beneficiary_rib"), 24)
            amt = float(ln.get("amount") or 0.0)
            c.drawString(left, y, ben)
            c.drawString(left + 95*mm, y, iban)
            c.drawRightString(w - left, y, _fmt_amount(amt))
            y -= 6*mm

        y -= 4*mm
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(w - left, y, f"TOTAL : {_boxed_amount(total_amount, currency)}")
        y -= 10*mm

    # Formule de politesse
    c.setFont("Helvetica", 10)
    c.drawString(left, 45*mm, "Avec nos remerciements, nous vous prions d’agréer, Messieurs, l’expression de nos salutations distinguées.")
    c.drawString(left, 30*mm, "Pr. (Raison Sociale) : ____________________________")
    c.drawString(left, 18*mm, "Signature / Cachet")


# ---------------- Public API ----------------

def generate_order_pdf(
    template_code: str,
    bank_name: str,
    debit_account: Optional[str],
    agency: Optional[str],
    city: Optional[str],
    payment_date: date,
    lines: List[Dict],
    total_amount: float,
    currency: str,
) -> bytes:
    """
    Génère 2 formats :
    - National MAD : style 'Ordre de Virement Unitaire' :contentReference[oaicite:4]{index=4}
    - International devise : style lettre 'Ordre de Virement' :contentReference[oaicite:5]{index=5}
    Auto-détection via devise + champs IBAN/SWIFT.
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    render_order_page(
        c=c,
        template_code=template_code,
        bank_name=bank_name,
        debit_account=debit_account,
        agency=agency,
        city=city,
        payment_date=payment_date,
        lines=lines,
        total_amount=total_amount,
        currency=currency,
    )

    c.showPage()
    c.save()
    return buf.getvalue()


def render_order_page(
    c: canvas.Canvas,
    template_code: str,
    bank_name: str,
    debit_account: Optional[str],
    agency: Optional[str],
    city: Optional[str],
    payment_date: date,
    lines: List[Dict],
    total_amount: float,
    currency: str,
) -> None:
    """Dessine UNE page d'ordre sur un canvas existant.

    Important : cette fonction ne fait pas showPage()/save().
    """
    cur = (currency or "MAD").upper()
    intl = _is_international(lines, cur)

    if intl:
        _render_international_transfer_letter(
            c=c,
            bank_name=bank_name,
            agency=agency,
            city=city,
            debit_account=debit_account,
            payment_date=payment_date,
            lines=lines,
            total_amount=total_amount,
            currency=cur,
        )
    else:
        _render_national_bmce_like(
            c=c,
            bank_name=bank_name,
            debit_account=debit_account,
            agency=agency,
            payment_date=payment_date,
            lines=lines,
            total_amount=total_amount,
            currency=cur,
        )


def generate_orders_pdf(
    template_code: str,
    bank_name: str,
    debit_account: Optional[str],
    agency: Optional[str],
    city: Optional[str],
    payment_date: date,
    orders: List[Dict],
) -> bytes:
    """Génère un PDF multi-pages (1 ordre = 1 page)."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    for o in (orders or []):
        render_order_page(
            c=c,
            template_code=template_code,
            bank_name=bank_name,
            debit_account=debit_account,
            agency=agency,
            city=city,
            payment_date=payment_date,
            lines=o.get("lines") or [],
            total_amount=float(o.get("total_amount") or 0.0),
            currency=str(o.get("currency") or "MAD"),
        )
        c.showPage()

    c.save()
    return buf.getvalue()
