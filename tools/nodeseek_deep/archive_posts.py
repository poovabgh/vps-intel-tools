#!/usr/bin/env python3
"""按 post_id 列表做 L2/L3 多页归档（样例回填 / 补洞）。

  python3 -m nodeseek_deep.archive_posts 981768 981828 981812 --repo /workspace/vps-intel
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent.parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from nodeseek_deep.funnel_rules import Funnel, load_rules
from nodeseek_deep.fetch_thread import fetch_thread_pages, post_url
from nodeseek_deep.parse_thread import parse_thread_pages
from nodeseek_deep.archive import archive_l3
from nodeseek_deep.run_bucket_deep_ingest import resolve_brand

PT = timezone(timedelta(hours=-7))

# 样例默认品牌覆盖（标题泛讨论时）
PID_BRAND = {
    "981768": "vpstaxi",
    "981828": "nobrand",
    "981812": "seednet",
    "981058": "ppflight",
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pids", nargs="+", help="post_id 列表")
    ap.add_argument("--repo", default="/workspace/vps-intel")
    ap.add_argument("--work", default="/workspace/vps-intel-review/funnel-sample-work")
    ap.add_argument("--ingest-tag", default="funnel-l3-sample-backfill-2026-10-14")
    ap.add_argument("--max-pages", type=int, default=0)
    args = ap.parse_args(argv)

    funnel = Funnel(load_rules())
    max_pages = args.max_pages or funnel.max_pages
    repo = Path(args.repo)
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    date_pt = datetime.now(PT).strftime("%Y-%m-%d")
    out_list = []

    for i, pid in enumerate(args.pids):
        pid = str(pid)
        print(f"archive {pid} …", flush=True)
        dest = work / pid
        fetch = fetch_thread_pages(pid, dest, max_pages=max_pages, sleep_sec=funnel.page_sleep)
        if not fetch.get("ok"):
            out_list.append({"pid": pid, "ok": False, "fetch": fetch})
            continue
        parsed = parse_thread_pages(fetch["html_by_page"])
        title = parsed.get("title") or f"post-{pid}"
        type_tag = funnel.classify_type(title, "", parsed.get("op_text") or "")
        decision = funnel.decide_layers(
            title=title,
            type_tag=type_tag,
            keywords="",
            op_text=parsed.get("op_text") or "",
            comments_text=parsed.get("comments_text") or "",
            already_l1=True,
        )
        # 样例回填：强制 L3 归档（用户点名的高价值帖）
        decision["l3"] = True
        if not decision["l2"]:
            decision["l2"] = True
            decision["reasons"].append("样例回填强制 L2/L3")
        brand = PID_BRAND.get(pid) or resolve_brand(title, parsed.get("all_text") or "")
        info = archive_l3(
            repo,
            post_id=pid,
            url=post_url(pid, 1),
            brand_slug=brand,
            type_tag=type_tag,
            date_pt=date_pt,
            parsed=parsed,
            funnel=decision,
            html_by_page=fetch["html_by_page"],
            fetch_meta=fetch,
            floor_max=funnel.floor_max,
            ingest_tag=args.ingest_tag,
            write_note=True,
        )
        out_list.append({
            "pid": pid,
            "ok": True,
            "title": title,
            "brand": brand,
            "type": type_tag,
            "pages": info.get("pages"),
            "funnel": decision,
            "archive": info,
        })
        print(f"  pages={info.get('pages')} evid={info.get('evidence')}", flush=True)
        if i + 1 < len(args.pids):
            time.sleep(funnel.page_sleep)

    report = work / "sample_archive_report.json"
    report.write_text(json.dumps(out_list, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("SAMPLE_DONE", report, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
