"""解析 Vanilla 论坛分类列表与单帖。"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None  # type: ignore

BASE = "https://lowendtalk.com"


def _soup(html: str):
    if BeautifulSoup is None:
        raise RuntimeError("需要 beautifulsoup4：pip install beautifulsoup4")
    return BeautifulSoup(html, "html.parser")


def discussion_id_from_href(href: str) -> str | None:
    m = re.search(r"/discussion/(\d+)", href or "")
    return m.group(1) if m else None


def parse_category_list(html: str, base_url: str = BASE) -> list[dict[str, Any]]:
    """返回讨论摘要列表：id, title, url, author, category_hint, meta_text, views, comments。"""
    soup = _soup(html)
    out: list[dict[str, Any]] = []
    for it in soup.select("li.ItemDiscussion"):
        raw_id = (it.get("id") or "").replace("Discussion_", "")
        a = it.select_one("a.Title") or it.select_one(".Title a") or it.select_one('a[href*="/discussion/"]')
        if not a:
            continue
        href = a.get("href") or ""
        url = urljoin(base_url, href.split("#")[0])
        did = raw_id or discussion_id_from_href(href)
        if not did:
            continue
        title = a.get_text(" ", strip=True)
        meta = it.select_one(".Meta")
        meta_text = meta.get_text(" ", strip=True) if meta else ""
        author = ""
        # Meta 常以作者名开头：Author · views · comments
        if meta_text:
            author = re.split(r"\s+\d", meta_text, maxsplit=1)[0].strip()
            author = re.sub(r"\s+views.*", "", author, flags=re.I).strip(" ·|-")
        u = it.select_one("a.Username") or it.select_one(".Username")
        if u:
            author = u.get_text(strip=True)
        views = comments = None
        vm = re.search(r"([\d.]+[KkMm]?)\s*views", meta_text, re.I)
        cm = re.search(r"([\d.]+[KkMm]?)\s*comments", meta_text, re.I)
        if vm:
            views = vm.group(1)
        if cm:
            comments = cm.group(1)
        out.append(
            {
                "discussion_id": str(did),
                "title": title,
                "url": url,
                "author": author,
                "meta_text": meta_text,
                "views": views,
                "comments": comments,
            }
        )
    return out


def parse_discussion(html: str, base_url: str = BASE) -> dict[str, Any]:
    """单帖：id, title, url, author, category, created, op_excerpt, op_text, comment_count。"""
    soup = _soup(html)
    can = soup.select_one('link[rel="canonical"]')
    url = (can.get("href") if can else "") or ""
    did = discussion_id_from_href(url)
    if not did:
        el = soup.select_one("[id^=Discussion_]")
        if el and el.get("id"):
            did = el.get("id").replace("Discussion_", "")
    h1 = soup.select_one("h1")
    title = h1.get_text(" ", strip=True) if h1 else (soup.title.get_text(strip=True) if soup.title else "")
    title = re.sub(r"\s*[—\-]\s*LowEndTalk.*$", "", title).strip()

    category = ""
    for a in soup.select(".Breadcrumbs a"):
        href = a.get("href") or ""
        if "/categories/" in href:
            category = a.get_text(strip=True)
    author_el = soup.select_one(".ItemDiscussion a.Username") or soup.select_one(
        "li.ItemDiscussion a.Username"
    )
    author = author_el.get_text(strip=True) if author_el else ""
    msg = soup.select_one(".ItemDiscussion .Message") or soup.select_one("li.ItemDiscussion .Message")
    op_text = msg.get_text(" ", strip=True) if msg else ""
    # 首条 time 往往是「最近回复」；取 ItemDiscussion 内最早或 DateCreated
    created = ""
    t = soup.select_one(".ItemDiscussion time[datetime]") or soup.select_one(
        ".DiscussionMeta time[datetime]"
    )
    if t and t.get("datetime"):
        created = t.get("datetime")
    # 更好：找带 title 的原创时间 — Vanilla 常把 OP 时间放在 .DiscussionMeta
    for t2 in soup.select(".ItemDiscussion time[datetime]"):
        # 保留最后一个在 OP 块内的？实际 samples 中第一条是 latest reply
        pass
    # 用页面里 ItemDiscussion 附近的 DateCreated
    dc = soup.select_one(".ItemDiscussion .MItem.DateCreated time, .ItemDiscussion .DateCreated time")
    if dc and dc.get("datetime"):
        created = dc.get("datetime")

    comments = soup.select("li.ItemComment")
    return {
        "discussion_id": str(did or ""),
        "title": title,
        "url": url or (f"{base_url}/discussion/{did}" if did else ""),
        "author": author,
        "category": category,
        "created": created,
        "op_text": op_text,
        "op_excerpt": op_text[:400],
        "comment_count": len(comments),
    }
