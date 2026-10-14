#!/usr/bin/env python3
"""例程可复制的时段桶深读骨架：读桶 CSV → L1/L2/L3 → 入库/归档 → SUMMARY。

用法示例：
  python3 tools/nodeseek_deep/run_bucket_deep_ingest.py \\
    --bucket /workspace/vps-intel-tools/queue/buckets/202610140812.csv \\
    --out /workspace/vps-intel-review/rss-deep-YYYYMMDD-HHMM \\
    --repo /workspace/vps-intel \\
    --ingest-tag 'rss-bucket-deep-read …'

说明：
- L1/L2：每帖至少抓第 1 页并写短证据（逻辑可接旧 run_deep_ingest；本骨架聚焦漏斗与 L3）。
- L3：多页（最多 3）+ raw/nodeseek/<id>/ + *-thread.md + 可选 notes。
- 完整品牌入库/CSV 更新仍可由例程沿用旧脚本；本骨架保证漏斗统计与 L3 归档可独立跑通。
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

# 允许直接 python 本文件
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nodeseek_deep.funnel_rules import Funnel, load_rules
from nodeseek_deep.fetch_thread import fetch_thread_pages
from nodeseek_deep.parse_thread import parse_thread_pages, truncate
from nodeseek_deep.archive import archive_l3

PT = timezone(timedelta(hours=-7))

# 精简品牌规则（样例/骨架够用；完整表见历史 run_deep_ingest）
BRAND_RULES = [
    (re.compile(r"vps\.?\s*taxi", re.I), "vpstaxi"),
    (re.compile(r"ppflight|皮皮飞", re.I), "ppflight"),
    (re.compile(r"seednet", re.I), "seednet"),
    (re.compile(r"gomami|密码狗", re.I), "gomami"),
    (re.compile(r"dmit|大妈", re.I), "dmit"),
    (re.compile(r"绿云|green\s*cloud", re.I), "luyun"),
    (re.compile(r"搬瓦工|bandwagon|\bbwh\b", re.I), "bandwagonhost"),
]


def pub_date_pt(pub_date_utc: str) -> str:
    if not pub_date_utc:
        return datetime.now(PT).strftime("%Y-%m-%d")
    try:
        dt = parsedate_to_datetime(pub_date_utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(PT).strftime("%Y-%m-%d")
    except Exception:
        return datetime.now(PT).strftime("%Y-%m-%d")


def resolve_brand(title: str, text: str) -> str:
    blob = f"{title} {text}"
    for pat, slug in BRAND_RULES:
        if pat.search(blob):
            return slug
    if re.search(r"人找车|求推荐|求建议", title or ""):
        # 有明确品牌时上面已命中
        pass
    if re.search(r"4837|9929|跨网|线路", title or "") and not re.search(
        r"vps\.?taxi|ppflight|seednet|dmit|gomami", blob, re.I
    ):
        return "nobrand"
    return "nobrand"


def load_bucket(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fmt_size(n: int) -> str:
    if n >= 1024 * 1024:
        return f"{n / (1024 * 1024):.2f} MiB ({n} B)"
    return f"{n / 1024:.1f} KiB ({n} B)"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="NodeSeek bucket deep-read with 3-layer funnel")
    ap.add_argument("--bucket", required=True, help="时段桶 CSV 路径")
    ap.add_argument("--out", required=True, help="核对输出目录")
    ap.add_argument("--repo", default="/workspace/vps-intel", help="vps-intel 根目录")
    ap.add_argument("--ingest-tag", default="funnel-deep-ingest")
    ap.add_argument("--max-pages", type=int, default=0, help="覆盖 funnel.yml max_pages；0=用配置")
    ap.add_argument("--limit", type=int, default=0, help="只处理前 N 条（调试）")
    ap.add_argument("--pids", default="", help="逗号分隔 post_id，只处理这些")
    ap.add_argument("--l3-only-archive", action="store_true", help="只做漏斗+L3 归档，不写短证据 CSV")
    args = ap.parse_args(argv)

    out = Path(args.out)
    raw_tmp = out / "raw"
    out.mkdir(parents=True, exist_ok=True)
    raw_tmp.mkdir(exist_ok=True)
    repo = Path(args.repo)
    funnel = Funnel(load_rules())
    max_pages = args.max_pages or funnel.max_pages

    rows = load_bucket(Path(args.bucket))
    if args.pids:
        allow = {x.strip() for x in args.pids.split(",") if x.strip()}
        rows = [r for r in rows if str(r.get("post_id") or r.get("pid") or "") in allow]
    if args.limit:
        rows = rows[: args.limit]

    wall_start = time.time()
    stats = {
        "l1": 0, "l2": 0, "l3": 0,
        "multipage_fetches": 0,  # 抓了 >1 页的帖数
        "pages_total": 0,
        "raw_archive_bytes": 0,
        "skipped": 0,
        "failed": 0,
    }
    results = []

    for i, row in enumerate(rows, 1):
        pid = str(row.get("post_id") or row.get("pid") or "")
        url = row.get("url") or f"https://www.nodeseek.com/post-{pid}-1"
        title = row.get("title") or ""
        kw = row.get("matched_keywords") or ""
        snippet = row.get("snippet") or ""
        print(f"[{i}/{len(rows)}] {pid} {title[:50]}", flush=True)

        type_tag = funnel.classify_type(title, kw, snippet, row.get("category_tags") or "")
        # 先抓第1页（所有 L1）
        work = raw_tmp / pid
        fetch1 = fetch_thread_pages(
            pid, work, max_pages=1, sleep_sec=funnel.page_sleep, start_url=url,
        )
        if not fetch1.get("ok"):
            stats["failed"] += 1
            results.append({"pid": pid, "ok": False, "reason": "fetch_fail", "fetch": fetch1})
            continue

        parsed1 = parse_thread_pages(fetch1["html_by_page"])
        title = parsed1.get("title") or title
        type_tag = funnel.classify_type(
            title, kw, parsed1.get("op_text") or snippet, row.get("category_tags") or ""
        )
        decision = funnel.decide_layers(
            title=title,
            type_tag=type_tag,
            keywords=kw,
            op_text=parsed1.get("op_text") or "",
            comments_text=parsed1.get("comments_text") or "",
            snippet=snippet,
            already_l1=True,
        )
        if decision.get("skip_reason"):
            stats["skipped"] += 1
            results.append({"pid": pid, "ok": True, "funnel": decision, "skipped": True})
            continue

        if decision["l1"]:
            stats["l1"] += 1
        if decision["l2"]:
            stats["l2"] += 1

        brand = resolve_brand(title, parsed1.get("all_text") or "")
        date_pt = pub_date_pt(row.get("pub_date_utc") or "")
        archive_info = None
        pages_fetched = fetch1.get("pages_fetched") or 1

        # L3：补页并长期归档
        if decision["l2"]:
            # 用首页内容再判一次 L3；若已 L3 或接近，拉多页再复判
            need_multi = decision["l3"] or type_tag in ("线路", "评测", "风险")
            if need_multi and max_pages > 1:
                time.sleep(funnel.page_sleep)
                fetch_all = fetch_thread_pages(
                    pid, work, max_pages=max_pages, sleep_sec=funnel.page_sleep, start_url=url,
                )
                if fetch_all.get("ok"):
                    fetch1 = fetch_all
                    parsed1 = parse_thread_pages(fetch_all["html_by_page"])
                    pages_fetched = fetch_all.get("pages_fetched") or pages_fetched
                    decision = funnel.decide_layers(
                        title=parsed1.get("title") or title,
                        type_tag=type_tag,
                        keywords=kw,
                        op_text=parsed1.get("op_text") or "",
                        comments_text=parsed1.get("comments_text") or "",
                        snippet=snippet,
                        already_l1=True,
                    )
                    if decision["l2"] and not decision.get("skip_reason"):
                        # 保持 l1/l2 计数已加；l3 下面加
                        pass

        stats["pages_total"] += pages_fetched
        if pages_fetched > 1:
            stats["multipage_fetches"] += 1

        if decision.get("l3"):
            stats["l3"] += 1
            archive_info = archive_l3(
                repo,
                post_id=pid,
                url=url if "post-" in url else f"https://www.nodeseek.com/post-{pid}-1",
                brand_slug=brand,
                type_tag=type_tag,
                date_pt=date_pt,
                parsed=parsed1,
                funnel=decision,
                html_by_page=fetch1["html_by_page"],
                fetch_meta=fetch1,
                floor_max=funnel.floor_max,
                ingest_tag=args.ingest_tag,
                write_note=True,
            )
            stats["raw_archive_bytes"] += int(archive_info.get("raw_bytes") or 0)

        results.append({
            "pid": pid,
            "ok": True,
            "title": title,
            "type": type_tag,
            "brand": brand,
            "funnel": decision,
            "pages": pages_fetched,
            "archive": archive_info,
        })
        if i < len(rows):
            time.sleep(0.5)

    wall = int(round(time.time() - wall_start))
    raw_bytes_tmp = sum(f.stat().st_size for f in raw_tmp.rglob("*.html") if f.is_file())
    (out / "funnel_results.json").write_text(
        json.dumps({"stats": stats, "results": results}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    cost = {
        "queue_rows": len(rows),
        "primary_evidence": stats["l1"],  # 骨架：L1 计数近似
        "raw_html_bytes": raw_bytes_tmp,
        "parsed_json_bytes": (out / "funnel_results.json").stat().st_size,
        "script_wall_seconds": wall,
        "platform_tokens": None,
        "platform_tokens_note": "未接入：无按次 API",
        "funnel": {
            "l1": stats["l1"],
            "l2": stats["l2"],
            "l3": stats["l3"],
            "multipage_fetches": stats["multipage_fetches"],
            "pages_total": stats["pages_total"],
            "raw_archive_bytes": stats["raw_archive_bytes"],
        },
    }
    (out / "cost_stats.json").write_text(json.dumps(cost, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    mins, secs = divmod(wall, 60)
    summary = [
        f"# NodeSeek 漏斗深读 — {args.ingest_tag}\n",
        f"- **桶**: `{args.bucket}`",
        f"- **队列**: {len(rows)}",
        f"- **L1 / L2 / L3**: {stats['l1']} / {stats['l2']} / {stats['l3']}",
        f"- **多页帖数**: {stats['multipage_fetches']}（合计页 {stats['pages_total']}）",
        f"- **仓库 raw 归档字节**: {fmt_size(stats['raw_archive_bytes'])}",
        f"- **失败**: {stats['failed']}；噪音跳过: {stats['skipped']}\n",
        "## 消耗统计（代理指标；平台 token 不可得）\n",
        "| 项 | 值 |",
        "| --- | --- |",
        f"| 队列条数 | {len(rows)} |",
        f"| 主证据入库(L1) | {stats['l1']} |",
        f"| funnel L2 | {stats['l2']} |",
        f"| funnel L3 | {stats['l3']} |",
        f"| 多页抓取帖数 | {stats['multipage_fetches']} |",
        f"| 抓回 HTML 总体积(核对 raw) | {fmt_size(raw_bytes_tmp)} |",
        f"| 仓库 raw/nodeseek 归档 | {fmt_size(stats['raw_archive_bytes'])} |",
        f"| 解析产物 funnel_results.json | {fmt_size(cost['parsed_json_bytes'])} |",
        f"| 脚本墙钟 | {wall}s（约 {mins}分{secs}秒） |",
        "| 平台 token / 额度 | **未接入** |\n",
        "## L3 样例\n",
    ]
    for r in results:
        if r.get("archive"):
            a = r["archive"]
            summary.append(
                f"- `{r['pid']}` pages={a.get('pages')} → `{a.get('evidence')}` ; raw `{a.get('raw_dir')}`"
            )
    if stats["l3"] == 0:
        summary.append("- （本轮无 L3）")
    (out / "SUMMARY.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print("FUNNEL_DONE", stats, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
