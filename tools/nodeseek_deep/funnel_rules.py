"""三层漏斗升降档规则。"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

_DEFAULT_YML = Path(__file__).with_name("funnel.yml")


def load_rules(path: Path | None = None) -> dict[str, Any]:
    p = path or _DEFAULT_YML
    text = p.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text) or {}
    # 极简 fallback：不依赖 PyYAML 时用内置默认
    return _builtin_defaults()


def _builtin_defaults() -> dict[str, Any]:
    return {
        "l2_theme_patterns": [
            r"线路", r"回程", r"去程", r"CN2", r"GIA", r"\bGT\b", r"9929", r"4837",
            r"CMIN2", r"CMI", r"软银", r"SoftBank", r"IIJ", r"\bNTT\b", r"家宽",
            r"落地", r"\bASN\b", r"三网", r"\bNQ\b", r"\bTQ\b", r"NodeQuality",
            r"TCPQuality", r"IP质量", r"晚高峰", r"强制CN2", r"拔线", r"Cogent",
            r"BGP", r"精品", r"跨网", r"丢包",
        ],
        "l2_type_tags": ["线路", "评测", "风险"],
        "trade_title_patterns": [
            r"^【?收】", r"^【?出】", r"已出", r"秒出", r"人找车", r"收台", r"折出", r"溢价收",
        ],
        "l3_density_patterns": [
            r"回程", r"去程", r"\bASN\b", r"丢包", r"晚高峰", r"IP质量",
            r"软银.*(互联|上游|体感|和NTT)", r"IIJ", r"NTT.*(路径|体感|一样)",
            r"9929.*(好|稳|比)", r"4837.*(好|稳|比|美西)", r"CN2GIA|CN2 GIA|强制CN2",
            r"电信.*(9929|4837|CN2)", r"联通.*(9929|4837)", r"移动.*(CMIN2|CMI)",
            r"精品BGP", r"普通BGP", r"国际互联", r"超售", r"被打", r"炸", r"解锁",
            r"NodeQuality|TCPQuality|\bNQ\b|\bTQ\b",
        ],
        "l3_min_comment_chars": 80,
        "l3_min_op_chars": 120,
        "l3_require_density_hit": True,
        "max_pages": 3,
        "page_sleep_sec": 0.9,
        "evidence_floor_max_chars": 4000,
        "l1_noise_title": [
            r"灵车", r"Claude封号", r"GPT封号", r"极简探针",
            r"YouTube的测速机制", r"Google Play.*GC折扣", r"自动回帖.*机器人",
        ],
    }


def _compile_list(patterns: list) -> list[re.Pattern]:
    out = []
    for p in patterns or []:
        p = str(p)
        try:
            out.append(re.compile(p, re.I))
        except re.error:
            out.append(re.compile(re.escape(p), re.I))
    return out


class Funnel:
    def __init__(self, rules: dict[str, Any] | None = None):
        self.rules = rules or load_rules()
        self.l2_pats = _compile_list(self.rules.get("l2_theme_patterns") or [])
        self.l3_pats = _compile_list(self.rules.get("l3_density_patterns") or [])
        self.trade_pats = _compile_list(self.rules.get("trade_title_patterns") or [])
        self.noise_pats = _compile_list(self.rules.get("l1_noise_title") or [])
        self.l2_types = set(self.rules.get("l2_type_tags") or ["线路", "评测", "风险"])
        self.max_pages = int(self.rules.get("max_pages") or 3)
        self.page_sleep = float(self.rules.get("page_sleep_sec") or 0.9)
        self.floor_max = int(self.rules.get("evidence_floor_max_chars") or 4000)

    def is_noise_title(self, title: str) -> bool:
        return any(p.search(title or "") for p in self.noise_pats)

    def is_trade_title(self, title: str) -> bool:
        return any(p.search(title or "") for p in self.trade_pats)

    def hit_l2_theme(self, text: str) -> list[str]:
        hits = []
        for p in self.l2_pats:
            m = p.search(text or "")
            if m:
                hits.append(m.group(0))
        # 去重保序
        seen, out = set(), []
        for h in hits:
            k = h.lower()
            if k not in seen:
                seen.add(k)
                out.append(h)
        return out

    def hit_l3_density(self, text: str) -> list[str]:
        hits = []
        for p in self.l3_pats:
            m = p.search(text or "")
            if m:
                hits.append(m.group(0)[:40])
        seen, out = set(), []
        for h in hits:
            k = h.lower()
            if k not in seen:
                seen.add(k)
                out.append(h)
        return out

    def classify_type(self, title: str, keywords: str = "", snippet: str = "", tags: str = "") -> str:
        blob = f"{title} {keywords} {tags} {snippet}"
        if re.search(r"【?NQ】?|【?TQ】?|NQ\+TQ|NodeQuality|测试留档|自测留档|晚高峰TQ", blob, re.I):
            return "评测"
        if re.search(r"风险|封号|被打|攻击|跑路|骗局|欺诈", blob):
            return "风险"
        if re.search(r"线路|回程|去程|CN2|GIA|9929|4837|CMI|软银|三网|晚高峰|BGP|跨网", blob, re.I):
            if not re.search(r"^【?收】|^【?出】", title or ""):
                return "线路"
        if self.is_trade_title(title or "") or "trade" in (tags or ""):
            return "交易"
        if re.search(r"黑五|促销|活动|优惠|券|抽奖", blob):
            return "活动"
        if re.search(r"人找车|求推荐|有没有.*(落地|家宽|鸡)", title or ""):
            return "需求"
        if re.search(r"测评|评测|对比", title or ""):
            return "评测"
        return "分享"

    def decide_layers(
        self,
        *,
        title: str,
        type_tag: str,
        keywords: str = "",
        op_text: str = "",
        comments_text: str = "",
        snippet: str = "",
        already_l1: bool = True,
    ) -> dict[str, Any]:
        """返回 {l1,l2,l3, reasons, l2_hits, l3_hits, skip_reason}。"""
        result = {
            "l1": False,
            "l2": False,
            "l3": False,
            "reasons": [],
            "l2_hits": [],
            "l3_hits": [],
            "skip_reason": "",
            "type_tag": type_tag,
            "is_trade": False,
        }
        if self.is_noise_title(title):
            result["skip_reason"] = "noise:l1_title"
            return result

        if not already_l1 and not (title or snippet or keywords):
            result["skip_reason"] = "empty"
            return result

        result["l1"] = True
        result["reasons"].append("L1:服务器相关/队列keep")
        result["is_trade"] = type_tag == "交易" or self.is_trade_title(title)

        blob_l2 = " ".join([title or "", keywords or "", snippet or "", type_tag or "", op_text[:800], comments_text[:1200]])
        l2_hits = self.hit_l2_theme(blob_l2)
        type_ok = type_tag in self.l2_types
        if l2_hits or type_ok:
            result["l2"] = True
            result["l2_hits"] = l2_hits
            if l2_hits:
                result["reasons"].append(f"L2:主题词 {', '.join(l2_hits[:8])}")
            if type_ok:
                result["reasons"].append(f"L2:类型 {type_tag}")

        # 纯交易弱匹配：可 L1，默认不上 L3
        if result["is_trade"] and not result["l2"]:
            result["reasons"].append("交易帖：仅 L1，不上 L3")
            return result

        if not result["l2"]:
            return result

        body_blob = f"{op_text}\n{comments_text}"
        l3_hits = self.hit_l3_density(body_blob)
        op_len = len((op_text or "").strip())
        cmt_len = len((comments_text or "").strip())
        min_op = int(self.rules.get("l3_min_op_chars") or 120)
        min_cmt = int(self.rules.get("l3_min_comment_chars") or 80)
        require_hit = bool(self.rules.get("l3_require_density_hit", True))

        density_ok = bool(l3_hits) if require_hit else True
        length_ok = (op_len >= min_op) or (cmt_len >= min_cmt) or bool(l3_hits)

        # 交易帖要更严：必须有强密度命中且 L2
        if result["is_trade"]:
            if l3_hits and density_ok and (op_len + cmt_len) >= 200:
                result["l3"] = True
                result["l3_hits"] = l3_hits
                result["reasons"].append(f"L3:交易帖但线路密度高 {', '.join(l3_hits[:6])}")
            else:
                result["reasons"].append("交易帖：L2 有主题但不升 L3")
            return result

        if density_ok and length_ok:
            result["l3"] = True
            result["l3_hits"] = l3_hits
            result["reasons"].append(
                f"L3:密度命中 {', '.join(l3_hits[:8]) or '（长度门槛）'}; op={op_len}cmt={cmt_len}"
            )
        else:
            result["reasons"].append("L2 未达 L3 密度/长度门槛")
        return result
