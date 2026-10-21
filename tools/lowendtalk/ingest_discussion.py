"""CLI：抓/读单帖 → 双轨路由 → promo 落盘或学习轨摘要。"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from lowendtalk.fetch import load_html
from lowendtalk.parse import parse_discussion, discussion_id_from_href
from lowendtalk.route import LetRouter
from lowendtalk.promo_write import write_promo_md


def _slug_from_category(name: str) -> str:
    m = {
        "Offers": "offers",
        "Shared Hosting Offers": "shared-hosting-offers",
        "Reviews": "reviews",
        "Providers": "providers",
        "General": "general",
        "Outages": "outages",
        "News": "news",
        "Giveaways & Freebies": "giveaways",
        "Service Transfers": "service-transfers",
        "Help": "help",
    }
    return m.get(name, re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="LowEndTalk 单帖入库（双轨）")
    ap.add_argument("--url", default="", help="讨论 permalink")
    ap.add_argument("--html", default="", help="本地 HTML")
    ap.add_argument("--repo", default="/workspace/vps-intel")
    ap.add_argument("--force-track", choices=["", "promo", "learning"], default="")
    ap.add_argument("--sample", action="store_true")
    ap.add_argument("--write-raw", action="store_true", help="学习轨 L3 时存 raw/lowendtalk/<id>/")
    args = ap.parse_args(argv)

    if not args.url and not args.html:
        print("需要 --url 或 --html", file=sys.stderr)
        return 2

    fetched = load_html(args.html or args.url)
    if not fetched.get("ok"):
        print(f"FETCH_FAIL {fetched.get('error')} challenged={fetched.get('challenged')}", file=sys.stderr)
        return 1

    disc = parse_discussion(fetched["html"])
    if not disc.get("discussion_id") and args.url:
        disc["discussion_id"] = discussion_id_from_href(args.url) or ""
        disc["url"] = disc.get("url") or args.url

    slug = _slug_from_category(disc.get("category") or "")
    router = LetRouter()
    decision = router.route(
        title=disc.get("title") or "",
        category_slug=slug,
        category_name=disc.get("category") or "",
        op_text=disc.get("op_text") or "",
        force_track=args.force_track or "",
    )

    repo = Path(args.repo)
    written = ""
    if decision["track"] == "promo":
        path = write_promo_md(
            repo,
            discussion_id=disc["discussion_id"],
            title=disc["title"],
            url=disc.get("url") or args.url,
            author=disc.get("author") or "",
            category=disc.get("category") or slug,
            created=disc.get("created") or "",
            op_excerpt=disc.get("op_excerpt") or "",
            confidence="low" if args.sample else "medium",
            sample=args.sample or fetched.get("source") == "file",
        )
        written = str(path)
    elif decision.get("l3") and args.write_raw:
        raw_dir = repo / "raw" / "lowendtalk" / str(disc["discussion_id"])
        raw_dir.mkdir(parents=True, exist_ok=True)
        html_path = Path(fetched["path"])
        dest = raw_dir / "page-1.html"
        dest.write_text(Path(html_path).read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
        meta = {**disc, "funnel": decision}
        # 不存整楼 op_text 过长版权：thread.json 可留摘录
        meta_out = {
            "discussion_id": disc["discussion_id"],
            "title": disc["title"],
            "url": disc.get("url"),
            "author": disc.get("author"),
            "category": disc.get("category"),
            "created": disc.get("created"),
            "op_excerpt": disc.get("op_excerpt"),
            "comment_count": disc.get("comment_count"),
            "funnel": {k: decision[k] for k in ("track", "l1", "l2", "l3", "l2_hits", "l3_hits", "topic_hint", "reasons")},
        }
        (raw_dir / "thread.json").write_text(json.dumps(meta_out, ensure_ascii=False, indent=2), encoding="utf-8")
        written = str(raw_dir)

    out = {"discussion": {k: disc[k] for k in disc if k != "op_text"}, "decision": decision, "written": written}
    # op_text 太长，只在 decision 需要时已用；输出用 excerpt
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
