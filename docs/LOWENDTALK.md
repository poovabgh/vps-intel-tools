# LowEndTalk 接入说明

与 NodeSeek RSS 环**独立**：不改 `nodeseek_rss`。  
工具包：`tools/lowendtalk/`。证据与优惠落在 [vps-intel](https://github.com/poovabgh/vps-intel)。

## 双轨

1. **学习轨** — 主题与 [FUNNEL.md](FUNNEL.md) 长期三话题一致（线路机 / IP质量 / 建站机）。高价值原文：`raw/lowendtalk/<discussion-id>/`。
2. **优惠推广轨** — Offers 等 → `promos/lowendtalk/`（按日目录 + `index.csv`）。字段：URL、日期、vendor/title、价格时间窗、地点、一句话摘要、confidence。短摘要，不整帖搬运。

## 分类默认

见 `tools/lowendtalk/categories.yml`：offers / shared-hosting-offers / giveaways → promo；reviews → learning；outages/news → learning_risk；providers/general → mixed。

## 抓取现实

| 方式 | 状态 |
|------|------|
| 分类页 HTML + curl | 本环境实测常 200 |
| WebFetch / 部分机房出口 | 可能被 CF 摘要页或 403 |
| `categories/*/feed.rss` | **不可依赖**（易被拦）；主路径用分类 HTML |

挡了就用 `--html` 离线文件，或 `LET_COOKIE_JAR` 只读 cookie。解析器可用 `tools/lowendtalk/fixtures/` 验证。

## 建议例程（草稿，由父代理决定是否建）

- 频率：每天 1–2 次即可（Offers 更新快但学习价值密度低于 NodeSeek 中文线路帖）。
- 动作：`discover_category --category offers --limit 40 --write-promo 15`；再抽 `reviews` / `outages` 做学习轨。
- 不与 NodeSeek 五档深读抢同一例程配额。

## 流水线位置

见 [PIPELINE.md](PIPELINE.md) 处理节末尾链接。仓库根 README 已列 `tools/lowendtalk/`。
