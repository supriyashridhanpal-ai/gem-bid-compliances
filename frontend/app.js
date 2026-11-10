const API_BASE = "http://127.0.0.1:5000";
const $ = id => document.getElementById(id);
let session = null;
let tenders = [];
let adminResults = [];

const pageNames = {
  tenders: ["Available government tenders", "Browse open opportunities and their published requirements."],
  upload: ["Upload bid document", "Submit a PDF bid document for a selected government tender."],
  submissions: ["My submissions", "Track receipt and administrative status of your own submissions."],
  dashboard: ["Admin dashboard", "Monitor incoming bid submissions and verification outcomes."],
  results: ["Company upload results", "Review confidential company verification results."],
  adminTenders: ["Manage tenders", "Publish and manage government tender opportunities."]
};

function esc(v) {
  return String(v ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  }[c]));
}

function toast(msg) {
  const t = $("toast");
  t.textContent = msg;
  t.classList.remove("hidden");
  setTimeout(() => t.classList.add("hidden"), 3500);
}

function showError(id, msg) {
  const e = $(id);
  e.textContent = msg;
  e.classList.remove("hidden");
}

function clearError(id) {
  $(id).classList.add("hidden");
}

function showOnly(id) {
  document.querySelectorAll("main > section").forEach(s => s.classList.add("hidden"));
  $(id).classList.remove("hidden");
  $("logout").classList.toggle("hidden", !["company-app", "admin-app"].includes(id));
}

function go(name) {
  showOnly(name);
}

document.querySelectorAll("[data-go]").forEach(b => b.addEventListener("click", () => go(b.dataset.go)));

$("brand-home").addEventListener("click", e => {
  e.preventDefault();
  if (session) logout();
  else go("auth-choice");
});

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (session?.token) headers.set("Authorization", `Bearer ${session.token}`);
  const response = await fetch(API_BASE + path, { ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || data.message || `Request failed (${response.status})`);
  return data;
}

async function checkApi() {
  try {
    await api("/");
    $("connection").classList.add("online");
    $("connection").lastChild.textContent = " API connected";
  } catch {
    $("connection").classList.remove("online");
    $("connection").lastChild.textContent = " API offline";
  }
}

function readForm(form) {
  return Object.fromEntries(new FormData(form).entries());
}

async function login(formId, errorId, role) {
  clearError(errorId);
  const d = readForm($(formId));
  try {
    const path = role === "company" ? "/auth/company/login" : "/auth/admin/login";
    const data = await api(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(d)
    });
    if (!data.token) throw new Error("The server did not return an authenticated session token.");
    
    session = { token: data.token, role, user: data.user || data.account || {} };
    sessionStorage.setItem("gem_session", JSON.stringify(session));

    if (role === "company") {
      $("company-name").textContent = session.user.name || session.user.company_name || d.username;
      go("company-app");
      showCompanyPage("tenders");
    } else {
      go("admin-app");
      showAdminPage("dashboard");
    }
    toast("Signed in successfully.");
  } catch (e) {
    showError(errorId, e.message + " Ensure the backend implements authentication and role permissions.");
  }
}

$("company-login-form").addEventListener("submit", e => {
  e.preventDefault();
  login("company-login-form", "company-login-error", "company");
});

$("admin-login-form").addEventListener("submit", e => {
  e.preventDefault();
  login("admin-login-form", "admin-login-error", "admin");
});

$("company-register-form").addEventListener("submit", async e => {
  e.preventDefault();
  clearError("company-register-error");
  const submittedForm = e.currentTarget;
  const d = readForm(e.currentTarget);
  try {
    await api("/auth/company/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(d)
    });
    toast("Company account created. Sign in to continue.");
    submittedForm.reset();
    go("company-login");
  } catch (err) {
    showError("company-register-error", err.message + " Ensure the backend implements company registration and password hashing.");
  }
});

function logout() {
  session = null;
  tenders = [];
  adminResults = [];
  sessionStorage.removeItem("gem_session");
  sessionStorage.removeItem("gem_admin_page");
  sessionStorage.removeItem("gem_company_page");
  go("auth-choice");
  toast("Signed out.");
}

