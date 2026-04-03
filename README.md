# Mini-ERP Trésorerie (Local, multi-utilisateur) — Démarrage ultra simple

## Ce que ce prototype fait (MVP)
- Accès via navigateur (PC + Téléphone)
- Comptes utilisateurs (2 employés)
- Import **relevé bancaire BMCE** depuis Excel (ton modèle)
- Import **canevas délais de paiement** (ton modèle) → table consultable
- Tableau **Trésorerie** (solde + mouvements) alimenté depuis le relevé
- Upload documents (factures/BC/BR) — stockage + index (MVP, sans extraction AI avancée)

> Ensuite on ajoutera l'OCR/AI pour extraire automatiquement les champs factures/BC/BR.

---

## 0) Pré-requis (1 seule fois)
1. Installer **Python 3.11+**
2. Ouvrir un terminal dans le dossier du projet
3. Installer les dépendances :

```bash
pip install -r requirements.txt
```

---

## 1) Lancer l'application
```bash
python run.py
```

Puis ouvrir:
- Sur le PC serveur : http://127.0.0.1:8000
- Sur un autre PC/téléphone **dans le même Wi‑Fi** : http://IP_DU_SERVEUR:8000

---

## 2) Créer les comptes (1ère fois)
Après lancement, ouvre:
http://127.0.0.1:8000/setup

Tu pourras créer 2 utilisateurs (Employé 1 / Employé 2).

---

## 3) Importer les fichiers (tes modèles)
### Import relevé BMCE
Menu **Banque → Import BMCE**
- Choisir le fichier Excel d’extrait de compte (ex: `Bmce 16-02-2026.xlsx`)
- L’app détecte la feuille et importe les lignes (Date, Libellé, Débit, Crédit, Solde)

### Import délais de paiement
Menu **Délais de paiement → Import**
- Choisir `Canevas délai de paiement ...xlsx`

---

## 4) Données & Base
- La base (SQLite) est créée automatiquement : `data/app.db`
- Les documents uploadés sont stockés dans : `data/uploads/`

---

## 5) Accès depuis l’extérieur (4G / maison)
Recommandation Finance: **VPN (WireGuard)**.
Principe:
- Le PC serveur reste au bureau
- Les employés se connectent au VPN depuis leur téléphone/PC
- Ils ouvrent ensuite l’ERP comme au bureau.

---

## Support / prochaine étape (AI extraction)
Quand tu valides le MVP:
- Ajout OCR + extraction automatique facture/BC/BR (FR/EN)
- Règles anti-doublon (fournisseur + n° facture)
- Génération batch ordres de virement + export CSV banque


## 3bis) Importer les factures (SUIVI)
Menu **Factures** → Importer `SUIVI 2026.xlsx` (sheet `BC`).
Puis lancer **Auto‑Match** pour récupérer les dates de paiement depuis la banque.


# Déploiement en ligne (Render) — mode "A"
## 1) Créer le repo GitHub
- Crée un repo GitHub (privé recommandé)
- Upload tout le contenu du dossier dans le repo

## 2) Créer la Web Service Render
- Render → New → Web Service → Connect GitHub → choisir le repo
- Runtime: Python
- Build command:
  `pip install -r requirements.txt`
- Start command:
  `uvicorn src.main:app --host 0.0.0.0 --port $PORT`

## 3) Ajouter PostgreSQL
- Render → New → PostgreSQL
- Render fournit `DATABASE_URL`
- Dans la Web Service → Environment → ajoute `DATABASE_URL`

## 4) Stockage des documents (uploads)
Option MVP: stockage local (peut être perdu si redeploy selon plan).
Option recommandée: Render Disks (Persistent Disk) → monter sur:
`/opt/render/project/src/data/uploads`

## 5) Accès
Render fournit une URL type `https://xxx.onrender.com`
