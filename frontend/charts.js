(function () {
  "use strict";

  function makeLayout(titleText, yLabel) {
    return {
      paper_bgcolor: "#181b22",
      plot_bgcolor:  "#181b22",
      font:  { color: "#e6e6e6", size: 12 },
      margin: { l: 68, r: 24, t: 56, b: 64 },
      title: {
        text:      titleText,
        font:      { size: 13, color: "#e6e6e6" },
        x:         0.02,
        xanchor:   "left",
        xref:      "paper",
      },
      xaxis: {
        title:     { text: "Время, мин", font: { size: 11, color: "#9aa0a6" }, standoff: 10 },
        gridcolor: "#2a2f3a",
        linecolor: "#3a3f4a",
        tickcolor: "#9aa0a6",
        tickfont:  { size: 10 },
        zeroline:  false,
        automargin: true,
      },
      yaxis: {
        title:     { text: yLabel || "", font: { size: 11, color: "#9aa0a6" }, standoff: 10 },
        gridcolor: "#2a2f3a",
        linecolor: "#3a3f4a",
        tickcolor: "#9aa0a6",
        tickfont:  { size: 10 },
        zeroline:  false,
        automargin: true,
      },
      legend: {
        orientation: "h",
        y:           -0.2,
        x:           0,
        font:        { size: 11 },
        bgcolor:     "rgba(0,0,0,0)",
      },
      hovermode: "x unified",
    };
  }

  const PLOTLY_CONFIG = {
    responsive:               true,
    displayModeBar:           true,
    modeBarButtonsToRemove:   ["toImage", "sendDataToCloud"],
    displaylogo:              false,
  };

  function render(container, figures) {
    if (!container) return;
    container.innerHTML = "";

    if (!Array.isArray(figures) || figures.length === 0) {
      container.innerHTML =
        '<p style="color:#9aa0a6;font-size:13px;padding:12px;">Графиков нет — загрузите файл.</p>';
      return;
    }

    container.style.cssText = "display:flex; flex-direction:column; gap:20px;";

    figures.forEach(function (fig, figIdx) {
      // Вычисляем подписи
      const channelNum = (fig.channel_num && fig.channel_num !== 0)
        ? fig.channel_num
        : (figIdx + 1);

      const rawUnit = fig.unit || fig.y_label || "";
      const yLabel  = (rawUnit && rawUnit !== "nan") ? rawUnit : "";

      const rawName  = fig.title || "";
      const safeName = (rawName && rawName !== "nan") ? rawName : ("Канал " + channelNum);
      const titleText = "№" + channelNum + " — " + safeName
        + (yLabel ? "  (" + yLabel + ")" : "");

      // ── Карточка канала ──────────────────────────────────────────────────
      const card = document.createElement("div");
      card.style.cssText = [
        "background:#181b22",
        "border:1px solid #23262d",
        "border-radius:8px",
        "padding:12px",
        "display:flex",
        "flex-direction:column",
        "gap:10px",
      ].join(";");
      container.appendChild(card);

      // ── Plotly div ───────────────────────────────────────────────────────
      const plotDiv = document.createElement("div");
      plotDiv.id = "chart-" + channelNum + "-" + figIdx;
      plotDiv.style.cssText = "width:100%; height:320px;";
      card.appendChild(plotDiv);

      // Трейс оригинала (синий)
      const origData = (fig.traces || []).find(function (t) {
        return !t.name || t.name === "Оригинал";
      }) || (fig.traces || [])[0] || { x: [], y: [] };

      const traces = [
        {
          x:    origData.x,
          y:    origData.y,
          name: "Оригинал",
          mode: "lines",
          type: "scatter",
          line: { width: 1.5, color: "#4f8cff" },
          hovertemplate: "%{y:.3f}" + (yLabel ? " " + yLabel : "") +
            "<br>%{x:.2f} мин<extra>Оригинал</extra>",
        },
        {
          x:    origData.x,
          y:    origData.y,
          name: "Исправление (заглушка)",
          mode: "lines",
          type: "scatter",
          line: { width: 1.5, color: "#06d6a0", dash: "dot" },
          hovertemplate: "%{y:.3f}" + (yLabel ? " " + yLabel : "") +
            "<br>%{x:.2f} мин<extra>Исправление</extra>",
        },
      ];

      window.Plotly.newPlot(plotDiv, traces, makeLayout(titleText, yLabel), PLOTLY_CONFIG);

      // ── Кнопка под графиком ─────────────────────────────────────────────
      const btnRow = document.createElement("div");
      btnRow.style.cssText = "display:flex; justify-content:flex-end;";
      card.appendChild(btnRow);

      const btn = document.createElement("button");
      btn.textContent = "Применить исправление";
      btn.style.cssText = [
        "padding:7px 18px",
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
        alert("Метод не реализован");
      });
      btnRow.appendChild(btn);
    });
  }

  window.OilCharts = { render: render };
})();