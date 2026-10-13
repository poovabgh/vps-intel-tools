#!/usr/bin/env python3
"""NodeSeek 官方 RSS → BJT 时段桶（关键词筛后只写 keep=Y）。

每 5 分钟跑一轮即可：拉 feed → seen 去重 → 复用 tg_index 词库分类 →
追加 queue/buckets/{YYYYMMDD}{HHMM}.csv → 全部 post_id 记入 seen。
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

# 复用电报索引的分类逻辑
_TG_INDEX = Path(__file__).resolve().parent.parent / "nodeseek_tg_index"
if str(_TG_INDEX) not in sys.path:
    sys.path.insert(0, str(_TG_INDEX))

from classify_index import (  # noqa: E402
    classify_row,
    collect_rules,
    load_keywords,
)

BJT = ZoneInfo("Asia/Shanghai")
RSS_URL = "https://rss.nodeseek.com/"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_KEYWORDS = _TG_INDEX / "keywords.yml"
DEFAULT_BUCKETS = REPO_ROOT / "queue" / "buckets"
DEFAULT_SEEN = REPO_ROOT / "state" / "seen_post_ids.txt"
SNIPPET_MAX = 240
SEEN_CAP = 5000
USER_AGENT = "vps-intel-tools-rss/1.0 (+https://github.com/poovabgh/vps-intel-tools)"

NS = {
    "dc": "http://purl.org/dc/elements/1.1/",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "atom": "http://www.w3.org/2005/Atom",
}

CSV_FIELDS = [
    "post_id",
    "url",
    "title",
    "pub_date_utc",
    "category",
    "creator",
    "snippet",
    "discovered_at_bjt",
    "matched_keywords",
    "server_score",
    "category_tags",
]


def bucket_name_for(now_bjt: datetime) -> str:
    """按发现时刻落 BJT 时段文件名（不含 .csv）。

    00–08 → YYYYMMDD0008
    08–12 → YYYYMMDD0812
    12–16 → YYYYMMDD1216
    16–20 → YYYYMMDD1620
    20–24 → YYYYMMDD2000  （20:00–次日00:00，日期=起点日）
    """
    d = now_bjt.strftime("%Y%m%d")
    h = now_bjt.hour
    if 0 <= h < 8:
        return f"{d}0008"
    if 8 <= h < 12:
        return f"{d}0812"
    if 12 <= h < 16:
        return f"{d}1216"
    if 16 <= h < 20:
        return f"{d}1620"
    return f"{d}2000"


def fetch_rss(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _text(el: ET.Element | None) -> str:
    if el is None:
        return ""
    if el.text:
        return el.text.strip()
    # CDATA / mixed
    parts = []
    if el.text:
        parts.append(el.text)
    for child in el:
        if child.tail:
            parts.append(child.tail)
    return "".join(parts).strip() or ("".join(el.itertext()).strip())


def _strip_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_items(xml_bytes: bytes) -> list[dict[str, str]]:
    root = ET.fromstring(xml_bytes)
    channel = root.find("channel")
    if channel is None:
        return []
    items: list[dict[str, str]] = []
    for item in channel.findall("item"):
        guid_el = item.find("guid")
        link_el = item.find("link")
        title_el = item.find("title")
        desc_el = item.find("description")
        cat_el = item.find("category")
        pub_el = item.find("pubDate")
        creator_el = item.find("dc:creator", NS)

        guid = _text(guid_el)
        link = _text(link_el)
        post_id = guid
        if not post_id and link:
            m = re.search(r"post-(\d+)", link)
            if m:
                post_id = m.group(1)
        if not post_id:
            continue

        snippet = _strip_html(_text(desc_el))
        if len(snippet) > SNIPPET_MAX:
            snippet = snippet[: SNIPPET_MAX - 1] + "…"

        items.append(
            {
                "post_id": post_id,
                "url": link or f"https://www.nodeseek.com/post-{post_id}-1",
                "title": _text(title_el),
                "pub_date_utc": _text(pub_el),
                "category": _text(cat_el),
                "creator": _text(creator_el),
                "snippet": snippet,
            }
        )
    return items


def load_seen(path: Path) -> set[str]:
    if not path.exists():
        return set()
    ids: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            ids.add(line)
    return ids


def save_seen(path: Path, feed_ids: list[str], cap: int = SEEN_CAP) -> None:
    """将本轮 feed 中的全部 post_id 记入 seen（含噪声）；保留末尾 cap 条。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: list[str] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                existing.append(line)
    seen_set = set(existing)
    for i in feed_ids:
        if i not in seen_set:
            existing.append(i)
            seen_set.add(i)
    if len(existing) > cap:
        existing = existing[-cap:]
    path.write_text("\n".join(existing) + ("\n" if existing else ""), encoding="utf-8")


