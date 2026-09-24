import { fetchRover, fetchAnalytics, getApiBase } from "./api.js?v=4.3.0";

const $ = (id) => document.getElementById(id);
const POLL_MS = 2000;
let timer = null;
const history = {
  accel: { x: [], y: [], z: [] },
  gyro: { x: [], y: [], z: [] },
  vibration: [],
};

function text(v, fallback = "NO DATA") {
  return v === null || v === undefined || v === "" ? fallback : String(v);
}
function num(v, digits = 0) {
  if (v === null || v === undefined || v === "") return "—";
  const n = Number(v);
  return Number.isFinite(n) ? n.toFixed(digits) : "—";
}
function ageText(sec) {
  if (sec === null || sec === undefined || !Number.isFinite(Number(sec))) return "No data";
  const s = Math.max(0, Math.round(Number(sec)));
  if (s < 2) return "now";
  if (s < 60) return `${s} sec ago`;
  return `${Math.floor(s / 60)} min ago`;
}
function boolState(v) {
  if (v === true) return ["DETECTED", "danger"];
  if (v === false) return ["CLEAR", "safe"];
  return ["NO DATA", "neutral"];
}
function gasCard(name, value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) {
    return `<article class="sensor-card neutral">
      <span class="sensor-name">${name}</span>
      <strong class="sensor-value">NO DATA</strong>
      <span class="sensor-foot">SENSOR RESPONSE · NO DATA</span>
    </article>`;
  }
  const raw = Math.round(Number(value));
  const saturated = raw >= 4090;
  const nearCeiling = raw >= 3950 && !saturated;
  const cls = saturated ? "danger" : nearCeiling ? "warning" : "";
  const state = saturated ? "SIGNAL SATURATED · CHECK SENSOR RANGE" : nearCeiling ? "HIGH SIGNAL · NEAR ADC RANGE LIMIT" : "LIVE SENSOR RESPONSE";
  return `<article class="sensor-card ${cls}">
    <span class="sensor-name">${name}</span>
    <strong class="sensor-value">${raw} <small>raw</small></strong>
    <span class="sensor-foot">${state}</span>
  </article>`;
}
function gasEstimateCard(title, est) {
  if (!est || est.raw_adc == null) return gasCard(title, null);
  const raw = Math.round(Number(est.raw_adc));
  const saturated = !!est.adc_saturated;
  const nearCeiling = !!est.near_adc_ceiling;
  const cls = saturated ? "danger" : nearCeiling ? "warning" : "";
  const ppmLine = est.display || "LEARNING BASELINE";
  const range = Array.isArray(est.reference_range) ? `${est.reference_range[0]}–${est.reference_range[1]} ${est.unit || "ppm"}` : "manufacturer reference model";
  const foot = saturated ? "ADC SATURATED · ESTIMATE LIMITED" : `${ppmLine} · REF RANGE ${range}`;
  return `<article class="sensor-card ${cls}">
    <span class="sensor-name">${escapeHtml(title)}</span>
    <strong class="sensor-value">${escapeHtml(ppmLine)}</strong>
    <span class="sensor-foot">ADC ${raw}/4095 · ${escapeHtml(foot)}</span>
  </article>`;
}

function metric(name, value, unit = "", foot = "", cls = "") {
  return `<article class="metric ${cls}">
    <span class="metric-name">${name}</span>
    <strong>${value}${unit ? ` <small>${unit}</small>` : ""}</strong>
    <em>${foot}</em>
  </article>`;
}
function statusCard(name, value, foot = "") {
  const [label, cls] = boolState(value);
  return `<article class="sensor-card ${cls}">
    <span class="sensor-name">${name}</span>
    <strong class="sensor-value">${label}</strong>
    <span class="sensor-foot">${foot}</span>
  </article>`;
}
function setBadge(el, label, cls = "neutral") {
  if (!el) return;
  el.textContent = label;
  el.className = `badge ${cls}`;
}

function pushHistory(group, x, y, z) {
  if (![x, y, z].every((v) => Number.isFinite(Number(v)))) return false;
  ["x", "y", "z"].forEach((axis, i) => {
    const v = [x, y, z][i];
    group[axis].push(Number(v));
    if (group[axis].length > 60) group[axis].shift();
  });
  return true;
}

