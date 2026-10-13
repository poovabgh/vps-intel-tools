#!/usr/bin/env python3
"""NodeSeek 官方电报频道索引：只存标题、时间、论坛帖链接，不入库证据。"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

CHANNEL = "nodeseekc"
BASE = f"https://t.me/s/{CHANNEL}"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
POST_RE = re.compile(
    r"https?://(?:www\.)?nodeseek\.com/post-(\d+)(?:-(\d+))?",
    re.I,
)
PT = ZoneInfo("America/Los_Angeles")


def fetch_page(before: int | None) -> str:
    url = BASE if before is None else f"{BASE}?before={before}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def strip_html(raw: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", raw, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_messages(html: str) -> tuple[list[dict[str, Any]], int | None]:
    """Return (messages newest-first on page ≈ chronological ascending), next before id."""
    prev_m = re.search(
        r'rel="prev"\s+href="/s/nodeseekc\?before=(\d+)"', html
    )
    if not prev_m:
        prev_m = re.search(
            r'class="tme_messages_more[^"]*"[^>]*data-before="(\d+)"', html
        )
    next_before = int(prev_m.group(1)) if prev_m else None

    parts = re.split(r'(?=<div class="tgme_widget_message_wrap)', html)
    rows: list[dict[str, Any]] = []
    for part in parts:
        post_m = re.search(rf'data-post="{CHANNEL}/(\d+)"', part)
        if not post_m:
            continue
        tg_id = int(post_m.group(1))
        dt_m = re.search(r'datetime="([^"]+)"', part)
        datetime_iso = dt_m.group(1) if dt_m else ""
        text_m = re.search(
            r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',
            part,
            re.S,
        )
        text = strip_html(text_m.group(1)) if text_m else ""
        # unique post ids in order of appearance
        seen_posts: list[str] = []
        post_urls: list[str] = []
        for m in POST_RE.finditer(part):
            pid = m.group(1)
            if pid in seen_posts:
                continue
            seen_posts.append(pid)
            # normalize to -1 page form
            post_urls.append(f"https://www.nodeseek.com/post-{pid}-1")

        rows.append(
            {
                "tg_msg_id": tg_id,
                "datetime_utc": datetime_iso,
                "title": text.split("\n", 1)[0][:200] if text else "",
                "text_snippet": text[:500],
                "post_ids": ",".join(seen_posts),
                "post_urls": " ".join(post_urls),
                "tg_permalink": f"https://t.me/{CHANNEL}/{tg_id}",
                "has_forum_link": bool(seen_posts),
            }
        )
    return rows, next_before


def to_pt_label(iso: str) -> str:
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(PT).strftime("%Y-%m-%d %H:%M PT")
    except ValueError:
        return iso


def write_outputs(rows: list[dict[str, Any]], out_dir: Path, meta: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    # enrich
    for r in rows:
        r["datetime_pt"] = to_pt_label(r.get("datetime_utc") or "")

    jsonl_path = out_dir / "index.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    csv_path = out_dir / "index.csv"
    fields = [
        "tg_msg_id",
        "datetime_utc",
        "datetime_pt",
        "title",
        "post_ids",
        "post_urls",
        "tg_permalink",
        "has_forum_link",
        "text_snippet",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # dedup by primary post id (first linked post)
    by_post: dict[str, dict] = {}
    for r in rows:
        if not r["post_ids"]:
            continue
        pid = r["post_ids"].split(",")[0]
        prev = by_post.get(pid)
        if prev is None or r["tg_msg_id"] > prev["tg_msg_id"]:
            by_post[pid] = r
    dedup_path = out_dir / "index_by_post.csv"
    with dedup_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "post_id",
                "post_url",
                "tg_msg_id",
                "datetime_utc",
                "datetime_pt",
                "title",
                "tg_permalink",
            ],
            extrasaction="ignore",
        )
        w.writeheader()
        for pid, r in sorted(by_post.items(), key=lambda x: -x[1]["tg_msg_id"]):
            w.writerow(
                {
                    "post_id": pid,
                    "post_url": f"https://www.nodeseek.com/post-{pid}-1",
                    "tg_msg_id": r["tg_msg_id"],
                    "datetime_utc": r["datetime_utc"],
                    "datetime_pt": r["datetime_pt"],
                    "title": r["title"],
                    "tg_permalink": r["tg_permalink"],
                }
            )

    meta_path = out_dir / "run_meta.json"
    meta = {
        **meta,
        "message_count": len(rows),
        "with_forum_link": sum(1 for r in rows if r["has_forum_link"]),
        "unique_post_ids": len(by_post),
        "tg_id_min": min((r["tg_msg_id"] for r in rows), default=None),
        "tg_id_max": max((r["tg_msg_id"] for r in rows), default=None),
        "datetime_utc_min": min(
            (r["datetime_utc"] for r in rows if r["datetime_utc"]), default=""
        ),
        "datetime_utc_max": max(
            (r["datetime_utc"] for r in rows if r["datetime_utc"]), default=""
        ),
    }
    meta_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    readme = out_dir / "README.md"
    readme.write_text(
        "\n".join(
            [
                "# NodeSeek 电报频道索引试用",
                "",
                f"- 来源：https://t.me/s/{CHANNEL}",
                f"- 抓取页数：{meta.get('pages_fetched')}",
                f"- 消息条数：{meta['message_count']}",
                f"- 带论坛链接：{meta['with_forum_link']}",
                f"- 去重后帖子数：{meta['unique_post_ids']}",
                f"- 时间范围（UTC）：{meta['datetime_utc_min']} → {meta['datetime_utc_max']}",
                f"- 电报消息 id：{meta['tg_id_min']} → {meta['tg_id_max']}",
                "",
                "本目录只做索引（标题、时间、论坛链接），**没有**写入 brands/evidence。",
                "",
                "文件：",
                "- `index.csv` / `index.jsonl`：每条电报消息一行",
                "- `index_by_post.csv`：按论坛帖 id 去重",
                "- `run_meta.json`：本次运行统计",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps(meta, ensure_ascii=False, indent=2))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="索引 NodeSeek 官方电报频道（只存链接与标题，不入库）"
    )
    ap.add_argument(
        "--pages", type=int, default=5, help="翻页次数，默认 5（约 100 条）"
    )
    ap.add_argument(
        "--before",
        type=int,
        default=None,
        help="从该电报消息 id 之前开始往回翻（可选）",
    )
    ap.add_argument(
        "--out",
        type=str,
        default=None,
        help="输出目录",
    )
    ap.add_argument(
        "--sleep-min", type=float, default=1.5, help="页间最短等待秒数"
    )
    ap.add_argument(
        "--sleep-max", type=float, default=2.5, help="页间最长等待秒数"
    )
    args = ap.parse_args()
    if args.pages < 1:
        print("--pages 至少为 1", file=sys.stderr)
        return 2

    out_dir = Path(
        args.out
        or f"/workspace/vps-intel-review/tg-index-trial-{datetime.now(PT).strftime('%Y-%m-%d')}"
    )

    all_rows: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    before = args.before
    pages_ok = 0
    stop_reason = "completed"

    for i in range(args.pages):
        try:
            html = fetch_page(before)
        except urllib.error.HTTPError as e:
            stop_reason = f"http_error:{e.code}"
            print(f"page {i+1}: HTTP {e.code}, stop", file=sys.stderr)
            break
        except Exception as e:  # noqa: BLE001
            stop_reason = f"error:{type(e).__name__}:{e}"
            print(f"page {i+1}: {e}, stop", file=sys.stderr)
            break

        rows, next_before = parse_messages(html)
        if not rows:
            stop_reason = "empty_page"
            print(f"page {i+1}: empty, stop", file=sys.stderr)
            break

        new = 0
        for r in rows:
            if r["tg_msg_id"] in seen_ids:
                continue
            seen_ids.add(r["tg_msg_id"])
            all_rows.append(r)
            new += 1

        pages_ok += 1
        print(
            f"page {i+1}/{args.pages}: got {len(rows)} msgs, +{new} new; "
            f"next_before={next_before}",
            file=sys.stderr,
        )

        if next_before is None:
            stop_reason = "no_prev_link"
            break
        if before is not None and next_before >= before:
            # pagination not advancing
            stop_reason = "before_not_advancing"
            break
        before = next_before

        if i + 1 < args.pages:
            delay = random.uniform(args.sleep_min, args.sleep_max)
            time.sleep(delay)

    # newest first
    all_rows.sort(key=lambda r: r["tg_msg_id"], reverse=True)

    write_outputs(
        all_rows,
        out_dir,
        {
            "channel": CHANNEL,
            "source": BASE,
            "pages_requested": args.pages,
            "pages_fetched": pages_ok,
            "start_before": args.before,
            "stop_reason": stop_reason,
            "finished_at_pt": datetime.now(PT).strftime("%Y-%m-%d %H:%M PT"),
            "out_dir": str(out_dir),
        },
    )
    print(f"wrote {out_dir}", file=sys.stderr)
    return 0 if pages_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