$("logout").addEventListener("click", logout);

document.querySelectorAll("[data-company-page]").forEach(b => b.addEventListener("click", () => showCompanyPage(b.dataset.companyPage)));

function showCompanyPage(name) {
  sessionStorage.setItem("gem_company_page", name);
  document.querySelectorAll("[data-company-page]").forEach(b => b.classList.toggle("active", b.dataset.companyPage === name));
  document.querySelectorAll("#company-app .portal-page").forEach(p => p.classList.add("hidden"));
  $("company-page-" + name).classList.remove("hidden");
  $("company-page-title").textContent = pageNames[name][0];
  $("company-page-subtitle").textContent = pageNames[name][1];
  if (name === "tenders") loadTenders();
  if (name === "submissions") loadCompanySubmissions();
}

document.querySelectorAll("[data-admin-page]").forEach(b => b.addEventListener("click", () => showAdminPage(b.dataset.adminPage)));

function showAdminPage(name) {
  sessionStorage.setItem("gem_admin_page", name);
  document.querySelectorAll("[data-admin-page]").forEach(button => {
    button.classList.toggle("active", button.dataset.adminPage === name);
  });

  document.querySelectorAll("#admin-app .portal-page").forEach(page => page.classList.add("hidden"));

  const key = name === "tenders" ? "tenders" : name;
  const adminPage = document.querySelector(`#admin-page-${key}`);

  if (adminPage) {
    adminPage.classList.remove("hidden");
  } else {
    console.error("Admin page not found:", `admin-page-${key}`);
    return;
  }

  const meta = {
    dashboard: ["Admin dashboard", "Monitor incoming bid submissions and verification outcomes."],
    tenders: ["Manage tenders", "Publish and manage government tender opportunities."],
    results: ["Company results", "Review company submissions and compliance outcomes."]
  };

  if (meta[name]) {
    document.querySelector("#admin-page-title").textContent = meta[name][0];
    document.querySelector("#admin-page-subtitle").textContent = meta[name][1];
  }

  if (name === "dashboard" || name === "results") loadAdminResults();
  if (name === "tenders") {
    injectBudgetFieldIfMissing();
    loadAdminTenders();
  }
}

// Injects the Budget input field into the publish tender form if missing in HTML
function injectBudgetFieldIfMissing() {
  const form = $("tender-form");
  if (!form || $("tender-budget-input")) return;

  const submitBtn = form.querySelector("button[type=submit]");
  const container = document.createElement("div");
  container.style.cssText = "margin-bottom: 14px;";
  container.innerHTML = `
    <label for="tender-budget-input" style="display:block; font-weight:600; margin-bottom:6px; font-size:0.9rem; color:#334155;">
      Tender Budget (in Lakhs)
    </label>
    <input type="number" id="tender-budget-input" name="budget" placeholder="e.g. 50" min="5" max="500" value="50" required style="width:100%; padding:10px 12px; border:1px solid #cbd5e1; border-radius:6px; font-size:0.95rem; box-sizing:border-box;" />
  `;

  if (submitBtn) {
    form.insertBefore(container, submitBtn);
  } else {
    form.appendChild(container);
  }
}

function tenderList(data) {
  return Array.isArray(data) ? data : (data.tenders || data.items || []);
}

// ============================================================================
// FEATURE 2: BST RANGE SEARCH FOR TENDERS
// ============================================================================
window.applyBSTRangeFilter = async function() {
  const minVal = $("bst-min-budget")?.value || 0;
  const maxVal = $("bst-max-budget")?.value || 500;

  $("tenders-list").innerHTML = '<div class="empty">Searching BST in C Engine…</div>';
  try {
    const filtered = await api(`/tenders/filter?min=${minVal}&max=${maxVal}`);
    tenders = Array.isArray(filtered) ? filtered : [];
    renderTenders();
    toast(`BST range search [${minVal}L - ${maxVal}L] returned ${tenders.length} tenders.`);
  } catch (err) {
    showError("tenders-error", "BST Filter failed: " + err.message);
  }
};

