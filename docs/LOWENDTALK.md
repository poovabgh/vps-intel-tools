# LowEndTalk 接入说明

**主题框架与 NodeSeek 相同**：vps-intel 固定四方向——长期三（线路机 / IP质量 / 建站机）+ 短期一（优惠推广抢购交易溢价）。  
NodeSeek 与 LowEndTalk **只是渠道不同**；本仓负责 LET 发现/解析，证据与优惠仍落 [vps-intel](https://github.com/poovabgh/vps-intel)。  
采集管线与 NodeSeek RSS 环**独立**（不改 `nodeseek_rss`），工具包：`tools/lowendtalk/`。

## 固定四方向（跨渠道）

| 方向 | 性质 | LET 落点（与 NS 同一套主题） |
|------|------|------------------------------|
| 线路机 routing | 长期 | `docs/learning/routing/`；L3 → `raw/lowendtalk/<id>/` |
| IP质量 ip-quality | 长期 | `docs/learning/ip-quality/`；同上 |
| 建站机 hosting | 长期 | `docs/learning/hosting/`；同上 |
| 优惠推广抢购交易溢价 | 短期 | `promos/lowendtalk/`（按日 + `index.csv`）；打时间窗，不当三长期基准 |

漏斗规则见 [FUNNEL.md](FUNNEL.md)（跨渠道框架；`channel=nodeseek|lowendtalk`）。

## 双轨（实现分轨，主题不另起一套）

1. **学习轨** — 三长期；高价值原文：`raw/lowendtalk/<discussion-id>/`。
2. **优惠推广轨** — 短期方向 → `promos/lowendtalk/`。字段：URL、日期、vendor/title、价格时间窗、地点、一句话摘要、confidence。短摘要，不整帖搬运。

## 分类默认

见 `tools/lowendtalk/categories.yml`：offers / shared-hosting-offers / giveaways → promo（短期）；reviews → learning（三长期）；outages/news → learning_risk；providers/general → mixed。

## 抓取现实

| 方式 | 状态 |
|------|------|
| 分类页 HTML + curl | 本环境实测常 200 |
| WebFetch / 部分机房出口 | 可能被 CF 摘要页或 403 |
| `categories/*/feed.rss` | **不可依赖**（易被拦）；主路径用分类 HTML |

挡了就用 `--html` 离线文件，或 `LET_COOKIE_JAR` 只读 cookie。解析器可用 `tools/lowendtalk/fixtures/` 验证。

## 建议例程（草稿，由父代理决定是否建）

- 频率：每天 1–2 次即可（Offers 更新快；学习价值密度因帖而异，主题仍按四方向筛）。
- 动作：`discover_category --category offers --limit 40 --write-promo 15`；再抽 `reviews` / `outages` 做学习轨。
- 不与 NodeSeek 五档深读抢同一例程配额；**主题词与升降档标准与 FUNNEL 一致**。

## 流水线位置

见 [PIPELINE.md](PIPELINE.md)。仓库根 README 已列 `tools/lowendtalk/`。

## 试点备注（2026-10-21）

- 计划与跑次见 vps-intel [`docs/LOWENDTALK-PILOT.md`](https://github.com/poovabgh/vps-intel/blob/main/docs/LOWENDTALK-PILOT.md)。
- 短投诉 / outages 常停在漏斗 L2：学习轨可用 `ingest_discussion --write-raw --force-raw` 强制归档。

