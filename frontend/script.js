/**
 * script.js — Distributed E-Commerce Dashboard
 *
 * All animations and UI updates are driven by REAL API responses.
 * No fake data. No fake animations.
 *
 * Flow:
 *   Browser → Load Balancer (:5000) → Round Robin → Node 1/2/3 (:5001-5003)
 *                                                          ↓
 *                                                     SQLite DB
 */

"use strict";

const API = "";   // same origin, load balancer on :5000

// ── Product emoji map ─────────────────────────────────────────────────────────
const EMOJI_MAP = {
  "laptop": "💻", "smartphone": "📱", "headphones": "🎧",
  "smart watch": "⌚", "keyboard": "⌨️", "mouse": "🖱️",
  "gaming monitor": "🖥️", "power bank": "🔋",
};

function getEmoji(name) {
  const n = name.toLowerCase();
  for (const [k, v] of Object.entries(EMOJI_MAP)) {
    if (n.includes(k)) return v;
  }
  return "📦";
}

function fmtPrice(p) {
  return "₹" + Number(p).toLocaleString("en-IN");
}

function esc(s) {
  return String(s)
    .replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ── State ─────────────────────────────────────────────────────────────────────
let currentProduct   = null;
let lastLogEntries   = 0;
let lastNodeSnapshot = [0, 0, 0];   // request counts per node for delta detection
let rrIndex          = 0;           // local Round Robin pointer for RR visualizer

// ══════════════════════════════════════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════════════════════════════════════
document.addEventListener("DOMContentLoaded", () => {
  loadProducts();
  refreshStats();
  setInterval(refreshStats, 3000);
});

// ══════════════════════════════════════════════════════════════════════════════
// STATISTICS POLLING
// ══════════════════════════════════════════════════════════════════════════════
async function refreshStats() {
  try {
    const res  = await fetch(`${API}/api/statistics`);
    if (!res.ok) return;
    const data = await res.json();

    updateKPIs(data);
    updateServerCards(data.nodes);
    updateDistChart(data.nodes);
    updateActivityLog(data.activity_log || []);
    updateArchDiagram(data.nodes);
    document.getElementById("health-last-check").textContent =
      "Updated " + new Date().toLocaleTimeString();

  } catch {
    /* silent — stale UI is fine */
  }
}

// ── KPIs ──────────────────────────────────────────────────────────────────────
function updateKPIs(data) {
  const total  = data.total_requests || 0;
  const nodes  = data.nodes || [];
  const online = nodes.filter(n => n.status === "online").length;
  const perNode = online > 0 ? (total / nodes.length).toFixed(1) : "—";

  animateCount("kpi-total", total);
  document.getElementById("kpi-nodes").textContent     = `${online} / ${nodes.length}`;
  document.getElementById("kpi-nodes-sub").textContent  = online === nodes.length ? "100% healthy" : `${nodes.length - online} offline`;
  document.getElementById("kpi-per-node").textContent   = perNode;
  document.getElementById("kpi-total-sub").textContent  = total > 0 ? `+${total} since start` : "Awaiting traffic";
}

/** Smooth number animation for KPI counters */
const _counts = {};
function animateCount(id, target) {
  const el  = document.getElementById(id);
  if (!el) return;
  const start   = _counts[id] || 0;
  if (start === target) return;
  _counts[id]   = target;
  const delta   = target - start;
  const steps   = Math.min(Math.abs(delta), 20);
  let   current = start;
  let   step    = 0;
  const tick = () => {
    step++;
    current = Math.round(start + (delta * step / steps));
    el.textContent = current;
    if (step < steps) requestAnimationFrame(tick);
    else el.textContent = target;
  };
  requestAnimationFrame(tick);
}

// ── Server cards ──────────────────────────────────────────────────────────────
function updateServerCards(nodes) {
  if (!nodes || !nodes.length) return;
  const total = nodes.reduce((s, n) => s + n.request_count, 0);

  nodes.forEach((node, i) => {
    const idx    = i + 1;
    const online = node.status === "online";
    const share  = total > 0 ? Math.round((node.request_count / total) * 100) : 0;
    const prev   = lastNodeSnapshot[i];
    const newReq = node.request_count > prev;

    // Detect new request → flash processing indicator
    if (newReq) {
      flashProcessing(idx);
      triggerPacketAnimation(idx);
    }
    lastNodeSnapshot[i] = node.request_count;

    // Update values
    const el = (id) => document.getElementById(id);
    animateCount(`srv-reqs-${idx}`,  node.request_count);
    if (el(`srv-load-${idx}`))  el(`srv-load-${idx}`).textContent  = `${share}%`;
    if (el(`srv-last-${idx}`))  el(`srv-last-${idx}`).textContent  = node.last_request_at ? node.last_request_at.slice(11) : "No requests yet";

    // Badge + indicator
    const badge = el(`srv-badge-${idx}`);
    const ind   = el(`srv-ind-${idx}`);
    const card  = el(`srv-card-${idx}`);
    if (badge) {
      badge.textContent = online ? "ONLINE" : "OFFLINE";
      badge.className   = `srv-status-badge${online ? "" : " offline"}`;
    }
    if (ind) ind.className = `srv-indicator${online ? "" : " offline"}`;
    if (card) card.className = `server-card${online ? " online" : " offline"}`;
  });
}

function flashProcessing(nodeIdx) {
  const proc = document.getElementById(`srv-proc-${nodeIdx}`);
  const card = document.getElementById(`srv-card-${nodeIdx}`);
  if (!proc || !card) return;
  proc.classList.remove("hidden");
  card.classList.add("processing");
  setTimeout(() => {
    proc.classList.add("hidden");
    card.classList.remove("processing");
  }, 1500);
}

// ── Distribution chart ────────────────────────────────────────────────────────
function updateDistChart(nodes) {
  if (!nodes || !nodes.length) return;
  const max = Math.max(...nodes.map(n => n.request_count), 1);
  nodes.forEach((n, i) => {
    const pct  = Math.round((n.request_count / max) * 100);
    const bar  = document.getElementById(`dist-bar-${i + 1}`);
    const cnt  = document.getElementById(`dist-count-${i + 1}`);
    if (bar) bar.style.width = `${pct}%`;
    if (cnt) cnt.textContent = n.request_count;
  });
}

// ── Architecture diagram node status ─────────────────────────────────────────
function updateArchDiagram(nodes) {
  if (!nodes) return;
  nodes.forEach((n, i) => {
    const idx    = i + 1;
    const online = n.status === "online";
    const box    = document.getElementById(`arch-node-${idx}`);
    const stat   = document.getElementById(`arch-status-${idx}`);
    const reqs   = document.getElementById(`arch-reqs-${idx}`);
    if (!box) return;

    box.className = `arch-node-box server-box${online ? "" : " offline-node"}`;
    if (reqs) reqs.textContent = `${n.request_count} req`;
    if (stat) {
      if (online) {
        stat.innerHTML = `<span class="pulse-dot green"></span> ONLINE`;
        stat.className = "arch-node-status";
      } else {
        stat.innerHTML = `<span class="pulse-dot red"></span> OFFLINE`;
        stat.className = "arch-node-status offline";
      }
    }
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// PACKET ANIMATION — triggered by real backend data change
// ══════════════════════════════════════════════════════════════════════════════
function triggerPacketAnimation(nodeIdx) {
  const colorClass = `traveling-n${nodeIdx}`;

  // Stage 1: CLIENT → LB
  firePacket("packet-1", colorClass, 0);

  // Stage 2: LB → selected NODE
  const fanPacketId = `packet-2${["a","b","c"][nodeIdx - 1]}`;
  firePacket(fanPacketId, colorClass, 400);

  // Stage 3: NODE → DB
  const dbPacketId = `packet-3${["a","b","c"][nodeIdx - 1]}`;
  firePacket(dbPacketId, colorClass, 800);

  // Flash the LB box
  flashBox("arch-lb", "active", 1200);

  // Flash the selected node box
  flashBox(`arch-node-${nodeIdx}`, `node-${nodeIdx}-active`, 800, 400);

  // Flash the DB box
  flashBox("arch-db", "active", 600, 800);

  // Flash the client box briefly
  flashBox("arch-client", "active", 400, 0);

  // Update RR visualizer
  updateRRVisualizer(nodeIdx);
}

function firePacket(packetId, colorClass, delay) {
  setTimeout(() => {
    const p = document.getElementById(packetId);
    if (!p) return;
    p.className = "arch-packet";
    void p.offsetWidth;  // force reflow to restart animation
    p.className = `arch-packet traveling ${colorClass}`;
    setTimeout(() => { p.className = "arch-packet"; }, 700);
  }, delay);
}

function flashBox(elemId, cls, duration, delay = 0) {
  setTimeout(() => {
    const el = document.getElementById(elemId);
    if (!el) return;
    el.classList.add(cls);
    setTimeout(() => el.classList.remove(cls), duration);
  }, delay);
}

// ── Round Robin visualizer ────────────────────────────────────────────────────
function updateRRVisualizer(activeNode) {
  [1, 2, 3].forEach(i => {
    const el = document.getElementById(`rr-node-${i}`);
    if (!el) return;
    el.className = `rr-node${activeNode === i ? ` rr-active-${i}` : ""}`;
  });
  const next = (activeNode % 3) + 1;
  const info = document.getElementById("rr-next-info");
  if (info) info.textContent = `Last → Node 0${activeNode}  ·  Next → Node 0${next}`;
  rrIndex = activeNode;
}

// ══════════════════════════════════════════════════════════════════════════════
// ACTIVITY LOG
// ══════════════════════════════════════════════════════════════════════════════
function updateActivityLog(entries) {
  if (!entries || entries.length === 0) return;
  if (entries.length === lastLogEntries) return;  // nothing new
  lastLogEntries = entries.length;

  const terminal = document.getElementById("log-terminal");
  const empty    = document.getElementById("log-empty");
  if (empty) empty.remove();

  // Re-render latest 10 entries (newest first from server)
  const show = entries.slice(0, 10);
  terminal.innerHTML = "";

  show.forEach(raw => {
    const row = buildLogRow(raw);
    terminal.appendChild(row);
  });
}

function buildLogRow(raw) {
  // raw = "[HH:MM:SS] message"
  const timeMatch = raw.match(/^\[(\d{2}:\d{2}:\d{2})\]\s*(.*)/);
  const time = timeMatch ? timeMatch[1] : "--:--:--";
  const msg  = timeMatch ? timeMatch[2] : raw;

  // Determine node from message
  let nodeClass = "";
  let nodeNum   = 0;
  if (msg.includes("Server Node 1") || msg.includes("Node 1")) { nodeClass = "log-node-1"; nodeNum = 1; }
  else if (msg.includes("Server Node 2") || msg.includes("Node 2")) { nodeClass = "log-node-2"; nodeNum = 2; }
  else if (msg.includes("Server Node 3") || msg.includes("Node 3")) { nodeClass = "log-node-3"; nodeNum = 3; }

  // Determine method/path
  const methodMatch = msg.match(/(GET|POST|PUT|DELETE)\s+(\/\S*)/);
  const method = methodMatch ? methodMatch[1] : "";
  const path   = methodMatch ? methodMatch[2] : "";

  // Determine status
  const isOk  = msg.includes("✓") || msg.includes("200") || msg.includes("201");
  const isErr = msg.includes("ERROR") || msg.includes("OFFLINE") || msg.includes("TIMEOUT");

  const row = document.createElement("div");
  row.className = "log-row";

  // Node label text
  let nodeLabel = "";
  if (nodeNum > 0) nodeLabel = `Server Node 0${nodeNum}`;

  const route = msg.includes("Load Balancer selected")
    ? `LB → <span class="${nodeClass}">${esc(nodeLabel)}</span>`
    : nodeLabel
      ? `<span class="${nodeClass}">${esc(nodeLabel)}</span>`
      : "Load Balancer";

  const statusHtml = isErr
    ? `<span class="log-status-err">ERROR</span>`
    : isOk
      ? `<span class="log-status-ok">200 OK</span>`
      : `<span class="log-status-ok">—</span>`;

  const methodBadge = method
    ? `<strong>${esc(method)}</strong> <span style="color:var(--text-3)">${esc(path)}</span>`
    : `<span style="color:var(--text-3)">${esc(msg.replace(/Server Node \d/g, "").slice(0, 50))}</span>`;

  row.innerHTML = `
    <div class="log-time">${esc(time)}</div>
    <div class="log-info">${methodBadge}</div>
    <div class="log-route">${route}</div>
    <div>${statusHtml}</div>
  `;
  return row;
}

function clearLog() {
  const t = document.getElementById("log-terminal");
  t.innerHTML = '<div class="log-empty-state">Log cleared.</div>';
  lastLogEntries = 0;
}

// ══════════════════════════════════════════════════════════════════════════════
// PRODUCTS
// ══════════════════════════════════════════════════════════════════════════════
async function loadProducts() {
  const grid = document.getElementById("products-grid");
  grid.innerHTML = '<div class="products-loading">Loading catalogue…</div>';

  try {
    const res  = await fetch(`${API}/api/products`);
    const data = await res.json();

    if (!res.ok || data.status !== "success") {
      grid.innerHTML = `<div class="products-loading" style="color:var(--red)">
        Could not load products. Ensure all servers are running.</div>`;
      return;
    }

    // Trigger animation for this real request
    const nodeNum = nodeStrToNum(data.server_id);
    if (nodeNum) triggerPacketAnimation(nodeNum);

    grid.innerHTML = data.products.map(renderCard).join("");

  } catch {
    grid.innerHTML = `<div class="products-loading" style="color:var(--red)">
      Load Balancer unreachable. Run start_all_servers.bat first.</div>`;
  }
}

function nodeStrToNum(serverId) {
  if (!serverId) return 0;
  if (serverId.includes("1")) return 1;
  if (serverId.includes("2")) return 2;
  if (serverId.includes("3")) return 3;
  return 0;
}

function renderCard(p) {
  const stockLabel = p.stock === 0
    ? `<span class="product-stock-badge out">Out of Stock</span>`
    : p.stock < 5
      ? `<span class="product-stock-badge low">Low Stock: ${p.stock}</span>`
      : `<span class="product-stock-badge">In Stock: ${p.stock}</span>`;

  const productJson = esc(JSON.stringify(p));

  return `<div class="product-card">
    <div class="product-emoji">${getEmoji(p.name)}</div>
    <div class="product-name">${esc(p.name)}</div>
    <div class="product-category">${esc(p.category)}</div>
    <div class="product-price">${fmtPrice(p.price)}</div>
    ${stockLabel}
    <div class="product-actions" style="margin-top:0.5rem">
      <button class="btn-secondary" onclick="viewProduct(${p.id})">Details</button>
      <button class="btn-primary" onclick='openOrderModal(${productJson})'
        ${p.stock === 0 ? "disabled" : ""}>Buy Now</button>
    </div>
  </div>`;
}

// ══════════════════════════════════════════════════════════════════════════════
// PRODUCT DETAIL MODAL
// ══════════════════════════════════════════════════════════════════════════════
async function viewProduct(id) {
  const overlay = document.getElementById("detail-overlay");
  const content = document.getElementById("detail-content");
  content.innerHTML = '<div style="padding:1rem;color:var(--text-3)">Loading…</div>';
  overlay.classList.remove("hidden");

  try {
    const res  = await fetch(`${API}/api/products/${id}`);
    const data = await res.json();

    if (!res.ok || data.status !== "success") {
      content.innerHTML = `<div style="color:var(--red);padding:1rem">${esc(data.message)}</div>`;
      return;
    }

    const nodeNum = nodeStrToNum(data.server_id);
    if (nodeNum) triggerPacketAnimation(nodeNum);

    const p = data.product;
    content.innerHTML = `
      <div class="detail-emoji">${getEmoji(p.name)}</div>
      <div class="detail-name">${esc(p.name)}</div>
      <div class="detail-price">${fmtPrice(p.price)}</div>
      <table class="detail-table">
        <tr><td>Category</td><td>${esc(p.category)}</td></tr>
        <tr><td>Stock</td><td>${p.stock} units</td></tr>
        <tr><td>Description</td><td>${esc(p.description || "—")}</td></tr>
      </table>
      <div class="detail-server">
        Served by <strong>${esc(data.server_id)}</strong> via Load Balancer (Round Robin)
      </div>
      <button class="btn-primary"
        onclick='closeDetailModal(); openOrderModal(${esc(JSON.stringify(p))})'
        ${p.stock === 0 ? "disabled" : ""}>
        Place Order
      </button>`;

  } catch (err) {
    content.innerHTML = `<div style="color:var(--red);padding:1rem">Request failed: ${esc(err.message)}</div>`;
  }
}

function closeDetailModal() {
  document.getElementById("detail-overlay").classList.add("hidden");
}

// ══════════════════════════════════════════════════════════════════════════════
// ORDER MODAL
// ══════════════════════════════════════════════════════════════════════════════
function openOrderModal(product) {
  if (typeof product === "string") {
    try { product = JSON.parse(product); } catch { return; }
  }
  currentProduct = product;

  document.getElementById("modal-title").textContent = `Order — ${product.name}`;
  document.getElementById("modal-product").innerHTML = `
    <div class="mp-name">${getEmoji(product.name)} ${esc(product.name)}</div>
    <div class="mp-price">${fmtPrice(product.price)}</div>
    <div class="mp-stock">Available: ${product.stock} units</div>
  `;

  const qtyInput = document.getElementById("order-quantity");
  qtyInput.max   = product.stock;
  qtyInput.value = "1";
  document.getElementById("customer-name").value = "";

  const result = document.getElementById("modal-result");
  result.className = "modal-result hidden";
  result.textContent = "";

  document.getElementById("modal-overlay").classList.remove("hidden");
}

function closeModal() {
  document.getElementById("modal-overlay").classList.add("hidden");
  currentProduct = null;
}

async function placeOrder() {
  if (!currentProduct) return;

  const name = document.getElementById("customer-name").value.trim();
  const qty  = parseInt(document.getElementById("order-quantity").value, 10);
  const btn  = document.getElementById("btn-place-order");
  const res_div = document.getElementById("modal-result");

  if (!name) { showModalResult("error", "Please enter your name."); return; }
  if (!qty || qty < 1) { showModalResult("error", "Quantity must be at least 1."); return; }

  btn.disabled    = true;
  btn.textContent = "Placing order…";

  try {
    const res  = await fetch(`${API}/api/orders`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ product_id: currentProduct.id, quantity: qty, customer_name: name }),
    });
    const data = await res.json();

    if (res.ok && data.status === "success") {
      const nodeNum = nodeStrToNum(data.server_id);
      if (nodeNum) triggerPacketAnimation(nodeNum);
      showModalResult("success",
        `Order #${data.order_id} confirmed\nProcessed by: ${data.server_id}`);
      showToast(`Order #${data.order_id} placed — ${data.server_id}`);
      loadProducts();
    } else {
      showModalResult("error", data.message || "Order failed.");
    }

  } catch (err) {
    showModalResult("error", `Request failed: ${err.message}`);
  } finally {
    btn.disabled    = false;
    btn.textContent = "Confirm Order";
  }
}

function showModalResult(type, msg) {
  const el = document.getElementById("modal-result");
  el.className    = `modal-result ${type}`;
  el.style.display = "block";
  el.textContent  = msg;
}

// ══════════════════════════════════════════════════════════════════════════════
// SIMULATE TRAFFIC — 12 real requests, sequential, animated
// ══════════════════════════════════════════════════════════════════════════════
async function sendTestRequests() {
  const btn      = document.getElementById("btn-simulate");
  const progress = document.getElementById("sim-progress");
  const simBar   = document.getElementById("sim-bar");
  const simLabel = document.getElementById("sim-label");
  const result   = document.getElementById("sim-result");

  btn.disabled    = true;
  btn.textContent = "SIMULATING…";
  progress.classList.remove("hidden");
  result.classList.add("hidden");

  const tally = { 1: 0, 2: 0, 3: 0 };
  const TOTAL = 12;

  for (let i = 1; i <= TOTAL; i++) {
    simBar.style.width  = `${Math.round((i / TOTAL) * 100)}%`;
    simLabel.textContent = `${i} / ${TOTAL} requests`;

    try {
      const res  = await fetch(`${API}/api/products`);
      const data = await res.json();
      const num  = nodeStrToNum(data.server_id);
      if (num) { tally[num]++; triggerPacketAnimation(num); }
    } catch {
      /* node may be offline — load balancer handles it */
    }

    await sleep(300);
  }

  progress.classList.add("hidden");
  simBar.style.width = "0%";

  // Build result
  const lines = [];
  lines.push(`TRAFFIC TEST COMPLETE — ${TOTAL} requests\n`);
  [1, 2, 3].forEach(n => {
    const bars = "█".repeat(tally[n]);
    const pct  = Math.round((tally[n] / TOTAL) * 100);
    lines.push(`Node 0${n}  ${bars.padEnd(12)}  ${tally[n]} req  (${pct}%)`);
  });
  lines.push(`\n✓ Traffic Successfully Distributed`);

  result.textContent = lines.join("\n");
  result.classList.remove("hidden");

  btn.disabled    = false;
  btn.textContent = "SIMULATE TRAFFIC";
  btn.querySelector ? null : null;
  btn.innerHTML   = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg> SIMULATE TRAFFIC`;

  refreshStats();
}

// ══════════════════════════════════════════════════════════════════════════════
// TOAST
// ══════════════════════════════════════════════════════════════════════════════
function showToast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.classList.remove("hidden");
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.add("hidden"), 3500);
}
