(function () {
  "use strict";

  const LAYOUT_BASE = {
    paper_bgcolor: "#181b22",
    plot_bgcolor:  "#181b22",
    font:          { color: "#e6e6e6", size: 12 },
    margin:        { l: 65, r: 20, t: 44, b: 56 },
    xaxis: {
      title:     { text: "Время, мин", font: { size: 11, color: "#9aa0a6" }, standoff: 8 },
      gridcolor: "#2a2f3a", linecolor: "#3a3f4a", tickcolor: "#9aa0a6",
      tickfont:  { size: 10 }, zeroline: false,
    },
    yaxis: {
      gridcolor: "#2a2f3a", linecolor: "#3a3f4a", tickcolor: "#9aa0a6",
      tickfont:  { size: 10 }, zeroline: false,
    },
    legend: { orientation: "h", y: -0.22, x: 0, font: { size: 11 }, bgcolor: "rgba(0,0,0,0)" },
    hovermode: "x unified",
  };

  const LINE_COLOR = "#4f8cff";

  function render(container, figures) {
    if (!container) return;
    container.innerHTML = "";

    if (!Array.isArray(figures) || figures.length === 0) {
      container.innerHTML =
        '<p style="color:#9aa0a6;font-size:13px;padding:12px;">Графиков нет — загрузите файл.</p>';
      return;
    }

    // Сбрасываем стиль контейнера — строки идут в column
    container.style.cssText = "display:flex; flex-direction:column; gap:16px;";

    figures.forEach(function (fig) {
      const channelNum = fig.channel_num !== undefined ? fig.channel_num : "";
      const yLabel     = fig.unit || fig.y_label || "";
      const titleText  = channelNum ? `№${channelNum} — ${fig.title}` : (fig.title || "");

      // Строка канала: левая + правая
      const row = document.createElement("div");
      row.style.cssText = "display:grid; grid-template-columns:1fr 1fr; gap:12px; align-items:stretch;";
      container.appendChild(row);

      // ── Левая панель: оригинальный график ─────────────────────────────
      const leftPanel = document.createElement("div");
      leftPanel.style.cssText = [
        "background:#181b22",
        "border:1px solid #23262d",
        "border-radius:8px",
        "padding:8px",
        "min-height:320px",
        "display:flex",
        "flex-direction:column",
      ].join(";");
      row.appendChild(leftPanel);

      const plotDiv = document.createElement("div");
      plotDiv.id = "chart-" + (fig.id || channelNum);
      plotDiv.style.cssText = "flex:1; min-height:300px;";
      leftPanel.appendChild(plotDiv);

      const traces = (fig.traces || []).map(function (t) {
        return {
          x:    t.x,
          y:    t.y,
          name: t.name || "Оригинал",
          mode: "lines",
          type: "scatter",
          line: { width: 1.5, color: LINE_COLOR },
          hovertemplate: `%{y:.3f} ${yLabel}<br>%{x:.2f} мин<extra>${t.name || "Оригинал"}</extra>`,
        };
      });

      const layout = JSON.parse(JSON.stringify(LAYOUT_BASE));
      layout.title = {
        text: titleText,
        font: { size: 13, color: "#e6e6e6" },
        x: 0.02, xanchor: "left",
      };
      layout.yaxis.title = { text: yLabel, font: { size: 11, color: "#9aa0a6" }, standoff: 8 };

      window.Plotly.newPlot(plotDiv, traces, layout, {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ["toImage", "sendDataToCloud"],
        displaylogo: false,
      });

      // ── Правая панель: заглушка коррекции ─────────────────────────────
      const rightPanel = document.createElement("div");
      rightPanel.style.cssText = [
        "background:#181b22",
        "border:1px solid #23262d",
        "border-radius:8px",
        "padding:20px 16px",
        "min-height:320px",
        "display:flex",
        "flex-direction:column",
        "justify-content:center",
        "align-items:center",
        "gap:16px",
        "text-align:center",
      ].join(";");
      row.appendChild(rightPanel);

      const icon = document.createElement("div");
      icon.textContent = "✅";
      icon.style.fontSize = "36px";
      rightPanel.appendChild(icon);

      const msg = document.createElement("p");
      msg.style.cssText = "color:#9aa0a6; font-size:13px; line-height:1.6; margin:0;";
      msg.textContent =
        `Данные канала «${fig.title}» корректны.\n` +
        "В случае провала проверки критерия здесь будет предлагаемый вариант исправления.";
      msg.style.whiteSpace = "pre-line";
      rightPanel.appendChild(msg);

      const btn = document.createElement("button");
      btn.textContent  = "Применить исправление";
      btn.style.cssText = [
        "margin-top:8px",
        "padding:8px 20px",
        "background:#2a2f3a",
        "color:#9aa0a6",
        "border:1px solid #3a3f4a",
        "border-radius:6px",
        "cursor:pointer",
        "font-size:13px",
        "font-weight:500",
        "transition:background 0.15s",
      ].join(";");
      btn.addEventListener("mouseenter", function () {
        btn.style.background = "#333a47";
      });
      btn.addEventListener("mouseleave", function () {
        btn.style.background = "#2a2f3a";
      });
      btn.addEventListener("click", function () {
        alert("Метод не реализован");
      });
      rightPanel.appendChild(btn);
    });
  }

  window.OilCharts = { render: render };
})();