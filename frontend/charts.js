(function () {
  "use strict";

  function makeLayout(titleText, yLabel) {
    return {
      paper_bgcolor: "#181b22",
      plot_bgcolor:  "#181b22",
      font:          { color: "#e6e6e6", size: 12 },
      margin:        { l: 68, r: 24, t: 60, b: 68 },
      title: {
        text:    titleText,
        font:    { size: 13, color: "#e6e6e6" },
        x:       0.02,
        xanchor: "left",
        xref:    "paper",
        pad:     { t: 4 },
      },
      xaxis: {
        title:      { text: "Время, мин", font: { size: 11, color: "#9aa0a6" }, standoff: 10 },
        gridcolor:  "#2a2f3a",
        linecolor:  "#3a3f4a",
        tickcolor:  "#9aa0a6",
        tickfont:   { size: 10 },
        zeroline:   false,
        automargin: true,
      },
      yaxis: {
        title:      { text: yLabel, font: { size: 11, color: "#9aa0a6" }, standoff: 10 },
        gridcolor:  "#2a2f3a",
        linecolor:  "#3a3f4a",
        tickcolor:  "#9aa0a6",
        tickfont:   { size: 10 },
        zeroline:   false,
        automargin: true,
      },
      legend: {
        orientation: "h",
        y:           -0.22,
        x:           0,
        font:        { size: 11 },
        bgcolor:     "rgba(0,0,0,0)",
      },
      hovermode: "x unified",
    };
  }

  const PLOTLY_CONFIG = {
    responsive:             true,
    displayModeBar:         true,
    modeBarButtonsToRemove: ["toImage", "sendDataToCloud"],
    displaylogo:            false,
  };

  // Всплывающий тост над кнопкой
  function showToast(anchorEl, message) {
    const existing = anchorEl.parentElement.querySelector(".oil-toast");
    if (existing) existing.remove();

    const toast = document.createElement("div");
    toast.className = "oil-toast";
    toast.textContent = message;
    toast.style.cssText = [
      "position:absolute",
      "bottom:calc(100% + 8px)",
      "right:0",
      "background:#2d1f1f",
      "color:#f87171",
      "border:1px solid #7f1d1d",
      "border-radius:6px",
      "padding:6px 14px",
      "font-size:12px",
      "white-space:nowrap",
      "pointer-events:none",
      "opacity:0",
      "transition:opacity 0.4s ease",
      "z-index:999",
    ].join(";");

    const wrapper = anchorEl.parentElement;
    wrapper.style.position = "relative";
    wrapper.appendChild(toast);

    // Плавное появление
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        toast.style.opacity = "1";
      });
    });

    // Через 1.5 сек — плавное исчезновение
    setTimeout(function () {
      toast.style.opacity = "0";
      setTimeout(function () { toast.remove(); }, 400);
    }, 1500);
  }

  function render(container, figures) {
    if (!container) return;
    container.innerHTML = "";

    if (!Array.isArray(figures) || figures.length === 0) {
      container.innerHTML =
        '<p style="color:#9aa0a6;font-size:13px;padding:12px;">Графиков нет — загрузите файл.</p>';
      return;
    }

    // 2 графика на строку
    container.style.cssText = [
      "display:grid",
      "grid-template-columns:1fr 1fr",
      "gap:16px",
    ].join(";");

    figures.forEach(function (fig, figIdx) {
      const channelNum = (fig.channel_num && fig.channel_num !== 0)
        ? fig.channel_num
        : (figIdx + 1);

      const yLabel = (fig.y_label && fig.y_label !== "nan") ? fig.y_label : "";

      const rawName  = fig.title || "";
      const safeName = (rawName && rawName !== "nan") ? rawName : ("Канал " + channelNum);

      // Заголовок: №N — Полное название канала (единица)
      const titleText = "№" + channelNum + " \u2014 " + safeName
        + (yLabel ? " (" + yLabel + ")" : "");

      // ── Карточка канала ────────────────────────────────────────────────
      const card = document.createElement("div");
      card.style.cssText = [
        "background:#181b22",
        "border:1px solid #23262d",
        "border-radius:8px",
        "padding:10px 10px 8px 10px",
        "display:flex",
        "flex-direction:column",
        "gap:8px",
      ].join(";");
      container.appendChild(card);

      // ── Plotly ─────────────────────────────────────────────────────────
      const plotDiv = document.createElement("div");
      plotDiv.id = "chart-" + channelNum + "-" + figIdx;
      plotDiv.style.cssText = "width:100%; height:300px;";
      card.appendChild(plotDiv);

      const origData = (fig.traces || []).find(function (t) {
        return !t.name || t.name === "Оригинал";
      }) || (fig.traces || [])[0] || { x: [], y: [] };

      const htSuffix = yLabel ? " " + yLabel : "";
      const traces = [
        {
          x:    origData.x,
          y:    origData.y,
          name: "Оригинал",
          mode: "lines",
          type: "scatter",
          line: { width: 1.5, color: "#4f8cff" },
          hovertemplate: "%{y:.3f}" + htSuffix + "<br>%{x:.2f} мин<extra>Оригинал</extra>",
        },
        {
          x:    origData.x,
          y:    origData.y,
          name: "Исправление (заглушка)",
          mode: "lines",
          type: "scatter",
          line: { width: 1.5, color: "#06d6a0", dash: "dot" },
          hovertemplate: "%{y:.3f}" + htSuffix + "<br>%{x:.2f} мин<extra>Исправление</extra>",
        },
      ];

      window.Plotly.newPlot(plotDiv, traces, makeLayout(titleText, yLabel), PLOTLY_CONFIG);

      // ── Кнопка ────────────────────────────────────────────────────────
      const btnRow = document.createElement("div");
      btnRow.style.cssText = "display:flex; justify-content:flex-end;";
      card.appendChild(btnRow);

      const btn = document.createElement("button");
      btn.textContent = "Применить исправление";
      btn.style.cssText = [
        "padding:6px 16px",
        "background:#2a2f3a",
        "color:#9aa0a6",
        "border:1px solid #3a3f4a",
        "border-radius:6px",
        "cursor:pointer",
        "font-size:12px",
        "font-weight:500",
        "transition:background 0.15s, color 0.15s",
      ].join(";");
      btn.addEventListener("mouseenter", function () {
        btn.style.background = "#333a47";
        btn.style.color = "#c9d1d9";
      });
      btn.addEventListener("mouseleave", function () {
        btn.style.background = "#2a2f3a";
        btn.style.color = "#9aa0a6";
      });
      btn.addEventListener("click", function () {
        showToast(btn, "Метод не реализован");
      });
      btnRow.appendChild(btn);
    });
  }

  window.OilCharts = { render: render };
})();