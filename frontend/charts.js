(function () {
  "use strict";

  const LAYOUT_BASE = {
    paper_bgcolor: "#181b22",
    plot_bgcolor:  "#181b22",
    font:          { color: "#e6e6e6", size: 12 },
    margin:        { l: 65, r: 20, t: 48, b: 60 },
    xaxis: {
      title:      { text: "Время, мин", font: { size: 11, color: "#9aa0a6" }, standoff: 8 },
      gridcolor:  "#2a2f3a",
      linecolor:  "#3a3f4a",
      tickcolor:  "#9aa0a6",
      tickfont:   { size: 10 },
      zeroline:   false,
    },
    yaxis: {
      gridcolor:  "#2a2f3a",
      linecolor:  "#3a3f4a",
      tickcolor:  "#9aa0a6",
      tickfont:   { size: 10 },
      zeroline:   false,
    },
    legend: {
      orientation: "h",
      y: -0.22,
      x: 0,
      font: { size: 11 },
      bgcolor: "rgba(0,0,0,0)",
    },
    hovermode: "x unified",
  };

  const COLORS = ["#4f8cff", "#ff6b6b", "#ffd166", "#06d6a0"];

  function render(container, figures) {
    if (!container) return;
    container.innerHTML = "";

    if (!Array.isArray(figures) || figures.length === 0) {
      container.innerHTML =
        '<p style="color:#9aa0a6;font-size:13px;padding:12px;">Графиков нет — загрузите файл.</p>';
      return;
    }

    container.style.display = "grid";
    container.style.gridTemplateColumns = figures.length === 1 ? "1fr" : "1fr 1fr";
    container.style.gap = "16px";

    figures.forEach(function (fig, figIdx) {
      const wrap = document.createElement("div");
      wrap.style.cssText = [
        "background:#181b22",
        "border-radius:8px",
        "border:1px solid #23262d",
        "padding:8px",
        "min-height:340px",
      ].join(";");
      container.appendChild(wrap);

      const plotDiv = document.createElement("div");
      plotDiv.id = "chart-" + (fig.id || figIdx);
      plotDiv.style.height = "340px";
      wrap.appendChild(plotDiv);

      const yLabel = fig.y_label || "";

      const traces = (fig.traces || []).map(function (t, tIdx) {
        return {
          x:    t.x,
          y:    t.y,
          name: t.name || "Оригинал",
          mode: "lines",
          type: "scatter",
          line: { width: 1.5, color: COLORS[tIdx % COLORS.length] },
          hovertemplate: `%{y:.3f} ${yLabel}<br>%{x:.2f} мин<extra>${t.name || "Оригинал"}</extra>`,
        };
      });

      // Глубокая копия layout с подписью оси Y для каждого графика
      const layout = JSON.parse(JSON.stringify(LAYOUT_BASE));
      layout.title = { text: fig.title || "", font: { size: 13, color: "#e6e6e6" }, x: 0.02, xanchor: "left" };
      layout.yaxis.title = { text: yLabel, font: { size: 11, color: "#9aa0a6" }, standoff: 8 };

      window.Plotly.newPlot(plotDiv, traces, layout, {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ["toImage", "sendDataToCloud"],
        displaylogo: false,
      });
    });
  }

  window.OilCharts = { render: render };
})();