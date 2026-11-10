/* 城市犯罪可视化地图 —— 前端逻辑 (Leaflet) */
"use strict";

const SEV_COLORS = { "轻微": "#2ecc71", "一般": "#f1c40f", "较重": "#e67e22", "严重": "#e74c3c" };
const POINT_ZOOM_THRESHOLD = 14;   // 缩放达到该级别才加载单点明细
const LEAST_BOUNDS = [[53.72, -1.66], [53.88, -1.38]];  // 利兹大致范围

const state = {
  severity: new Set(),
  month: "",
  categories: new Set(),
  outcomeType: "",
  neighbourhood: "",
  choroCounts: {},     // neighbourhood_id -> count
  choroMax: 1,
  playing: false,
  playTimer: null,
};

// ---------------- 地图与图层 ----------------
const map = L.map("map", { zoomControl: true });
map.fitBounds(LEAST_BOUNDS);

const baseLight = L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
  attribution: "&copy; OpenStreetMap &copy; CARTO", maxZoom: 19,
});
const baseDark = L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
  attribution: "&copy; OpenStreetMap &copy; CARTO", maxZoom: 19,
});
baseLight.addTo(map);

const heatLayer = L.heatLayer([], { radius: 18, blur: 16, maxZoom: 17, minOpacity: 0.25 });
const clusterLayer = L.markerClusterGroup({ maxClusterRadius: 60, showCoverageOnHover: false });
let choroLayer = null;

// ---------------- 工具 ----------------
function getBbox() {
  const b = map.getBounds();
  // minLng,minLat,maxLng,maxLat
  return `${b.getWest()},${b.getSouth()},${b.getEast()},${b.getNorth()}`;
}

function buildQuery() {
  const p = new URLSearchParams();
  if (state.severity.size) p.set("severity", [...state.severity].join(","));
  if (state.month) p.set("month", state.month);
  if (state.categories.size) p.set("category", [...state.categories].join(","));
  if (state.outcomeType) p.set("outcome_type", state.outcomeType);
  if (state.neighbourhood) p.set("neighbourhood", state.neighbourhood);
  const q = p.toString();
  return q ? "&" + q : "";
}

