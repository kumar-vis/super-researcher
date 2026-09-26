import { EmbeddingView } from "embedding-atlas";

let currentView = null;
let currentResizeObserver = null;

export function mountEmbeddingAtlas(target, payload, handlers = {}) {
  destroyCurrent();
  const points = payload.points || [];
  const selections = payload.selections || {};
  const selectedChunkId = payload.selectedChunkId || null;
  const theme = payload.theme === "dark" ? "dark" : "light";

  const x = Float32Array.from(points.map((point) => Number(point.x) || 0));
  const y = Float32Array.from(points.map((point) => Number(point.y) || 0));
  const category = Uint8Array.from(points.map((point) => categoryForPoint(point, selections)));
  const identifiers = points.map((point) => point.id);
  const text = points.map((point) => point.text_preview || point.metadata?.title || point.id);
  const selectedIndex = selectedChunkId ? identifiers.indexOf(selectedChunkId) : -1;
  const categoryColors =
    theme === "dark"
      ? ["#8fa39a", "#34b8a7", "#ef7777", "#e2a84a", "#77a7e8", "#bd8be8"]
      : ["#5f6f68", "#0f766e", "#a23b3b", "#b7791f", "#315f9a", "#7a4f9a"];

  const props = {
    data: { x, y, category, identifier: identifiers, text },
    categoryColors,
    width: target.clientWidth || null,
    height: target.clientHeight || null,
    selection: selectedIndex >= 0 ? [dataPoint(selectedIndex, x, y, category, identifiers, text)] : null,
    config: {
      colorScheme: theme,
      mode: "points",
      pointSize: 3.5,
      autoLabelEnabled: false
    },
    querySelection: async (queryX, queryY, unitDistance) => {
      const threshold = Math.max(unitDistance * 14, 0.015);
      let bestIndex = -1;
      let bestDistance = threshold;
      for (let index = 0; index < points.length; index += 1) {
        const distance = Math.hypot(x[index] - queryX, y[index] - queryY);
        if (distance < bestDistance) {
          bestDistance = distance;
          bestIndex = index;
        }
      }
      return bestIndex >= 0 ? dataPoint(bestIndex, x, y, category, identifiers, text) : null;
    },
    onSelection: (selection) => {
      const point = selection?.[selection.length - 1];
      if (point?.identifier && handlers.onSelect) {
        handlers.onSelect(point.identifier);
      }
    }
  };

  target.innerHTML = "";
  currentView = new EmbeddingView(target, props);
  currentResizeObserver = new ResizeObserver(() => {
    if (!currentView) return;
    currentView.update({
      ...props,
      width: target.clientWidth || null,
      height: target.clientHeight || null
    });
  });
  currentResizeObserver.observe(target);

  return { destroy: destroyCurrent };
}

function destroyCurrent() {
  if (currentResizeObserver) currentResizeObserver.disconnect();
  if (currentView) currentView.destroy();
  currentResizeObserver = null;
  currentView = null;
}

function categoryForPoint(point, selections) {
  const status = selections[point.id]?.status || "none";
  if (status === "keep") return 1;
  if (status === "reject") return 2;
  if (status === "key_evidence") return 3;
  if (status === "maybe") return 4;
  if (point.metadata?.warning_flags?.length) return 5;
  return 0;
}

function dataPoint(index, x, y, category, identifiers, text) {
  return {
    x: x[index],
    y: y[index],
    category: category[index],
    identifier: identifiers[index],
    text: text[index]
  };
}

window.SuperResearcherEmbeddingAtlas = { mountEmbeddingAtlas };
