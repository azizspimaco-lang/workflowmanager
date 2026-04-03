// static/app.js
(function () {
  "use strict";

  function $all(sel, root) {
    return Array.from((root || document).querySelectorAll(sel));
  }

  function setLoading(formId, btnId, msgId) {
    const form = document.getElementById(formId);
    if (!form) return;

    const btn = document.getElementById(btnId);
    const msg = document.getElementById(msgId);

    form.addEventListener("submit", function () {
      if (btn) {
        btn.disabled = true;
        btn.classList.add("is-loading");
      }
      if (msg) msg.style.display = "block";
    });
  }

  // -------- spinners --------
  setLoading("scanForm", "scanBtn", "scanMsg");
  setLoading("addDocsForm", "addDocsBtn", "addDocsMsg");

  
  // -------- modal (messages) --------
  function showModal(message, title) {
    const modal = document.getElementById("erpModal");
    const msg = document.getElementById("erpModalMsg");
    const ttl = document.getElementById("erpModalTitle");
    const ok = document.getElementById("erpModalOk");
    if (!modal || !msg || !ttl || !ok) {
      // fallback
      window.alert(message || "");
      return;
    }
    ttl.textContent = title || "Information";
    msg.textContent = message || "";
    modal.style.display = "block";
    modal.setAttribute("aria-hidden", "false");

    function close() {
      modal.style.display = "none";
      modal.setAttribute("aria-hidden", "true");
      ok.removeEventListener("click", close);
      modal.querySelectorAll("[data-close]").forEach((el) => el.removeEventListener("click", close));
      document.removeEventListener("keydown", onKey);
    }
    function onKey(e) {
      if (e.key === "Escape") close();
    }

    ok.addEventListener("click", close);
    modal.querySelectorAll("[data-close]").forEach((el) => el.addEventListener("click", close));
    document.addEventListener("keydown", onKey);
  }

  function getQueryParam(name) {
    try {
      const u = new URL(window.location.href);
      return u.searchParams.get(name);
    } catch (e) {
      return null;
    }
  }

  // Affiche un message s'il y a ?toast=...
  const toastMsg = getQueryParam("toast");
  if (toastMsg) {
    showModal(decodeURIComponent(toastMsg), "Action impossible");
    try {
      const u = new URL(window.location.href);
      u.searchParams.delete("toast");
      window.history.replaceState({}, "", u.toString());
    } catch (e) {}
  }

  // -------- mobile sidebar toggle --------
  (function setupMobileMenu() {
    const btn = document.getElementById("menuBtn");
    const sidebar = document.getElementById("sidebar");
    const backdrop = document.getElementById("sidebarBackdrop");
    if (!btn || !sidebar || !backdrop) return;

    function open() {
      sidebar.classList.add("is-open");
      backdrop.style.display = "block";
      backdrop.setAttribute("aria-hidden", "false");
      document.body.style.overflow = "hidden";
    }

    function close() {
      sidebar.classList.remove("is-open");
      backdrop.style.display = "none";
      backdrop.setAttribute("aria-hidden", "true");
      document.body.style.overflow = "";
    }

    btn.addEventListener("click", function () {
      if (sidebar.classList.contains("is-open")) close();
      else open();
    });
    backdrop.addEventListener("click", close);
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") close();
    });

    // Close menu when clicking a link (mobile)
    $all("a.nav-link", sidebar).forEach((a) => a.addEventListener("click", close));
  })();

  // -------- delete invoice (AJAX to stay on same page) --------
  $all("form.js-delete-invoice").forEach((form) => {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();

      const ok = window.confirm("Supprimer définitivement cette facture ?");
      if (!ok) return;

      const action = form.getAttribute("action");
      const row = form.closest("tr");
      try {
        const res = await fetch(action, {
          method: "POST",
          headers: { "X-Requested-With": "fetch" },
        });

        if (res.ok) {
          // Remove row for immediate feedback
          if (row) row.remove();
          // Recompute KPIs if function exists
          if (typeof window.recomputeInvoicesKpi === "function") window.recomputeInvoicesKpi();
          return;
        }

        let payload = null;
        try { payload = await res.json(); } catch (e2) {}
        const msg = (payload && (payload.detail || payload.message)) ? (payload.detail || payload.message) : "Suppression impossible.";
        showModal(msg, "Action impossible");
      } catch (err) {
        showModal("Erreur réseau/serveur. Réessaie.", "Erreur");
      }
    });
  });

  // -------- delete supplier bank account (AJAX) --------
  $all("form.js-delete-supacc").forEach((form) => {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const ok = window.confirm("Supprimer ce compte bancaire associé ?");
      if (!ok) return;

      const action = form.getAttribute("action");
      const item = form.closest(".supacc-item") || form;
      try {
        const res = await fetch(action, {
          method: "POST",
          headers: { "X-Requested-With": "fetch" },
        });

        if (res.ok) {
          // retirer le bloc du compte
          if (item) item.remove();
          return;
        }

        let payload = null;
        try { payload = await res.json(); } catch (e2) {}
        const msg = (payload && (payload.detail || payload.message)) ? (payload.detail || payload.message) : "Suppression impossible.";
        showModal(msg, "Action impossible");
      } catch (err) {
        showModal("Erreur réseau/serveur. Réessaie.", "Erreur");
      }
    });
  });

  // -------- open supplier accounts (toggle details) --------
  $all("button.js-open-supacc").forEach((btn) => {
    btn.addEventListener("click", () => {
      const supid = btn.getAttribute("data-supid");
      if (!supid) return;
      const det = document.getElementById("supacc-" + supid);
      if (det) {
        det.open = true;
        // scroll a bit into view if needed
        try { det.scrollIntoView({ block: "nearest", behavior: "smooth" }); } catch(e) {}
      } else {
        showModal("Aucun compte associé pour ce fournisseur.", "Comptes");
      }
    });
  });

  // -------- delete supplier (AJAX) --------
  $all("form.js-delete-supplier").forEach((form) => {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const ok = window.confirm("Supprimer ce fournisseur ? (comptes associés inclus)\n\n⚠️ Impossible si lié à des factures.");
      if (!ok) return;

      const action = form.getAttribute("action");
      const row = form.closest("tr");
      try {
        const res = await fetch(action, {
          method: "POST",
          headers: { "X-Requested-With": "fetch" },
        });

        if (res.ok) {
          if (row) row.remove();
          return;
        }

        let payload = null;
        try { payload = await res.json(); } catch (e2) {}
        const msg = (payload && (payload.detail || payload.message)) ? (payload.detail || payload.message) : "Suppression impossible.";
        showModal(msg, "Action impossible");
      } catch (err) {
        showModal("Erreur réseau/serveur. Réessaie.", "Erreur");
      }
    });
  });



  // -------- delete payment batch (ordre de virement) (AJAX) --------
  $all("form.js-delete-batch").forEach((form) => {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const ok = window.confirm("Supprimer cet ordre de virement ?");
      if (!ok) return;

      const action = form.getAttribute("action");
      const row = form.closest("tr") || form.closest(".card") || form;
      try {
        const res = await fetch(action, {
          method: "POST",
          headers: { "X-Requested-With": "fetch", "Accept": "application/json" },
        });

        if (res.ok) {
          if (row) row.remove();
          return;
        }

        let payload = null;
        try { payload = await res.json(); } catch (e2) {}
        const msg = (payload && (payload.detail || payload.message)) ? (payload.detail || payload.message) : "Suppression impossible.";
        showModal(msg, "Action impossible");
      } catch (err) {
        showModal("Erreur réseau/serveur. Réessaie.", "Erreur");
      }
    });
  });

  // -------- reset export payment batch (AJAX) --------
  $all("form.js-reset-export").forEach((form) => {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const ok = window.confirm("Réinitialiser l'export de cet ordre ? (il repassera en DRAFT)");
      if (!ok) return;

      const action = form.getAttribute("action");
      const row = form.closest("tr") || null;
      try {
        const res = await fetch(action, {
          method: "POST",
          headers: { "X-Requested-With": "fetch", "Accept": "application/json" },
        });

        if (res.ok) {
          // Update status in list view if we are inside a table row
          if (row) {
            const tds = row.querySelectorAll("td");
            // status is 6th column in reglements.html
            if (tds && tds.length >= 6) {
              tds[5].textContent = "DRAFT";
            }
          }

          // In detail view: update the status label if present
          const statusB = document.querySelector(".erp .card .muted b");
          // safer: find the "Statut:" line
          document.querySelectorAll(".muted").forEach((el) => {
            if ((el.textContent || "").toLowerCase().includes("statut")) {
              const b = el.querySelector("b");
              if (b) b.textContent = "DRAFT";
            }
          });

          // remove the reset button (no longer relevant)
          form.remove();
          showModal("Export réinitialisé. Tu peux maintenant supprimer l'ordre.", "OK");
          return;
        }

        let payload = null;
        try { payload = await res.json(); } catch (e2) {}
        const msg = (payload && (payload.detail || payload.message)) ? (payload.detail || payload.message) : "Action impossible.";
        showModal(msg, "Action impossible");
      } catch (err) {
        showModal("Erreur réseau/serveur. Réessaie.", "Erreur");
      }
    });
  });

  // -------- delete banque template (AJAX) --------
  $all("form.js-delete-banktpl").forEach((form) => {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const ok = window.confirm("Supprimer ce modèle de banque ?");
      if (!ok) return;

      const action = form.getAttribute("action");
      const row = form.closest("tr") || form;
      try {
        const res = await fetch(action, {
          method: "POST",
          headers: { "X-Requested-With": "fetch", "Accept": "application/json" },
        });

        if (res.ok) {
          if (row) row.remove();
          return;
        }

        let payload = null;
        try { payload = await res.json(); } catch (e2) {}
        const msg = (payload && (payload.detail || payload.message)) ? (payload.detail || payload.message) : "Suppression impossible.";
        showModal(msg, "Action impossible");
      } catch (err) {
        showModal("Erreur réseau/serveur. Réessaie.", "Erreur");
      }
    });
  });

  // -------- delete company bank account (AJAX) --------
  $all("form.js-delete-companybank").forEach((form) => {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const ok = window.confirm("Supprimer ce compte bancaire ?");
      if (!ok) return;

      const action = form.getAttribute("action");
      const row = form.closest("tr") || form;
      try {
        const res = await fetch(action, {
          method: "POST",
          headers: { "X-Requested-With": "fetch", "Accept": "application/json" },
        });

        if (res.ok) {
          if (row) row.remove();
          return;
        }

        let payload = null;
        try { payload = await res.json(); } catch (e2) {}
        const msg = (payload && (payload.detail || payload.message)) ? (payload.detail || payload.message) : "Suppression impossible.";
        showModal(msg, "Action impossible");
      } catch (err) {
        showModal("Erreur réseau/serveur. Réessaie.", "Erreur");
      }
    });
  });

