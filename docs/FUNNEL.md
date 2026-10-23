# 深读三层漏斗（跨渠道）

把「发现很多帖」收成「能复盘的学习笔记」：一层一层收紧，只有高价值帖才存整页原文。

**渠道**（`channel`）目前：`nodeseek` | `lowendtalk`。漏斗与**固定四方向**对所有渠道共用；渠道只影响发现入口与 `raw/<channel>/` 路径，**不另起主题套**。

## 固定四方向（框架）

| 方向 | 性质 | 目录 / 落点 |
|------|------|-------------|
| **线路机 routing** | 长期 | `docs/learning/routing/` |
| **IP质量 ip-quality** | 长期 | `docs/learning/ip-quality/` |
| **建站机 hosting** | 长期 | `docs/learning/hosting/` |
| **优惠推广抢购交易溢价** | 短期 | 品牌证据时间窗，或 `promos/<channel>/`（如 LET Offers） |

长期三话题**并列**升 L2；短期可入库、打时间窗，**不当**三长期基准，且不轻易 L3。

## 总览

```
发现 keep（渠道脚本：NS RSS 关键词 / LET 分类页等）
    │
    ▼
 L1  服务器相关？ ──否──► 跳过（噪音）
    │是
    ▼
    抓第 1 页 → 短证据可入库（标题/摘录/首页短评）
    │
    ▼
 L2  长期三话题？ ──否──► 停在 L1（短期优惠/交易/闲聊也常停这里）
    │是（线路机 / IP质量 / 建站机 + 主题词）
    ▼
    看正文 + 首页评论信息密度
    │
    ▼
 L3  高价值？ ──否──► 停在 L2（已深读，不扩页、不存 raw）
    │是
    ▼
    最多再抓到第 3 页 → 完整正文 + 评论全文
    → raw/<channel>/<id>/ + thread.json + *-thread.md
    → 有观点时写 docs/learning/{routing|ip-quality|hosting}/notes 短判断
```

## 长期话题（L2 升档目标）

命中任一主题词或类型 ∈ {线路, 评测, 风险} 即升 L2：

| 话题 | 目录 | 学什么 |
|------|------|--------|
| **线路机 routing** | `docs/learning/routing/` | 三网直连、去程/回程、延迟/丢包、CN2/GIA/9929/4837/CMIN2、软银/IIJ/NTT、IX DIY |
| **IP 质量 ip-quality** | `docs/learning/ip-quality/` | 纯净度、流媒体解锁、AI（ChatGPT/Claude 等）、TikTok 电商、X/Reddit 社媒、原生/家宽广播、送中/风险分 |
| **建站机 hosting** | `docs/learning/hosting/` | 性能、带宽、并发、优化、超售、YABS、IO、建站场景回程体验 |

主题词：NodeSeek 见 `tools/nodeseek_deep/funnel.yml` → `l2_theme_patterns`；LowEndTalk 见 `tools/lowendtalk/let_funnel.yml`（**同一四方向**，词表可按语言补全，不是另一套主题）。

## 短期话题（可入库，不轻易 L3）

优惠 / 推广 / 抢购 / 交易 / 溢价 / 拼车 / 抽奖 —— **打时间窗标签**，当供需噪音，**不当线路/IP/建站基准**。  
纯收售标题即使带品牌名，也只算弱匹配：**可 L1，不上 L3**（除非正文/评论强打学习密度）。  
LET Offers 等默认进 `promos/lowendtalk/`，仍属本方向，不是 LET 专属主题。

**母鸡 / 产品线盯梢**：NodeSeek（及日后 LET）做优惠排查时，须对照 intel 仓 [`docs/learning/short-term/mother-chicken-watch-2026-10.md`](https://github.com/poovabgh/vps-intel/blob/main/docs/learning/short-term/mother-chicken-watch-2026-10.md)。品牌 + 产品线命中 → **优先记时间窗**；不自动下单；「已知特征」非评价。词库旁注见 `tools/nodeseek_deep/funnel.yml` → `mother_chicken`。

## L1 — 服务器相关

- **已过**：渠道发现层 keep（NS：RSS 时段桶；LET：分类列表等）。
- **仍跳过**：明显噪音标题（规则在各渠道 funnel yml，如 `l1_noise_title`）。
- **动作**：抓第 1 页；可写品牌短证据。
- **交易/优惠帖**：默认可 L1 入库，打时间窗，**不轻易升 L3**。

## L2 — 长期学习向（三话题）

命中主题词或类型 ∈ {线路, 评测, 风险} 即升档。除线路词外，明确包含：

- IP：解锁 / ChatGPT / TikTok / Reddit / Twitter / 社媒 / 原生IP / 送中 …
- 建站：YABS / 超售 / 并发 / IO / 建站 / Geekbench …

## L3 — 高价值原文归档

**触发**：已 L2，且正文或评论出现有信息密度的观点 / 测速 / 路由 / IP / 性能讨论，并满足长度门槛。

**动作**：

1. 保存**完整楼主正文**（证据里每楼上限约 4000 字；`thread.json` 可更满）。
2. 首页评论**全文**（不再用 180 字短截）。
3. 若存在分页，**最多再抓到第 3 页**；多页 HTML 都进仓并合并评论。
4. 长期路径（均在 **vps-intel**）：
   - `raw/<channel>/<id>/`（如 `raw/nodeseek/<post_id>/`、`raw/lowendtalk/<discussion_id>/`）
   - `brands/<slug>/evidence/<date>-…-thread.md`（旁路全文，**不覆盖**旧摘要）
   - 可选：`docs/learning/{routing|ip-quality|hosting}/notes/<date>-…-judgment.md`

## 升降档一句话

| 从 → 到 | 条件 |
|---------|------|
| 无 → L1 | 发现 keep 且非噪音 |
| L1 → L2 | 三长期主题词或类型 线路/评测/风险 |
| L2 → L3 | 正文/评论密度词 + 长度；交易/优惠帖额外从严 |
| 任意 → 跳过 | L1 噪音标题 / 拉取失败 |

## 实现

| 渠道 | 代码包 | 说明 |
|------|--------|------|
| NodeSeek | `tools/nodeseek_deep/` | RSS 桶深读例程见 `ROUTINE_DEEP_INGEST.md` |
| LowEndTalk | `tools/lowendtalk/` | 分类双轨实现见 `LOWENDTALK.md` |

流水线总览：[PIPELINE.md](PIPELINE.md)。