def append_bucket(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        if write_header:
            w.writeheader()
        for r in rows:
            w.writerow(r)


def run(
    rss_url: str,
    keywords_path: Path,
    buckets_dir: Path,
    seen_path: Path,
    now: datetime | None = None,
) -> int:
    now_bjt = now.astimezone(BJT) if now else datetime.now(BJT)
    discovered_at = now_bjt.strftime("%Y-%m-%d %H:%M:%S%z")
    # normalize +0800 style
    if len(discovered_at) >= 5 and discovered_at[-5] in "+-" and discovered_at[-3] != ":":
        discovered_at = discovered_at[:-2] + ":" + discovered_at[-2:]

    bucket = bucket_name_for(now_bjt)
    bucket_path = buckets_dir / f"{bucket}.csv"

    kw = load_keywords(keywords_path)
    priority, regular, noise = collect_rules(kw)
    keep_threshold = int(kw.get("keep_threshold", 2))
    noise_override_min = int(kw.get("noise_override_min", 3))
    noise_override_need_server = int(kw.get("noise_override_need_server", 6))

    try:
        raw = fetch_rss(rss_url)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"fetched 0, new 0, kept 0, bucket {bucket_path} ERROR={e}", flush=True)
        return 1

    items = parse_items(raw)
    seen = load_seen(seen_path)
    fetched = len(items)

    new_items = [it for it in items if it["post_id"] not in seen]
    new_m = len(new_items)

    keep_rows: list[dict[str, Any]] = []
    for it in new_items:
        cls = classify_row(
            it["title"],
            it["snippet"],
            priority,
            regular,
            noise,
            keep_threshold,
            noise_override_min,
            noise_override_need_server,
        )
        if cls["keep_server_y_n"] != "Y":
            continue
        keep_rows.append(
            {
                "post_id": it["post_id"],
                "url": it["url"],
                "title": it["title"],
                "pub_date_utc": it["pub_date_utc"],
                "category": it["category"],
                "creator": it["creator"],
                "snippet": it["snippet"],
                "discovered_at_bjt": discovered_at,
                "matched_keywords": cls["matched_keywords"],
                "server_score": cls["server_score"],
                "category_tags": cls["category_tags"],
            }
        )

    if keep_rows:
        append_bucket(bucket_path, keep_rows)

    # 全部 feed 里出现的 id 都记 seen（含噪声），避免反复重评
    save_seen(seen_path, [it["post_id"] for it in items])

    print(
        f"fetched {fetched}, new {new_m}, kept {len(keep_rows)}, bucket {bucket_path}",
        flush=True,
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="NodeSeek RSS → BJT keep buckets")
    ap.add_argument("--rss-url", default=RSS_URL)
    ap.add_argument("--keywords", type=Path, default=DEFAULT_KEYWORDS)
    ap.add_argument("--buckets-dir", type=Path, default=DEFAULT_BUCKETS)
    ap.add_argument("--seen", type=Path, default=DEFAULT_SEEN)
    ap.add_argument(
        "--now",
        default="",
        help="测试用：ISO 时间（按 BJT 解释若无时区），否则用当前时间",
    )
    args = ap.parse_args()
    now = None
    if args.now:
        raw = args.now.replace("Z", "+00:00")
        now = datetime.fromisoformat(raw)
        if now.tzinfo is None:
            now = now.replace(tzinfo=BJT)
    return run(args.rss_url, args.keywords, args.buckets_dir, args.seen, now=now)


if __name__ == "__main__":
    raise SystemExit(main())
