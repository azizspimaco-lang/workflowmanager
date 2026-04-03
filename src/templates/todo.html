{% extends "_base.html" %}
{% block content %}
<div class="erp">
  <div class="card hero-guide section-gap">
    <div>
      <div class="eyebrow">Page guidée</div>
      <h1 style="margin:0 0 6px;">À faire aujourd'hui</h1>
      <div class="muted">Cette page regroupe les prochaines actions utiles pour un utilisateur non expert.</div>
    </div>
    <a class="btn btn-primary btn-xl" href="/factures">➕ Ajouter une facture</a>
  </div>

  <div class="quick-grid section-gap">
    {% for item in quick_actions %}
    <a class="card quick-card" href="{{ item.href }}">
      <h3>{{ item.title }}</h3>
      <p class="muted">{{ item.desc }}</p>
      <div class="cta-inline">{{ item.cta }} →</div>
    </a>
    {% endfor %}
  </div>

  <div class="auto-grid section-gap">
    <div class="card"><div class="muted">Critiques</div><div class="auto-big">{{ automation.action_buckets.critical|length }}</div></div>
    <div class="card"><div class="muted">Hautes</div><div class="auto-big">{{ automation.action_buckets.high|length }}</div></div>
    <div class="card"><div class="muted">À corriger</div><div class="auto-big">{{ automation.action_buckets.missing_data|length }}</div></div>
    <div class="card"><div class="muted">Rapprochements fiables</div><div class="auto-big">{{ automation.high_conf_matches|length }}</div></div>
  </div>

  <div class="card section-gap">
    <div class="section-head">
      <div><h3 style="margin:0;">Factures les plus urgentes</h3><div class="muted">Tri automatique par score de priorité.</div></div>
      <a class="btn-secondary" href="/planning">Ouvrir le planning</a>
    </div>
    <div class="table-wrap" style="margin-top:10px;">
      <table class="table">
        <thead><tr><th>Priorité</th><th>Fournisseur</th><th>Facture</th><th>Échéance</th><th>Jours</th><th style="text-align:right;">Montant</th><th>Complétude</th></tr></thead>
        <tbody>
          {% for row in automation.priority_rows[:12] %}
          <tr>
            <td><span class="badge auto-priority auto-{{ row.label|lower }}">{{ row.label }}</span></td>
            <td><a href="/factures/{{ row.invoice_id }}">{{ row.supplier_name }}</a></td>
            <td>{{ row.invoice_no }}</td>
            <td>{{ row.due.isoformat() if row.due else '—' }}</td>
            <td>{{ row.days_left if row.days_left is not none else '—' }}</td>
            <td style="text-align:right;">{{ "%.2f"|format(row.amount) }} {{ row.currency }}</td>
            <td>{{ row.completion.score }}%</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
</div>
{% endblock %}