window.resetBSTRangeFilter = async function() {
  if ($("bst-min-budget")) $("bst-min-budget").value = "";
  if ($("bst-max-budget")) $("bst-max-budget").value = "";
  await loadTenders();
};

async function loadTenders() {
  $("tenders-list").innerHTML = '<div class="empty">Loading tenders…</div>';
  try {
    tenders = tenderList(await api("/tenders"));
    renderTenders();
    fillTenderSelect();
  } catch (e) {
    $("tenders-list").innerHTML = '<div class="empty">Tenders could not be loaded.</div>';
    showError("tenders-error", e.message + " The backend needs a GET /tenders endpoint.");
  }
}

function renderTenders() {
  const filterToolbar = `
    <div style="grid-column: 1 / -1; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 18px; margin-bottom: 12px; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
      <div style="display: flex; align-items: center; gap: 8px;">
        <span style="font-weight: 700; color: #0f172a; font-size: 0.95rem;">🌳 Filter Turnover / Budget (BST Range Search):</span>
      </div>
      <div style="display: flex; align-items: center; gap: 10px;">
        <input type="number" id="bst-min-budget" placeholder="Min (Lakhs)" style="width: 110px; padding: 6px 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 0.85rem;" />
        <span style="color: #64748b;">to</span>
        <input type="number" id="bst-max-budget" placeholder="Max (Lakhs)" style="width: 110px; padding: 6px 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 0.85rem;" />
        <button type="button" class="btn btn-primary" style="padding: 6px 14px; font-size: 0.85rem;" onclick="applyBSTRangeFilter()">Filter</button>
        <button type="button" class="btn" style="padding: 6px 12px; font-size: 0.85rem; background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1;" onclick="resetBSTRangeFilter()">Reset</button>
      </div>
    </div>
  `;

  $("tenders-list").innerHTML = filterToolbar + (tenders.length
    ? tenders.map(t => `
        <article class="tender-card">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <span class="tag">OPEN TENDER</span>
            <span style="font-size: 0.8rem; font-weight: 700; color: #0284c7; background: #e0f2fe; padding: 3px 8px; border-radius: 4px;">
              Budget: ${esc(t.budget ?? 50)} Lakhs
            </span>
          </div>
          <h3 style="margin-top: 8px;">${esc(t.title || t.name || "Untitled tender")}</h3>
          <p><b>Tender ID:</b> #${esc(t.id ?? t.tender_id ?? "—")}</p>
          <p><b>Requirements</b><br>${esc(Array.isArray(t.requirements) ? t.requirements.join(", ") : t.requirements || "See tender notice")}</p>
          <button class="btn btn-primary" data-apply="${esc(t.id ?? t.tender_id)}">Submit a bid</button>
        </article>
      `).join("")
    : '<div class="empty" style="grid-column: 1 / -1;">No tenders found within this budget range in the BST.</div>');

  document.querySelectorAll("[data-apply]").forEach(b => b.addEventListener("click", () => {
    fillTenderSelect();
    $("tender-select").value = b.dataset.apply;
    showCompanyPage("upload");
  }));
}

function fillTenderSelect() {
  const s = $("tender-select");
  const current = s.value;
  s.innerHTML = '<option value="">Select a tender</option>' + tenders.map(t => `<option value="${esc(t.id ?? t.tender_id)}">${esc(t.title || t.name || "Tender")}</option>`).join("");
  if (current) s.value = current;
}

$("refresh-tenders").addEventListener("click", loadTenders);

