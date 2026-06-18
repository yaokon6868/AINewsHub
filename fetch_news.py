import difflib
import html
import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "data", "news.json")
CURATED_COUNT = 36

SOURCE_WEIGHT = {
    "Hacker News - AI": 6,
    "TechCrunch AI": 6,
    "VentureBeat AI": 6,
    "Google News - AI Tools": 3,
    "Google News - AI(中文)": 2,
}

KEYWORDS = [
    "openai", "chatgpt", "gpt-5", "gpt5", "claude", "anthropic", "gemini",
    "google deepmind", "deepmind", "mistral", "llama", "copilot", "sora",
    "midjourney", "stable diffusion", "agent", "智能体", "大模型", "开源模型",
    "发布", "融资", "估值", "ai agent", "llm", "多模态",
]

NEGATIVE_KEYWORDS = [
    "股票", "基金", "etf", "涨幅", "涨停", "跌停", "大宗", "邮票", "龙虎榜",
    "校招", "招聘", "毕业", "stock price", "shares", "dividend", "nasdaq",
]

COMPANY_KEYWORDS = {
    "anthropic": ["claude", "anthropic"],
    "openai": [
        "openai", "chatgpt", "gpt-5", "gpt5", "gpt-4", "gpt4", "sora",
        "dall-e", "dalle", "altman", "奥特曼",
    ],
    "google": ["gemini", "deepmind", "谷歌", "google"],
}

OTHER_BIG_KEYWORDS = [
    "meta", "llama", "microsoft", "copilot", "微软", "grok", "xai", "马斯克",
    "mistral", "deepseek", "阿里", "百度", "腾讯", "字节跳动", "字节", "智谱",
    "月之暗面", "kimi", "文心一言", "通义千问", "qwen", "baidu", "tencent",
    "bytedance", "nvidia", "英伟达", "amazon", "亚马逊", "华为", "huawei",
    "小米", "xiaomi", "三星", "samsung", "cohere", "perplexity", "runway",
    "suno", "midjourney", "stability", "stable diffusion", "minimax",
    "零一万物", "苹果", "apple",
]

BREAKTHROUGH_KEYWORDS = [
    "突破", "重磅", "里程碑", "震惊", "全球首", "首个", "新纪录", "超越",
    "登顶", "breakthrough", "milestone", "unveils", "unveiled", "announces",
    "announced", "funding round", "valuation", "估值", "融资", "ipo",
    "收购", "acquisition", "acquire", "发布会", "重大",
]

TOPIC_KEYWORDS = {
    "tools_apps": [
        "插件", "app", "应用", "工具", "上架", "extension", "浏览器扩展",
        "生产力工具", "效率工具", "agent", "智能体", "助手",
    ],
    "image_video": [
        "图像", "视频", "文生图", "文生视频", "sora", "midjourney",
        "stable diffusion", "runway", "suno", "图片生成", "视频生成",
        "image generation", "video generation", "text-to-image",
        "text-to-video", "绘画", "ai绘画", "ai视频", "数字人",
    ],
    "local_model": [
        "本地模型", "local model", "开源权重", "ollama", "llama.cpp",
        "量化", "gguf", "本地部署", "端侧", "on-device", "离线运行",
        "手机端", "端侧模型",
    ],
    "open_source": [
        "开源", "huggingface", "hugging face", "开放权重", "open source",
        "开源模型", "开源项目", "开放源代码", "github",
    ],
    "chips": [
        "芯片", "gpu", "算力", "tpu", "显卡", "半导体", "chip", "compute",
        "h100", "h200", "blackwell", "昇腾", "寒武纪", "晶圆", "光刻",
    ],
}


def classify(title, summary):
    text = f"{title} {summary}".lower()
    categories = []

    company = None
    for key, kws in COMPANY_KEYWORDS.items():
        if any(kw in text for kw in kws):
            company = key
            break
    if company:
        categories.append(company)
    elif any(kw.lower() in text for kw in OTHER_BIG_KEYWORDS):
        categories.append("other_big")

    if any(kw.lower() in text for kw in BREAKTHROUGH_KEYWORDS):
        categories.append("breakthrough")

    for topic, kws in TOPIC_KEYWORDS.items():
        if any(kw.lower() in text for kw in kws):
            categories.append(topic)

    if not categories:
        categories.append("other")
    return categories


def google_news_url(query, lang, country):
    params = {"q": query, "hl": lang, "gl": country, "ceid": f"{country}:{lang.split('-')[0]}"}
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode(params)


CN_NEG = "-股票 -基金 -ETF -涨幅 -邮票 -校招 -毕业 -招聘"

FEEDS = [
    {"name": "Google News - AI(中文)", "type": "rss",
     "url": google_news_url(f"人工智能 {CN_NEG}", "zh-CN", "CN")},
    {"name": "Google News - AI(中文)", "type": "rss",
     "url": google_news_url(f"大模型 OR ChatGPT OR Claude OR Gemini OR DeepSeek OR 智能体 OR AI芯片 OR 人工智能工具 {CN_NEG}", "zh-CN", "CN")},
    {"name": "Google News - AI Tools", "type": "rss",
     "url": google_news_url("AI tools", "en-US", "US")},
    {"name": "TechCrunch AI", "type": "rss",
     "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    {"name": "VentureBeat AI", "type": "rss",
     "url": "https://venturebeat.com/category/ai/feed/"},
    {"name": "Hacker News - AI", "type": "hn_algolia",
     "url": None},
]


