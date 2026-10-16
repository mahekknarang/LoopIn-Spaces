const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const pageState = { venues: [], slots: [], grid: {}, day: "", date: "", visibleNames: null };

async function api(url, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (!(options.body instanceof FormData)) headers["Content-Type"] ||= "application/json";
  const response = await fetch(url, { ...options, headers });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error || "That didn’t work. Please try again.");
  return body;
}

function toast(message) {
  const box = $("#toast");
  if (!box) return;
  box.textContent = message;
  box.classList.add("show");
  setTimeout(() => box.classList.remove("show"), 3200);
}

function localDate(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function openBooking(venue, dateText, firstSlot, suggestedHours = 1) {
  const startIndex = pageState.slots.indexOf(firstSlot);
  const endIndex = Math.min(startIndex + suggestedHours - 1, pageState.slots.length - 1);
  const options = pageState.slots.slice(startIndex).map((slot, offset) => {
    const index = startIndex + offset;
    const separatedByBreak = index > startIndex && ((pageState.slots[index - 1] === "9:45-10:40" && slot === "11:15-12:10") || (pageState.slots[index - 1] === "1:15-2:10" && slot === "2:45-3:40"));
    return `<option value="${slot}" ${index === endIndex ? "selected" : ""} ${separatedByBreak ? "disabled" : ""}>${slot}</option>`;
  }).join("");
  $("#modal-content").innerHTML = `
    <div class="modal-head"><div><div class="section-kicker">BOOK A SPACE</div><h2>${escapeHtml(venue)}</h2><p>${dateText} · Starts at ${firstSlot}</p></div><button class="close" type="button" data-close aria-label="Close">×</button></div>
    <form id="booking-form"><input type="hidden" name="venue" value="${escapeHtml(venue)}"><input type="hidden" name="date" value="${dateText}"><input type="hidden" name="start" value="${firstSlot}">
      <div class="form-grid"><div class="form-field"><label for="booking-end">END TIME</label><select id="booking-end" name="end">${options}</select></div>
      <div class="form-field"><label for="name">YOUR NAME</label><input id="name" name="name" required autocomplete="name"></div>
      <div class="form-field"><label for="contact">CONTACT</label><input id="contact" name="contact" required placeholder="Email or phone"></div>
      <div class="form-field"><label for="event">EVENT NAME</label><input id="event" name="event" required></div>
      <div class="form-field full"><label for="purpose">PURPOSE</label><textarea id="purpose" name="purpose" required></textarea></div></div>
      <div class="form-actions"><button class="button secondary" type="button" data-close>Cancel</button><button class="button primary">Send request</button></div></form>`;
  $("#modal").classList.remove("hidden");
  $$('[data-close]').forEach(button => button.onclick = closeModal);
  $("#booking-form").onsubmit = submitBooking;
}

function closeModal() { $("#modal")?.classList.add("hidden"); }

async function submitBooking(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = Object.fromEntries(new FormData(form));
  try {
    const booking = await api("/api/requests", { method: "POST", body: JSON.stringify(payload) });
    $("#modal-content").innerHTML = `<div class="success"><div class="success-icon">✓</div><div class="section-kicker">REQUEST SENT</div><h2>Now we wait.</h2><p>Keep this ID to check your request.</p><div class="request-id">${booking.id}</div><button class="button primary" id="copy-id">Copy ID</button><a class="button secondary" href="/status">Check status</a></div>`;
    $("#copy-id").onclick = async () => { try { await navigator.clipboard.writeText(booking.id); toast("Request ID copied."); } catch (_) { toast(`Your Request ID is ${booking.id}`); } };
    celebrate();
    await loadBookPage();
  } catch (error) { toast(error.message); }
}

function celebrate() {
  for (let i = 0; i < 14; i++) {
    const piece = document.createElement("span");
    piece.className = "confetti";
    piece.textContent = "•";
    piece.style.setProperty("--x", `${Math.random() * 260 - 130}px`);
    document.body.append(piece);
    setTimeout(() => piece.remove(), 1200);
  }
}

function drawGrid() {
  const host = $("#venue-grid");
  if (!host) return;
  const shownVenues = pageState.visibleNames ? pageState.venues.filter(venue => pageState.visibleNames.has(venue.name)) : pageState.venues;
  const desktop = [`<div class="availability-grid desktop-grid" style="--slot-count:${pageState.slots.length}"><div class="grid-head venue-head">VENUE</div>${pageState.slots.map(slot => `<div class="grid-head">${slot}</div>`).join("")}`];
  const mobile = ['<div class="mobile-venues">'];
  shownVenues.forEach(venue => {
    desktop.push(`<div class="venue-label">${escapeHtml(venue.name)}<small>${venue.capacity} seats</small></div>`);
    const chips = [];
    pageState.slots.forEach(slot => {
      const item = pageState.grid[venue.name]?.[slot] || { state: "free", label: "Open" };
      const label = item.state === "lecture" ? item.label : item.state === "approved" ? "Booked" : item.state === "pending" ? "Pending" : "Open";
      const open = ["free", "pending"].includes(item.state);
      const attributes = open ? `data-venue="${escapeHtml(venue.name)}" data-slot="${slot}"` : `disabled title="${escapeHtml(label)}"`;
      const button = `<button class="slot-pill ${item.state}" ${attributes}>${escapeHtml(label)}</button>`;
      desktop.push(`<div class="slot-cell">${button}</div>`);
      chips.push(button);
    });
    mobile.push(`<article class="mobile-venue"><header><b>${escapeHtml(venue.name)}</b><span>${venue.capacity} seats</span></header><div class="mobile-chips">${chips.join("")}</div></article>`);
  });
  desktop.push("</div>"); mobile.push("</div>");
  host.innerHTML = desktop.join("") + mobile.join("");
  $$(".slot-pill[data-slot]", host).forEach(button => button.onclick = () => openBooking(button.dataset.venue, pageState.date, button.dataset.slot));
}

async function searchVenues(prefix) {
  try {
    const found = (await api(`/api/venues/search?q=${encodeURIComponent(prefix)}`)).names;
    pageState.visibleNames = prefix ? new Set(found) : null;
    drawGrid();
  } catch (error) { toast(error.message); }
}

async function loadBookPage() {
  const errorBox = $("#grid-error");
  try {
    const dateInput = $("#grid-date");
    if (!dateInput.value) dateInput.value = localDate(new Date());
    dateInput.min = localDate(new Date());
    const data = await api(`/api/grid?date=${encodeURIComponent(dateInput.value)}`);
    pageState.venues = data.venues; pageState.slots = data.slots; pageState.grid = data.grid; pageState.day = data.day; pageState.date = dateInput.value;
    $("#grid-day").textContent = `${data.day} · ${dateInput.value}`;
    errorBox?.classList.add("hidden");
    drawGrid();
  } catch (error) {
    if (errorBox) { errorBox.classList.remove("hidden"); errorBox.innerHTML = `<span>We couldn’t load availability. ${escapeHtml(error.message)}</span> <button class="retry-button" id="retry-grid">Retry</button>`; $("#retry-grid").onclick = loadBookPage; }
    if ($("#grid-day")) $("#grid-day").textContent = "Schedule unavailable";
  }
}

async function findBestRoom() {
  const payload = { date: $("#grid-date").value, hours: $("#find-hours").value, people: $("#find-people").value };
  try {
    const data = await api("/api/find", { method: "POST", body: JSON.stringify(payload) });
    const host = $("#find-results");
    if (!data.results.length) { host.innerHTML = '<p class="empty">No room fits that plan. Try another time or group size.</p>'; return; }
    let bestMarked = false;
    host.innerHTML = data.results.map(item => { const best = !bestMarked && item.venue.name === data.best; if (best) bestMarked = true; return `<article class="result-card">${best ? '<span class="badge-fit">Best fit</span>' : ""}<div class="section-kicker">${item.venue.capacity} SEATS</div><h3>${escapeHtml(item.venue.name)}</h3><p>${item.slots[0]} to ${item.slots[item.slots.length - 1]}</p><button class="button secondary" data-room="${escapeHtml(item.venue.name)}" data-start="${item.slots[0]}">Request</button></article>`; }).join("");
    $$('[data-room]', host).forEach(button => button.onclick = () => openBooking(button.dataset.room, payload.date, button.dataset.start, Number(payload.hours)));
  } catch (error) { toast(error.message); }
}

async function checkRequest(event) {
  event.preventDefault();
  const id = new FormData(event.currentTarget).get("id").trim();
  const resultBox = $("#check-result");
  resultBox.innerHTML = "";
  try {
    const booking = await api(`/api/requests/${encodeURIComponent(id)}`);
    resultBox.innerHTML = `<article class="status-result"><span class="status ${booking.status}">${booking.status}</span><h2>${escapeHtml(booking.event)}</h2><p>${escapeHtml(booking.venue)} · ${booking.date} · ${booking.slots.join(", ")}</p>${booking.reason ? `<p class="reason">Reason: ${escapeHtml(booking.reason)}</p>` : ""}</article>`;
  } catch (error) { resultBox.innerHTML = `<p class="friendly-error">${escapeHtml(error.message)}</p>`; }
}

async function loginAdmin() {
  const errorBox = $("#pin-error");
  try {
    await api("/api/admin/login", { method: "POST", body: JSON.stringify({ pin: $("#pin-value").value }) });
    $("#admin-login").classList.add("hidden");
    await renderAdmin();
  } catch (error) {
    errorBox.textContent = error.message;
    $("#admin-login").classList.remove("shake"); void $("#admin-login").offsetWidth; $("#admin-login").classList.add("shake");
    $("#pin-value").value = "";
  }
}

async function renderAdmin(tab = "Requests") {
  const host = $("#admin-app");
  if (!host) return;
  try { window.adminData = await api("/api/admin/data"); }
  catch (error) { toast(error.message); $("#admin-login")?.classList.remove("hidden"); return; }
  host.classList.remove("hidden");
  const data = window.adminData;
  const now = new Date(), start = new Date(now);
  start.setDate(now.getDate() - ((now.getDay() + 6) % 7)); start.setHours(0, 0, 0, 0);
  const end = new Date(start); end.setDate(start.getDate() + 7);
  const approved = data.history.filter(item => item.status === "Approved" && item.approved_at && new Date(item.approved_at) >= start && new Date(item.approved_at) < end).length;
  host.innerHTML = `<div class="admin-wrap"><aside class="admin-side"><h2>Spaces admin</h2>${["Requests", "Timetable", "Venues", "History"].map(name => `<button class="admin-tab ${name === tab ? "active" : ""}" data-tab="${name}">${name}</button>`).join("")}<button class="admin-tab" id="logout">Logout</button></aside><section class="admin-main"><h1>${tab}</h1><div class="admin-stats"><div class="admin-stat"><b>${data.venues.length}</b>Total venues</div><div class="admin-stat"><b>${data.requests.length}</b>Pending requests</div><div class="admin-stat"><b>${approved}</b>Approved this week</div></div><div id="admin-content"></div></section></div>`;
  $$('[data-tab]', host).forEach(button => button.onclick = () => renderAdmin(button.dataset.tab));
  $("#logout").onclick = async () => { try { await api("/api/admin/logout", { method: "POST" }); location.href = "/"; } catch (error) { toast(error.message); } };
  if (tab === "Requests") renderRequests();
  if (tab === "History") renderHistory();
  if (tab === "Timetable") renderTimetable();
  if (tab === "Venues") renderVenues();
}

function adminTable(rows, headings) {
  const table = document.createElement("table");
  table.className = "table";
  table.innerHTML = `<thead><tr>${headings.map(item => `<th>${item}</th>`).join("")}</tr></thead><tbody>${rows}</tbody>`;
  $$("tbody tr", table).forEach(row => $$("td", row).forEach((cell, index) => cell.dataset.label = headings[index] || "DETAIL"));
  return table.outerHTML;
}

function renderRequests() {
  const host = $("#admin-content"), data = window.adminData;
  host.className = "admin-panel";
  host.innerHTML = `<h2>Pending requests</h2>${data.requests.length ? adminTable(data.requests.map(item => `<tr><td><b>${item.id}</b></td><td>${escapeHtml(item.name)}<small>${escapeHtml(item.contact)}</small></td><td>${escapeHtml(item.event)}</td><td>${escapeHtml(item.venue)}</td><td>${item.date}<small>${item.slots.join(", ")}</small></td><td><button class="button green" data-approve="${item.id}">Approve</button> <button class="button red" data-reject="${item.id}">Reject</button></td></tr>`).join(""), ["ID", "NAME", "EVENT", "VENUE", "DATE · TIME", "ACTION"]) : '<div class="empty">No requests right now. Admin is chilling.</div>'}`;
  $$('[data-approve]', host).forEach(button => button.onclick = async () => { try { await decideRequest(button.dataset.approve, "approve"); toast("Request approved."); await renderAdmin("Requests"); } catch (error) { toast(error.message); } });
  $$('[data-reject]', host).forEach(button => button.onclick = () => rejectRequest(button.dataset.reject));
}

function rejectRequest(id) {
  $("#modal-content").innerHTML = `<h2>Reject request</h2><p>Give a short reason for the decision.</p><form id="reject-form"><div class="form-field"><label>REASON</label><input name="reason" required></div><div class="form-actions"><button class="button secondary" type="button" data-close>Cancel</button><button class="button red">Reject</button></div></form>`;
  $("#modal").classList.remove("hidden"); $("[data-close]").onclick = closeModal;
  $("#reject-form").onsubmit = async event => { event.preventDefault(); try { await decideRequest(id, "reject", new FormData(event.currentTarget).get("reason")); closeModal(); toast("Request rejected."); await renderAdmin("Requests"); } catch (error) { toast(error.message); } };
}

async function decideRequest(id, decision, reason = "") { await api(`/api/admin/requests/${id}`, { method: "POST", body: JSON.stringify({ decision, reason }) }); }

function renderHistory() {
  const data = window.adminData, host = $("#admin-content"); host.className = "admin-panel";
  host.innerHTML = `<h2>Decided requests</h2>${data.history.length ? adminTable(data.history.map(item => `<tr><td>${item.id}</td><td>${escapeHtml(item.name)}</td><td>${escapeHtml(item.event)}</td><td>${escapeHtml(item.venue)}<small>${item.date} · ${item.slots.join(", ")}</small></td><td><span class="status ${item.status}">${item.status}</span></td><td>${escapeHtml(item.reason || "—")}</td></tr>`).join(""), ["ID", "NAME", "EVENT", "VENUE · TIME", "STATUS", "REASON"]) : '<p class="empty">No request history yet.</p>'}`;
}

function renderTimetable() {
  const data = window.adminData, host = $("#admin-content"); host.className = "admin-panel";
  host.innerHTML = `<h2>Weekly timetable</h2><div class="timetable-import"><label for="timetable-image">UPLOAD TIMETABLE</label><input id="timetable-image" type="file" accept="image/*,.pdf,application/pdf"><p id="timetable-import-status">Upload the college timetable PDF or a clear image. The PDF importer reads the college grid and room codes. Importing replaces the saved timetable.</p></div><div class="admin-form"><label>VENUE<select id="tt-venue">${data.venues.map(item => `<option>${escapeHtml(item.name)}</option>`).join("")}</select></label><label>DAY<select id="tt-day">${data.days.map(day => `<option>${day}</option>`).join("")}</select></label></div><div id="tt-slots"></div>`;
  $("#timetable-image").onchange = importTimetableImage;
  function draw() { const venue = $("#tt-venue").value, day = $("#tt-day").value; $("#tt-slots").innerHTML = adminTable(data.slots.map(slot => { const row = data.timetable.find(item => item.venue === venue && item.day === day && item.slot === slot); return `<tr><td>${slot}</td><td>${row ? escapeHtml(row.lecture) : "Open"}</td><td><button class="button secondary mini" data-edit-slot="${slot}">${row ? "Edit" : "Add"}</button>${row ? `<button class="button red mini" data-delete-slot="${slot}">Delete</button>` : ""}</td></tr>`; }).join(""), ["SLOT", "LECTURE", "ACTION"]); $$('[data-edit-slot]').forEach(button => button.onclick = () => editLecture(venue, day, button.dataset.editSlot)); $$('[data-delete-slot]').forEach(button => button.onclick = () => saveLecture(venue, day, button.dataset.deleteSlot, "")); }
  $("#tt-venue").onchange = draw; $("#tt-day").onchange = draw; draw();
}

async function importTimetableImage(event) {
  const file = event.currentTarget.files?.[0];
  if (!file) return;
  const status = $("#timetable-import-status");
  const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
  if (isPdf) {
    status.textContent = "Reading the college timetable PDF…";
    try {
      const form = new FormData(); form.append("file", file);
      const saved = await api("/api/admin/timetable/import-pdf", { method: "POST", body: form });
      toast(`Imported ${saved.count} Friday room entries.`);
      await renderAdmin("Timetable");
    } catch (error) {
      status.textContent = error.message;
      status.classList.add("form-error");
    } finally {
      event.currentTarget.value = "";
    }
    return;
  }
  if (!file.type.startsWith("image/")) { status.textContent = "Choose a timetable PDF or image file."; return; }
  status.textContent = "Reading the timetable image…";
  try {
    if (!window.Tesseract) {
      await new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = "https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js";
        script.onload = resolve; script.onerror = () => reject(new Error("Text recognition could not load. Check your internet connection and try again."));
        document.head.append(script);
      });
    }
    const result = await window.Tesseract.recognize(file, "eng", { logger: progress => {
      if (progress.status === "recognizing text") status.textContent = `Reading timetable… ${Math.round((progress.progress || 0) * 100)}%`;
    }});
    const rows = parseTimetableText(result.data.text, window.adminData);
    if (!rows.length) throw new Error("I couldn’t match entries. Use a clear image with each class on a line containing its venue, weekday, time slot, and class name.");
    status.textContent = `Saving ${rows.length} recognized class entries…`;
    const saved = await api("/api/admin/timetable/import", { method: "POST", body: JSON.stringify({ rows }) });
    toast(`Imported ${saved.count} class entries. Check the timetable for OCR mistakes.`);
    await renderAdmin("Timetable");
  } catch (error) {
    status.textContent = error.message;
    status.classList.add("form-error");
  } finally {
    event.currentTarget.value = "";
  }
}

