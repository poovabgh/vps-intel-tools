# NodeSeek 深读三层漏斗

把「发现很多帖」收成「能复盘的线路知识」：一层一层收紧，只有高价值帖才存整页原文。

## 总览

```
RSS keep（脚本关键词）
    │
    ▼
 L1  服务器相关？ ──否──► 跳过（噪音）
    │是
    ▼
    抓第 1 页 → 短证据可入库（标题/摘录/首页短评）
    │
    ▼
 L2  近期线路学习主题？ ──否──► 停在 L1（交易/闲聊也常停这里）
    │是（线路 / 评测 / 风险 + 主题词）
    ▼
    看正文 + 首页评论信息密度
    │
    ▼
 L3  高价值？ ──否──► 停在 L2（已深读，不扩页、不存 raw）
    │是
    ▼
    最多再抓到第 3 页 → 完整正文 + 评论全文
    → raw/nodeseek/<id>/ + thread.json + *-thread.md
    → 有观点时写 routing/notes 短判断
```

## L1 — 服务器相关

- **已过**：RSS 时段桶里的 keep 行（见关键词路由）。
- **仍跳过**：明显噪音标题（灵车闲聊无测速、探针/GC 折扣等，规则在 `funnel.yml` → `l1_noise_title`）。
- **动作**：curl 第 1 页 SSR；可写品牌短证据（现有例程逻辑）。
- **交易帖**：默认可 L1 入库，打时间窗，**不轻易升 L3**。

## L2 — 近期学习向（线路主题）

命中主题词或类型 ∈ {线路, 评测, 风险} 即升档。主题词包括但不限于：

线路 / 回程 / 去程 / CN2 / GIA / GT / 9929 / 4837 / CMIN2 / 软银 / IIJ / NTT /  
家宽 / 落地 / ASN / 三网 / NQ / TQ / NodeQuality / TCPQuality / IP质量 /  
晚高峰 / 强制CN2 / 拔线 / Cogent / BGP …

纯收售标题即使带品牌名，也只算弱匹配：**可 L1，不上 L3**（除非正文/评论强打线路密度）。

## L3 — 高价值原文归档

**触发**：已 L2，且正文或评论出现有信息密度的观点 / 测速 / 路由讨论（`l3_density_patterns`），并满足长度门槛（楼主或评论够长，或密度词已命中）。

**动作**：

1. 保存**完整楼主正文**（证据里每楼上限约 4000 字；`thread.json` 可更满）。
2. 首页评论**全文**（不再用 180 字短截）。
3. 若存在分页（`https://www.nodeseek.com/post-{id}-{page}`），**最多再抓到第 3 页**，页间间隔约 0.8–1.0s；多页 HTML 都进仓并合并评论。
4. 长期路径（均在 **vps-intel**）：
   - `raw/nodeseek/<post_id>/page-1.html` … `page-N.html`
   - `raw/nodeseek/<post_id>/thread.json`
   - `brands/<slug>/evidence/<date>-…-thread.md`（旁路全文，**不覆盖**旧摘要）
   - 可选：`docs/learning/routing/notes/<date>-ns-<id>-judgment.md`

## 升降档一句话

| 从 → 到 | 条件 |
|---------|------|
| 无 → L1 | 桶 keep 且非噪音 |
| L1 → L2 | 线路主题词或类型 线路/评测/风险 |
| L2 → L3 | 正文/评论密度词 + 长度；交易帖额外从严 |
| 任意 → 跳过 | L1 噪音标题 / 拉取失败 |

## 实现

代码包：`tools/nodeseek_deep/`（见该目录 README）。  
例程约定：`docs/ROUTINE_DEEP_INGEST.md`、`docs/PIPELINE.md`（处理节指向本文）。