$("submission-form").addEventListener("submit", async e => {
  e.preventDefault();
  clearError("submission-error");
  const form = e.currentTarget;
  const file = form.elements.file.files[0];
  if (!file) return showError("submission-error", "Choose a PDF document.");
  if (!file.name.toLowerCase().endsWith(".pdf")) return showError("submission-error", "Only PDF files are supported.");
  if (file.size > 10 * 1024 * 1024) return showError("submission-error", "Maximum upload size is 10 MB.");

  const fd = new FormData();
  fd.append("file", file);
  fd.append("tender_id", form.elements.tender_id.value);
  fd.append("note", form.elements.note.value);

  const btn = form.querySelector("button[type=submit]");
  btn.disabled = true;
  btn.textContent = "Submitting…";

  try {
    await api("/company/submissions", { method: "POST", body: fd });
    form.reset();
    toast("Bid submitted! Placed in FIFO verification queue.");
    showCompanyPage("submissions");
  } catch (err) {
    showError("submission-error", err.message + " The backend needs an authenticated POST /company/submissions endpoint.");
  } finally {
    btn.disabled = false;
    btn.textContent = "Submit bid document";
  }
});

// ============================================================================
// RESET COMPANY SUBMISSIONS
// ============================================================================
window.resetCompanySubmissions = async function() {
  if (!confirm("Are you sure you want to reset all your submitted bids? This cannot be undone.")) return;
  try {
    const res = await api("/company/submissions/reset", { method: "POST" });
    toast(res.message || "Your submissions have been reset.");
    await loadCompanySubmissions();
  } catch (err) {
    alert("Reset failed: " + err.message);
  }
};

async function loadCompanySubmissions() {
  let resetBtn = $("company-reset-submissions-btn");
  if (!resetBtn && $("refresh-submissions")) {
    resetBtn = document.createElement("button");
    resetBtn.id = "company-reset-submissions-btn";
    resetBtn.type = "button";
    resetBtn.style.cssText = "background: #ef4444; color: white; margin-left: 10px; border: none; padding: 6px 14px; border-radius: 6px; font-weight: 600; cursor: pointer;";
    resetBtn.textContent = "🗑️ Reset My Submissions";
    resetBtn.onclick = resetCompanySubmissions;
    $("refresh-submissions").parentNode.appendChild(resetBtn);
  }

  $("company-submissions-body").innerHTML = '<tr><td colspan="5" class="empty">Loading submissions…</td></tr>';
  try {
    const d = await api("/company/submissions");
    const rows = Array.isArray(d) ? d : (d.submissions || []);
    $("company-submissions-body").innerHTML = rows.length
      ? rows.map(s => {
          const st = s.submission_status || s.status || "Submitted";
          return `
            <tr>
              <td>#${esc(s.id ?? s.submission_id ?? "—")}</td>
              <td>${esc(s.tender_title || s.tender || "—")}</td>
              <td>${esc(s.filename || "—")}</td>
              <td>${esc(s.created_at || s.submitted_at || "—")}</td>
              <td><span class="status ${st.toLowerCase() === 'queued' ? 'manual-review' : ''}">${esc(st)}</span></td>
            </tr>
          `;
        }).join("")
      : '<tr><td colspan="5" class="empty">No submissions found.</td></tr>';
  } catch (e) {
    $("company-submissions-body").innerHTML = '<tr><td colspan="5" class="empty">Submissions could not be loaded.</td></tr>';
    showError("submissions-error", e.message + " The backend needs GET /company/submissions.");
  }
}

$("refresh-submissions").addEventListener("click", loadCompanySubmissions);

$("tender-form").addEventListener("submit", async e => {
  e.preventDefault();
  clearError("tender-error");
  const d = readForm(e.currentTarget);
  try {
    await api("/admin/tenders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(d)
    });
    e.target.closest("form").reset();
    toast("Tender published.");
    await loadAdminTenders();
  } catch (err) {
    showError("tender-error", err.message + " The backend needs an admin-only POST /admin/tenders endpoint.");
  }
});

window.deleteTender = async function(event, tenderId) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }
  if (!tenderId || tenderId === "—") return;
  if (!confirm(`Are you sure you want to delete Tender #${tenderId}?`)) return;

  try {
    const res = await api(`/admin/tenders/${tenderId}`, { method: "DELETE" });
    toast(res.message || `Tender #${tenderId} deleted successfully.`);
    await loadAdminTenders();
  } catch (err) {
    alert("Delete failed: " + err.message);
  }
};