function drawChart(canvas, group) {
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#04111d";
  ctx.fillRect(0, 0, w, h);

  ctx.strokeStyle = "#153d57";
  ctx.lineWidth = 1;
  for (let i = 1; i < 6; i++) {
    const x = (w / 6) * i;
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
  }
  for (let i = 1; i < 4; i++) {
    const y = (h / 4) * i;
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
  }

  const values = [...group.x, ...group.y, ...group.z];
  if (!values.length) return;
  let min = Math.min(...values), max = Math.max(...values);
  if (min === max) { min -= 1; max += 1; }
  const pad = (max - min) * 0.15;
  min -= pad; max += pad;
  const colors = { x: "#42bfff", y: "#45e48b", z: "#ffc857" };
  for (const axis of ["x", "y", "z"]) {
    const arr = group[axis];
    if (arr.length < 2) continue;
    ctx.strokeStyle = colors[axis];
    ctx.lineWidth = 2;
    ctx.beginPath();
    arr.forEach((v, i) => {
      const x = (i / Math.max(1, arr.length - 1)) * w;
      const y = h - ((v - min) / (max - min)) * h;
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.stroke();
  }
}

function pushBinaryHistory(group, value) {
  if (value !== true && value !== false) return false;
  group.push(value ? 1 : 0);
  if (group.length > 60) group.shift();
  return true;
}

function drawBinaryChart(canvas, values) {
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#04111d";
  ctx.fillRect(0, 0, w, h);
  ctx.strokeStyle = "#153d57";
  ctx.lineWidth = 1;
  for (let i = 1; i < 8; i++) {
    const x = (w / 8) * i;
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
  }
  const yClear = h * 0.76;
  const yDetected = h * 0.24;
  ctx.strokeStyle = "#23485f";
  [yClear, yDetected].forEach((y) => { ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(w,y); ctx.stroke(); });
  ctx.font = "24px Consolas";
  ctx.fillStyle = "#71899c";
  ctx.fillText("DETECTED", 12, yDetected - 10);
  ctx.fillText("CLEAR", 12, yClear - 10);
  if (!values.length) return;
  ctx.strokeStyle = values[values.length - 1] ? "#ff4965" : "#45e48b";
  ctx.lineWidth = 4;
  ctx.beginPath();
  values.forEach((v, i) => {
    const x = (i / Math.max(1, values.length - 1)) * w;
    const y = v ? yDetected : yClear;
    if (i === 0) ctx.moveTo(x, y);
    else {
      const prevX = ((i - 1) / Math.max(1, values.length - 1)) * w;
      const prevY = values[i-1] ? yDetected : yClear;
      ctx.lineTo(x, prevY);
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();
}

function renderTelemetry(data) {
  const t = data?.telemetry || {};
  const online = !!data?.rover_online;
  const hazard = data?.server_hazard?.state || "unknown";

  $("gasGrid").innerHTML = [
    gasCard("▣ MQ-4 · Methane Response", t.mq4_raw),
    gasCard("⊙ MQ-7 · CO Response", t.mq7_raw),
    gasCard("≋ MQ-135 · Air Quality Response", t.mq135_raw),
    gasCard("◯ MQ-3 · VOC / Gas Response", t.mq3_raw),
  ].join("");

  $("envModuleLabel").textContent = (t.temp != null || t.pressure != null || t.humidity != null) ? "BMP280 + DHT22" : "ENVIRONMENT SENSORS";
  $("environmentGrid").innerHTML = [
    metric("♨ Temperature", t.temp == null ? "N/A" : num(t.temp, 2), t.temp == null ? "" : "°C", "BMP280"),
    metric("◯ Humidity", t.humidity == null ? "N/A" : num(t.humidity, 1), t.humidity == null ? "" : "%", "DHT22 · GPIO 27"),
    metric("◉ Pressure", t.pressure == null ? "N/A" : num(t.pressure, 2), t.pressure == null ? "" : "hPa", "BMP280"),
  ].join("");

  const [flameLabel, flameCls] = boolState(t.flame);
  const [waterLabel, waterCls] = boolState(t.water);
  $("hazardGrid").innerHTML = [
    metric("♨ Flame Detection", flameLabel, "", "GPIO 2", flameCls),
    metric("◯ Water Detection", waterLabel, "", "GPIO 12", waterCls),
    metric(
      "⌁ Obstacle Distance",
      t.distance_cm == null ? "NO DATA" : num(t.distance_cm, 2),
      t.distance_cm == null ? "" : "cm",
      t.distance_cm == null ? "HC-SR04 · UNAVAILABLE" : "HC-SR04",
      t.distance_cm == null ? "neutral" : Number(t.distance_cm) <= 10 ? "danger" : Number(t.distance_cm) <= 25 ? "warning" : ""
    ),
  ].join("");

  const soundDetected = t.sound == null ? null : Number(t.sound) > 0;
  const [soundLabel, soundCls] = boolState(soundDetected);
  const imuLive = [t.accel_x, t.accel_y, t.accel_z, t.gyro_x, t.gyro_y, t.gyro_z].some((v) => v !== null && v !== undefined && Number.isFinite(Number(v)));
  $("presenceGrid").innerHTML = [
    statusCard("⊙ Human Motion — PIR", t.motion, "GPIO 14"),
    statusCard("≋ Vibration — SW-420", t.vibration, "GPIO 13"),
    (() => {
      const tilt = t.tilt_deg == null ? null : Number(t.tilt_deg);
      const tiltCls = tilt == null ? "neutral" : tilt >= 70 ? "danger" : tilt >= 45 ? "warning" : "";
      const tiltFoot = tilt == null ? "IMU TILT UNAVAILABLE" : tilt >= 70 ? "EXTREME TILT · STOP / ASSESS" : tilt >= 45 ? "HIGH TILT · CAUTION" : "LIVE IMU DATA";
      return `<article class="sensor-card ${tiltCls}"><span class="sensor-name">◇ Rover Tilt</span><strong class="sensor-value">${tilt == null ? "NO DATA" : `${num(tilt, 2)}°`}</strong><span class="sensor-foot">${tiltFoot}</span></article>`;
    })(),
    `<article class="sensor-card ${soundCls}"><span class="sensor-name">≋ Sound Detection</span><strong class="sensor-value">${soundLabel}</strong><span class="sensor-foot">GPIO 15 · DIGITAL</span></article>`,
  ].join("");

  $("connectBackend").textContent = online ? "ONLINE" : "OFFLINE";
  $("connectBackend").className = online ? "online" : "";
  const wifiRssi = t.wifi_rssi ?? t.rssi;
  $("connectWifi").textContent = wifiRssi == null ? "NO DATA" : `${wifiRssi} dBm`;
  $("connectPacket").textContent = ageText(data?.telemetry_age_seconds);
  $("connectCamera").textContent = data?.camera_url ? "STREAM READY" : "PENDING INTEGRATION";

  $("headerOnlineDot").classList.toggle("online", online);
  $("headerOnline").textContent = online ? "ONLINE" : "OFFLINE";
  $("headerOnline").className = online ? "online" : "";
  $("headerPacket").textContent = ageText(data?.telemetry_age_seconds);
  $("headerCamera").textContent = data?.camera_url ? "READY" : "PENDING";

  setBadge($("backendStatus"), online ? "BACKEND + ESP32 ONLINE" : "BACKEND / ESP32 OFFLINE", online ? "safe" : "danger");
  const hazardLabel = hazard === "danger" ? "CRITICAL HAZARD" : hazard === "warning" ? "SAFETY WARNING" : hazard === "safe" ? "NO ACTIVE HAZARD" : "HAZARD UNKNOWN";
  setBadge($("hazardBadge"), hazardLabel, hazard === "safe" ? "safe" : hazard === "warning" ? "warning" : hazard === "danger" ? "danger" : "neutral");
  $("hazardBadge").title = (data?.server_hazard?.reasons || []).join("; ") || "No active hazard reasons";
  setBadge($("roverLinkBadge"), online ? "ROVER TELEMETRY ONLINE" : "ROVER TELEMETRY OFFLINE", online ? "safe" : "neutral");

  const who = t.imu_who_am_i || "";
  const imuStatus = t.imu_status || "";
  const imuHasLiveData = [t.accel_x, t.accel_y, t.accel_z, t.gyro_x, t.gyro_y, t.gyro_z].some((v) => v !== null && v !== undefined && Number.isFinite(Number(v)));
  $("imuIdentity").textContent = imuHasLiveData
    ? `LIVE MPU DATA · I²C ${t.imu_address || "0x68"}${who ? ` · WHO_AM_I ${who}` : ""}`
    : (who || imuStatus ? `I²C ${t.imu_address || "0x68"} · WHO_AM_I ${who || "—"} · ${imuStatus || "detected"}` : "WAITING FOR IMU DATA");
  $("accelSummary").innerHTML = `X: ${num(t.accel_x, 3)} &nbsp;&nbsp; Y: ${num(t.accel_y, 3)} &nbsp;&nbsp; Z: ${num(t.accel_z, 3)}`;
  $("gyroSummary").innerHTML = `X: ${num(t.gyro_x, 3)} &nbsp;&nbsp; Y: ${num(t.gyro_y, 3)} &nbsp;&nbsp; Z: ${num(t.gyro_z, 3)}`;

  const gotAccel = pushHistory(history.accel, t.accel_x, t.accel_y, t.accel_z);
  const gotGyro = pushHistory(history.gyro, t.gyro_x, t.gyro_y, t.gyro_z);
  $("accelEmpty").style.display = history.accel.x.length ? "none" : "block";
  $("gyroEmpty").style.display = history.gyro.x.length ? "none" : "block";
  drawChart($("accelChart"), history.accel);
  drawChart($("gyroChart"), history.gyro);
  pushBinaryHistory(history.vibration, t.vibration);
  drawBinaryChart($("vibrationChart"), history.vibration);
  $("vibrationEmpty").style.display = history.vibration.length ? "none" : "block";
  $("vibrationChartState").textContent = t.vibration === true ? "DETECTED" : t.vibration === false ? "CLEAR" : "NO DATA";
  $("vibrationChartState").className = t.vibration === true ? "chart-state danger" : t.vibration === false ? "chart-state safe" : "chart-state";

  renderCamera(data);
}


function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function riskClass(state) {
  if (["emergency", "danger"].includes(state)) return "danger";
  if (state === "warning") return "warning";
  if (state === "caution") return "caution";
  if (state === "safe") return "safe";
  return "neutral";
}

function renderAnalytics(response) {
  const a = response?.analytics || {};
  const state = a.state || "unknown";
  const cls = riskClass(state);
  const score = Number.isFinite(Number(a.risk_score)) ? Math.max(0, Math.min(100, Number(a.risk_score))) : 0;
  const coverage = Number.isFinite(Number(a.analysis_coverage_percent)) ? Math.max(0, Math.min(100, Number(a.analysis_coverage_percent))) : 0;

  setBadge($("aiEngineBadge"), a.engine ? "SAFETY ANALYSIS ONLINE" : "ANALYSIS WAITING", a.engine ? "safe" : "neutral");
  const label = state === "emergency" ? "EMERGENCY" : state === "danger" ? "CRITICAL" : state === "warning" ? "WARNING" : state === "caution" ? "CAUTION" : state === "safe" ? "NORMAL" : "RISK UNKNOWN";
  setBadge($("aiRiskBadge"), label, cls === "caution" ? "warning" : cls);

  $("riskScore").textContent = Math.round(score);
  $("riskGauge").className = `risk-gauge ${cls}`;
  $("riskSummary").textContent = a.summary || "Waiting for analytics";
  $("riskMethod").textContent = a.method || "Live telemetry rules + trend analysis";
  const drivers = Array.isArray(a.risk_drivers) ? a.risk_drivers : [];
  $("riskDrivers").innerHTML = drivers.length
    ? `<span>Primary drivers</span>${drivers.map((d) => `<b class="${riskClass(d.severity)}">${escapeHtml(d.title)}</b>`).join("")}`
    : `<span>Primary drivers</span><b class="safe">No active warning-level driver</b>`;
  const breakdown = Array.isArray(a.risk_breakdown) ? a.risk_breakdown : [];
  $("riskBreakdown").innerHTML = breakdown.length
    ? `<div class="risk-breakdown-title">Why this risk level</div>${breakdown.map((d) => `<article class="risk-reason ${riskClass(d.severity)}"><div><b>${escapeHtml(d.title)}</b><span>${escapeHtml(d.message)}</span></div><strong>${escapeHtml(String(d.severity || "info").toUpperCase())}</strong><small>${escapeHtml(d.action || "")}</small></article>`).join("")}`
    : `<article class="risk-reason safe"><div><b>No active warning condition</b><span>Current live inputs are within the configured operational rules.</span></div><strong>NORMAL</strong></article>`;
  $("coverageValue").textContent = `${Math.round(coverage)}%`;
  $("coverageBar").style.width = `${coverage}%`;

  const mq = a.mq_reference_estimates || {};
  if (Object.keys(mq).length) {
    $("gasGrid").innerHTML = [
      gasEstimateCard("▣ MQ-4 · Methane", mq.mq4_raw),
      gasEstimateCard("⊙ MQ-7 · Carbon Monoxide", mq.mq7_raw),
      gasEstimateCard("≋ MQ-135 · Air Quality / H₂-eq", mq.mq135_raw),
      gasEstimateCard("◯ MQ-3 · Ethanol", mq.mq3_raw),
    ].join("");
  }

  const checkLabels = {
    live_telemetry: "Live telemetry",
    methane_concentration: "Methane reference estimate",
    co_concentration: "CO reference estimate",
    heat_compliance: "Wet-bulb/heat input",
    physical_hazards: "Physical hazard sensors",
    obstacle: "Obstacle sensor",
    imu: "IMU / tilt",
    connectivity: "Telemetry link",
    sound_event: "Sound event input",
  };
  $("aiChecks").innerHTML = Object.entries(a.checks || {}).map(([key, ok]) => `
    <article class="ai-check ${ok ? "ready" : "limited"}">
      <span>${ok ? "✓" : "!"}</span>
      <div><b>${escapeHtml(checkLabels[key] || key)}</b><small>${ok ? "SUPPORTED" : (key === "methane_concentration" || key === "co_concentration" ? "REFERENCE MODEL LEARNING" : key === "heat_compliance" ? "ENVIRONMENT INPUT PARTIAL" : "DATA UNAVAILABLE")}</small></div>
    </article>`).join("") || '<div class="ai-empty">No decision-gate data yet.</div>';

  const alerts = Array.isArray(a.alerts) ? a.alerts : [];
  $("aiAlertCount").textContent = `${alerts.length} active item${alerts.length === 1 ? "" : "s"}`;
  $("aiAlerts").innerHTML = alerts.length ? alerts.map((alert) => `
    <article class="ai-alert ${riskClass(alert.severity)}">
      <div class="ai-alert-severity">${escapeHtml(String(alert.severity || "info").toUpperCase())}</div>
      <div class="ai-alert-main">
        <h4>${escapeHtml(alert.title)}</h4>
        <p>${escapeHtml(alert.message)}</p>
        <div class="ai-action"><b>Recommended action:</b> ${escapeHtml(alert.action)}</div>
      </div>
      <div class="ai-alert-basis"><span>${alert.regulatory ? "REGULATORY / OFFICIAL REFERENCE" : "ENGINEERING / ANALYTIC RULE"}</span><small>${escapeHtml(alert.basis)}</small></div>
    </article>`).join("") : '<div class="ai-empty safe-text">No active warnings detected by the current rule set.</div>';

  const trends = Array.isArray(a.gas_trends) ? a.gas_trends : [];
  $("gasTrendGrid").innerHTML = trends.map((item) => {
    const statusClass = item.status === "saturated" || item.status === "rapid-rise" ? "warning" : ["near-ceiling", "elevated-trend"].includes(item.status) ? "caution" : "neutral";
    const delta = item.change_percent == null ? "baseline learning" : `${item.change_percent > 0 ? "+" : ""}${item.change_percent}% vs baseline`;
    const ref = item.reference_estimate || {};
    const estimateText = ref.display || "LEARNING BASELINE";
    const ratioText = ref.rs_r0 == null ? "Rs/R0 learning" : `Rs/R0 ${Number(ref.rs_r0).toFixed(3)}`;
    return `<article class="ai-trend-card ${statusClass}">
      <span>${escapeHtml(item.label)}</span>
      <strong>${escapeHtml(estimateText)}</strong>
      <b>${escapeHtml(String(item.status || "monitoring").replaceAll("-", " ").toUpperCase())}</b>
      <em>ADC ${item.current == null ? "—" : Math.round(item.current)}/4095 · ${escapeHtml(ratioText)} · ${escapeHtml(delta)}</em>
    </article>`;
  }).join("") || '<div class="ai-empty">Collecting baseline telemetry.</div>';

  const refs = Array.isArray(a.regulatory_references) ? a.regulatory_references : [];
  const checks = a.checks || {};
  $("regulatoryThresholds").innerHTML = refs.map((ref) => {
    let applies = "REFERENCE ONLY";
    let applyClass = "neutral";
    if (ref.field === "ch4_ppm") { applies = checks.methane_concentration ? "REFERENCE ESTIMATE ACTIVE" : "BASELINE LEARNING"; applyClass = checks.methane_concentration ? "safe" : "neutral"; }
    if (ref.field === "co_ppm") { applies = checks.co_concentration ? "REFERENCE ESTIMATE ACTIVE" : "BASELINE LEARNING"; applyClass = checks.co_concentration ? "safe" : "neutral"; }
    if (ref.field === "wet_bulb_temp") { applies = checks.heat_compliance ? "ACTIVE" : "WET-BULB DATA REQUIRED"; applyClass = checks.heat_compliance ? "safe" : "warning"; }
    if (ref.field === "sound_dba") { applies = "dBA INPUT NOT AVAILABLE"; applyClass = "warning"; }
    return `<tr>
      <td><b>${escapeHtml(ref.parameter)}</b><small>${escapeHtml(ref.source)}</small></td>
      <td>${escapeHtml(ref.warning)}</td>
      <td>${escapeHtml(ref.critical)}</td>
      <td>${escapeHtml(ref.emergency)}</td>
      <td><span class="threshold-state ${applyClass}">${escapeHtml(applies)}</span><small>${escapeHtml(ref.note)}</small></td>
    </tr>`;
  }).join("");

  const operational = Array.isArray(a.operational_references) ? a.operational_references : [];
  $("operationalThresholds").innerHTML = operational.map((ref) => `<tr>
    <td><b>${escapeHtml(ref.parameter)}</b></td>
    <td>${escapeHtml(ref.warning)}</td>
    <td>${escapeHtml(ref.critical)}</td>
    <td><small>${escapeHtml(ref.basis)}</small></td>
  </tr>`).join("");

  const limitations = Array.isArray(a.limitations) ? a.limitations : [];
  $("aiLimitations").innerHTML = limitations.map((item) => `<span>${escapeHtml(item)}</span>`).join("");
}

function renderCamera(data) {
  const frame = $("cameraFrame");
  const url = data?.camera_url;
  if (url) {
    frame.innerHTML = `<img class="camera-stream" src="${url}" alt="Live MineRakshak rover camera stream" />`;
    $("cameraTitle")?.remove?.();
    return;
  }
  if (!frame.querySelector(".camera-copy")) {
    frame.innerHTML = `<div class="camera-crosshair" aria-hidden="true"></div><div class="camera-copy"><b id="cameraTitle">CAMERA STREAM NOT CONNECTED</b><p id="cameraText">The camera is part of the rover kit, not the ESP32 test stack. We will connect the stream here after confirming the rover camera output/API.</p><span>Reserved live-view panel</span></div>`;
  }
}

async function refresh() {
  try {
    const [data, analytics] = await Promise.all([
      fetchRover("MRR-01"),
      fetchAnalytics("MRR-01"),
    ]);
    renderTelemetry(data);
    renderAnalytics(analytics);
  } catch (error) {
    $("headerOnlineDot").classList.remove("online");
    $("headerOnline").textContent = "OFFLINE";
    $("headerOnline").className = "";
    $("headerPacket").textContent = "Backend unavailable";
    $("connectBackend").textContent = "OFFLINE";
    setBadge($("backendStatus"), "BACKEND OFFLINE", "danger");
    setBadge($("hazardBadge"), "NO LIVE DATA", "neutral");
    setBadge($("roverLinkBadge"), "ROVER TELEMETRY OFFLINE", "neutral");
    setBadge($("aiEngineBadge"), "SAFETY ANALYSIS OFFLINE", "danger");
    setBadge($("aiRiskBadge"), "NO LIVE ANALYTICS", "neutral");
  }
}

function initTabs() {
  document.querySelectorAll("[data-page]").forEach((button) => {
    button.addEventListener("click", () => {
      const page = button.dataset.page;
      document.querySelectorAll(".page").forEach((section) => section.classList.toggle("active", section.id === page));
      document.querySelectorAll(".tab[data-page]").forEach((tab) => {
        const active = tab === button;
        tab.classList.toggle("active", active);
        if (active) tab.setAttribute("aria-current", "page"); else tab.removeAttribute("aria-current");
      });
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  });
}

function init() {
  initTabs();
  $("refreshButton").addEventListener("click", refresh);
  $("footerEndpoint").textContent = `Backend: ${getApiBase()}`;
  refresh();
  timer = setInterval(refresh, POLL_MS);
}

document.addEventListener("DOMContentLoaded", init);