function parseTimetableText(text, data) {
  const days = data.days;
  const slots = data.slots;
  const found = new Map();
  for (const sourceLine of text.split(/\n+/)) {
    const line = sourceLine.replace(/[|¦]/g, " ").replace(/\s+/g, " ").trim();
    if (!line) continue;
    const lower = line.toLowerCase();
    const venue = data.venues.find(item => lower.includes(item.name.toLowerCase()));
    const day = days.find(item => lower.includes(item.toLowerCase())) ||
      (lower.includes("mon") ? "Monday" : lower.includes("tue") ? "Tuesday" : lower.includes("wed") ? "Wednesday" : lower.includes("thu") ? "Thursday" : lower.includes("fri") ? "Friday" : lower.includes("sat") ? "Saturday" : null);
    const slot = slots.find(item => {
      const [start, end] = item.split("-");
      const pattern = new RegExp(`\\b${start}\\s*[-–to]+\\s*${end}\\b`, "i");
      return pattern.test(lower);
    });
    if (!venue || !day || !slot) continue;
    let lecture = line;
    for (const token of [venue.name, day, slot, slot.replace("-", " to ")]) { const at = lecture.toLowerCase().indexOf(token.toLowerCase()); if (at >= 0) lecture = lecture.slice(0, at) + " " + lecture.slice(at + token.length); }
    lecture = lecture.replace(/\b(mon(day)?|tue(sday)?|wed(nesday)?|thu(rsday)?|fri(day)?|sat(urday)?)\b/ig, " ").replace(/\s+/g, " ").trim().replace(/^[\-:|,\s]+|[\-:|,\s]+$/g, "");
    if (!lecture || /^(venue|day|time|subject|class|lecture)$/i.test(lecture)) continue;
    found.set(`${venue.name}|${day}|${slot}`, { venue: venue.name, day, slot, lecture });
  }
  return [...found.values()];
}

