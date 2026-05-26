(function () {
  "use strict";

  // Заглушка для отрисовки графиков через Plotly.
  //
  // В будущем здесь будут две дорожки на каждый канал:
  //   - оригинальный сигнал из Excel-отчёта,
  //   - предложенная корректировка (preview, без автоприменения).
  // Инженер должен сам подтвердить или отклонить правки.

  function render(container, figures) {
    if (!container) return;
    container.innerHTML = "";

    if (!Array.isArray(figures) || figures.length === 0) {
      const placeholder = document.createElement("div");
      placeholder.className = "muted";
      placeholder.textContent = "Графиков пока нет (backend возвращает пустой ответ).";
      container.appendChild(placeholder);
      return;
    }

    figures.forEach(function (fig) {
      const div = document.createElement("div");
      div.id = "chart-" + fig.id;
      div.style.minHeight = "320px";
      div.style.marginBottom = "16px";
      container.appendChild(div);

      const traces = (fig.traces || []).map(function (t) {
        return { x: t.x, y: t.y, name: t.name, mode: "lines", type: "scatter" };
      });

      window.Plotly.newPlot(
        div,
        traces,
        { title: fig.title || "", paper_bgcolor: "#181b22", plot_bgcolor: "#181b22", font: { color: "#e6e6e6" } },
        { responsive: true }
      );
    });
  }

  window.OilCharts = { render: render };
})();
