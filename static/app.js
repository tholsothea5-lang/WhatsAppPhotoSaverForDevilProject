const $ = id => document.getElementById(id);
let view = "login", allChats = [], ticked = new Set(), lastAct = 0, running = false;

const api = async (url, body) => {
  const r = await fetch(url, body === undefined ? {} : {
    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.error || r.statusText);
  return j;
};

/* theme */
function setTheme(t) {
  document.documentElement.dataset.theme = t;
  $("theme").textContent = t === "dark" ? "☀ Light" : "☾ Dark";
  localStorage.setItem("wps-theme", t);
}
setTheme(localStorage.getItem("wps-theme") || "dark");
$("theme").onclick = () => setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");

/* dates: default = last 7 days */
const local = d => new Date(d - d.getTimezoneOffset() * 6e4).toISOString().slice(0, 16);
$("end").value = local(new Date());
$("start").value = local(new Date(Date.now() - 7 * 864e5));

/* status polling */
async function poll() {
  let s;
  try { s = await api("/api/status"); }
  catch { $("login-note").textContent = "Lost contact with the tool. Is it still running?"; $("login-note").className = "note bad"; return; }

  const ready = s.state === "ready";
  if (ready && view !== "work") enterWork(s);
  if (!ready && view !== "login") leaveWork();

  if (!ready) {
    const qr = $("qr"), wait = $("qr-wait"), note = $("login-note");
    note.className = "note";
    if (s.state === "qr" && s.qr) { qr.src = s.qr; qr.hidden = false; wait.hidden = true; note.textContent = "The workspace opens automatically after linking."; }
    else if (s.state === "starting" && !qr.hidden) {
      // QR rotation can transiently report "starting" — never blank a code that is already on screen.
      wait.hidden = true; note.textContent = "Refreshing the QR code…";
    }
    else {
      qr.hidden = true; wait.hidden = false;
      if (s.state === "error") { wait.textContent = "Couldn't start WhatsApp Web."; note.textContent = s.error; note.className = "note bad"; }
      else if (s.state === "authenticated") { wait.textContent = "Linked — loading your chats…"; }
      else wait.textContent = "Starting WhatsApp Web… the first start can take a minute.";
    }
  } else {
    if (s.me) {
      $("me-name").textContent = s.me.name || "Linked account";
      const av = $("avatar");
      if (s.me.pic && !av.querySelector("img")) { av.innerHTML = ""; const i = new Image(); i.referrerPolicy = "no-referrer"; i.src = s.me.pic; i.onerror = () => { av.textContent = (s.me.name || "?")[0]; }; av.appendChild(i); }
      else if (!s.me.pic) av.textContent = (s.me.name || "?")[0].toUpperCase();
    }
  }
  const st = s.stats;
  $("p-saved").textContent = st.saved + " saved"; $("p-skipped").textContent = st.skipped + " skipped"; $("p-failed").textContent = st.failed + " failed";
  $("s-saved").textContent = st.saved; $("s-skipped").textContent = st.skipped; $("s-failed").textContent = st.failed;
  running = s.job.running;
  $("go").disabled = running; $("go").textContent = running ? "Downloading…" : "Download range";
}

function enterWork() { view = "work"; $("login").hidden = true; $("work").hidden = false; loadChats(); loadRecent(); }
function leaveWork() { view = "login"; $("login").hidden = false; $("work").hidden = true; allChats = []; ticked.clear(); }

/* chats */
async function loadChats() {
  $("rescan").disabled = true; $("count").textContent = "Scanning…";
  try { allChats = await api("/api/chats"); renderChats(); }
  catch (e) { $("count").textContent = "Couldn't load chats: " + e.message; }
  $("rescan").disabled = false;
}
function renderChats() {
  const q = $("search").value.trim().toLowerCase();
  const ul = $("chats"); ul.innerHTML = "";
  const list = allChats.filter(c => c.name.toLowerCase().includes(q));
  for (const c of list) {
    const li = document.createElement("li"), lab = document.createElement("label"), cb = document.createElement("input");
    cb.type = "checkbox"; cb.checked = ticked.has(c.id);
    cb.onchange = () => { cb.checked ? ticked.add(c.id) : ticked.delete(c.id); counts(); };
    lab.append(cb, document.createTextNode(c.name)); li.append(lab); ul.append(li);
  }
  if (!list.length) ul.innerHTML = '<li class="empty">No chats match.</li>';
  $("count").textContent = allChats.length + " chats"; counts();
}
const counts = () => $("ticked").textContent = ticked.size + " ticked";
$("search").oninput = renderChats;
$("rescan").onclick = loadChats;
$("tick-all").onclick = () => { const q = $("search").value.trim().toLowerCase(); allChats.filter(c => c.name.toLowerCase().includes(q)).forEach(c => ticked.add(c.id)); renderChats(); };
$("untick-all").onclick = () => { ticked.clear(); renderChats(); };

/* download */
$("go").onclick = async () => {
  const msg = $("msg"); msg.hidden = true;
  try {
    await api("/api/download", {
      chats: [...ticked], start: new Date($("start").value).getTime(), end: new Date($("end").value).getTime(),
      sender: $("sender").value, skip: $("skip").checked, folder: $("folder").value });
    poll();
  } catch (e) { msg.textContent = e.message; msg.hidden = false; }
};
$("open-folder").onclick = () => api("/api/open-folder", {folder: $("folder").value}).catch(e => { $("msg").textContent = e.message; $("msg").hidden = false; });
$("logout").onclick = async () => { if (confirm("Log out of WhatsApp on this tool?")) { await api("/api/logout", {}).catch(e => alert(e.message)); poll(); } };
$("close").onclick = async () => {
  if (!confirm("Close the tool? You'll need to start it again from the terminal.")) return;
  await api("/api/shutdown", {}).catch(() => {});
  document.body.innerHTML = '<p style="padding:40px;font-family:system-ui">The tool has stopped. You can close this tab.</p>';
};

/* paste a folder path from the clipboard (read by the local server, so no browser permission is needed) */
$("paste-folder").onclick = async () => {
  const input = $("folder"), msg = $("msg");
  msg.hidden = true;
  try {
    const r = await api("/api/paste-path", {});
    if (!r.path) throw new Error("the clipboard is empty");
    input.value = r.path;
    input.focus();
  } catch (e) {
    input.focus(); input.select();
    msg.textContent = "Couldn't paste a folder path: " + e.message + " — press Ctrl+V in the folder box instead.";
    msg.hidden = false;
  }
};

/* activity + recent */
async function pollActivity() {
  if (view !== "work") return;
  const items = await api("/api/activity?since=" + lastAct).catch(() => []);
  if (!items.length) return;
  const ul = $("activity");
  for (const a of items) {
    lastAct = a.n;
    const li = document.createElement("li"), t = document.createElement("time");
    t.textContent = a.t; li.append(t, document.createTextNode(a.msg)); ul.prepend(li);
  }
  while (ul.children.length > 200) ul.lastChild.remove();
  loadRecent();
}
async function loadRecent() {
  const items = await api("/api/recent?n=8").catch(() => []);
  const ul = $("recent"); ul.innerHTML = "";
  for (const r of items) {
    const li = document.createElement("li"), s = document.createElement("small");
    li.textContent = r.name; s.textContent = r.folder; li.append(s); ul.append(li);
  }
}

/* gallery */
$("show-photos").onclick = async () => {
  const items = await api("/api/recent?n=300").catch(() => []);
  const g = $("g-grid"); g.innerHTML = items.length ? "" : '<p class="muted">No downloaded photos yet.</p>';
  for (const r of items) {
    const a = document.createElement("a"), i = new Image();
    a.href = "/api/photo?id=" + encodeURIComponent(r.id); a.target = "_blank"; a.title = r.name;
    i.loading = "lazy"; i.src = a.href; i.alt = r.name; a.append(i); g.append(a);
  }
  $("gallery").showModal();
};
$("g-close").onclick = () => $("gallery").close();

poll(); setInterval(poll, 1500); setInterval(pollActivity, 1000);