function editLecture(venue, day, slot) {
  const old = window.adminData.timetable.find(item => item.venue === venue && item.day === day && item.slot === slot);
  $("#modal-content").innerHTML = `<h2>${escapeHtml(venue)} · ${day} · ${slot}</h2><form id="lecture-form"><div class="form-field"><label>LECTURE NAME (leave blank to delete)</label><input name="lecture" value="${escapeHtml(old?.lecture || "")}"></div><div class="form-actions"><button type="button" class="button secondary" data-close>Cancel</button><button class="button primary">Save</button></div></form>`;
  $("#modal").classList.remove("hidden"); $("[data-close]").onclick = closeModal;
  $("#lecture-form").onsubmit = async event => { event.preventDefault(); await saveLecture(venue, day, slot, new FormData(event.currentTarget).get("lecture"), true); };
}

async function saveLecture(venue, day, slot, lecture, replace = false) {
  try { await api("/api/admin/timetable", { method: "POST", body: JSON.stringify({ venue, day, slot, lecture, replace }) }); closeModal(); toast("Timetable saved."); await renderAdmin("Timetable"); }
  catch (error) { toast(error.message); }
}

function renderVenues() {
  const data = window.adminData, host = $("#admin-content"); host.className = "admin-panel";
  host.innerHTML = `<div class="panel-title"><h2>Venues</h2><button class="button primary mini" id="add-venue">Add venue</button></div>${adminTable(data.venues.map(item => `<tr><td>${escapeHtml(item.name)}</td><td>${escapeHtml(item.type)}</td><td>${item.capacity}</td><td><button class="button secondary mini" data-edit-venue="${escapeHtml(item.name)}">Edit</button> <button class="button red mini" data-delete-venue="${escapeHtml(item.name)}">Delete</button></td></tr>`).join(""), ["NAME", "TYPE", "CAPACITY", "ACTION"])}`;
  $("#add-venue").onclick = () => editVenue();
  $$('[data-edit-venue]').forEach(button => button.onclick = () => editVenue(data.venues.find(item => item.name === button.dataset.editVenue)));
  $$('[data-delete-venue]').forEach(button => button.onclick = async () => { try { await api("/api/admin/venues", { method: "DELETE", body: JSON.stringify({ name: button.dataset.deleteVenue }) }); toast("Venue deleted."); await renderAdmin("Venues"); } catch (error) { toast(error.message); } });
}

