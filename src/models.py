# src/models.py
from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


# ---------------- AUTH ----------------

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=50)
    password_hash: str


# ---------------- BANQUES (templates ordre de virement) ----------------

class Bank(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    name: str = Field(max_length=80, index=True, unique=True)
    template_code: str = Field(max_length=30, index=True)  # "BOA" / "BMCE_VIREMENT" / "BMCE_TRANSFERT" / etc.

    # infos optionnelles (en-tête ordre de virement)
    debit_account: Optional[str] = Field(default=None, max_length=80)
    agency: Optional[str] = Field(default=None, max_length=80)
    city: Optional[str] = Field(default=None, max_length=80)


# ---------------- BANK TXNS ----------------

class BankTxn(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    bank_name: Optional[str] = Field(default=None, max_length=80, index=True)
    account_no: Optional[str] = Field(default=None, max_length=80, index=True)
    currency: Optional[str] = Field(default=None, max_length=10)

    date: datetime = Field(index=True)  # date opération
    value_date: Optional[datetime] = Field(default=None, index=True)  # date valeur (cash réel)

    label: str = Field(max_length=400)
    label_norm: Optional[str] = Field(default=None, max_length=400, index=True)

    debit: float = 0.0
    credit: float = 0.0
    balance: Optional[float] = None

    # anti-doublon (banque+compte+date valeur+montant+libellé)
    dedup_key: Optional[str] = Field(default=None, max_length=200, index=True, unique=True)

    processing_status: Optional[str] = Field(default="IMPORTED", max_length=20, index=True)
    processing_note: Optional[str] = Field(default=None, max_length=120)

    created_at: datetime = Field(default_factory=datetime.now, index=True)


# ---------------- PAY DELAY ----------------

class PayDelayRow(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    dedup_key: str = Field(index=True, unique=True, max_length=120)

    if_code: Optional[str] = Field(default=None, max_length=30)
    ice: Optional[str] = Field(default=None, max_length=30)
    supplier_name: Optional[str] = Field(default=None, max_length=200)
    address: Optional[str] = Field(default=None, max_length=250)
    rc: Optional[str] = Field(default=None, max_length=30)
    rc_city: Optional[str] = Field(default=None, max_length=60)

    invoice_no: str = Field(index=True, max_length=80)
    invoice_date: Optional[datetime] = Field(default=None, index=True)
    nature: Optional[str] = Field(default=None, max_length=20)
    delivery_date: Optional[datetime] = None
    due_date_planned: Optional[datetime] = None
    due_date_agreed: Optional[datetime] = None


# ---------------- DOCUMENTS ----------------

class Document(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str = Field(max_length=255)
    stored_path: str = Field(max_length=255)
    doc_type: str = Field(default="AUTRE", max_length=12)  # AUTRE/FACTURE/BC/BR
    created_at: datetime = Field(default_factory=datetime.now, index=True)


# ---------------- FACTURES ----------------

class Invoice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    # ✅ lien vers la fiche fournisseur (source de vérité)
    supplier_id: Optional[int] = Field(default=None, foreign_key="supplier.id", index=True)

    supplier_name: Optional[str] = Field(default=None, index=True, max_length=200)
    invoice_no: Optional[str] = Field(default=None, index=True, max_length=80)

    invoice_date: Optional[datetime] = Field(default=None, index=True)
    reception_date: Optional[datetime] = None

    bc_no: Optional[str] = Field(default=None, max_length=80)
    bc_date: Optional[datetime] = None

    br_no: Optional[str] = Field(default=None, max_length=80)
    br_date: Optional[datetime] = None

    amount: float = 0.0
    currency: Optional[str] = Field(default=None, max_length=10)

    department: Optional[str] = Field(default=None, max_length=80)
    analytic: Optional[str] = Field(default=None, max_length=80)
    category: Optional[str] = Field(default=None, index=True, max_length=60)

    due_date: Optional[datetime] = None
    due_date_planned: Optional[datetime] = None
    due_date_agreed: Optional[datetime] = None

    status: str = Field(default="A_PAYER", index=True, max_length=20)
    payment_date: Optional[datetime] = Field(default=None, index=True)
    payment_mode: Optional[str] = Field(default=None, max_length=60)

    dedup_key: str = Field(index=True, unique=True, max_length=140)
    file_path: Optional[str] = Field(default=None, max_length=255)

    supplier_if: Optional[str] = Field(default=None, max_length=30)
    supplier_ice: Optional[str] = Field(default=None, max_length=30)
    supplier_rc: Optional[str] = Field(default=None, max_length=30)
    supplier_rc_city: Optional[str] = Field(default=None, max_length=60)
    supplier_address: Optional[str] = Field(default=None, max_length=250)

    service_date: Optional[datetime] = None
    nature_operation: Optional[str] = Field(default=None, max_length=20)

    payment_terms_days: Optional[int] = None
    derogation_sector: bool = Field(default=False)
    derogation_days: Optional[int] = None
    derogation_ref: Optional[str] = Field(default=None, max_length=120)

    calc_start_date: Optional[datetime] = None
    calc_start_rule: Optional[str] = Field(default=None, max_length=30)
    applied_terms_days: Optional[int] = None
    legal_due_date: Optional[datetime] = None

    amount_ht: Optional[float] = None
    vat_rate: Optional[float] = None
    amount_vat: Optional[float] = None
    amount_ttc: Optional[float] = None
    amount_paid: float = 0.0

    cashflow_category: Optional[str] = Field(default=None, max_length=60)

    cashflow_rubrique: Optional[str] = Field(default=None, max_length=80)
    reporting_groupe: Optional[str] = Field(default=None, max_length=80)
    impact_budget: Optional[bool] = Field(default=None)

    site: Optional[str] = Field(default=None, max_length=30)
    cost_center: Optional[str] = Field(default=None, max_length=60)
    project: Optional[str] = Field(default=None, max_length=80)
    gl_account: Optional[str] = Field(default=None, max_length=20)
    expense_nature: Optional[str] = Field(default=None, max_length=60)

    is_disputed: bool = Field(default=False)
    dispute_reason: Optional[str] = Field(default=None, max_length=200)
    disputed_amount: Optional[float] = None


class InvoicePaymentMatch(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    invoice_id: int = Field(foreign_key="invoice.id", index=True)
    banktxn_id: int = Field(foreign_key="banktxn.id", index=True)

    matched_amount: float = 0.0  # utile pour paiements partiels / groupés
    method: str = Field(default="MANUAL", max_length=12)  # MANUAL / AUTO
    notes: Optional[str] = Field(default=None, max_length=200)

    created_at: datetime = Field(default_factory=datetime.now, index=True)



class InvoiceDocument(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    # IMPORTANT:
    # Ces lignes sont dépendantes d'une facture.
    # Sans FK déclarée ici, l'ordre des DELETE n'est pas garanti et peut
    # supprimer la facture avant ses docs => IntegrityError/500.
    invoice_id: int = Field(foreign_key="invoice.id", index=True)
    doc_type: str = Field(default="AUTRE", index=True, max_length=12)

    filename: str = Field(max_length=255)
    stored_path: str = Field(max_length=255)

    ref_no: Optional[str] = Field(default=None, max_length=80)
    ref_date: Optional[datetime] = None

    created_at: datetime = Field(default_factory=datetime.now, index=True)



# ---------------- POSTES (Analytique / Budget) ----------------

class Post(SQLModel, table=True):
    """Poste paramétrable utilisé par:
    - Analytique (centres de coûts / natures)
    - Budget (postes budgétaires)
    """
    id: Optional[int] = Field(default=None, primary_key=True)

    kind: str = Field(index=True, max_length=12)  # ANALYTIC / BUDGET
    code: Optional[str] = Field(default=None, index=True, max_length=40)
    name: str = Field(index=True, max_length=120)

    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now, index=True)


# ---------------- AFFECTATIONS ----------------

class AllocationLine(SQLModel, table=True):
    """Affectation d'une facture vers un poste (analytique ou budget).
    Permet plusieurs lignes par facture (split).
    """
    id: Optional[int] = Field(default=None, primary_key=True)

    invoice_id: int = Field(foreign_key="invoice.id", index=True)
    kind: str = Field(index=True, max_length=12)  # ANALYTIC / BUDGET

    post_id: Optional[int] = Field(default=None, foreign_key="post.id", index=True)
    post_code: Optional[str] = Field(default=None, max_length=40)
    post_name: Optional[str] = Field(default=None, max_length=120)

    amount: float = 0.0
    note: Optional[str] = Field(default=None, max_length=200)

    created_at: datetime = Field(default_factory=datetime.now, index=True)

# ---------------- BUDGET ----------------

class BudgetLine(SQLModel, table=True):
    """Budget simple par mois (pilotage).

    Modèle minimal : période (year/month) + axes optionnels.
    On masque/affiche côté UI selon tes besoins, sans casser la DB.
    """

    id: Optional[int] = Field(default=None, primary_key=True)

    year: int = Field(index=True)
    month: int = Field(index=True)  # 1..12

    currency: str = Field(default="MAD", max_length=10)
    amount_planned: float = 0.0

    cashflow_category: Optional[str] = Field(default=None, max_length=60, index=True)
    cashflow_rubrique: Optional[str] = Field(default=None, max_length=80, index=True)

    site: Optional[str] = Field(default=None, max_length=30, index=True)
    project: Optional[str] = Field(default=None, max_length=80, index=True)
    analytic: Optional[str] = Field(default=None, max_length=80, index=True)
    cost_center: Optional[str] = Field(default=None, max_length=60, index=True)

    notes: Optional[str] = Field(default=None, max_length=200)
    created_at: datetime = Field(default_factory=datetime.now, index=True)


# ---------------- FOURNISSEURS ----------------

class Supplier(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    name: str = Field(index=True, max_length=200)
    ice: Optional[str] = Field(default=None, index=True, max_length=30)
    if_code: Optional[str] = Field(default=None, max_length=30)
    rc: Optional[str] = Field(default=None, max_length=30)
    rc_city: Optional[str] = Field(default=None, max_length=60)
    address: Optional[str] = Field(default=None, max_length=250)

    # ✅ clé métier: national vs étranger (décision explicite, pas une déduction)
    is_foreign: bool = Field(default=False, index=True)  # False=Marocain / True=Étranger
    country_code: Optional[str] = Field(default="MA", max_length=2)  # MA/FR/ES/... (optionnel)

    created_at: datetime = Field(default_factory=datetime.now, index=True)


class SupplierBankAccount(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    supplier_id: int = Field(foreign_key="supplier.id", index=True)

    bank_name: Optional[str] = Field(default=None, max_length=80)

    agency_name: Optional[str] = Field(default=None, max_length=80)

    # ✅ un seul champ: selon supplier.is_foreign => interprété RIB ou IBAN
    rib_or_iban: str = Field(max_length=50)

    # ✅ utile surtout pour l'étranger, mais peut rester vide pour marocain
    swift: Optional[str] = Field(default=None, max_length=20)

    attestation_filename: Optional[str] = Field(default=None, max_length=255)
    attestation_path: Optional[str] = Field(default=None, max_length=255)

    created_at: datetime = Field(default_factory=datetime.now, index=True)


# ---------------- CASHFLOW ----------------

class CashflowRubrique(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    rubrique: str = Field(max_length=80, index=True)
    nature_flux: Optional[str] = Field(default=None, max_length=40)
    reporting_groupe: Optional[str] = Field(default=None, max_length=80)
    impact_budget: bool = Field(default=True)


class CashflowActual(SQLModel, table=True):
    """Flux réel (alimenté uniquement par relevé bancaire / matching)."""
    id: Optional[int] = Field(default=None, primary_key=True)

    rubrique_id: Optional[int] = Field(default=None, foreign_key="cashflowrubrique.id", index=True)

    invoice_id: Optional[int] = Field(default=None, foreign_key="invoice.id", index=True)
    banktxn_id: Optional[int] = Field(default=None, foreign_key="banktxn.id", index=True)

    actual_debit_date: datetime = Field(index=True)  # date valeur prioritaire
    actual_month: str = Field(max_length=7, index=True)  # YYYY-MM

    amount: float = 0.0  # débit = sortie (positif), crédit = entrée (positif)
    created_at: datetime = Field(default_factory=datetime.now, index=True)

# ---------------- REGLEMENTS ----------------

class PaymentBatch(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    # ✅ compte bancaire société (source de vérité pour le suivi trésorerie "par banque")
    company_account_id: Optional[int] = Field(default=None, foreign_key="companybankaccount.id", index=True)

    bank_name: str = Field(max_length=60)
    debit_account: str = Field(max_length=80)

    payment_date: datetime
    total_amount: float = 0.0

    payment_type: str = Field(default="VIREMENT", max_length=20, index=True)
    instrument_ref: Optional[str] = Field(default=None, max_length=80)
    note: Optional[str] = Field(default=None, max_length=200)

    status: str = Field(default="DRAFT", max_length=20)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PaymentLine(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    batch_id: int = Field(foreign_key="paymentbatch.id", index=True)
    invoice_id: int = Field(foreign_key="invoice.id", index=True)

    amount: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Payment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    invoice_id: int = Field(foreign_key="invoice.id", index=True)

    amount: float = 0.0
    payment_date: Optional[datetime] = None

    payment_mode: Optional[str] = None
    bank_name: Optional[str] = None
    reference: Optional[str] = None

    status: Optional[str] = "BROUILLON"


# ---------------- BANQUES SOCIETE ----------------

class CompanyBankAccount(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    bank_name: str = Field(max_length=60)
    account_no: str = Field(max_length=80)

    agency_name: Optional[str] = Field(default=None, max_length=80)
    iban: Optional[str] = Field(default=None, max_length=64)
    swift: Optional[str] = Field(default=None, max_length=32)

    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    attestation_filename: Optional[str] = Field(default=None, max_length=255)
    attestation_path: Optional[str] = Field(default=None, max_length=255)


# ---------------- BUDGET COMPTABLE V3 ----------------

class GlBalanceLine(SQLModel, table=True):
    """Ligne de balance générale importée mensuellement depuis le système comptable externe."""
    id: Optional[int] = Field(default=None, primary_key=True)

    period_month: str = Field(index=True, max_length=7)  # YYYY-MM
    gl_account: str = Field(index=True, max_length=20)
    account_label: Optional[str] = Field(default=None, max_length=160)

    debit: float = 0.0
    credit: float = 0.0
    net_amount: float = 0.0

    source_filename: Optional[str] = Field(default=None, max_length=255)
    imported_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class GlBudgetTarget(SQLModel, table=True):
    """Cible budgétaire comptable par compte général et par mois."""
    id: Optional[int] = Field(default=None, primary_key=True)

    period_month: str = Field(index=True, max_length=7)  # YYYY-MM
    gl_account: str = Field(index=True, max_length=20)
    account_label: Optional[str] = Field(default=None, max_length=160)

    budget_amount: float = 0.0
    budget_group: Optional[str] = Field(default=None, max_length=80, index=True)
    note: Optional[str] = Field(default=None, max_length=200)

    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
