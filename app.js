const state = {
  items: [],
  activeCategory: "all",
  activeSource: "all",
  query: "",
};

const CATEGORY_LABELS = {
  all: "全部",
  anthropic: "Claude",
  openai: "OpenAI",
  google: "Gemini",
  other_big: "其他大厂",
  breakthrough: "重大进展",
  tools_apps: "工具应用",
  image_video: "图像视频",
  local_model: "本地模型",
  open_source: "开源社区",
  chips: "芯片算力",
  other: "其他",
};
const CATEGORY_ORDER = [
  "all", "anthropic", "openai", "google", "other_big", "breakthrough",
  "tools_apps", "image_video", "local_model", "open_source", "chips", "other",
];

const listEl = document.getElementById("news-list");
const emptyEl = document.getElementById("empty-state");
const updatedEl = document.getElementById("updated-at");
const debugEl = document.getElementById("debug-line");
const searchEl = document.getElementById("search");
const categoryFiltersEl = document.getElementById("categoryFilters");
const sourceFiltersEl = document.getElementById("sourceFilters");

function formatTime(iso) {
  try {
    const d = new Date(iso);
    return d.toLocaleString("zh-CN", { hour12: false });
  } catch {
    return iso;
  }
}

function itemCategories(it) {
  if (it.categories && it.categories.length) return it.categories;
  if (it.category) return [it.category];
  return ["other"];
}

function render() {
  const q = state.query.trim().toLowerCase();
  const filtered = state.items.filter((it) => {
    const categories = itemCategories(it);
    const matchCategory = state.activeCategory === "all" || categories.includes(state.activeCategory);
    const matchSource = state.activeSource === "all" || it.source === state.activeSource;
    const matchQuery = !q || it.title.toLowerCase().includes(q);
    return matchCategory && matchSource && matchQuery;
  });

  listEl.innerHTML = "";
  emptyEl.hidden = filtered.length > 0;

  for (const it of filtered) {
    const categories = itemCategories(it);
    const badges = categories
      .map((c) => `<span class="category-badge${c === "breakthrough" ? " category-badge-hot" : ""}">${CATEGORY_LABELS[c] || c}</span>`)
      .join("");
    const card = document.createElement("div");
    card.className = "news-card";
    card.innerHTML = `
      <a href="${it.link}" target="_blank" rel="noopener noreferrer">${it.title}</a>
      <div class="category-badges">${badges}</div>
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

function renderCategoryFilters() {
  categoryFiltersEl.innerHTML = "";
  for (const key of CATEGORY_ORDER) {
    const chip = document.createElement("span");
    chip.className = "filter-chip" + (state.activeCategory === key ? " active" : "");
    chip.textContent = CATEGORY_LABELS[key];
    chip.addEventListener("click", () => {
      state.activeCategory = key;
      renderCategoryFilters();
      render();
    });
    categoryFiltersEl.appendChild(chip);
  }
  return CATEGORY_ORDER.length;
}

function renderSourceFilters() {
  const sources = ["all", ...new Set(state.items.map((it) => it.source))];
  sourceFiltersEl.innerHTML = "";
  for (const src of sources) {
    const chip = document.createElement("span");
    chip.className = "filter-chip" + (state.activeSource === src ? " active" : "");
    chip.textContent = src === "all" ? "全部" : src;
    chip.addEventListener("click", () => {
      state.activeSource = src;
      renderSourceFilters();
      render();
    });
    sourceFiltersEl.appendChild(chip);
  }
  return sources.length;
}

async function load() {
  try {
    const res = await fetch(`data/news.json?v=${Date.now()}`, { cache: "no-store" });
    const data = await res.json();
    state.items = data.items || [];
    updatedEl.textContent = "最后更新：" + formatTime(data.updated_at);
    const categoryCount = renderCategoryFilters();
    const sourceCount = renderSourceFilters();
    debugEl.textContent = `分类数量：${categoryCount} ・ 来源数量：${sourceCount}`;
    render();
  } catch (e) {
    updatedEl.textContent = "加载失败，请稍后刷新";
    debugEl.textContent = "分类数量：加载出错 ・ 来源数量：加载出错";
    console.error(e);
  }
}

searchEl.addEventListener("input", (e) => {
  state.query = e.target.value;
  render();
});

load();
