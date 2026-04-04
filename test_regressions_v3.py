{% extends "_base.html" %}
{% block content %}

<div class="page-head" style="display:flex; justify-content:space-between; gap:16px; align-items:flex-start; flex-wrap:wrap;">
  <div>
    <h1 style="margin:0;">Qualification des flux hors facture</h1>
    <div class="muted">Les mouvements bancaires classés hors facture restent dans le journal source et alimentent le budget de trésorerie après qualification.</div>
  </div>
  <div style="display:flex; gap:8px; flex-wrap:wrap;">
    <a class="btn-secondary" href="/releves?view=hors_facture">Voir le journal source</a>
    <a class="btn-secondary" href="/cashflow">Budget de trésorerie</a>
  </div>
</div>

{% if msg %}
<div class="card" style="margin-top:12px; border-left:4px solid #2563eb;"><b>Statut :</b> {% if msg == 'class_ok' %}qualification enregistrée{% elif msg == 'restore_ok' %}mouvement remis à classer{% else %}{{ msg }}{% endif %}</div>
{% endif %}

<div class="kpi-grid" style="margin-top:14px; grid-template-columns: repeat(3, minmax(0,1fr));">
  <a class="card kpi-card" href="/qualification?status=open"><div class="kpi-title">À qualifier</div><div class="kpi-value">{{ counts.open }}</div></a>
  <a class="card kpi-card" href="/qualification?status=qualified"><div class="kpi-title">Déjà qualifiés</div><div class="kpi-value">{{ counts.qualified }}</div></a>
  <a class="card kpi-card" href="/qualification?status=all"><div class="kpi-title">Tous les flux hors facture</div><div class="kpi-value">{{ counts.open + counts.qualified }}</div></a>
</div>

<div class="card section-gap" style="margin-top:14px;">
  <form method="get" action="/qualification" style="display:grid; grid-template-columns: 180px 180px 180px auto; gap:10px; align-items:end;">
    <div>
      <label class="muted">Statut</label><br/>
      <select name="status" style="width:100%;">
        <option value="open" {% if status == 'open' %}selected{% endif %}>À qualifier</option>
        <option value="qualified" {% if status == 'qualified' %}selected{% endif %}>Qualifiés</option>
        <option value="all" {% if status == 'all' %}selected{% endif %}>Tous</option>
      </select>
    </div>
    <div>
      <label class="muted">Banque</label><br/>
      <select name="bank" style="width:100%;">
        <option value="">Toutes</option>
        {% for item in banks %}<option value="{{ item }}" {% if bank == item %}selected{% endif %}>{{ item }}</option>{% endfor %}
      </select>
    </div>
    <div>
      <label class="muted">Mois</label><br/>
      <select name="month" style="width:100%;">
        <option value="">Tous</option>
        {% for item in months %}<option value="{{ item }}" {% if month == item %}selected{% endif %}>{{ item }}</option>{% endfor %}
      </select>
    </div>
    <div style="display:flex; gap:8px;">
      <button class="btn btn-primary" type="submit">Filtrer</button>
      <a class="btn-secondary" href="/qualification">Réinitialiser</a>
    </div>
  </form>
</div>

<div class="card section-gap" style="margin-top:14px; overflow:auto;">
  <table class="table">
    <thead>
      <tr>
        <th>Date valeur</th>
        <th>Banque</th>
        <th>Montant</th>
        <th>Libellé</th>
        <th>Rubrique actuelle</th>
        <th>Qualifier / corriger</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      {% for t in txns %}
      {% set cf = cf_map.get(t.id) %}
      {% set current_rub = rub_map.get(cf.rubrique_id) if cf and cf.rubrique_id else None %}
      <tr>
        <td>{{ (t.value_date or t.date).date().isoformat() }}</td>
        <td>{{ t.bank_name or '-' }}<div class="muted" style="font-size:12px;">{{ t.account_no or '' }}</div></td>
        <td style="text-align:right;">{{ "%.2f"|format((t.debit if t.debit else t.credit) or 0) }}</td>
        <td style="max-width:420px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{{ t.label }}</td>
        <td>
          {% if current_rub %}
            <b>{{ current_rub.rubrique }}</b>
          {% else %}
            <span class="muted">Non qualifié</span>
          {% endif %}
        </td>
        <td style="min-width:320px;">
          <form method="post" action="/releves/{{ t.id }}/classify" style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
            <select name="rubrique_id" required style="min-width:220px;">
              <option value="">Choisir une rubrique</option>
              {% for rb in rubs %}
                <option value="{{ rb.id }}" {% if current_rub and current_rub.id == rb.id %}selected{% endif %}>{{ rb.rubrique }}</option>
              {% endfor %}
            </select>
            <input name="amount" value="{{ '%.2f'|format(cf.amount if cf else ((t.debit if t.debit else t.credit) or 0)) }}" style="width:110px;" />
            <button class="btn btn-primary" type="submit">Enregistrer</button>
          </form>
        </td>
        <td>
          <form method="post" action="/releves/{{ t.id }}/restore" style="display:inline;">
            <button class="btn-secondary" type="submit">Remettre à classer</button>
          </form>
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>

{% endblock %}
