(function () {
  "use strict";

  const LAYOUT_BASE = {
    paper_bgcolor: "#181b22",
    plot_bgcolor:  "#181b22",
    font:          { color: "#e6e6e6", size: 12 },
    margin:        { l: 55, r: 16, t: 44, b: 44 },
    xaxis: {
      title:      { text: "Время, мин", font: { size: 11 } },
      gridcolor:  "#2a2f3a",
      linecolor:  "#2a2f3a",
      tickcolor:  "#9aa0a6",
    },
    yaxis: {
      gridcolor:  "#2a2f3a",
      linecolor:  "#2a2f3a",
      tickcolor:  "#9aa0a6",
    },
    legend: { orientation: "h", y: -0.18 },
  };

  const COLORS = ["#4f8cff", "#ff6b6b", "#ffd166", "#06d6a0"];

  function render(container, figures) {
    if (!container) return;
    container.innerHTML = "";

    if (!Array.isArray(figures) || figures.length === 0) {
      container.innerHTML =
        '<p style="color:#9aa0a6;font-size:13px;">Графиков нет — загрузите файл.</p>';
      return;
    }

    // Сетка 2 колонки
    container.style.display = "grid";
    container.style.gridTemplateColumns = "1fr 1fr";
    container.style.gap = "16px";

    figures.forEach(function (fig, figIdx) {
      const wrap = document.createElement("div");
      wrap.style.background    = "#181b22";
      wrap.style.borderRadius  = "8px";
      wrap.style.border        = "1px solid #23262d";
      wrap.style.padding       = "8px";
      wrap.style.minHeight     = "320px";
      container.appendChild(wrap);

      const plotDiv = document.createElement("div");
      plotDiv.id = "chart-" + (fig.id || figIdx);
      wrap.appendChild(plotDiv);

      const traces = (fig.traces || []).map(function (t, tIdx) {
        return {
          x:    t.x,
          y:    t.y,
          name: t.name || "Оригинал",
          mode: "lines",
          type: "scatter",
          line: { width: 1.5, color: COLORS[tIdx % COLORS.length] },
        };
      });

      const layout = Object.assign({}, LAYOUT_BASE, {
        title: { text: fig.title || "", font: { size: 13 }, x: 0.02 },
        yaxis: Object.assign({}, LAYOUT_BASE.yaxis, {
          title: { text: fig.y_label || "", font: { size: 11 } },
        }),
      });

      window.Plotly.newPlot(plotDiv, traces, layout, { responsive: true });
    });
  }

  window.OilCharts = { render: render };
})();