async function loadAdminTenders() {
  injectBudgetFieldIfMissing();
  $("admin-tenders-list").innerHTML = '<div class="empty">Loading tenders…</div>';
  try {
    const list = tenderList(await api("/admin/tenders"));
    $("admin-tenders-list").innerHTML = list.length
      ? list.map(t => {
          const tid = t.id ?? t.tender_id;
          return `
            <article class="tender-card">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <h3>${esc(t.title || "Untitled tender")}</h3>
                <span style="font-size: 0.8rem; font-weight: 700; color: #0284c7; background: #e0f2fe; padding: 3px 8px; border-radius: 4px;">
                  Budget: ${esc(t.budget ?? 50)}L
                </span>
              </div>
              <p><b>Tender ID:</b> #${esc(tid ?? "—")}</p>
              <p>${esc(t.requirements || "")}</p>
              <div style="display:flex; justify-content:space-between; align-items:center; margin-top:12px; gap:8px;">
                <span class="tag">${esc(t.status || "PUBLISHED")}</span>
                <button type="button" class="btn" style="background:#dc2626; color:#ffffff; border:none; padding:6px 14px; border-radius:6px; font-weight:600; cursor:pointer;" onclick="deleteTender(event, ${tid})">
                  🗑️ Delete
                </button>
              </div>
            </article>
          `;
        }).join("")
      : '<div class="empty">No tenders found.</div>';
  } catch (e) {
    $("admin-tenders-list").innerHTML = '<div class="empty">Tender list unavailable.</div>';
    showError("tender-error", e.message + " The backend needs GET /admin/tenders.");
  }
}

// ============================================================================
// CONCEPT 2: QUEUE (FIFO BID PROCESSING IN C)
// ============================================================================
window.processNextQueuedBid = async function() {
  try {
    const res = await api("/admin/queue/process_next", { method: "POST" });
    toast(res.message || "Queue processed.");
    await loadAdminResults();
  } catch (err) {
    alert("Queue processing error: " + err.message);
  }
};

window.resetAdminDashboard = async function() {
  if (!confirm("Reset all incoming bid submissions, evaluation queues, and test results back to 0?")) return;
  try {
    const res = await api("/admin/reset", { method: "POST" });
    toast(res.message || "All submissions and queues have been reset.");
    await loadAdminResults();
  } catch (err) {
    alert("Reset failed: " + err.message);
  }
};

