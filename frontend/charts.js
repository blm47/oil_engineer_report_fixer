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

  function makeLayout(titleText, yLabel) {
    const layout = JSON.parse(JSON.stringify(LAYOUT_BASE));
    layout.title = {
      text: titleText,
      font: { size: 13, color: "#e6e6e6" },
      x: 0.02,
      xanchor: "left",
    };
    layout.yaxis.title = {
      text: yLabel,
      font: { size: 11, color: "#9aa0a6" },
      standoff: 8,
    };
    return layout;
  }

  function makePlotlyConfig() {
    return {
      responsive: true,
      displayModeBar: true,
      modeBarButtonsToRemove: ["toImage", "sendDataToCloud"],
      displaylogo: false,
    };
  }

  function panelStyle(extra) {
    return [
      "background:#181b22",
      "border:1px solid #23262d",
      "border-radius:8px",
      "padding:8px",
      "min-height:340px",
      "display:flex",
      "flex-direction:column",
    ].concat(extra || []).join(";");
  }

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
      const channelNum = (fig.channel_num !== undefined && fig.channel_num !== 0)
        ? fig.channel_num
        : (figIdx + 1);
      const yLabel    = (fig.unit && fig.unit !== "nan") ? fig.unit
                      : (fig.y_label && fig.y_label !== "nan") ? fig.y_label
                      : "";
      const shortName = fig.title || `Канал ${channelNum}`;
      const titleText = `№${channelNum} — ${shortName}`;

      // ── Строка: левый + правый ──────────────────────────────────────────
      const row = document.createElement("div");
      row.style.cssText = "display:grid; grid-template-columns:1fr 1fr; gap:12px; align-items:stretch;";
      container.appendChild(row);

      // ── Левая панель: оригинал (синяя линия) ───────────────────────────
      const leftPanel = document.createElement("div");
      leftPanel.style.cssText = panelStyle();
      row.appendChild(leftPanel);

      const leftPlot = document.createElement("div");
      leftPlot.id = "chart-orig-" + channelNum;
      leftPlot.style.cssText = "flex:1; min-height:300px;";
      leftPanel.appendChild(leftPlot);

      const origTraces = (fig.traces || []).map(function (t) {
        return {
          x:    t.x,
          y:    t.y,
          name: t.name || "Оригинал",
          mode: "lines",
          type: "scatter",
          line: { width: 1.5, color: "#4f8cff" },
          hovertemplate: `%{y:.3f}${yLabel ? " " + yLabel : ""}<br>%{x:.2f} мин<extra>${t.name || "Оригинал"}</extra>`,
        };
      });

      window.Plotly.newPlot(leftPlot, origTraces, makeLayout(titleText, yLabel), makePlotlyConfig());

      // ── Правая панель: исправление (заглушка с графиком) ───────────────
      const rightPanel = document.createElement("div");
      rightPanel.style.cssText = panelStyle(["border-color:#1e3a2a"]);
      row.appendChild(rightPanel);

      // Верхняя часть: график-заглушка зелёной линией (копия оригинала)
      const rightPlot = document.createElement("div");
      rightPlot.id = "chart-fix-" + channelNum;
      rightPlot.style.cssText = "flex:1; min-height:220px;";
      rightPanel.appendChild(rightPlot);

      const fixTraces = (fig.traces || []).map(function (t) {
        return {
          x:    t.x,
          y:    t.y,
          name: "Предложение",
          mode: "lines",
          type: "scatter",
          line: { width: 1.5, color: "#06d6a0", dash: "dot" },
          hovertemplate: `%{y:.3f}${yLabel ? " " + yLabel : ""}<br>%{x:.2f} мин<extra>Предложение</extra>`,
        };
      });

      const fixTitleText = `№${channelNum} — ${shortName} (исправление)`;
      const fixLayout = makeLayout(fixTitleText, yLabel);
      // Затемняем заголовок чтобы визуально показать что это заглушка
      fixLayout.title.font.color = "#4a5568";
      fixLayout.paper_bgcolor = "#161a20";
      fixLayout.plot_bgcolor  = "#161a20";

      window.Plotly.newPlot(rightPlot, fixTraces, fixLayout, makePlotlyConfig());

      // Нижняя часть: текст + кнопка
      const infoBlock = document.createElement("div");
      infoBlock.style.cssText = [
        "padding:12px 8px 8px 8px",
        "display:flex",
        "flex-direction:column",
        "align-items:center",
        "gap:10px",
        "text-align:center",
      ].join(";");
      rightPanel.appendChild(infoBlock);

      const statusIcon = document.createElement("span");
      statusIcon.textContent = "✅";
      statusIcon.style.fontSize = "20px";
      infoBlock.appendChild(statusIcon);

      const msg = document.createElement("p");
      msg.style.cssText = "color:#9aa0a6; font-size:12px; line-height:1.6; margin:0; max-width:420px;";
      msg.textContent =
        `Данные канала «${shortName}» корректны. ` +
        "В случае провала проверки критерия тут будет предлагаемый вариант исправления.";
      infoBlock.appendChild(msg);

      const btn = document.createElement("button");
      btn.textContent = "Применить исправление";
      btn.style.cssText = [
        "padding:7px 18px",
        "background:#1e2a1e",
        "color:#4a5568",
        "border:1px solid #2a3a2a",
        "border-radius:6px",
        "cursor:pointer",
        "font-size:12px",
        "font-weight:500",
      ].join(";");
      btn.addEventListener("mouseenter", function () {
        btn.style.background = "#243024";
        btn.style.color = "#6b7280";
      });
      btn.addEventListener("mouseleave", function () {
        btn.style.background = "#1e2a1e";
        btn.style.color = "#4a5568";
      });
      btn.addEventListener("click", function () {
        alert("Метод не реализован");
      });
      infoBlock.appendChild(btn);
    });
  }

  window.OilCharts = { render: render };
})();