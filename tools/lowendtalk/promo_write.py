"""把优惠轨条目写入 vps-intel/promos/lowendtalk/。"""
from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _slug(s: str, n: int = 60) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff\-]+", "-", s, flags=re.U).strip("-").lower()
    return (s or "item")[:n]


def guess_price_window(title: str, op: str = "") -> str:
    blob = f"{title}\n{op[:500]}"
    m = re.search(
        r"(\$\s?\d+(?:\.\d+)?\s*/\s*(?:mo|month|year|yr|yr\.?)|€\s?\d+(?:\.\d+)?\s*/\s*(?:mo|month|year)|£\s?\d+)",
        blob,
        re.I,
    )
    if m:
        return m.group(1).replace(" ", "")
    m2 = re.search(r"(from\s+\$?\d+(?:\.\d+)?|starting\s+at\s+[\$€£]?\d+)", blob, re.I)
    return m2.group(1) if m2 else ""


def guess_location(title: str, op: str = "") -> str:
    blob = f"{title} {op[:800]}"
    places = [
        "Frankfurt", "Amsterdam", "London", "Dallas", "Los Angeles", "LA", "NY", "New York",
        "Singapore", "Hong Kong", "HK", "Tokyo", "Seoul", "Paris", "Nuremberg", "Atlanta",
        "Miami", "Chicago", "Netherlands", "Germany", "NL", "DE", "UK", "US", "EU",
    ]
    found = []
    for p in places:
        if re.search(rf"\b{re.escape(p)}\b", blob, re.I):
            found.append(p)
    # 去重保序
    seen, out = set(), []
    for f in found:
        k = f.lower()
        if k not in seen:
            seen.add(k)
            out.append(f)
    return ", ".join(out[:5])


def write_promo_md(
    repo: Path,
    *,
    discussion_id: str,
    title: str,
    url: str,
    author: str = "",
    category: str = "",
    created: str = "",
    op_excerpt: str = "",
    price_window: str = "",
    location: str = "",
    confidence: str = "medium",
    sample: bool = False,
    date_str: str = "",
) -> Path:
    root = repo / "promos" / "lowendtalk"
    root.mkdir(parents=True, exist_ok=True)
    day = date_str or (created[:10] if created else datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    # store by day folder + id
    day_dir = root / day
    day_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{discussion_id}-{_slug(title)}.md"
    path = day_dir / fname
    price_window = price_window or guess_price_window(title, op_excerpt)
    location = location or guess_location(title, op_excerpt)
    summary = (op_excerpt or title).replace("\n", " ").strip()[:180]
    flag = "sample: true\n" if sample else ""
    body = f"""---
source: {url}
date: {day}
discussion_id: {discussion_id}
vendor: {author or "unknown"}
title: {_yaml_escape(title)}
category: {category}
price_window: {_yaml_escape(price_window)}
location: {_yaml_escape(location)}
confidence: {confidence}
track: promo
{flag}---

# {title}

- **链接**: {url}
- **商家/作者**: {author or "unknown"}
- **分类**: {category or "offers"}
- **价格/时间窗**: {price_window or "（标题未解析到明确价，待人工）"}
- **地点**: {location or "（未解析）"}
- **一句话**: {summary}
- **confidence**: {confidence}

> 短摘要 + 链接；不整帖搬运。优惠有时效，只作供需噪音，不当线路/IP/建站基准。
"""
    path.write_text(body, encoding="utf-8")
    _append_index(root, {
        "date": day,
        "discussion_id": discussion_id,
        "title": title,
        "url": url,
        "vendor": author,
        "price_window": price_window,
        "location": location,
        "confidence": confidence,
        "path": str(path.relative_to(repo)),
        "sample": "yes" if sample else "no",
    })
    return path


def _yaml_escape(s: str) -> str:
    s = (s or "").replace("\n", " ").strip()
    if s == "":
        return '""'
    if any(c in s for c in ":#{}[],&*?|>!%@`'\""):
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def _append_index(root: Path, row: dict[str, str]) -> None:
    idx = root / "index.csv"
    fields = ["date", "discussion_id", "title", "url", "vendor", "price_window", "location", "confidence", "path", "sample"]
    exists = idx.exists()
    # 去重：同 discussion_id 覆盖式跳过追加若已有
    if exists:
        with idx.open(encoding="utf-8") as f:
            for line in f:
                if f",{row['discussion_id']}," in f",{line}" or line.startswith(f"{row['date']},{row['discussion_id']},"):
                    # 简易：仍追加，index 可有重复日更；或读 csv
                    pass
        rows = list(csv.DictReader(idx.open(encoding="utf-8")))
        rows = [r for r in rows if r.get("discussion_id") != row["discussion_id"]]
        rows.append(row)
        with idx.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        return
    with idx.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerow(row)
