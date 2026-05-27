(function () {
  "use strict";

  const API_BASE = "/api";

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

  function log(label, payload) {
    const stamp = new Date().toISOString().substring(11, 19);
    const body = typeof payload === "string" ? payload : JSON.stringify(payload, null, 2);
    els.status.textContent = `[${stamp}] ${label}\n${body}\n\n` + els.status.textContent;
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
      log("validation", "Заполните дату, номер операции и скважину");
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
      log("session created", data);
    } catch (err) {
      log("session error", err.message);
    }
  }

  async function uploadFile() {
    if (sessionId == null) return;
    const file = els.file.files[0];
    if (!file) { log("validation", "Выберите Excel-файл"); return; }

    const form = new FormData();
    form.append("file", file);

    try {
      const res  = await fetch(`${API_BASE}/sessions/${sessionId}/upload`, {
        method: "POST",
        body: form,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(JSON.stringify(data));
      log("file uploaded", {
        sheets: { customer: data.customer_sheet, analyzer: data.analyzer_sheet },
        charts_count: (data.charts || []).length,
        status: data.status,
      });

      // Немедленно рисуем графики из ответа upload — не делаем второй запрос
      if (data.charts && data.charts.length > 0) {
        const figures = data.charts.map((c, i) => ({
          id: "ch_" + i,
          title: c.name,
          traces: [{ name: "Оригинал", x: c.x, y: c.y }],
        }));
        window.OilCharts.render(els.chartsContainer, figures);
        log("charts rendered", `${figures.length} графиков`);
      }
    } catch (err) {
      log("upload error", err.message);
    }
  }

  async function fetchCharts() {
    if (sessionId == null) return;
    try {
      const res  = await fetch(`${API_BASE}/sessions/${sessionId}/charts`);
      const data = await res.json();
      if (!res.ok) throw new Error(JSON.stringify(data));
      log("charts response", { figures: (data.figures || []).length });
      window.OilCharts.render(els.chartsContainer, data.figures || []);
    } catch (err) {
      log("charts error", err.message);
    }
  }

  async function closeSession() {
    if (sessionId == null) return;
    try {
      const res  = await fetch(`${API_BASE}/sessions/${sessionId}`, { method: "DELETE" });
      const data = await res.json();
      if (!res.ok) throw new Error(JSON.stringify(data));
      log("session closed", data);
      sessionId = null;
      setHasSession(false);
      els.chartsContainer.innerHTML = "";
    } catch (err) {
      log("close error", err.message);
    }
  }

  els.btnCreate.addEventListener("click", createSession);
  els.btnUpload.addEventListener("click", uploadFile);
  els.btnCharts.addEventListener("click", fetchCharts);
  els.btnClose.addEventListener("click", closeSession);
})();