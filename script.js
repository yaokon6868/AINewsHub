const state = {
  items: [],
  activeSource: "all",
  query: "",
};

const listEl = document.getElementById("news-list");
const emptyEl = document.getElementById("empty-state");
const updatedEl = document.getElementById("updated-at");
const searchEl = document.getElementById("search");
const filtersEl = document.getElementById("source-filters");

function formatTime(iso) {
  try {
    const d = new Date(iso);
    return d.toLocaleString("zh-CN", { hour12: false });
  } catch {
    return iso;
  }
}

function render() {
  const q = state.query.trim().toLowerCase();
  const filtered = state.items.filter((it) => {
    const matchSource = state.activeSource === "all" || it.source === state.activeSource;
    const matchQuery = !q || it.title.toLowerCase().includes(q);
    return matchSource && matchQuery;
  });

  listEl.innerHTML = "";
  emptyEl.hidden = filtered.length > 0;

  for (const it of filtered) {
    const card = document.createElement("div");
    card.className = "news-card";
    card.innerHTML = `
      <a href="${it.link}" target="_blank" rel="noopener noreferrer">${it.title}</a>
      <div class="news-meta">
        <span>${it.source}</span>
        <span>${formatTime(it.published)}</span>
        ${it.translated ? '<span title="机器翻译">机翻</span>' : ""}
      </div>
      ${it.summary ? `<div class="news-summary">${it.summary}</div>` : ""}
    `;
    listEl.appendChild(card);
  }
}

function renderFilters() {
  const sources = ["all", ...new Set(state.items.map((it) => it.source))];
  filtersEl.innerHTML = "";
  for (const src of sources) {
    const chip = document.createElement("span");
    chip.className = "source-chip" + (state.activeSource === src ? " active" : "");
    chip.textContent = src === "all" ? "全部" : src;
    chip.addEventListener("click", () => {
      state.activeSource = src;
      renderFilters();
      render();
    });
    filtersEl.appendChild(chip);
  }
}

async function load() {
  try {
    const res = await fetch("data/news.json", { cache: "no-store" });
    const data = await res.json();
    state.items = data.items || [];
    updatedEl.textContent = "最后更新：" + formatTime(data.updated_at);
    renderFilters();
    render();
  } catch (e) {
    updatedEl.textContent = "加载失败，请稍后刷新";
    console.error(e);
  }
}

searchEl.addEventListener("input", (e) => {
  state.query = e.target.value;
  render();
});

load();
