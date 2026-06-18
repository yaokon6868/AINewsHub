const state = {
  items: [],
  activeCategory: "all",
  query: "",
};

const CATEGORY_LABELS = {
  all: "全部",
  anthropic: "Claude",
  openai: "OpenAI",
  google: "Gemini",
  other_big: "其他大厂",
  breakthrough: "重大进展",
  other: "其他",
};
const CATEGORY_ORDER = ["all", "anthropic", "openai", "google", "other_big", "breakthrough", "other"];

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
    const categories = it.categories && it.categories.length ? it.categories : ["other"];
    const matchCategory = state.activeCategory === "all" || categories.includes(state.activeCategory);
    const matchQuery = !q || it.title.toLowerCase().includes(q);
    return matchCategory && matchQuery;
  });

  listEl.innerHTML = "";
  emptyEl.hidden = filtered.length > 0;

  for (const it of filtered) {
    const categories = it.categories && it.categories.length ? it.categories : ["other"];
    const tags = categories
      .filter((c) => c !== "other")
      .map((c) => `<span class="news-tag${c === "breakthrough" ? " news-tag-hot" : ""}">${CATEGORY_LABELS[c] || c}</span>`)
      .join("");
    const card = document.createElement("div");
    card.className = "news-card";
    card.innerHTML = `
      <a href="${it.link}" target="_blank" rel="noopener noreferrer">${it.title}</a>
      <div class="news-meta">
        <span>${it.source}</span>
        <span>${formatTime(it.published)}</span>
        ${it.translated ? '<span title="机器翻译">机翻</span>' : ""}
        ${tags}
      </div>
      ${it.summary ? `<div class="news-summary">${it.summary}</div>` : ""}
    `;
    listEl.appendChild(card);
  }
}

function renderFilters() {
  const present = new Set();
  for (const it of state.items) {
    const categories = it.categories && it.categories.length ? it.categories : ["other"];
    for (const c of categories) present.add(c);
  }
  filtersEl.innerHTML = "";
  for (const key of CATEGORY_ORDER) {
    if (key !== "all" && !present.has(key)) continue;
    const chip = document.createElement("span");
    chip.className = "source-chip" + (state.activeCategory === key ? " active" : "");
    chip.textContent = CATEGORY_LABELS[key];
    chip.addEventListener("click", () => {
      state.activeCategory = key;
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
