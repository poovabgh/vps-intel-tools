"""双轨路由：promo vs learning；learning 再套简化 L1/L2/L3。"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

_CAT_YML = Path(__file__).with_name("categories.yml")
_FUNNEL_YML = Path(__file__).with_name("let_funnel.yml")


def _load_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text) or {}
    return {}


def _compile(patterns: list) -> list[re.Pattern]:
    out = []
    for p in patterns or []:
        try:
            out.append(re.compile(str(p), re.I))
        except re.error:
            out.append(re.compile(re.escape(str(p)), re.I))
    return out


class LetRouter:
    def __init__(self, categories: dict | None = None, funnel: dict | None = None):
        self.categories = categories or _load_yaml(_CAT_YML)
        self.funnel = funnel or _load_yaml(_FUNNEL_YML)
        self.promo_pats = _compile(self.funnel.get("promo_title_patterns") or [])
        self.l2_pats = _compile(self.funnel.get("l2_theme_patterns") or [])
        self.l3_pats = _compile(self.funnel.get("l3_density_patterns") or [])
        self.cat_map = self.categories.get("categories") or {}

    def category_default_track(self, category_slug: str) -> str:
        info = self.cat_map.get(category_slug) or {}
        return str(info.get("track") or "mixed")

    def hit(self, pats: list[re.Pattern], text: str) -> list[str]:
        hits, seen = [], set()
        for p in pats:
            m = p.search(text or "")
            if m:
                h = m.group(0)[:40]
                k = h.lower()
                if k not in seen:
                    seen.add(k)
                    hits.append(h)
        return hits

    def route(
        self,
        *,
        title: str,
        category_slug: str = "",
        category_name: str = "",
        op_text: str = "",
        force_track: str = "",
    ) -> dict[str, Any]:
        """返回 track=promo|learning, layer 决策, reasons。"""
        reasons: list[str] = []
        default = self.category_default_track(category_slug) if category_slug else "mixed"
        blob = f"{title}\n{category_name}\n{(op_text or '')[:1500]}"

        promo_hits = self.hit(self.promo_pats, f"{title}\n{category_name}")
        l2_hits = self.hit(self.l2_pats, blob)

        track = force_track or ""
        if not track:
            if default == "promo":
                track = "promo"
                reasons.append(f"分类默认 promo ({category_slug or category_name})")
            elif default == "learning_risk":
                track = "learning"
                reasons.append(f"分类 learning_risk ({category_slug})")
            elif default == "learning":
                # 评测分类：标题很像纯促销时仍可分流 promo
                if promo_hits and not l2_hits:
                    track = "promo"
                    reasons.append(f"评测分类但标题促销词且无学习词: {promo_hits[:4]}")
                else:
                    track = "learning"
                    reasons.append("分类默认 learning")
            else:  # mixed
                if l2_hits and not (promo_hits and len(op_text or "") < 80):
                    track = "learning"
                    reasons.append(f"mixed→learning 主题词 {l2_hits[:6]}")
                elif promo_hits or default == "promo":
                    track = "promo"
                    reasons.append(f"mixed→promo {promo_hits[:4] or 'default'}")
                else:
                    track = "learning"
                    reasons.append("mixed→learning 兜底")

        result: dict[str, Any] = {
            "track": track,
            "l1": False,
            "l2": False,
            "l3": False,
            "l2_hits": l2_hits,
            "l3_hits": [],
            "promo_hits": promo_hits,
            "reasons": reasons,
            "topic_hint": self._topic_hint(l2_hits),
        }

        if track == "promo":
            result["l1"] = True
            result["reasons"].append("优惠轨：记 promos/，不升学习 L3")
            return result

        # learning track funnel
        result["l1"] = True
        result["reasons"].append("L1:学习轨候选")
        if l2_hits or default in ("learning", "learning_risk"):
            result["l2"] = True
            result["reasons"].append(f"L2: {', '.join(l2_hits[:8]) or default}")
        if not result["l2"]:
            return result

        l3_hits = self.hit(self.l3_pats, op_text or "")
        min_op = int(self.funnel.get("l3_min_op_chars") or 120)
        require = bool(self.funnel.get("l3_require_density_hit", True))
        op_len = len((op_text or "").strip())
        density_ok = bool(l3_hits) if require else True
        if density_ok and op_len >= min_op and l3_hits:
            result["l3"] = True
            result["l3_hits"] = l3_hits
            result["reasons"].append(f"L3: {', '.join(l3_hits[:6])}")
        else:
            result["reasons"].append("学习轨停在 L2（密度/长度不足）")
        return result

    def _topic_hint(self, l2_hits: list[str]) -> str:
        blob = " ".join(l2_hits).lower()
        if any(k in blob for k in ("yabs", "geekbench", "iops", "oversell", "建站", "超售", "并发", "性能")):
            return "hosting"
        if any(
            k in blob
            for k in (
                "unlock",
                "chatgpt",
                "netflix",
                "tiktok",
                "reddit",
                "twitter",
                "ip quality",
                "解锁",
                "原生",
                "送中",
                "社媒",
                "streaming",
            )
        ):
            return "ip-quality"
        if l2_hits:
            return "routing"
        return ""