// -------- filters table factures --------
  const table = document.getElementById("invoicesTable");
  if (!table) return;

  const tbody = table.tBodies && table.tBodies[0];
  if (!tbody) return;

  const qInput = document.getElementById("q");
  const statusFilter = document.getElementById("statusFilter");
  const curFilter = document.getElementById("curFilter");
  const qualityFilter = document.getElementById("qualityFilter");
  const dateFrom = document.getElementById("dateFrom");
  const dateTo = document.getElementById("dateTo");
  const resetBtn = document.getElementById("resetFilters");
  const rowCount = document.getElementById("rowCount");

  // KPIs
  const kpiTotal = document.getElementById("kpiTotal");
  const kpiCount = document.getElementById("kpiCount");
  const kpiAPayer = document.getElementById("kpiAPayer");
  const kpiAPayerCount = document.getElementById("kpiAPayerCount");
  const kpiPayee = document.getElementById("kpiPayee");
  const kpiPayeeCount = document.getElementById("kpiPayeeCount");
  const kpiIssues = document.getElementById("kpiIssues");
  const kpiIssuesCount = document.getElementById("kpiIssuesCount");

  const rows = $all("tr", tbody);

  function norm(s) {
    return (s || "").toString().toLowerCase().trim();
  }

  function toNum(v) {
    const s = (v || "").toString().replace(",", ".");
    const n = Number(s);
    return Number.isFinite(n) ? n : 0;
  }

  function fmtMoney(n) {
    try {
      return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    } catch (e) {
      return (Math.round(n * 100) / 100).toFixed(2);
    }
  }

  function inDateRange(d, from, to) {
    // d/from/to: "YYYY-MM-DD" (comparaison lexicographique OK)
    if (!d) return true;
    if (from && d < from) return false;
    if (to && d > to) return false;
    return true;
  }

  function applyFilters() {
    const q = norm(qInput ? qInput.value : "");
    const st = (statusFilter ? statusFilter.value : "").toUpperCase().trim();
    const cur = (curFilter ? curFilter.value : "").toUpperCase().trim();
    const qual = (qualityFilter ? qualityFilter.value : "").toUpperCase().trim();
    const dFrom = dateFrom ? dateFrom.value : "";
    const dTo = dateTo ? dateTo.value : "";

    let visible = 0;

    let totalVisible = 0;
    let aPayerTotal = 0;
    let payeeTotal = 0;
    let issuesTotal = 0;

    let aPayerCount = 0;
    let payeeCount = 0;
    let issuesCount = 0;

    for (const tr of rows) {
      const ds = (tr.getAttribute("data-search") || "").toLowerCase();
      const dStatus = (tr.getAttribute("data-status") || "").toUpperCase();
      const dCur = (tr.getAttribute("data-cur") || "").toUpperCase();
      const dDate = tr.getAttribute("data-date") || "";
      const dAmount = toNum(tr.getAttribute("data-amount"));
      const incomplete = tr.getAttribute("data-incomplete") === "1";
      const disputed = tr.getAttribute("data-disputed") === "1";

      const okQ = !q || ds.includes(q);
      const okSt = !st || dStatus === st;
      const okCur = !cur || dCur === cur;

      let okQual = true;
      if (qual === "OK") okQual = !incomplete && !disputed;
      else if (qual === "INCOMPLETE") okQual = incomplete;
      else if (qual === "DISPUTED") okQual = disputed;

      const okDate = inDateRange(dDate, dFrom, dTo);

      const show = okQ && okSt && okCur && okQual && okDate;
      tr.style.display = show ? "" : "none";

      if (show) {
        visible++;
        totalVisible += dAmount;

        if (dStatus === "A_PAYER") {
          aPayerTotal += dAmount;
          aPayerCount++;
        } else if (dStatus === "PAYEE") {
          payeeTotal += dAmount;
          payeeCount++;
        }

        if (incomplete || disputed) {
          issuesTotal += dAmount;
          issuesCount++;
        }
      }
    }

    if (rowCount) rowCount.textContent = `${visible} / ${rows.length}`;

    if (kpiTotal) kpiTotal.textContent = fmtMoney(totalVisible);
    if (kpiCount) kpiCount.textContent = `${visible} facture(s) visibles`;

    if (kpiAPayer) kpiAPayer.textContent = fmtMoney(aPayerTotal);
    if (kpiAPayerCount) kpiAPayerCount.textContent = `${aPayerCount} ligne(s)`;

    if (kpiPayee) kpiPayee.textContent = fmtMoney(payeeTotal);
    if (kpiPayeeCount) kpiPayeeCount.textContent = `${payeeCount} ligne(s)`;

    if (kpiIssues) kpiIssues.textContent = fmtMoney(issuesTotal);
    if (kpiIssuesCount) kpiIssuesCount.textContent = `${issuesCount} ligne(s)`;
  }

  function bind(el, ev) {
    if (!el) return;
    el.addEventListener(ev, applyFilters);
  }

  bind(qInput, "input");
  bind(statusFilter, "change");
  bind(curFilter, "change");
  bind(qualityFilter, "change");
  bind(dateFrom, "change");
  bind(dateTo, "change");

  if (resetBtn) {
    resetBtn.addEventListener("click", function () {
      if (qInput) qInput.value = "";
      if (statusFilter) statusFilter.value = "";
      if (curFilter) curFilter.value = "";
      if (qualityFilter) qualityFilter.value = "";
      if (dateFrom) dateFrom.value = "";
      if (dateTo) dateTo.value = "";
      applyFilters();
    });
  }

  // -------- Row click -> open invoice detail --------
  for (const tr of rows) {
    tr.style.cursor = "pointer";

    tr.addEventListener("click", function (e) {
      // Si clic sur une action (lien/bouton/form), ne pas rediriger
      if (e.target.closest("a,button,form")) return;

      // On prend le lien "modifier" (page détail), on exclut open / download_pdf
      const editLink = tr.querySelector(
        'a[href^="/factures/"]:not([href$="/open"]):not([href$="/download_pdf"])'
      );

      if (editLink) window.location.href = editLink.getAttribute("href");
    });
  }

  // Expose pour recalcul (ex: suppression AJAX)
  window.recomputeInvoicesKpi = applyFilters;
  // Init
  applyFilters();
})();

