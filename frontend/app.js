const API_BASE = "http://127.0.0.1:5000";
const $ = id => document.getElementById(id);
let session = null;
let tenders = [];
let adminResults = [];
const pageNames = {
  tenders:["Available government tenders","Browse open opportunities and their published requirements."],
  upload:["Upload bid document","Submit a PDF bid document for a selected government tender."],
  submissions:["My submissions","Track receipt and administrative status of your own submissions."],
  dashboard:["Admin dashboard","Monitor incoming bid submissions and verification outcomes."],
  results:["Company upload results","Review confidential company verification results."],
  adminTenders:["Manage tenders","Publish and manage government tender opportunities."]
};
function esc(v){return String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
function toast(msg){const t=$("toast");t.textContent=msg;t.classList.remove("hidden");setTimeout(()=>t.classList.add("hidden"),3500);}
function showError(id,msg){const e=$(id);e.textContent=msg;e.classList.remove("hidden");}
function clearError(id){$(id).classList.add("hidden");}
function showOnly(id){document.querySelectorAll("main > section").forEach(s=>s.classList.add("hidden"));$(id).classList.remove("hidden");$("logout").classList.toggle("hidden",!["company-app","admin-app"].includes(id));}
function go(name){showOnly(name);}
document.querySelectorAll("[data-go]").forEach(b=>b.addEventListener("click",()=>go(b.dataset.go)));
$("brand-home").addEventListener("click",e=>{e.preventDefault();if(session)logout();else go("auth-choice");});
async function api(path, options={}) {
  const headers = new Headers(options.headers||{});
  if(session?.token) headers.set("Authorization",`Bearer ${session.token}`);
  const response=await fetch(API_BASE+path,{...options,headers});
  const data=await response.json().catch(()=>({}));
  if(!response.ok) throw new Error(data.error||data.message||`Request failed (${response.status})`);
  return data;
}
async function checkApi(){try{await api("/");$("connection").classList.add("online");$("connection").lastChild.textContent=" API connected";}catch{$("connection").classList.remove("online");$("connection").lastChild.textContent=" API offline";}}
function readForm(form){return Object.fromEntries(new FormData(form).entries());}
async function login(formId,errorId,role){
  clearError(errorId);const d=readForm($(formId));
  try{
    const path=role==="company"?"/auth/company/login":"/auth/admin/login";
    const data=await api(path,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(d)});
    if(!data.token) throw new Error("The server did not return an authenticated session token.");
    session={token:data.token,role,user:data.user||data.account||{}};
    if(role==="company"){ $("company-name").textContent=session.user.name||session.user.company_name||d.username;go("company-app");await loadTenders();showCompanyPage("tenders");}
    else{go("admin-app");showAdminPage("dashboard");await loadAdminResults();}
    toast("Signed in successfully.");
  }catch(e){showError(errorId,e.message+" Ensure the backend implements authentication and role permissions.");}
}
$("company-login-form").addEventListener("submit",e=>{e.preventDefault();login("company-login-form","company-login-error","company");});
$("admin-login-form").addEventListener("submit",e=>{e.preventDefault();login("admin-login-form","admin-login-error","admin");});
$("company-register-form").addEventListener("submit",async e=>{
  e.preventDefault();clearError("company-register-error");const submittedForm = e.currentTarget;const d=readForm(e.currentTarget);
  try{await api("/auth/company/register",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(d)});toast("Company account created. Sign in to continue.");submittedForm.reset();go("company-login");}
  catch(err){showError("company-register-error",err.message+" Ensure the backend implements company registration and password hashing.");}
});
function logout(){session=null;tenders=[];adminResults=[];go("auth-choice");toast("Signed out.");}
$("logout").addEventListener("click",logout);
document.querySelectorAll("[data-company-page]").forEach(b=>b.addEventListener("click",()=>showCompanyPage(b.dataset.companyPage)));
function showCompanyPage(name){
  document.querySelectorAll("[data-company-page]").forEach(b=>b.classList.toggle("active",b.dataset.companyPage===name));
  document.querySelectorAll("#company-app .portal-page").forEach(p=>p.classList.add("hidden"));
  $("company-page-"+name).classList.remove("hidden");
  $("company-page-title").textContent=pageNames[name][0];$("company-page-subtitle").textContent=pageNames[name][1];
  if(name==="tenders")loadTenders();if(name==="submissions")loadCompanySubmissions();
}
document.querySelectorAll("[data-admin-page]").forEach(b=>b.addEventListener("click",()=>showAdminPage(b.dataset.adminPage)));

