const chartData = window.MEDEXTRACT_CHARTS || {};

const palette = {
  blue: "#15345a",
  gold: "#c7903f",
  green: "#2f855a",
  red: "#b42318",
  slate: "#536174",
  sand: "#e7d6bb"
};

function chartDefaults() {
  Chart.defaults.font.family = "Inter, system-ui, sans-serif";
  Chart.defaults.color = "#536174";
  Chart.defaults.plugins.legend.labels.boxWidth = 12;
}

function shortLabel(value) {
  const label = String(value || "");
  return label.length > 30 ? `${label.slice(0, 30)}...` : label;
}

function buildBar(id, labels, values, color, horizontal = false) {
  const element = document.getElementById(id);
  if (!element) return;
  new Chart(element, {
    type: "bar",
    data: {
      labels: labels && labels.length ? labels : ["Sem dados"],
      datasets: [{
        data: values && values.length ? values : [0],
        backgroundColor: color,
        borderRadius: 6
      }]
    },
    options: {
      indexAxis: horizontal ? "y" : "x",
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: {
          beginAtZero: horizontal,
          grid: { display: !horizontal },
          ticks: {
            precision: 0,
            callback: horizontal ? undefined : function(value) {
              return shortLabel(this.getLabelForValue(value));
            }
          }
        },
        y: {
          beginAtZero: !horizontal,
          grid: { display: false },
          ticks: {
            precision: 0,
            autoSkip: false,
            callback: horizontal ? function(value) {
              return shortLabel(this.getLabelForValue(value));
            } : undefined
          }
        }
      }
    }
  });
}

function buildDoughnut(id, labels, values) {
  const element = document.getElementById(id);
  if (!element) return;
  new Chart(element, {
    type: "doughnut",
    data: {
      labels: labels && labels.length ? labels : ["Sem dados"],
      datasets: [{
        data: values && values.length ? values : [1],
        backgroundColor: [palette.green, palette.gold, palette.red, palette.blue]
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: "bottom" } },
      cutout: "64%"
    }
  });
}

chartDefaults();
buildBar(
  "documentsByMonth",
  chartData.documents_by_month?.labels,
  chartData.documents_by_month?.values,
  palette.blue
);
buildDoughnut("statusChart", chartData.status?.labels, chartData.status?.values);
buildBar(
  "hospitalChart",
  chartData.documents_by_hospital?.labels,
  chartData.documents_by_hospital?.values,
  palette.gold,
  true
);
buildBar(
  "diagnosisChart",
  chartData.top_diagnoses?.labels,
  chartData.top_diagnoses?.values,
  palette.slate,
  true
);
buildBar(
  "medicationChart",
  chartData.top_medications?.labels,
  chartData.top_medications?.values,
  palette.green,
  true
);