HN_MIN_POINTS = 15


def hn_algolia_url():
    since_ts = int((datetime.now(timezone.utc).timestamp())) - 5 * 24 * 3600
    params = {
        "tags": "story",
        "query": "AI",
        "numericFilters": f"created_at_i>{since_ts}",
        "hitsPerPage": "50",
    }
    return "https://hn.algolia.com/api/v1/search?" + urllib.parse.urlencode(params)


def clean_text(text):
    text = re.sub(r"<[^>]+>", "", text or "")
    return html.unescape(text).strip()


def parse_date(s):
    try:
        return parsedate_to_datetime(s)
    except Exception:
        return None


def fetch_rss(feed):
    req = urllib.request.Request(feed["url"], headers=HEADERS)
    items = []
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read()
    root = ET.fromstring(data)
    for item in root.iter("item"):
        title = clean_text(item.findtext("title") or "")
        link = (item.findtext("link") or "").strip()
        pub = item.findtext("pubDate") or ""
        desc = clean_text(item.findtext("description") or "")[:200]
        dt = parse_date(pub)
        items.append({
            "title": title,
            "link": link,
            "source": feed["name"],
            "published": dt.isoformat() if dt else pub,
            "summary": desc,
        })
    return items


def fetch_hn_algolia(feed):
    req = urllib.request.Request(hn_algolia_url(), headers=HEADERS)
    items = []
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    for hit in data.get("hits", []):
        title = clean_text(hit.get("title") or "")
        if not title:
            continue
        if (hit.get("points") or 0) < HN_MIN_POINTS:
            continue
        object_id = hit.get("objectID")
        link = hit.get("url") or f"https://news.ycombinator.com/item?id={object_id}"
        created_at = hit.get("created_at")
        try:
            dt = datetime.fromisoformat(created_at)
        except Exception:
            dt = None
        points = hit.get("points") or 0
        comments = hit.get("num_comments") or 0
        items.append({
            "title": title,
            "link": link,
            "source": feed["name"],
            "published": dt.isoformat() if dt else created_at,
            "summary": f"{points} 赞 · {comments} 条评论 · Hacker News",
            "points": points,
        })
    return items


def fetch_feed(feed):
    try:
        if feed["type"] == "hn_algolia":
            items = fetch_hn_algolia(feed)
        else:
            items = fetch_rss(feed)
        print(f"[OK] {feed['name']}: {len(items)} items")
        return items
    except Exception as e:
        print(f"[WARN] {feed['name']} failed: {e}")
        return []


def parsed_date(it):
    try:
        return datetime.fromisoformat(it["published"])
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


def score_item(it, now):
    title_lower = it["title"].lower()
    score = SOURCE_WEIGHT.get(it["source"], 1)
    score += 2 * sum(1 for kw in KEYWORDS if kw in title_lower)
    score += min(5, (it.get("points") or 0) / 10)
    hours_old = max(0, (now - parsed_date(it)).total_seconds() / 3600)
    score += max(0, 48 - hours_old) * 0.1
    return score


def is_near_duplicate(title, kept_titles):
    norm = re.sub(r"[^\w一-鿿]", "", title.lower())
    for kept in kept_titles:
        if difflib.SequenceMatcher(None, norm, kept).ratio() > 0.6:
            return True
    return False


def is_chinese(title):
    return bool(re.search(r"[一-鿿]", title))


def translate_to_zh(text):
    if not text or is_chinese(text):
        return text
    params = {"client": "gtx", "sl": "auto", "tl": "zh-CN", "dt": "t", "q": text}
    url = "https://translate.googleapis.com/translate_a/single?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return "".join(seg[0] for seg in data[0] if seg[0])
    except Exception as e:
        print(f"[WARN] translate failed for '{text[:30]}...': {e}")
        return text


def fill_from(pool, curated, kept_titles, limit):
    for it in pool:
        if len(curated) >= limit:
            break
        if is_near_duplicate(it["title"], kept_titles):
            continue
        curated.append(it)
        kept_titles.append(re.sub(r"[^\w一-鿿]", "", it["title"].lower()))


def curate(items):
    now = datetime.now(timezone.utc)
    filtered = []
    for it in items:
        title_lower = it["title"].lower()
        if any(neg in title_lower for neg in NEGATIVE_KEYWORDS):
            continue
        filtered.append(it)

    filtered.sort(key=lambda it: score_item(it, now), reverse=True)
    zh_items = [it for it in filtered if is_chinese(it["title"])]
    other_items = [it for it in filtered if not is_chinese(it["title"])]

    curated = []
    kept_titles = []
    fill_from(zh_items, curated, kept_titles, CURATED_COUNT)
    fill_from(other_items, curated, kept_titles, CURATED_COUNT)

    for it in curated:
        if not is_chinese(it["title"]):
            it["title"] = translate_to_zh(it["title"])
            it["summary"] = translate_to_zh(it.get("summary", ""))
            it["translated"] = True

    for it in curated:
        it["categories"] = classify(it["title"], it.get("summary", ""))

    curated.sort(key=parsed_date, reverse=True)
    return curated


def main():
    all_items = []
    seen_links = set()
    for feed in FEEDS:
        for item in fetch_feed(feed):
            if item["link"] and item["link"] not in seen_links:
                seen_links.add(item["link"])
                all_items.append(item)

    all_items = curate(all_items)

    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "items": all_items,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(all_items)} items to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
