"""解析 NodeSeek 帖：楼主全文 + 各页评论全文。"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup


def clean_text(s: str | None) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", s).strip()


def full_text(el) -> str:
    if el is None:
        return ""
    # 保留换行感：用 \n 连接块
    return el.get_text("\n", strip=True)


def truncate(s: str, n: int) -> str:
    s = s or ""
    if len(s) <= n:
        return s
    return s[:n] + "…"


def parse_page_html(html: str, *, is_first: bool = False) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    out: dict[str, Any] = {
        "title": "",
        "op": None,
        "comments": [],
    }

    if is_first:
        title_el = (
            soup.select_one("a.post-title-link")
            or soup.select_one(".post-title h1 a")
            or soup.select_one(".post-title h1")
        )
        title = clean_text(title_el.get_text()) if title_el else ""
        if not title:
            t = soup.find("title")
            title = clean_text(t.get_text()) if t else ""
        out["title"] = title

        op_el = None
        for div in soup.select("div.nsk-post > div.content-item, div.nsk-post div.content-item"):
            if div.find_parent("ul", class_="comments"):
                continue
            op_el = div
            break
        if op_el is None:
            op_el = soup.select_one("div.content-item#0") or soup.select_one("div.content-item")

        if op_el:
            an = op_el.select_one("a.author-name")
            art = op_el.select_one("article.post-content")
            tm = op_el.select_one("time")
            out["op"] = {
                "author": clean_text(an.get_text()) if an else "",
                "body": full_text(art) if art else "",
                "time": (tm.get("title") or tm.get("datetime") or clean_text(tm.get_text())) if tm else "",
                "floor": op_el.get("id") or "0",
            }

    for li in soup.select("ul.comments > li.content-item"):
        an = li.select_one("a.author-name")
        art = li.select_one("article.post-content")
        tm = li.select_one("time")
        out["comments"].append({
            "author": clean_text(an.get_text()) if an else "",
            "body": full_text(art) if art else "",
            "time": (tm.get("title") or tm.get("datetime") or clean_text(tm.get_text())) if tm else "",
            "floor": li.get("id") or "",
        })
    return out


def parse_thread_pages(html_by_page: dict[int, str | Path]) -> dict[str, Any]:
    """合并多页解析结果。html_by_page: page_num -> path or html string。"""
    pages_sorted = sorted(int(k) for k in html_by_page.keys())
    title = ""
    op = None
    comments: list[dict[str, Any]] = []
    seen_floors: set[str] = set()

    for i, page in enumerate(pages_sorted):
        raw = html_by_page[page]
        if isinstance(raw, Path) or (isinstance(raw, str) and raw.endswith(".html") and Path(raw).exists()):
            html = Path(raw).read_text(encoding="utf-8", errors="replace")
        else:
            html = str(raw)
        parsed = parse_page_html(html, is_first=(i == 0 and page == pages_sorted[0]))
        if i == 0:
            title = parsed.get("title") or ""
            op = parsed.get("op")
        for c in parsed.get("comments") or []:
            key = c.get("floor") or f"{c.get('author')}:{c.get('body','')[:40]}"
            if key in seen_floors:
                continue
            seen_floors.add(key)
            c = dict(c)
            c["page"] = page
            comments.append(c)

    op_body = (op or {}).get("body") or ""
    comments_text = "\n".join(c.get("body") or "" for c in comments)
    participants: list[str] = []
    seen_p: set[str] = set()
    for name in ([((op or {}).get("author") or "")] + [c.get("author") or "" for c in comments]):
        if name and name not in seen_p:
            participants.append(name)
            seen_p.add(name)

    return {
        "title": title,
        "op": op or {"author": "", "body": "", "time": "", "floor": "0"},
        "comments": comments,
        "comments_count": len(comments),
        "pages_parsed": pages_sorted,
        "participants": participants,
        "op_text": op_body,
        "comments_text": comments_text,
        "all_text": f"{title}\n{op_body}\n{comments_text}",
    }
