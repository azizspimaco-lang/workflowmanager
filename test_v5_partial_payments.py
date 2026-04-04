{% extends "_base.html" %}
{% block content %}

<div class="page-head" style="display:flex; justify-content:space-between; gap:16px; align-items:flex-start; flex-wrap:wrap;">
  <div>
    <h1 style="margin:0;">Budget comptable V3</h1>
    <div class="muted">Import mensuel de la balance générale, comparaison au budget par compte général, sans dépendre du module relevés bancaires.</div>
  </div>
</div>

{% if msg %}
<div class="card" style="margin-top:12px; border-left:4px solid #2563eb;"><b>Statut :</b> {% if msg == 'import_ok' %}balance importée{% elif msg == 'target_saved' %}cible budgétaire enregistrée{% else %}{{ msg }}{% endif %}</div>
{% endif %}

<div class="kpi-grid" style="margin-top:14px; grid-template-columns: repeat(3, minmax(0,1fr));">
  <div class="card kpi-card"><div class="kpi-title">Réalisé comptable</div><div class="kpi-value">{{ "%.2f"|format(total_actual) }}</div></div>
  <div class="card kpi-card"><div class="kpi-title">Budget</div><div class="kpi-value">{{ "%.2f"|format(total_budget) }}</div></div>
  <div class="card kpi-card"><div class="kpi-title">Écart</div><div class="kpi-value">{{ "%.2f"|format(variance) }}</div></div>
</div>

<div class="card section-gap" style="margin-top:14px;">
  <div style="display:grid; grid-template-columns: 1.2fr .8fr; gap:16px; align-items:start;">
    <form method="post" action="/budget-comptable/import" enctype="multipart/form-data">
      <h3 style="margin-top:0;">Importer la balance du mois</h3>
      <div style="display:grid; grid-template-columns:180px 1fr auto; gap:10px; align-items:end;">
        <div>
          <label class="muted">Période</label><br/>
          <input name="period_month" value="{{ month }}" placeholder="YYYY-MM" style="width:100%;" />
        </div>
        <div>
          <label class="muted">Fichier balance</label><br/>
          <input type="file" name="file" accept=".csv,.xlsx,.xls" required style="width:100%;" />
        </div>
        <label style="display:flex; align-items:center; gap:6px; white-space:nowrap;"><input type="checkbox" name="replace_existing" value="1" checked /> Remplacer le mois</label>
      </div>
      <div style="margin-top:10px;"><button class="btn btn-primary" type="submit">Importer</button></div>
    </form>

    <form method="post" action="/budget-comptable/target">
      <h3 style="margin-top:0;">Saisir une cible budgétaire</h3>
      <div style="display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px;">
        <input name="period_month" value="{{ month }}" placeholder="YYYY-MM" />
        <input name="gl_account" placeholder="Compte général" required />
        <input name="account_label" placeholder="Libellé" />
        <input name="budget_group" placeholder="Groupe budgétaire" />
        <input name="budget_amount" placeholder="Montant budget" required />
      </div>
      <div style="margin-top:10px;"><button class="btn btn-primary" type="submit">Enregistrer</button></div>
    </form>
  </div>
</div>

<div class="card section-gap" style="margin-top:14px; overflow:auto;">
  <div style="display:flex; justify-content:space-between; gap:10px; align-items:center; flex-wrap:wrap; margin-bottom:10px;">
    <h3 style="margin:0;">Comparatif {{ month }}</h3>
    <div style="display:flex; gap:8px; flex-wrap:wrap;">
      {% for item in months %}
        <a class="btn-secondary {% if month == item %}active{% endif %}" href="/budget-comptable?month={{ item }}">{{ item }}</a>
      {% endfor %}
    </div>
  </div>
  <table class="table">
    <thead>
      <tr>
        <th>Compte</th>
        <th>Libellé</th>
        <th>Groupe</th>
        <th>Réalisé</th>
        <th>Budget</th>
        <th>Écart</th>
      </tr>
    </thead>
    <tbody>
      {% for row in rows %}
      <tr>
        <td>{{ row.gl_account }}</td>
        <td>{{ row.account_label or '-' }}</td>
        <td>{{ row.budget_group or '-' }}</td>
        <td style="text-align:right;">{{ "%.2f"|format(row.actual) }}</td>
        <td style="text-align:right;">{{ "%.2f"|format(row.budget) }}</td>
        <td style="text-align:right;">{{ "%.2f"|format(row.variance) }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>

{% endblock %}
