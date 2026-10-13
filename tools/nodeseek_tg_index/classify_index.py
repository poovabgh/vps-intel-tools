#!/usr/bin/env python3
"""用关键词给电报索引打标：是否服务器相关 + 分类标签。不做论坛深读、不入库。"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


def load_keywords(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix in (".yml", ".yaml"):
        if yaml is None:
            raise SystemExit("需要 PyYAML：apt install python3-yaml")
        return yaml.safe_load(text)
    return json.loads(text)


def collect_rules(kw: dict[str, Any]) -> tuple[list[dict], list[dict], list[dict]]:
    """Return (keep_rules, regular, noise).

    keep_rules = priority + general brands. Both can trigger keep.
    Items carry tier: "priority" | "general" | "regular" | "noise".
    """
    priority: list[dict] = []
    regular: list[dict] = []
    noise: list[dict] = []
    for group in (kw.get("priority") or {}).values():
        if isinstance(group, list):
            for item in group:
                priority.append({**item, "tier": "priority"})
    # 通用名单：命中也会 keep，但不算重点观测批次
    for group in (kw.get("general") or {}).values():
        if isinstance(group, list):
            for item in group:
                priority.append({**item, "tier": "general"})
    for group in (kw.get("regular") or {}).values():
        if isinstance(group, list):
            for item in group:
                regular.append({**item, "tier": "regular"})
    for item in kw.get("noise") or []:
        noise.append({**item, "tier": "noise"})
    # longer keywords first to prefer specific matches in reporting
    priority.sort(key=lambda x: len(str(x["kw"])), reverse=True)
    regular.sort(key=lambda x: len(str(x["kw"])), reverse=True)
    noise.sort(key=lambda x: len(str(x["kw"])), reverse=True)
    return priority, regular, noise


def find_matches(text: str, rules: list[dict]) -> list[dict]:
    hits = []
    lower = text  # keep original for CN; casefold for ascii
    text_cf = text.casefold()
    for rule in rules:
        kw = str(rule["kw"])
        # ASCII-only keywords: case-insensitive; otherwise literal
        if kw.isascii():
            if kw.casefold() in text_cf:
                hits.append(rule)
        else:
            if kw in text:
                hits.append(rule)
    return hits


def classify_row(
    title: str,
    snippet: str,
    priority: list[dict],
    regular: list[dict],
    noise: list[dict],
    keep_threshold: int,
    noise_override_min: int,
    noise_override_need_server: int,
) -> dict[str, Any]:
    blob = f"{title or ''}\n{snippet or ''}"
    p_hits = find_matches(blob, priority)
    r_hits = find_matches(blob, regular)
    n_hits = find_matches(blob, noise)

    server_score = sum(int(h.get("weight", 1)) for h in p_hits + r_hits)
    noise_score = sum(int(h.get("weight", 1)) for h in n_hits)
    tags = []
    for h in p_hits + r_hits + n_hits:
        tg = h.get("tag")
        if tg and tg not in tags:
            tags.append(tg)
        # catalog marker for 通用名单
        if h.get("tier") == "general" and "catalog:general" not in tags:
            tags.append("catalog:general")
        if h.get("tier") == "priority" and h.get("tag", "").startswith("brand:") and "catalog:priority" not in tags:
            # only mark priority catalog when a priority *brand* hit (not merely strong_signals)
            pass

    focus_hits = [h for h in p_hits if h.get("tier") == "priority"]
    general_hits = [h for h in p_hits if h.get("tier") == "general"]
    if focus_hits and any(str(h.get("tag", "")).startswith("brand:") for h in focus_hits):
        if "catalog:priority" not in tags:
            tags.append("catalog:priority")

    matched = []
    for h in p_hits:
        prefix = "G" if h.get("tier") == "general" else "P"
        matched.append(f"{prefix}:{h['kw']}")
    for h in r_hits:
        matched.append(f"R:{h['kw']}")
    for h in n_hits:
        matched.append(f"N:{h['kw']}")

    keep = False
    reason_parts = []
    if focus_hits:
        keep = True
        reason_parts.append(f"重点词命中({len(focus_hits)})")
    if general_hits:
        keep = True
        reason_parts.append(f"通用名单命中({len(general_hits)})")
    if server_score >= keep_threshold:
        keep = True
        reason_parts.append(f"服务器分={server_score}>={keep_threshold}")

    # noise override: strong noise + weak server → drop
    if n_hits and noise_score >= noise_override_min and server_score < noise_override_need_server:
        # exception: if focus priority score alone is strong enough (>=5) keep;
        # general-only hits need higher bar (not treated as 重点观测)
        focus_score = sum(int(h.get("weight", 1)) for h in p_hits if h.get("tier") == "priority")
        gen_score = sum(int(h.get("weight", 1)) for h in p_hits if h.get("tier") == "general")
        if focus_score >= 5:
            reason_parts.append(f"有噪声但重点分={focus_score}仍保留")
        elif gen_score >= 8:
            reason_parts.append(f"有噪声但通用名单分={gen_score}仍保留")
        else:
            keep = False
            reason_parts.append(
                f"噪声覆盖(噪声分={noise_score},服务器分={server_score}<{noise_override_need_server})"
            )

    if not keep and not reason_parts:
        reason_parts.append(f"未达阈值(服务器分={server_score})")

    return {
        "keep_server_y_n": "Y" if keep else "N",
        "server_score": server_score,
        "noise_score": noise_score,
        "category_tags": "|".join(tags),
        "matched_keywords": ";".join(matched),
        "classify_reason": ";".join(reason_parts),
    }


def split_batches(rows: list[dict], batch_size: int = 100) -> list[list[dict]]:
    ordered = sorted(rows, key=lambda r: int(r["tg_msg_id"]))
    batches = []
    for i in range(0, len(ordered), batch_size):
        batches.append(ordered[i : i + batch_size])
    return batches


def main() -> int:
    ap = argparse.ArgumentParser(description="关键词路由：标记服务器相关帖")
    ap.add_argument(
        "--index",
        default="/workspace/vps-intel-review/tg-index-backfill-2026-10-12/index.csv",
    )
    ap.add_argument(
        "--keywords",
        default=str(Path(__file__).resolve().parent / "keywords.yml"),
    )
    ap.add_argument(
        "--out",
        default="/workspace/vps-intel-review/tg-index-backfill-2026-10-12/index_classified.csv",
    )
    ap.add_argument("--batch", type=int, default=0, help="只处理第 N 批(1-10)，0=全量")
    ap.add_argument("--batch-size", type=int, default=100)
    ap.add_argument("--summary-json", default="", help="写出统计 JSON")
    args = ap.parse_args()

    kw = load_keywords(Path(args.keywords))
    priority, regular, noise = collect_rules(kw)
    keep_threshold = int(kw.get("keep_threshold", 2))
    noise_override_min = int(kw.get("noise_override_min", 3))
    noise_override_need_server = int(kw.get("noise_override_need_server", 6))

    with open(args.index, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    batches = split_batches(rows, args.batch_size)
    if args.batch:
        if args.batch < 1 or args.batch > len(batches):
            print(f"--batch 超出范围 1..{len(batches)}", file=sys.stderr)
            return 2
        work = batches[args.batch - 1]
        batch_label = args.batch
    else:
        work = [r for b in batches for r in b]
        batch_label = 0

    out_fields = list(rows[0].keys()) + [
        "batch_id",
        "keep_server_y_n",
        "server_score",
        "noise_score",
        "category_tags",
        "matched_keywords",
        "classify_reason",
    ]

    # map tg_msg_id -> batch
    id_to_batch = {}
    for i, b in enumerate(batches, 1):
        for r in b:
            id_to_batch[int(r["tg_msg_id"])] = i

    out_rows = []
    for r in work:
        cls = classify_row(
            r.get("title", ""),
            r.get("text_snippet", ""),
            priority,
            regular,
            noise,
            keep_threshold,
            noise_override_min,
            noise_override_need_server,
        )
        out = {**r, **cls, "batch_id": id_to_batch[int(r["tg_msg_id"])]}
        out_rows.append(out)

    out_path = Path(args.out)
    if args.batch:
        out_path = out_path.with_name(
            out_path.stem + f"_batch{args.batch:02d}" + out_path.suffix
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=out_fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(out_rows)

    keep_n = sum(1 for r in out_rows if r["keep_server_y_n"] == "Y")
    drop_n = len(out_rows) - keep_n
    tag_counter: Counter[str] = Counter()
    for r in out_rows:
        if r["keep_server_y_n"] != "Y":
            continue
        for t in (r["category_tags"] or "").split("|"):
            if t:
                tag_counter[t] += 1

    summary = {
        "batch": batch_label,
        "total": len(out_rows),
        "keep": keep_n,
        "drop": drop_n,
        "keep_rate": round(keep_n / len(out_rows), 4) if out_rows else 0,
        "out": str(out_path),
        "top_tags": tag_counter.most_common(25),
        "keywords_file": str(args.keywords),
        "keep_threshold": keep_threshold,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.summary_json:
        Path(args.summary_json).write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
