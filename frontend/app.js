(function () {
  "use strict";

  const API_BASE = "/api";
  const MAX_LOG_ENTRIES = 8;

  const els = {
    date:            document.getElementById("operation-date"),
    number:          document.getElementById("operation-number"),
    well:            document.getElementById("well-name"),
    file:            document.getElementById("report-file"),
    status:          document.getElementById("status"),
    btnCreate:       document.getElementById("btn-create"),
    btnUpload:       document.getElementById("btn-upload"),
    btnCharts:       document.getElementById("btn-charts"),
    btnClose:        document.getElementById("btn-close"),
    chartsContainer: document.getElementById("charts-container"),
  };

  let sessionId = null;
  let logEntries = [];

  function log(label, payload) {
    const stamp = new Date().toISOString().substring(11, 19);
    let body;
    if (typeof payload === "string") {
      body = payload;
    } else {
      // Срезаем тяжёлые массивы x/y — оставляем только мета
      const safe = stripArrays(payload);
      body = JSON.stringify(safe, null, 2);
    }
    logEntries.unshift(`[${stamp}] ${label}\n${body}`);
    if (logEntries.length > MAX_LOG_ENTRIES) logEntries.length = MAX_LOG_ENTRIES;
    els.status.textContent = logEntries.join("\n\n");
  }

  // Рекурсивно заменяет массивы длиннее 5 элементов на краткое описание
  function stripArrays(obj) {
    if (Array.isArray(obj)) {
      return obj.length > 5 ? `[...${obj.length} values]` : obj;
    }
    if (obj !== null && typeof obj === "object") {
      const out = {};
      for (const [k, v] of Object.entries(obj)) {
        out[k] = stripArrays(v);
      }
      return out;
    }
    return obj;
  }

  function setHasSession(hasIt) {
    els.btnUpload.disabled = !hasIt;
    els.btnCharts.disabled = !hasIt;
    els.btnClose.disabled = !hasIt;
  }

  async function createSession() {
    const payload = {
      operation_date:   els.date.value,
      operation_number: els.number.value.trim(),
      well_name:        els.well.value.trim(),
    };
    if (!payload.operation_date || !payload.operation_number || !payload.well_name) {
      log("❌ validation", "Заполните дату, номер операции и скважину");
      return;
    }
    try {
      const res  = await fetch(`${API_BASE}/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(JSON.stringify(data));
      sessionId = data.id;
      setHasSession(true);
      log("✅ session created", { id: data.id, well: data.well_name, date: data.operation_date });
    } catch (err) {
      log("❌ session error", err.message);
    }
  }

  async function uploadFile() {
    if (sessionId == null) return;
    const file = els.file.files[0];
    if (!file) { log("❌ validation", "Выберите Excel-файл"); return; }

    log("⏳ uploading", file.name);
    const form = new FormData();
    form.append("file", file);

    try {
      const res  = await fetch(`${API_BASE}/sessions/${sessionId}/upload`, {
        method: "POST",
        body: form,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(JSON.stringify(data.detail || data));

      log("✅ file uploaded", {
        filename: data.filename,
        size_kb: Math.round(data.size_bytes / 1024) + " KB",
        sheets: { customer: data.customer_sheet, analyzer: data.analyzer_sheet },
        charts: (data.charts || []).length + " каналов",
        status: data.status,
      });

      if (data.charts && data.charts.length > 0) {
        const figures = data.charts.map((c, i) => ({
          id: "ch_" + i,
          title: c.name,
          y_label: resolveYLabel(c.name),
          traces: [{ name: "Оригинал", x: c.x, y: c.y }],
        }));
        window.OilCharts.render(els.chartsContainer, figures);
        log("📊 charts rendered", figures.length + " графиков");
      }
    } catch (err) {
      log("❌ upload error", err.message);
    }
  }

  async function fetchCharts() {
    if (sessionId == null) return;
    try {
      const res  = await fetch(`${API_BASE}/sessions/${sessionId}/charts`);
      const data = await res.json();
      if (!res.ok) throw new Error(JSON.stringify(data));
      const figures = (data.figures || []).map(fig => ({
        ...fig,
        y_label: resolveYLabel(fig.title),
      }));
      log("📊 charts fetched", figures.length + " графиков");
      window.OilCharts.render(els.chartsContainer, figures);
    } catch (err) {
      log("❌ charts error", err.message);
    }
  }

  async function closeSession() {
    if (sessionId == null) return;
    try {
      const res  = await fetch(`${API_BASE}/sessions/${sessionId}`, { method: "DELETE" });
      const data = await res.json();
      if (!res.ok) throw new Error(JSON.stringify(data));
      log("🔒 session closed", { id: sessionId });
      sessionId = null;
      logEntries = [];
      els.status.textContent = "сессия закрыта";
      setHasSession(false);
      els.chartsContainer.innerHTML = "";
    } catch (err) {
      log("❌ close error", err.message);
    }
  }

  // Маппинг названия канала → единица измерения для подписи оси Y
  function resolveYLabel(name) {
    if (!name) return "";
    const n = name.toLowerCase();
    if (n.includes("расход")) return "м³/мин";
    if (n.includes("сумматор")) return "м³";
    if (n.includes("давление")) return "атм";
    if (n.includes("концентрац")) return "кг/м³";
    if (n.includes("время")) return "мин";
    return "";
  }

  els.btnCreate.addEventListener("click", createSession);
  els.btnUpload.addEventListener("click", uploadFile);
  els.btnCharts.addEventListener("click", fetchCharts);
  els.btnClose.addEventListener("click", closeSession);
})();