async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url} -> ${r.status}`);
  return r.json();
}

function choroColor(count) {
  if (!count) return "#eeeeee";
  const t = Math.sqrt(count / state.choroMax);   // 开方让低值层次更明显
  // 浅橙 -> 深红
  const r = Math.round(253 + (183 - 253) * t);
  const g = Math.round(224 + (28 - 224) * t);
  const b = Math.round(221 + (28 - 221) * t);
  return `rgb(${r},${g},${b})`;
}

// ---------------- 数据加载 ----------------
async function loadOverview() {
  const o = await getJSON("/api/overview");
  document.getElementById("total").textContent = o.total.toLocaleString();

  // 分级 chips
  const box = document.getElementById("severity-box");
  box.innerHTML = "";
  o.severity.forEach(s => {
    const lab = document.createElement("label");
    lab.innerHTML = `<input type="checkbox" value="${s.k}"> <span style="color:${SEV_COLORS[s.k]||'#333'}">${s.k}</span> <span class="muted">(${s.v})</span>`;
    box.appendChild(lab);
    lab.querySelector("input").addEventListener("change", e => {
      toggleSet(state.severity, s.k, e.target.checked);
      refresh(true);
    });
  });

  // 类别 checklist
  const catBox = document.getElementById("category-box");
  catBox.innerHTML = "";
  o.categories.forEach(c => {
    const lab = document.createElement("label");
    lab.innerHTML = `<input type="checkbox" value="${c.name}"> ${c.k} <span class="muted">(${c.v})</span>`;
    catBox.appendChild(lab);
    lab.querySelector("input").addEventListener("change", e => {
      toggleSet(state.categories, c.name, e.target.checked);
      refresh(true);
    });
  });

  // 月份
  const ms = document.getElementById("month-select");
  o.months.forEach(m => {
    const opt = document.createElement("option");
    opt.value = m.k; opt.textContent = m.k;
    ms.appendChild(opt);
  });
  ms.addEventListener("change", e => { state.month = e.target.value; refresh(true); });
}

async function loadNeighbourhoodOptions() {
  const o = await getJSON("/api/neighbourhoods");
  const sel = document.getElementById("neighbourhood-select");
  o.neighbourhoods.forEach(n => {
    const opt = document.createElement("option");
    opt.value = n.id; opt.textContent = n.name;
    sel.appendChild(opt);
  });
  sel.addEventListener("change", e => { state.neighbourhood = e.target.value; refresh(true); });
}

function toggleSet(set, v, on) { on ? set.add(v) : set.delete(v); }

async function loadHeat() {
  const o = await getJSON(`/api/heatmap?bbox=${getBbox()}${buildQuery()}`);
  heatLayer.setLatLngs(o.points);
}

async function loadChoro() {
  const o = await getJSON(`/api/neighbourhoods${buildQuery().replace("&", "?")}`);
  state.choroCounts = {};
  o.neighbourhoods.forEach(n => { state.choroCounts[n.id] = n.count; });
  state.choroMax = Math.max(1, ...Object.values(state.choroCounts));
  if (choroLayer) choroLayer.setStyle(styleChoro);
}

function styleChoro(feature) {
  const id = feature.properties.neighbourhood_id;
  return {
    fillColor: choroColor(state.choroCounts[id] || 0),
    fillOpacity: 0.75,
    color: "#999",
    weight: 1,
  };
}

async function initChoro() {
  const gj = await fetch("/static/geojson/neighbourhoods.geojson").then(r => r.json());
  choroLayer = L.geoJSON(gj, {
    style: styleChoro,
    onEachFeature: (f, layer) => {
      layer.bindTooltip(() =>
        `${f.properties.name}：${state.choroCounts[f.properties.neighbourhood_id] || 0} 件`,
        { sticky: true });
    },
  });
}

async function loadPoints() {
  if (!document.getElementById("layer-points").checked) { clusterLayer.clearLayers(); return; }
  if (map.getZoom() < POINT_ZOOM_THRESHOLD) { clusterLayer.clearLayers(); return; }
  const o = await getJSON(`/api/crimes?bbox=${getBbox()}&limit=6000${buildQuery()}`);
  clusterLayer.clearLayers();
  const markers = o.features.map(f => {
    const [lng, lat] = f.geometry.coordinates;
    const p = f.properties;
    const m = L.circleMarker([lat, lng], {
      radius: 5, weight: 0.5, color: "#fff",
      fillColor: SEV_COLORS[p.severity] || "#999", fillOpacity: 0.85,
    });
    m.bindPopup(`
      <div class="crime-popup">
        <b>${p.category_cn}</b>（${p.severity}）<br>
        案件号：${p.crime_id}<br>
        时间：${p.month}<br>
        地点：${p.street || "—"}<br>
        处理结果：${p.outcome_cn || "未记录"}
      </div>`);
    return m;
  });
  clusterLayer.addLayers(markers);
}

// ---------------- 刷新 ----------------
function refresh(filtersChanged) {
  loadHeat();
  if (filtersChanged) loadChoro();
  if (map.getZoom() >= POINT_ZOOM_THRESHOLD) loadPoints();
}

// ---------------- 图层开关 ----------------
function bindLayers() {
  const sync = () => {
    if (document.getElementById("layer-heat").checked) {
      if (!map.hasLayer(heatLayer)) heatLayer.addTo(map);
    } else if (map.hasLayer(heatLayer)) map.removeLayer(heatLayer);

    if (document.getElementById("layer-choro").checked) {
      if (choroLayer && !map.hasLayer(choroLayer)) choroLayer.addTo(map);
    } else if (choroLayer && map.hasLayer(choroLayer)) map.removeLayer(choroLayer);

    if (document.getElementById("layer-points").checked) {
      if (!map.hasLayer(clusterLayer)) clusterLayer.addTo(map);
      loadPoints();
    } else if (map.hasLayer(clusterLayer)) map.removeLayer(clusterLayer);
  };
  ["layer-heat", "layer-choro", "layer-points"].forEach(id =>
    document.getElementById(id).addEventListener("change", sync));
  return sync;
}

// ---------------- 图例 ----------------
function renderLegend() {
  const el = document.getElementById("legend");
  el.innerHTML = "<b>分级图例</b>" + Object.entries(SEV_COLORS).map(([k, c]) =>
    `<div class="leg-item"><span class="dot" style="background:${c}"></span>${k}</div>`).join("");
}

// ---------------- 逐月播放 ----------------
function playMonths() {
  if (state.playing) return;
  const sel = document.getElementById("month-select");
  const months = [...sel.options].slice(1).map(o => o.value);
  state.playing = true;
  document.getElementById("play-btn").disabled = true;
  document.getElementById("stop-btn").disabled = false;
  let i = 0;
  state.playTimer = setInterval(() => {
    if (i >= months.length) { stopPlay(); return; }
    sel.value = months[i];
    state.month = months[i];
    refresh(true);
    i++;
  }, 1300);
}
function stopPlay() {
  state.playing = false;
  clearInterval(state.playTimer);
  document.getElementById("play-btn").disabled = false;
  document.getElementById("stop-btn").disabled = true;
}

// ---------------- 启动 ----------------
(async function main() {
  renderLegend();
  await initChoro();
  const syncLayers = bindLayers();
  await loadOverview();
  await loadNeighbourhoodOptions();
  syncLayers();
  refresh(true);

  // 底图切换
  L.control.layers({ "浅色底图": baseLight, "暗色底图": baseDark }, {}, { position: "topright" }).addTo(map);

  // 视口变化 -> 刷新热力与单点
  map.on("moveend", () => {
    loadHeat();
    if (map.getZoom() >= POINT_ZOOM_THRESHOLD) loadPoints();
  });

  document.getElementById("play-btn").addEventListener("click", playMonths);
  document.getElementById("stop-btn").addEventListener("click", stopPlay);
  document.getElementById("cat-all").addEventListener("click", () => {
    document.querySelectorAll("#category-box input").forEach(c => { c.checked = true; state.categories.add(c.value); });
    refresh(true);
  });
  document.getElementById("cat-none").addEventListener("click", () => {
    document.querySelectorAll("#category-box input").forEach(c => c.checked = false);
    state.categories.clear();
    refresh(true);
  });
  document.getElementById("outcome-select").addEventListener("change", e => {
    state.outcomeType = e.target.value; refresh(true);
  });
})();