function showAdminPage(name) {
  document.querySelectorAll("[data-admin-page]").forEach((button) => {
    button.classList.toggle("active", button.dataset.adminPage === name);
  });

  document
    .querySelectorAll("#admin-app .portal-page")
    .forEach((page) => page.classList.add("hidden"));

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
  if (name === "tenders") loadAdminTenders();
}

function tenderList(data){return Array.isArray(data)?data:(data.tenders||data.items||[]);}
async function loadTenders(){
  $("tenders-list").innerHTML='<div class="empty">Loading tenders…</div>';
  try{tenders=tenderList(await api("/tenders"));renderTenders();fillTenderSelect();}
  catch(e){$("tenders-list").innerHTML='<div class="empty">Tenders could not be loaded.</div>';showError("tenders-error",e.message+" The backend needs a GET /tenders endpoint that returns published tenders only.");}
}
function renderTenders(){
  $("tenders-list").innerHTML=tenders.length?tenders.map(t=>`<article class="tender-card"><span class="tag">OPEN TENDER</span><h3>${esc(t.title||t.name||"Untitled tender")}</h3><p><b>Tender ID:</b> ${esc(t.id??t.tender_id??"—")}</p><p><b>Requirements</b><br>${esc(Array.isArray(t.requirements)?t.requirements.join(", "):t.requirements||"See tender notice")}</p><button class="btn btn-primary" data-apply="${esc(t.id??t.tender_id)}">Submit a bid</button></article>`).join(""):'<div class="empty">No open tenders are currently available.</div>';
  document.querySelectorAll("[data-apply]").forEach(b=>b.addEventListener("click",()=>{fillTenderSelect();$("tender-select").value=b.dataset.apply;showCompanyPage("upload");}));
}
function fillTenderSelect(){const s=$("tender-select");const current=s.value;s.innerHTML='<option value="">Select a tender</option>'+tenders.map(t=>`<option value="${esc(t.id??t.tender_id)}">${esc(t.title||t.name||"Tender")}</option>`).join("");if(current)s.value=current;}
$("refresh-tenders").addEventListener("click",loadTenders);
$("submission-form").addEventListener("submit",async e=>{
  e.preventDefault();clearError("submission-error");const form=e.currentTarget;const file=form.elements.file.files[0];
  if(!file)return showError("submission-error","Choose a PDF document.");
  if(!file.name.toLowerCase().endsWith(".pdf"))return showError("submission-error","Only PDF files are supported.");
  if(file.size>10*1024*1024)return showError("submission-error","Maximum upload size is 10 MB.");
  const fd=new FormData();fd.append("file",file);fd.append("tender_id",form.elements.tender_id.value);fd.append("note",form.elements.note.value);
  const btn=form.querySelector("button[type=submit]");btn.disabled=true;btn.textContent="Submitting…";
  try{await api("/company/submissions",{method:"POST",body:fd});form.reset();toast("Bid document submitted. Government review results are not shown here.");showCompanyPage("submissions");}
  catch(err){showError("submission-error",err.message+" The backend needs an authenticated POST /company/submissions endpoint that stores the submission and does not return confidential results.");}
  finally{btn.disabled=false;btn.textContent="Submit bid document";}
});
async function loadCompanySubmissions(){
  $("company-submissions-body").innerHTML='<tr><td colspan="5" class="empty">Loading submissions…</td></tr>';
  try{const d=await api("/company/submissions");const rows=Array.isArray(d)?d:(d.submissions||[]);
    $("company-submissions-body").innerHTML=rows.length?rows.map(s=>`<tr><td>#${esc(s.id??s.submission_id??"—")}</td><td>${esc(s.tender_title||s.tender||"—")}</td><td>${esc(s.filename||"—")}</td><td>${esc(s.created_at||s.submitted_at||"—")}</td><td><span class="status">${esc(s.submission_status||s.status||"Submitted")}</span></td></tr>`).join(""):'<tr><td colspan="5" class="empty">No submissions yet.</td></tr>';
  }catch(e){$("company-submissions-body").innerHTML='<tr><td colspan="5" class="empty">Submissions could not be loaded.</td></tr>';showError("submissions-error",e.message+" The backend needs GET /company/submissions filtered to the signed-in company and must omit compliance results.");}
}
$("refresh-submissions").addEventListener("click",loadCompanySubmissions);
$("tender-form").addEventListener("submit",async e=>{
  e.preventDefault();clearError("tender-error");const d=readForm(e.currentTarget);
  try{await api("/admin/tenders",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(d)});e.target.closest("form").reset();toast("Tender published.");await loadAdminTenders();await loadTenders();}
  catch(err){showError("tender-error",err.message+" The backend needs an admin-only POST /admin/tenders endpoint.");}
});
async function loadAdminTenders(){
  $("admin-tenders-list").innerHTML='<div class="empty">Loading tenders…</div>';
  try{const list=tenderList(await api("/admin/tenders"));$("admin-tenders-list").innerHTML=list.length?list.map(t=>`<article class="tender-card"><h3>${esc(t.title||"Untitled tender")}</h3><p>${esc(t.requirements||"")}</p><span class="tag">${esc(t.status||"PUBLISHED")}</span></article>`).join(""):'<div class="empty">No tenders found.</div>';}
  catch(e){$("admin-tenders-list").innerHTML='<div class="empty">Tender list unavailable.</div>';showError("tender-error",e.message+" The backend needs GET /admin/tenders.");}
}
function normalizeStatus(v){return String(v||"MANUAL_REVIEW").toUpperCase().replaceAll("-","_");}
function statusBadge(v){const s=normalizeStatus(v);const c=s.toLowerCase().replaceAll("_","-");return `<span class="status ${esc(c)}">${esc(s.replaceAll("_"," "))}</span>`;}
async function loadAdminResults(){
  $("admin-recent").innerHTML='<div class="empty">Loading results…</div>';
  try{
    const d=await api("/admin/results");adminResults=Array.isArray(d)?d:(d.results||d.submissions||[]);
    const counts={VERIFIED:0,NON_COMPLIANT:0,MANUAL_REVIEW:0};adminResults.forEach(r=>{const s=normalizeStatus(
  r.compliance_status || r.status || r.verification_status
);if(counts[s]!==undefined)counts[s]++;});
    $("admin-total").textContent=adminResults.length;$("admin-verified").textContent=counts.VERIFIED;$("admin-noncompliant").textContent=counts.NON_COMPLIANT;$("admin-manual").textContent=counts.MANUAL_REVIEW;
    $("admin-recent").innerHTML=adminResults.slice(0,4).map(r=>`<article class="result-card"><h3>${esc(r.filename||"Bid submission")}</h3><p><b>Company:</b> ${esc(r.company_name||r.company||"—")}</p><p><b>Tender:</b> ${esc(r.tender_title||"—")}</p><p><b>Status:</b> ${statusBadge(
  r.compliance_status || r.status || r.verification_status
)}</p><p><b>Score:</b> ${esc(r.score??"—")}${r.score===undefined?"":"%"}</p></article>`).join("")||'<div class="empty">No company submissions found.</div>';
    $("admin-results-body").innerHTML=adminResults.length?adminResults.map((r,i)=>`<tr><td>#${esc(r.id??r.submission_id??i+1)}</td><td>${esc(r.company_name||r.company||"—")}</td><td>${esc(r.tender_title||"—")}</td><td>${esc(r.filename||"—")}</td><td>${statusBadge(
  r.compliance_status || r.status || r.verification_status
)}</td><td>${esc(r.score??"—")}${r.score===undefined?"":"%"}</td><td>${esc(r.details||r.message||"Human review may be required.")}</td></tr>`).join(""):'<tr><td colspan="7" class="empty">No results found.</td></tr>';
  }catch(e){$("admin-recent").innerHTML='<div class="empty">Admin results are unavailable.</div>';showError("admin-results-error",e.message+" The backend needs an admin-only GET /admin/results endpoint that joins submissions, company, tender and verification result data.");$("admin-results-body").innerHTML='<tr><td colspan="7" class="empty">Results endpoint unavailable.</td></tr>';}
}
$("admin-refresh").addEventListener("click",loadAdminResults);$("admin-results-refresh").addEventListener("click",loadAdminResults);
checkApi();go("auth-choice");
