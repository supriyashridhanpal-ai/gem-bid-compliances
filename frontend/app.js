const API_BASE = "http://127.0.0.1:5000";
const $ = (id) => document.getElementById(id);
let historyRecords = [];
let toastTimer;

function showToast(message) {
  const toast = $("toast");
  toast.textContent = message;
  toast.classList.remove("hidden");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.add("hidden"), 3200);
}
function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
function prettyDate(value) {
  if (!value) return "—";
  const d = new Date(value.includes("Z") || value.includes("+") ? value : value.replace(" ", "T") + "Z");
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString([], {year:"numeric",month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"});
}
function statusClass(status) {
  const s = String(status || "").toLowerCase().replaceAll("_","-");
  if (s === "verified") return "verified";
  if (s === "non-compliant") return "non-compliant";
  return "manual-review";
}
function statusLabel(status) {
  return String(status || "UNKNOWN").replaceAll("_"," ").replaceAll("-"," ").toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
}
function pill(status) {
  return `<span class="status-pill ${statusClass(status)}">${escapeHtml(statusLabel(status))}</span>`;
}
function showPage(name) {
  document.querySelectorAll(".page").forEach(p => p.classList.toggle("active", p.id === `page-${name}`));
  document.querySelectorAll(".nav-item").forEach(b => b.classList.toggle("active", b.dataset.page === name));
  const titles = {overview:"Overview",verify:"New verification",history:"Verification history"};
  $("page-title").textContent = titles[name] || "Overview";
  if (name === "history") loadHistory();
  if (name === "overview") loadHistory(true);
  window.scrollTo({top:0, behavior:"auto"});
}
document.querySelectorAll(".nav-item").forEach(btn => btn.addEventListener("click", () => showPage(btn.dataset.page)));
["header-verify","start-verify"].forEach(id => $(id).addEventListener("click", () => showPage("verify")));
$("view-all").addEventListener("click", () => showPage("history"));

async function checkApi() {
  try {
    const response = await fetch(`${API_BASE}/`);
    if (!response.ok) throw new Error("API unavailable");
    const data = await response.json();
    $("api-dot").classList.add("online");
    $("api-status-text").textContent = data.message ? "API connected" : "API online";
  } catch {
    $("api-dot").classList.remove("online");
    $("api-status-text").textContent = "API offline";
  }
}
async function loadHistory(quiet = false) {
  try {
    const response = await fetch(`${API_BASE}/history`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Unable to load history.");
    historyRecords = Array.isArray(data) ? data : [];
    renderHistory();
    renderRecent();
    updateStats();
    $("history-error").classList.add("hidden");
  } catch (error) {
    historyRecords = [];
    renderHistory();
    renderRecent();
    updateStats();
    if (!quiet) {
      $("history-error").textContent = `${error.message} Make sure the Flask backend is running on port 5000.`;
      $("history-error").classList.remove("hidden");
    }
  }
}
function inferStatus(summary) {
  const match = String(summary || "").match(/Status:\s*([^;]+)/i);
  return match ? match[1].trim() : "MANUAL_REVIEW";
}
function inferScore(summary) {
  const match = String(summary || "").match(/Score:\s*([\d.]+)%/i);
  return match ? Number(match[1]) : 0;
}
function updateStats() {
  $("stat-total").textContent = historyRecords.length;
  $("stat-verified").textContent = historyRecords.filter(r => inferStatus(r.result_summary) === "VERIFIED").length;
  $("stat-noncompliant").textContent = historyRecords.filter(r => inferStatus(r.result_summary) === "NON_COMPLIANT").length;
  $("stat-manual").textContent = historyRecords.filter(r => inferStatus(r.result_summary) === "MANUAL_REVIEW").length;
}
function renderRecent() {
  const target = $("recent-list");
  if (!historyRecords.length) {
    target.innerHTML = `<div class="empty-state">No verifications saved yet.<br>Start by uploading a bid PDF.</div>`;
    return;
  }
  target.innerHTML = historyRecords.slice(0,4).map(r => `
    <div class="recent-item">
      <span class="file-badge">PDF</span>
      <div class="recent-meta"><strong title="${escapeHtml(r.filename)}">${escapeHtml(r.filename)}</strong><small>${escapeHtml(prettyDate(r.created_at))} · Review #${escapeHtml(r.id)}</small></div>
      ${pill(inferStatus(r.result_summary))}
    </div>`).join("");
}
function renderHistory() {
  const query = ($("history-search")?.value || "").toLowerCase().trim();
  const rows = historyRecords.filter(r => String(r.filename || "").toLowerCase().includes(query) || String(r.requirements || "").toLowerCase().includes(query));
  $("history-count").textContent = `${rows.length} record${rows.length === 1 ? "" : "s"}`;
  $("history-body").innerHTML = rows.length ? rows.map(r => `
    <tr>
      <td>#${escapeHtml(r.id)}</td>
      <td><div class="doc-cell"><span class="file-badge">PDF</span><span title="${escapeHtml(r.filename)}">${escapeHtml(r.filename)}</span></div></td>
      <td>${escapeHtml(r.requirements || "—")}</td>
      <td>${pill(inferStatus(r.result_summary))} <span style="color:#8995a5;margin-left:5px">${inferScore(r.result_summary)}%</span></td>
      <td>${escapeHtml(prettyDate(r.created_at))}</td>
      <td><button class="view-btn" data-review-id="${escapeHtml(r.id)}">Details</button></td>
    </tr>`).join("") : `<tr><td colspan="6" class="empty-cell">${query ? "No matching records." : "No verification history yet."}</td></tr>`;
  document.querySelectorAll("[data-review-id]").forEach(btn => btn.addEventListener("click", () => openReview(btn.dataset.reviewId)));
}
$("history-search").addEventListener("input", renderHistory);
$("refresh-history").addEventListener("click", () => loadHistory());
$("pdf-file").addEventListener("change", () => displaySelectedFile());
function displaySelectedFile() {
  const file = $("pdf-file").files[0];
  if (!file) {
    $("file-preview").classList.add("hidden");
    $("upload-zone").classList.remove("hidden");
    return;
  }
  $("file-label").textContent = file.name;
  $("file-name").textContent = file.name;
  $("file-size").textContent = `${(file.size / 1024 / 1024).toFixed(2)} MB`;
  $("upload-zone").classList.add("hidden");
  $("file-preview").classList.remove("hidden");
}
$("remove-file").addEventListener("click", () => { $("pdf-file").value = ""; displaySelectedFile(); });
$("clear-form").addEventListener("click", () => {
  $("verify-form").reset();
  $("requirements").value = "";
  $("form-error").classList.add("hidden");
  $("result-section").classList.add("hidden");
  displaySelectedFile();
});
const zone = $("upload-zone");
["dragenter","dragover"].forEach(event => zone.addEventListener(event, e => {e.preventDefault(); zone.style.borderColor="#2864d7";}));
["dragleave","drop"].forEach(event => zone.addEventListener(event, e => {e.preventDefault(); zone.style.borderColor="";}));
zone.addEventListener("drop", e => {
  const file = e.dataTransfer.files[0];
  if (file) {
    const transfer = new DataTransfer();
    transfer.items.add(file);
    $("pdf-file").files = transfer.files;
    displaySelectedFile();
  }
});
$("verify-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const file = $("pdf-file").files[0];
  const requirements = $("requirements").value.trim();
  $("form-error").classList.add("hidden");
  if (!file) return showFormError("Please select a PDF file.");
  if (!file.name.toLowerCase().endsWith(".pdf")) return showFormError("Only PDF files are supported.");
  if (file.size > 10 * 1024 * 1024) return showFormError("The PDF exceeds the 10 MB limit.");
  if (!requirements || !requirements.split(",").some(x => x.trim())) return showFormError("Enter at least one requirement, separated by commas.");
  const button = $("submit-btn");
  button.disabled = true; button.textContent = "Checking document…";
  const form = new FormData();
  form.append("file", file);
  form.append("requirements", requirements);
  try {
    const response = await fetch(`${API_BASE}/verify`, {method:"POST", body:form});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Verification failed.");
    renderResult(data);
    $("result-section").classList.remove("hidden");
    $("result-section").scrollIntoView({behavior:"auto",block:"start"});
    showToast("Verification completed and saved to history.");
    await loadHistory(true);
  } catch (error) {
    showFormError(`${error.message} Check that your backend is running at ${API_BASE}.`);
  } finally {
    button.disabled = false; button.innerHTML = 'Run verification <span>→</span>';
  }
});
function showFormError(message) {
  $("form-error").textContent = message;
  $("form-error").classList.remove("hidden");
}
function resultGroup(title, items) {
  return `<div class="result-group"><h4>${escapeHtml(title)} <span style="color:#8995a5;font-weight:400">(${items.length})</span></h4>${items.length ? `<ul>${items.map(item => `<li>${escapeHtml(item)}</li>`).join("")}</ul>` : `<div class="none">No items</div>`}</div>`;
}
function renderResult(data) {
  const target = $("result-section");
  target.innerHTML = `
    <div class="result-header"><div><h3>Verification result</h3><p>${escapeHtml(data.filename)} · Review #${escapeHtml(data.review_id)}</p><div style="margin-top:12px">${pill(data.status)}</div></div><div class="score-circle"><strong>${Number(data.score || 0)}%</strong><small>COMPLIANCE</small></div></div>
    <div class="result-summary"><strong style="font-size:11px">Assessment</strong><p>${escapeHtml(data.message || "Review completed.")}</p></div>
    <div class="result-columns">${resultGroup("Matched requirements", data.matched_requirements || [])}${resultGroup("Missing requirements", data.missing_requirements || [])}${resultGroup("Manual review", data.manual_review || [])}</div>
    <div class="notice"><span class="notice-icon">i</span><div><strong>Human confirmation required for critical decisions</strong><p>This result is based on phrase matching in extracted PDF text. It is not independent validation of registrations or statutory compliance.</p></div></div>`;
}
async function openReview(id) {
  $("modal-content").innerHTML = `<div class="empty-state">Loading details…</div>`;
  $("detail-modal").classList.remove("hidden");
  try {
    const response = await fetch(`${API_BASE}/history/${encodeURIComponent(id)}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not load record.");
    $("modal-content").innerHTML = `<dl class="detail-grid">
      <dt>Review ID</dt><dd>#${escapeHtml(data.id)}</dd>
      <dt>Document</dt><dd>${escapeHtml(data.filename)}</dd>
      <dt>Requirements</dt><dd>${escapeHtml(data.requirements)}</dd>
      <dt>Created</dt><dd>${escapeHtml(prettyDate(data.created_at))}</dd>
      <dt>Status</dt><dd>${pill(inferStatus(data.result_summary))}</dd>
      <dt>Score</dt><dd>${inferScore(data.result_summary)}%</dd>
    </dl><div class="detail-summary">${escapeHtml(data.result_summary)}</div>`;
  } catch (error) {
    $("modal-content").innerHTML = `<div class="form-error">${escapeHtml(error.message)}</div>`;
  }
}
$("close-modal").addEventListener("click", () => $("detail-modal").classList.add("hidden"));
$("detail-modal").addEventListener("click", e => {if (e.target === $("detail-modal")) $("detail-modal").classList.add("hidden");});
document.addEventListener("keydown", e => {if (e.key === "Escape") $("detail-modal").classList.add("hidden");});
checkApi();
loadHistory(true);
