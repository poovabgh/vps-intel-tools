"""L3 归档：证据全文 + raw HTML + thread.json + 可选线路短笔记。"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from .parse_thread import truncate

PT = timezone(timedelta(hours=-7))


def slugify(s: str, n: int = 48) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip()).lower()
    s = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return (s[:n] or "post")


def copy_raw_pages(
    repo: Path,
    post_id: str | int,
    html_by_page: dict[int, str | Path],
) -> Path:
    """写入 vps-intel/raw/nodeseek/<post_id>/page-N.html。"""
    dest_dir = Path(repo) / "raw" / "nodeseek" / str(post_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    for page, src in sorted(html_by_page.items(), key=lambda x: int(x[0])):
        src_p = Path(src)
        data = src_p.read_bytes() if src_p.exists() else Path(str(src)).read_bytes()
        (dest_dir / f"page-{int(page)}.html").write_bytes(data)
    return dest_dir


def write_thread_json(
    dest_dir: Path,
    *,
    post_id: str,
    url: str,
    parsed: dict[str, Any],
    funnel: dict[str, Any],
    fetch_meta: dict[str, Any] | None = None,
) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "post_id": str(post_id),
        "url": url,
        "archived_at_pt": datetime.now(PT).strftime("%Y-%m-%d %H:%M:%S PT"),
        "title": parsed.get("title"),
        "op": parsed.get("op"),
        "comments": parsed.get("comments"),
        "comments_count": parsed.get("comments_count"),
        "pages_parsed": parsed.get("pages_parsed"),
        "participants": parsed.get("participants"),
        "funnel": funnel,
        "fetch": fetch_meta or {},
    }
    path = dest_dir / "thread.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def format_full_thread_md(
    *,
    title: str,
    url: str,
    date_pt: str,
    brand_slug: str,
    type_tag: str,
    parsed: dict[str, Any],
    funnel: dict[str, Any],
    floor_max: int = 4000,
    ingest_tag: str = "funnel-l3-archive",
) -> str:
    op = parsed.get("op") or {}
    participants = parsed.get("participants") or []
    part_str = ", ".join(participants[:20]) or "（未解析到）"
    pages = parsed.get("pages_parsed") or [1]
    reasons = "; ".join(funnel.get("reasons") or [])

    lines = [
        f"# {title}",
        "",
        f"- **source**: {url}",
        f"- **date**: {date_pt} PT",
        f"- **type**: {type_tag}",
        f"- **brand**: {brand_slug}",
        f"- **funnel**: L3（L2 hits: {', '.join(funnel.get('l2_hits') or []) or '—'}; "
        f"L3 hits: {', '.join(funnel.get('l3_hits') or []) or '—'}）",
        f"- **pages_archived**: {pages}",
        f"- **raw**: `raw/nodeseek/{_pid_from_url(url)}/`",
        f"- **participants**: {part_str}",
        f"- **author**: {op.get('author') or '—'}",
        f"- **ingest**: {ingest_tag}",
        f"- **funnel_reasons**: {reasons}",
        "",
        "## Full thread archive",
        "",
        "### 楼主正文",
        "",
        "```",
        truncate(op.get("body") or "", floor_max),
        "```",
        "",
        f"### 评论全文（共 {parsed.get('comments_count', 0)} 条，页 {pages}）",
        "",
    ]
    for c in parsed.get("comments") or []:
        fl = c.get("floor") or "?"
        author = c.get("author") or "?"
        page = c.get("page") or "?"
        body = truncate(c.get("body") or "", floor_max)
        lines.append(f"#### #{fl} {author}（p{page}）")
        lines.append("")
        lines.append("```")
        lines.append(body)
        lines.append("```")
        lines.append("")
    return "\n".join(lines) + "\n"


def _pid_from_url(url: str) -> str:
    m = re.search(r"post-(\d+)", url or "")
    return m.group(1) if m else "unknown"


def write_thread_evidence(
    repo: Path,
    *,
    brand_slug: str,
    date_pt: str,
    title: str,
    url: str,
    type_tag: str,
    parsed: dict[str, Any],
    funnel: dict[str, Any],
    floor_max: int = 4000,
    ingest_tag: str = "funnel-l3-archive",
    mode: str = "sidecar",  # sidecar | append
) -> Path:
    """写入 *-thread.md 旁路文件，或向已有证据追加 Full thread archive。

    默认 sidecar，不毁掉旧摘要。
    """
    evid_dir = Path(repo) / "brands" / brand_slug / "evidence"
    evid_dir.mkdir(parents=True, exist_ok=True)
    pid = _pid_from_url(url)
    short = slugify(re.sub(r"[【】\[\]「」\(\)]", "", title or f"post-{pid}"), 36)
    sidecar = evid_dir / f"{date_pt}-{short}-thread.md"
    body = format_full_thread_md(
        title=title or f"post-{pid}",
        url=url,
        date_pt=date_pt,
        brand_slug=brand_slug,
        type_tag=type_tag,
        parsed=parsed,
        funnel=funnel,
        floor_max=floor_max,
        ingest_tag=ingest_tag,
    )
    if mode == "append":
        # 找已有同 pid 证据
        existing = None
        for p in evid_dir.glob("*.md"):
            try:
                t = p.read_text(encoding="utf-8")
            except Exception:
                continue
            if f"post-{pid}" in t and "Full thread archive" not in t and "-thread.md" not in p.name:
                existing = p
                break
        if existing:
            existing.write_text(
                existing.read_text(encoding="utf-8").rstrip()
                + "\n\n## Full thread archive\n\n"
                + "详见旁路 `"
                + sidecar.name
                + "` 与 `raw/nodeseek/"
                + pid
                + "/`。\n",
                encoding="utf-8",
            )
    sidecar.write_text(body, encoding="utf-8")
    return sidecar


def maybe_routing_judgment_note(
    repo: Path,
    *,
    post_id: str,
    title: str,
    url: str,
    brand_slug: str,
    parsed: dict[str, Any],
    funnel: dict[str, Any],
    date_pt: str | None = None,
) -> Path | None:
    """有线路观点时写一篇短判断笔记到 docs/learning/routing/notes/。"""
    if not funnel.get("l3"):
        return None
    blob = parsed.get("all_text") or ""
    if not re.search(
        r"回程|去程|CN2|9929|4837|软银|IIJ|NTT|家宽|丢包|晚高峰|精品|普通BGP|Cogent|IP质量",
        blob,
        re.I,
    ):
        return None

    notes_dir = Path(repo) / "docs" / "learning" / "routing" / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    day = date_pt or datetime.now(PT).strftime("%Y-%m-%d")
    path = notes_dir / f"{day}-ns-{post_id}-judgment.md"
    if path.exists():
        return None

    # 抽几条含密度词的评论作要点
    dens = re.compile(
        r"回程|去程|CN2|9929|4837|软银|IIJ|NTT|家宽|丢包|晚高峰|精品|BGP|IP质量|超售|解锁",
        re.I,
    )
    bullets = []
    op_body = (parsed.get("op") or {}).get("body") or ""
    if dens.search(op_body):
        bullets.append(f"楼主：{truncate(op_body.replace(chr(10), ' '), 220)}")
    for c in parsed.get("comments") or []:
        if dens.search(c.get("body") or ""):
            bullets.append(
                f"{c.get('author') or '?'} #{c.get('floor')}: "
                f"{truncate((c.get('body') or '').replace(chr(10), ' '), 200)}"
            )
        if len(bullets) >= 6:
            break

    judgment = _heuristic_judgment(title, blob, funnel)
    text = (
        f"# 短判断：{truncate(title, 60)}\n\n"
        f"- **post**: [{post_id}]({url})\n"
        f"- **brand**: `{brand_slug}`\n"
        f"- **date**: {day} PT\n"
        f"- **funnel**: L3；命中 {', '.join((funnel.get('l3_hits') or [])[:8])}\n"
        f"- **raw**: `raw/nodeseek/{post_id}/`\n\n"
        f"## 判断（工作笔记，非定论）\n\n"
        f"{judgment}\n\n"
        f"## 摘录\n\n"
        + ("\n".join(f"- {b}" for b in bullets) if bullets else "- （无）")
        + "\n"
    )
    path.write_text(text, encoding="utf-8")
    return path


def _heuristic_judgment(title: str, blob: str, funnel: dict[str, Any]) -> str:
    bits = []
    if re.search(r"软银|SoftBank", blob, re.I):
        bits.append(
            "软银出口热度与 IP 质量要拆开：跟帖若强调「上游软银可用、IP 杂」，"
            "则促销价不能外推为全年线路锚。"
        )
    if re.search(r"4837|9929", blob):
        bits.append(
            "电信跨网场景下，跟帖常分化为「德/欧向偏 9929、美西向常提 4837」；"
            "两者接近时看落地与价格，电信正道仍多推 CN2。"
        )
    if re.search(r"seednet|HK|香港|精品BGP|普通BGP", blob, re.I):
        bits.append(
            "HK 备用/中转讨论里，电信侧「普通 BGP 不够、要精品/CN2GIA」是反复出现的经验口述；"
            "大厂段抗轮询与专线中转是另一条线索，需对照实测。"
        )
    if re.search(r"解锁|过白|IP质量", blob, re.I):
        bits.append(
            "回程标签与 IP 解锁画像可能不一致：评测留档时同时记 NQ/TQ 链接与跟帖解锁观察。"
        )
    if not bits:
        hits = ", ".join((funnel.get("l3_hits") or [])[:6]) or "线路关键词"
        bits.append(f"本帖因 {hits} 升 L3；复盘以 raw HTML / thread.json 为准，此处仅作索引。")
    return " ".join(bits)


def archive_l3(
    repo: Path,
    *,
    post_id: str,
    url: str,
    brand_slug: str,
    type_tag: str,
    date_pt: str,
    parsed: dict[str, Any],
    funnel: dict[str, Any],
    html_by_page: dict[int, str | Path],
    fetch_meta: dict[str, Any] | None = None,
    floor_max: int = 4000,
    ingest_tag: str = "funnel-l3-archive",
    write_note: bool = True,
) -> dict[str, Any]:
    raw_dir = copy_raw_pages(repo, post_id, html_by_page)
    tj = write_thread_json(
        raw_dir,
        post_id=str(post_id),
        url=url,
        parsed=parsed,
        funnel=funnel,
        fetch_meta=fetch_meta,
    )
    evid = write_thread_evidence(
        repo,
        brand_slug=brand_slug,
        date_pt=date_pt,
        title=parsed.get("title") or f"post-{post_id}",
        url=url,
        type_tag=type_tag,
        parsed=parsed,
        funnel=funnel,
        floor_max=floor_max,
        ingest_tag=ingest_tag,
        mode="append",
    )
    note = None
    if write_note:
        note = maybe_routing_judgment_note(
            repo,
            post_id=str(post_id),
            title=parsed.get("title") or "",
            url=url,
            brand_slug=brand_slug,
            parsed=parsed,
            funnel=funnel,
            date_pt=date_pt,
        )
    raw_bytes = sum(
        (raw_dir / f"page-{p}.html").stat().st_size
        for p in html_by_page
        if (raw_dir / f"page-{p}.html").exists()
    )
    return {
        "raw_dir": str(raw_dir),
        "thread_json": str(tj),
        "evidence": str(evid),
        "note": str(note) if note else None,
        "pages": sorted(int(k) for k in html_by_page.keys()),
        "raw_bytes": raw_bytes,
    }
