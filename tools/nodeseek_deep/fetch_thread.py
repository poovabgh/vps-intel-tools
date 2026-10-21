"""按页拉取 NodeSeek 帖子 SSR HTML（无登录）。"""
from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"


def post_url(post_id: str | int, page: int = 1) -> str:
    return f"https://www.nodeseek.com/post-{post_id}-{page}"


def curl_to_file(url: str, dest: Path, timeout: int = 45) -> dict[str, Any]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "curl", "-sS", "-L", "--max-time", str(timeout),
        "-A", UA,
        "-H", "Accept: text/html,application/xhtml+xml",
        "-H", "Accept-Language: zh-CN,zh;q=0.9,en;q=0.8",
        "-w", "\n__HTTP__:%{http_code}",
        "-o", str(dest),
        url,
    ]
    jar = os.environ.get("NODESEEK_COOKIE_JAR", "").strip()
    if jar:
        # Insert cookie jar after program name so curl sends/stores clearance cookies.
        cmd[1:1] = ["-b", jar, "-c", jar]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 15)
        m = re.search(r"__HTTP__:(\d+)", r.stdout or "")
        code = m.group(1) if m else "000"
        size = dest.stat().st_size if dest.exists() else 0
        body = dest.read_text(encoding="utf-8", errors="replace") if size else ""
        has_title = 'class="post-title"' in body or "post-title-link" in body
        useful = (code == "200") and has_title and size > 3000
        reason = "ok" if useful else ("no post-title" if code == "200" else f"HTTP {code}")
        return {
            "url": url, "http": code, "size": size, "useful": useful,
            "reason": reason, "path": str(dest),
        }
    except Exception as e:
        return {
            "url": url, "http": "err", "size": 0, "useful": False,
            "reason": str(e)[:160], "path": str(dest),
        }


def detect_max_page(html: str, post_id: str | int) -> int:
    """从首页 HTML 估计总页数（最多看 pagination 链接）。"""
    pid = str(post_id)
    pages = {1}
    for m in re.finditer(rf"/post-{pid}-(\d+)", html or ""):
        try:
            pages.add(int(m.group(1)))
        except ValueError:
            pass
    # 常见页码控件文案
    for m in re.finditer(r'data-page=["\']?(\d+)', html or "", re.I):
        try:
            pages.add(int(m.group(1)))
        except ValueError:
            pass
    return max(pages) if pages else 1


def fetch_thread_pages(
    post_id: str | int,
    out_dir: Path,
    *,
    max_pages: int = 3,
    sleep_sec: float = 0.9,
    start_url: str | None = None,
) -> dict[str, Any]:
    """拉取最多 max_pages 页，写入 out_dir/page-N.html。

    返回 {post_id, pages:[{page, meta...}], html_by_page:{n: path}, bytes_total}
    """
    pid = str(post_id)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pages_meta: list[dict[str, Any]] = []
    html_by_page: dict[int, Path] = {}
    bytes_total = 0

    # page 1
    url1 = start_url or post_url(pid, 1)
    if not re.search(rf"post-{pid}-\d+", url1):
        url1 = post_url(pid, 1)
    p1 = out_dir / "page-1.html"
    meta1 = curl_to_file(url1, p1)
    pages_meta.append({"page": 1, **meta1})
    if meta1["useful"]:
        html_by_page[1] = p1
        bytes_total += meta1["size"]
    else:
        return {
            "post_id": pid,
            "pages": pages_meta,
            "html_by_page": {k: str(v) for k, v in html_by_page.items()},
            "bytes_total": bytes_total,
            "pages_fetched": len(html_by_page),
            "ok": False,
        }

    html1 = p1.read_text(encoding="utf-8", errors="replace")
    detected = detect_max_page(html1, pid)
    target = min(max(detected, 1), max_pages)

    for page in range(2, target + 1):
        time.sleep(sleep_sec)
        dest = out_dir / f"page-{page}.html"
        meta = curl_to_file(post_url(pid, page), dest)
        pages_meta.append({"page": page, **meta})
        if not meta["useful"]:
            dest.unlink(missing_ok=True)
            break
        # 若与第1页几乎同内容且无新评论，停
        body = dest.read_text(encoding="utf-8", errors="replace")
        # 简单启发：页面标记当前页或评论 li 数量
        if f"post-{pid}-{page}" not in body and page > detected:
            dest.unlink(missing_ok=True)
            break
        html_by_page[page] = dest
        bytes_total += meta["size"]

    return {
        "post_id": pid,
        "pages": pages_meta,
        "html_by_page": {k: str(v) for k, v in html_by_page.items()},
        "bytes_total": bytes_total,
        "pages_fetched": len(html_by_page),
        "detected_max_page": detected,
        "ok": bool(html_by_page),
    }
