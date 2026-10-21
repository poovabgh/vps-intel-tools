"""抓取 LowEndTalk 分类页 / 讨论页（优先 curl；遇 CF 可走本地 HTML）。"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
DEFAULT_BASE = "https://lowendtalk.com"


def looks_like_challenge(html: str) -> bool:
    low = (html or "")[:8000].lower()
    markers = (
        "cf-browser-verification",
        "just a moment",
        "challenge-platform",
        "cf-challenge",
        "attention required",
    )
    return any(m in low for m in markers)


def curl_get(url: str, dest: Path | None = None, timeout: int = 45) -> dict[str, Any]:
    """用 curl 拉页面。返回 {ok, status, html|path, error, challenged}。"""
    dest = dest or Path("/tmp") / f"let-{abs(hash(url)) % 10**8}.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "curl", "-sL", "-A", UA,
        "--max-time", str(timeout),
        "-w", "__HTTP__:%{http_code}",
        "-o", str(dest),
        url,
    ]
    jar = os.environ.get("LET_COOKIE_JAR", "").strip()
    if jar:
        cmd[1:1] = ["-b", jar, "-c", jar]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 15)
        m = re.search(r"__HTTP__:(\d+)", r.stdout or "")
        status = int(m.group(1)) if m else 0
        html = dest.read_text(encoding="utf-8", errors="replace") if dest.exists() else ""
        challenged = looks_like_challenge(html) or status in (403, 503)
        ok = status == 200 and not challenged and len(html) > 500
        return {
            "ok": ok,
            "status": status,
            "path": str(dest),
            "html": html if ok or len(html) < 200_000 else html[:50_000],
            "error": "" if ok else (r.stderr or f"http={status} challenged={challenged}"),
            "challenged": challenged,
        }
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "status": 0, "path": str(dest), "html": "", "error": str(e), "challenged": False}


def load_html(path_or_url: str, cache_dir: Path | None = None) -> dict[str, Any]:
    """本地文件 或 URL。"""
    p = Path(path_or_url)
    if p.is_file():
        html = p.read_text(encoding="utf-8", errors="replace")
        return {
            "ok": True,
            "status": 200,
            "path": str(p),
            "html": html,
            "error": "",
            "challenged": looks_like_challenge(html),
            "source": "file",
        }
    cache_dir = cache_dir or Path("/tmp/let-cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^\w.-]+", "_", path_or_url)[-120:]
    dest = cache_dir / f"{safe}.html"
    out = curl_get(path_or_url, dest=dest)
    out["source"] = "curl"
    return out