// ============================================================================
// FEATURE 4: BINARY MAX-HEAP LEADERBOARD
// ============================================================================
window.viewLeaderboardHeap = async function() {
  try {
    const data = await api("/admin/leaderboard");
    const groups = data.tender_leaderboards || [];

    if (!groups.length) {
      alert("No verified bids available yet. Process pending bids in the queue first.");
      return;
    }

    const sectionsHtml = groups.map(g => {
      const rows = (g.leaderboard && g.leaderboard.length)
        ? g.leaderboard.map(b => `
            <tr style="border-bottom: 1px solid #e2e8f0;">
              <td style="padding: 10px; font-weight: bold; color: ${b.rank === 1 ? '#d97706' : b.rank === 2 ? '#64748b' : '#b45309'};">
                ${b.rank === 1 ? '🥇 #1 (L1/H1)' : b.rank === 2 ? '🥈 #2' : b.rank === 3 ? '🥉 #3' : '#' + b.rank}
              </td>
              <td style="padding: 10px; font-weight: 600;">${esc(b.company_name)}</td>
              <td style="padding: 10px; font-weight: bold; color: ${b.score >= 80 ? '#16a34a' : b.score >= 50 ? '#ca8a04' : '#dc2626'};">
                ${b.score}%
              </td>
              <td style="padding: 10px; color: #64748b;">Sub #${b.submission_id}</td>
            </tr>
          `).join("")
        : `<tr><td colspan="4" style="padding: 12px; text-align: center; color: #94a3b8;">No bids verified for this tender yet.</td></tr>`;

      return `
        <div style="margin-bottom: 22px; background: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
          <div style="background: #f1f5f9; padding: 10px 14px; border-bottom: 1px solid #cbd5e1; display: flex; justify-content: space-between; align-items: center;">
            <strong style="color: #0369a1; font-size: 0.95rem;">📌 ${esc(g.tender_title)}</strong>
            <span style="font-size: 0.8rem; background: #e0f2fe; color: #0284c7; padding: 2px 8px; border-radius: 4px; font-weight: 600;">
              ${g.total_bids} Bids Evaluated
            </span>
          </div>
          <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 0.88rem;">
            <thead>
              <tr style="background: #fafafa; border-bottom: 1px solid #e2e8f0; color: #475569;">
                <th style="padding: 8px 10px;">Rank</th>
                <th style="padding: 8px 10px;">Contractor / Company</th>
                <th style="padding: 8px 10px;">Score</th>
                <th style="padding: 8px 10px;">ID</th>
              </tr>
            </thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      `;
    }).join("");

    const existing = document.getElementById("heap-leaderboard-modal");
    if (existing) existing.remove();

    const modal = document.createElement("div");
    modal.id = "heap-leaderboard-modal";
    modal.style.cssText = "position: fixed; inset: 0; background: rgba(15, 23, 42, 0.7); display: flex; align-items: center; justify-content: center; z-index: 9999; backdrop-filter: blur(4px);";
    modal.innerHTML = `
      <div style="background: white; border-radius: 12px; width: 92%; max-width: 720px; padding: 22px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.2); max-height: 85vh; display: flex; flex-direction: column;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
          <div>
            <h3 style="margin: 0; color: #0f172a; font-size: 1.25rem;">🏆 Tender Bidder Leaderboard (Binary Max-Heap)</h3>
            <p style="margin: 4px 0 0; color: #64748b; font-size: 0.85rem;">Ranked independently per tender from highest to lowest score via Priority Queue</p>
          </div>
          <button style="background: transparent; border: none; font-size: 1.5rem; cursor: pointer; color: #94a3b8;" onclick="document.getElementById('heap-leaderboard-modal').remove()">✕</button>
        </div>
        <div style="overflow-y: auto; flex: 1; padding-right: 4px;">
          ${sectionsHtml}
        </div>
        <div style="text-align: right; margin-top: 14px; border-top: 1px solid #e2e8f0; padding-top: 12px;">
          <button class="btn btn-primary" onclick="document.getElementById('heap-leaderboard-modal').remove()">Close</button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
  } catch (err) {
    alert("Leaderboard calculation failed: " + err.message);
  }
};

function normalizeStatus(v) {
  return String(v || "MANUAL_REVIEW").toUpperCase().replaceAll("-", "_");
}

function statusBadge(v) {
  const s = normalizeStatus(v);
  const c = s.toLowerCase().replaceAll("_", "-");
  return `<span class="status ${esc(c)}">${esc(s.replaceAll("_", " "))}</span>`;
}

async function loadAdminResults() {
  $("admin-recent").innerHTML = '<div class="empty">Loading results…</div>';
  try {
    const d = await api("/admin/results");
    adminResults = Array.isArray(d) ? d : (d.results || d.submissions || []);
    
    const pendingBids = adminResults.filter(r => (r.submission_status || r.status) === "Queued" || (r.compliance_status || r.status) === "QUEUED");
    
    const counts = { VERIFIED: 0, NON_COMPLIANT: 0, MANUAL_REVIEW: 0, QUEUED: pendingBids.length };
    adminResults.forEach(r => {
      const s = normalizeStatus(r.compliance_status || r.status || r.verification_status);
      if (counts[s] !== undefined) counts[s]++;
    });
    
    $("admin-total").textContent = adminResults.length;
    $("admin-verified").textContent = counts.VERIFIED;
    $("admin-noncompliant").textContent = counts.NON_COMPLIANT;
    $("admin-manual").textContent = counts.MANUAL_REVIEW;

    const queueBanner = `
      <div style="background: linear-gradient(135deg, #1e293b, #0f172a); color: white; border-radius: 10px; padding: 18px 24px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 12px rgba(0,0,0,0.15); flex-wrap: wrap; gap: 14px;">
        <div>
          <h3 style="margin: 0 0 6px; font-size: 1.15rem; color: #38bdf8;">📥 FIFO Bid Processing & Priority Queue</h3>
          <p style="margin: 0; font-size: 0.9rem; color: #94a3b8;">
            Pending Submissions in Queue: <strong style="color: #f8fafc; font-size: 1.05rem;">${pendingBids.length}</strong>
          </p>
        </div>
        <div style="display: flex; gap: 10px; flex-wrap: wrap;">
          <button type="button" class="btn" style="background: #0284c7; color: white; border: none; padding: 9px 16px; border-radius: 8px; font-weight: 600; cursor: pointer;" onclick="processNextQueuedBid()">
            ⚡ Process Next (FIFO)
          </button>
          <button type="button" class="btn" style="background: #f59e0b; color: #0f172a; border: none; padding: 9px 16px; border-radius: 8px; font-weight: 700; cursor: pointer;" onclick="viewLeaderboardHeap()">
            🏆 Top Bidders (Max-Heap)
          </button>
          <button type="button" class="btn" style="background: #dc2626; color: white; border: none; padding: 9px 16px; border-radius: 8px; font-weight: 600; cursor: pointer;" onclick="resetAdminDashboard()">
            🗑️ Reset Queue & Results
          </button>
        </div>
      </div>
    `;

    $("admin-recent").innerHTML = queueBanner + (adminResults.slice(0, 4).map(r => `
      <article class="result-card">
        <h3>${esc(r.filename || "Bid submission")}</h3>
        <p><b>Company:</b> ${esc(r.company_name || r.company || "—")}</p>
        <p><b>Tender:</b> ${esc(r.tender_title || "—")}</p>
        <p><b>Status:</b> ${statusBadge(r.compliance_status || r.status || r.verification_status)}</p>
        <p><b>Score:</b> ${r.score !== null && r.score !== undefined ? esc(r.score) + '%' : '— (In Queue)'}</p>
      </article>
    `).join("") || '<div class="empty">No company submissions found.</div>');

    $("admin-results-body").innerHTML = adminResults.length
      ? adminResults.map((r, i) => `
          <tr>
            <td>#${esc(r.id ?? r.submission_id ?? i + 1)}</td>
            <td>${esc(r.company_name || r.company || "—")}</td>
            <td>${esc(r.tender_title || "—")}</td>
            <td>${esc(r.filename || "—")}</td>
            <td>${statusBadge(r.compliance_status || r.status || r.verification_status)}</td>
            <td>${r.score !== null && r.score !== undefined ? esc(r.score) + '%' : '—'}</td>
            <td>${esc(r.details || r.message || "Pending evaluation")}</td>
          </tr>
        `).join("")
      : '<tr><td colspan="7" class="empty">No results found.</td></tr>';
  } catch (e) {
    $("admin-recent").innerHTML = '<div class="empty">Admin results are unavailable.</div>';
    showError("admin-results-error", e.message + " The backend needs an admin-only GET /admin/results endpoint.");
    $("admin-results-body").innerHTML = '<tr><td colspan="7" class="empty">Results endpoint unavailable.</td></tr>';
  }
}

$("admin-refresh").addEventListener("click", loadAdminResults);
$("admin-results-refresh").addEventListener("click", loadAdminResults);

// ============================================================================
// RESTORE SESSION ON LOAD / RELOAD
// ============================================================================
checkApi();

const savedSession = sessionStorage.getItem("gem_session");
if (savedSession) {
  try {
    session = JSON.parse(savedSession);
    if (session?.role === "company") {
      $("company-name").textContent = session.user.name || session.user.company_name || session.user.username || "Company";
      go("company-app");
      const targetPage = sessionStorage.getItem("gem_company_page") || "tenders";
      showCompanyPage(targetPage);
    } else if (session?.role === "admin") {
      go("admin-app");
      const targetPage = sessionStorage.getItem("gem_admin_page") || "dashboard";
      showAdminPage(targetPage);
    } else {
      go("auth-choice");
    }
  } catch (err) {
    session = null;
    go("auth-choice");
  }
} else {
  go("auth-choice");
}