// ================= Floating assistant widget =================
(function () {
  const fab = document.getElementById("assistFab");
  const modal = document.getElementById("assistModal");
  const closeBtn = document.getElementById("assistClose");
  const form = document.getElementById("assistForm");
  const input = document.getElementById("assistInput");
  const msgs = document.getElementById("assistMsgs");

  if (!fab || !modal || !form || !input || !msgs) return;

  function open() {
    modal.classList.remove("is-hidden");
    modal.setAttribute("aria-hidden", "false");
    setTimeout(() => input.focus(), 50);
  }

  function close() {
    modal.classList.add("is-hidden");
    modal.setAttribute("aria-hidden", "true");
  }

  function addMsg(text, who) {
    const div = document.createElement("div");
    div.className = "assist-msg " + (who === "me" ? "me" : "bot");
    div.textContent = text;
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
  }

  fab.addEventListener("click", open);
  if (closeBtn) closeBtn.addEventListener("click", close);
  modal.addEventListener("click", function (e) {
    if (e.target === modal) close();
  });

  async function ask(q) {
    const res = await fetch("/assistant/api", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ q }),
    });
    if (!res.ok) throw new Error("HTTP " + res.status);
    return await res.json();
  }

  form.addEventListener("submit", async function (e) {
    e.preventDefault();
    const q = (input.value || "").trim();
    if (!q) return;
    input.value = "";
    addMsg(q, "me");
    const btn = form.querySelector("button[type='submit']");
    if (btn) btn.disabled = true;
    try {
      const data = await ask(q);
      addMsg((data && data.answer) || "(Aucune réponse)", "bot");
    } catch (err) {
      addMsg("Désolé, je n'ai pas pu répondre (erreur technique).", "bot");
    } finally {
      if (btn) btn.disabled = false;
    }
  });
})();

// ================= Dropzone import factures =================
(function () {
  const input = document.getElementById("files");
  const dz = document.getElementById("dropzone");
  const label = document.getElementById("filesLabel");

  if (!input || !dz || !label) return;

  function refreshLabel() {
    const files = Array.from(input.files || []);
    if (!files.length) {
      label.textContent = "Aucun fichier sélectionné";
      return;
    }
    if (files.length === 1) {
      label.textContent = files[0].name;
      return;
    }
    label.textContent = `${files.length} fichiers sélectionnés — ${files[0].name}…`;
  }

  input.addEventListener("change", refreshLabel);

  dz.addEventListener("dragover", (e) => {
    e.preventDefault();
    dz.classList.add("is-dragover");
  });

  dz.addEventListener("dragleave", () => {
    dz.classList.remove("is-dragover");
  });

  dz.addEventListener("drop", (e) => {
    e.preventDefault();
    dz.classList.remove("is-dragover");

    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length) {
      input.files = e.dataTransfer.files;
      refreshLabel();
    }
  });

  refreshLabel();
})();