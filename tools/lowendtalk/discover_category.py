"""CLI：拉分类列表并双轨路由；promo 可直接落样例。"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from lowendtalk.fetch import load_html
from lowendtalk.parse import parse_category_list
from lowendtalk.route import LetRouter
from lowendtalk.promo_write import write_promo_md

_CAT_YML = Path(__file__).with_name("categories.yml")


def _category_url(slug: str) -> str:
    try:
        import yaml
        data = yaml.safe_load(_CAT_YML.read_text(encoding="utf-8")) or {}
    except Exception:
        data = {}
    base = (data.get("base_url") or "https://lowendtalk.com").rstrip("/")
    info = (data.get("categories") or {}).get(slug) or {}
    path = info.get("path") or f"/categories/{slug}"
    return base + path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="LowEndTalk 分类发现 + 双轨路由")
    ap.add_argument("--category", default="offers", help="分类 slug，如 offers / reviews")
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--html", default="", help="本地 HTML（离线/CF 挡时）")
    ap.add_argument("--url", default="", help="覆盖分类 URL")
    ap.add_argument("--repo", default="/workspace/vps-intel", help="vps-intel 根目录")
    ap.add_argument("--write-promo", type=int, default=0, help="把前 N 条 promo 写入 promos/lowendtalk/")
    ap.add_argument("--sample", action="store_true", help="写入时标记 sample: true")
    ap.add_argument("--out-csv", default="", help="列表+路由结果 CSV")
    ap.add_argument("--json", action="store_true", help="打印 JSON")
    args = ap.parse_args(argv)

    url = args.url or _category_url(args.category)
    src = args.html or url
    fetched = load_html(src)
    if not fetched.get("ok"):
        print(
            f"FETCH_FAIL status={fetched.get('status')} challenged={fetched.get('challenged')} "
            f"err={fetched.get('error')}\n"
            "提示：RSS/部分出口可能被 CF 拦。可用 --html 指向已保存页面，"
            "或设置 LET_COOKIE_JAR 后重试。见 docs/LOWENDTALK.md。",
            file=sys.stderr,
        )
        return 1

    items = parse_category_list(fetched["html"])[: args.limit]
    router = LetRouter()
    rows = []
    for it in items:
        decision = router.route(
            title=it["title"],
            category_slug=args.category,
            category_name=args.category,
            op_text="",
        )
        row = {**it, **{k: decision[k] for k in ("track", "l1", "l2", "l3", "topic_hint", "reasons")}}
        row["reasons"] = "; ".join(decision["reasons"])
        rows.append(row)

    if args.write_promo > 0:
        repo = Path(args.repo)
        n = 0
        for row in rows:
            if row["track"] != "promo":
                continue
            if n >= args.write_promo:
                break
            write_promo_md(
                repo,
                discussion_id=row["discussion_id"],
                title=row["title"],
                url=row["url"],
                author=row.get("author") or "",
                category=args.category,
                op_excerpt=row["title"],
                confidence="low" if args.sample else "medium",
                sample=args.sample or (fetched.get("source") == "file"),
            )
            n += 1
        print(f"wrote {n} promo files under {repo}/promos/lowendtalk/")

    if args.out_csv:
        outp = Path(args.out_csv)
        outp.parent.mkdir(parents=True, exist_ok=True)
        fields = ["discussion_id", "title", "url", "author", "track", "topic_hint", "l1", "l2", "l3", "reasons"]
        with outp.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        print(f"csv: {outp}")

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        print(f"category={args.category} source={fetched.get('source')} count={len(rows)}")
        for r in rows[:20]:
            print(f"  [{r['track']}] {r['discussion_id']} {r['title'][:70]}")
        if len(rows) > 20:
            print(f"  … {len(rows) - 20} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