function editVenue(old = null) {
  $("#modal-content").innerHTML = `<h2>${old ? "Edit venue" : "Add venue"}</h2><form id="venue-form"><div class="form-grid"><div class="form-field"><label>NAME</label><input name="new_name" value="${escapeHtml(old?.name || "")}" required></div><div class="form-field"><label>TYPE</label><select name="type"><option ${old?.type === "LR" ? "selected" : ""}>LR</option><option ${old?.type === "Lab" ? "selected" : ""}>Lab</option><option ${old?.type === "Hall" ? "selected" : ""}>Hall</option><option ${old?.type === "Library" ? "selected" : ""}>Library</option></select></div><div class="form-field"><label>CAPACITY</label><input name="capacity" type="number" min="1" value="${old?.capacity || 30}" required></div></div><div class="form-actions"><button class="button secondary" type="button" data-close>Cancel</button><button class="button primary">Save venue</button></div></form>`;
  $("#modal").classList.remove("hidden"); $("[data-close]").onclick = closeModal;
  $("#venue-form").onsubmit = async event => { event.preventDefault(); const payload = Object.fromEntries(new FormData(event.currentTarget)); if (old) payload.name = old.name; try { await api("/api/admin/venues", { method: old ? "PUT" : "POST", body: JSON.stringify(payload) }); closeModal(); toast("Venue saved."); await renderAdmin("Venues"); } catch (error) { toast(error.message); } };
}

function escapeHtml(value) { return String(value ?? "").replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char])); }

if ($("#grid-date")) {
  $("#grid-date").onchange = loadBookPage;
  $("#grid-date").min = localDate(new Date());
  $("#venue-search").oninput = () => searchVenues($("#venue-search").value.trim());
  $("#find-button").onclick = findBestRoom;
  $("#finder-toggle").onclick = () => { const finder = $("#finder"); const open = finder.classList.toggle("hidden") === false; $("#finder-toggle").setAttribute("aria-expanded", open); $("#finder-toggle").textContent = open ? "− Hide best-fit finder" : "+ Show me the best room"; };
  $("#modal").onclick = event => { if (event.target.id === "modal") closeModal(); };
  loadBookPage();
}
if ($("#check-form")) $("#check-form").onsubmit = checkRequest;
if ($("#pin-submit")) {
  $("#pin-submit").onclick = loginAdmin;
  $("#pin-value").onkeydown = event => { if (event.key === "Enter") loginAdmin(); };
  api("/api/admin/data").then(() => { $("#admin-login").classList.add("hidden"); renderAdmin(); }).catch(() => {});
}
if ($("#modal")) $("#modal").onclick = event => { if (event.target.id === "modal") closeModal(); };
