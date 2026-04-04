{% extends "_base.html" %}
{% block content %}

<div class="page-head">
  <div>
    <h1 class="page-title">Vue Trésorerie (90 jours)</h1>
    <div class="page-sub">Échéances factures (A_PAYER) + soldes issus des relevés importés.</div>
  </div>
</div>

<div class="bi-grid">
  <section class="card bi-card bi-bank">
    <div class="card-hd">
      <div>
        <div class="card-title">Trésorerie par banque</div>
        <div class="card-sub">Projection MAD basée sur les échéances (7/30/60/90 jours).</div>
      </div>
    </div>

    <div class="table-wrap">
      <table class="bi-table">
        <thead>
          <tr>
            <th>Banque</th>
            <th>Compte</th>
            <th class="num">Solde</th>
            <th class="num">-7j</th>
            <th class="num">-30j</th>
            <th class="num">-60j</th>
            <th class="num">-90j</th>
            <th class="num">Proj -30j</th>
            <th class="num">Proj -90j</th>
            <th>Alerte</th>
          </tr>
        </thead>
        <tbody>
          {% for r in bank_rows %}
          <tr>
            <td>
              <b>{{ r.bank }}</b>
              {% if r.multi_currency %}
                <span class="pill">multi-devise</span>
              {% endif %}
            </td>
            <td class="muted">{{ r.account }}</td>
            <td class="num">{{ ("%0.2f"|format(r.cur_bal)) if r.cur_bal is not none else "—" }}</td>
            <td class="num">{{ "%0.2f"|format(r.out_7) }}</td>
            <td class="num">{{ "%0.2f"|format(r.out_30) }}</td>
            <td class="num">{{ "%0.2f"|format(r.out_60) }}</td>
            <td class="num">{{ "%0.2f"|format(r.out_90) }}</td>
            <td class="num">{{ ("%0.2f"|format(r.proj_30)) if r.proj_30 is not none else "—" }}</td>
            <td class="num">{{ ("%0.2f"|format(r.proj_90)) if r.proj_90 is not none else "—" }}</td>
            <td>
              {% if r.alert %}
                <span class="pill pill-warn">{{ r.alert }}</span>
              {% else %}
                <span class="muted">—</span>
              {% endif %}
            </td>
          </tr>
          {% else %}
          <tr><td colspan="10" class="muted">Ajouter un compte société actif (Paramètres → Comptes société).</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </section>

  <aside class="card bi-card bi-side">
    <div class="card-hd">
      <div>
        <div class="card-title">Prochaines échéances</div>
        <div class="card-sub">Horizon 90 jours (toutes devises).</div>
      </div>
      <a class="link" href="/factures">Voir achats →</a>
    </div>
    <div class="mini-list">
      {% for u in upcoming %}
      <div class="mini-row">
        <div>
          <div class="mini-top"><b>{{ u.due }}</b> • {{ u.supplier }}</div>
          <div class="mini-sub"><a href="/factures/{{ u.id }}">{{ u.ref }}</a></div>
        </div>
        <div class="mini-amt">{{ "%0.2f"|format(u.amount) }} {{ u.currency }}</div>
      </div>
      {% else %}
      <div class="muted">Aucune échéance sur 90 jours.</div>
      {% endfor %}
    </div>
  </aside>

  <section class="card bi-card bi-bank">
    <div class="card-hd">
      <div>
        <div class="card-title">Échéancier trésorerie</div>
        <div class="card-sub">Montants à payer vs retards (7/30/60/90j) par devise.</div>
      </div>
      <div class="tabs" id="treCurTabs">
        {% for c, v in chart_by_cur.items() %}
          <button class="tab-btn {% if c==default_chart_cur %}active{% endif %}" data-cur="{{ c }}">{{ c }}</button>
        {% endfor %}
      </div>
    </div>
    <div class="chart-area">
      <canvas id="treChart"></canvas>
    </div>
  </section>

  <aside class="card bi-card bi-side">
    <div class="card-hd">
      <div>
        <div class="card-title">Flux bancaires</div>
        <div class="card-sub">Somme débit / crédit (30 derniers jours importés).</div>
      </div>
      <a class="link" href="/releves">Importer →</a>
    </div>
    <div class="table-wrap">
      <table class="bi-table">
        <thead><tr><th>Date</th><th class="num">Débit</th><th class="num">Crédit</th><th class="num">Net</th></tr></thead>
        <tbody>
          {% for r in flux_rows %}
          <tr>
            <td class="muted">{{ r.date }}</td>
            <td class="num">{{ "%0.2f"|format(r.debit) }}</td>
            <td class="num">{{ "%0.2f"|format(r.credit) }}</td>
            <td class="num">{{ "%0.2f"|format(r.credit - r.debit) }}</td>
          </tr>
          {% else %}
          <tr><td colspan="4" class="muted">Importer un relevé bancaire pour alimenter ce bloc.</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </aside>
</div>

<script>
  window.__TRE_CHART_BY_CUR__ = {{ chart_by_cur|tojson }};
  window.__TRE_CHART_DEFAULT_CUR__ = {{ default_chart_cur|tojson }};
</script>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script>
  (function () {
    const byCur = window.__TRE_CHART_BY_CUR__ || {};
    const defaultCur = window.__TRE_CHART_DEFAULT_CUR__ || "MAD";
    const canvas = document.getElementById("treChart");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    const d0 = byCur[defaultCur] || { labels: [], a_payer: [], retard: [] };

    const chart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: d0.labels,
        datasets: [
          { label: "À payer", data: d0.a_payer, borderWidth: 0, borderRadius: 8 },
          { label: "Retard", data: d0.retard, borderWidth: 0, borderRadius: 8 },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "bottom" } },
        scales: { y: { beginAtZero: true } },
      },
    });

    const tabs = document.getElementById("treCurTabs");
    if (!tabs) return;
    tabs.addEventListener("click", function (e) {
      const btn = e.target.closest("button[data-cur]");
      if (!btn) return;
      const cur = btn.getAttribute("data-cur");
      const d = byCur[cur];
      if (!d) return;
      for (const b of tabs.querySelectorAll("button")) b.classList.remove("active");
      btn.classList.add("active");
      chart.data.labels = d.labels;
      chart.data.datasets[0].data = d.a_payer;
      chart.data.datasets[1].data = d.retard;
      chart.update();
    });
  })();
</script>

{% endblock %}
