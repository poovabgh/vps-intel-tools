# lowendtalk — LowEndTalk 渠道采集

[LowEndTalk](https://lowendtalk.com/)（Vanilla 论坛）采集脚手架。

**主题 = 全仓固定四方向**（与 NodeSeek 相同，不是 LET 另起一套）：

- **长期三**：线路机 / IP质量 / 建站机 → 学习轨  
- **短期一**：优惠推广抢购交易溢价 → 优惠轨  

渠道只决定发现方式与落盘路径（`raw/lowendtalk/`、`promos/lowendtalk/`）。漏斗见 [docs/FUNNEL.md](../../docs/FUNNEL.md)。

## 双轨（实现分轨 = 四方向里的长期 vs 短期）

| 轨 | 对应方向 | 进哪 |
|----|----------|------|
| **学习** | 三长期 | `brands/` 或 `docs/learning/{routing,ip-quality,hosting}/`；L3 → `raw/lowendtalk/<id>/` |
| **优惠推广** | 短期 | `vps-intel/promos/lowendtalk/` — Offers / Giveaways / 转让等；短摘要+链接+时间窗 |

分类默认轨道见 [`categories.yml`](categories.yml)。`mixed` 类（providers/general）看标题+正文再判（仍落在四方向内）。

## Cloudflare / RSS

- **分类 HTML**：本机 `curl` 多数时候可用（实测 200）。
- **RSS**（`…/feed.rss`）：部分抓取出口会被 CF 拦；**不要依赖 RSS** 做主发现。
- 若遇到 **CF challenge / 403**：
  1. 浏览器打开页面 → 导出 HTML，用 `--html` 离线解析；或
  2. 把 clearance cookie 存进 jar，设环境变量 `LET_COOKIE_JAR=/path/to/cookies.txt` 再 curl。
- 仓库内 [`fixtures/`](fixtures/) 有精简样本，供无网/被挡时验证解析器。

**禁止**：发帖、登录改内容；只读采集。

## 怎么跑

```bash
cd /workspace/vps-intel-tools
PYTHONPATH=tools python3 -m lowendtalk help

# 拉 Offers 列表（在线）→ 短期方向
PYTHONPATH=tools python3 -m lowendtalk discover_category --category offers --limit 30

# 离线样本 + 写入 5 条 promo（标记 sample）
PYTHONPATH=tools python3 -m lowendtalk discover_category \
  --category offers \
  --html tools/lowendtalk/fixtures/offers_p1.html \
  --write-promo 5 --sample \
  --repo /workspace/vps-intel

# 单帖（学习轨或短期，由路由按四方向判定）
PYTHONPATH=tools python3 -m lowendtalk ingest_discussion \
  --url 'https://lowendtalk.com/discussion/220866/…' \
  --repo /workspace/vps-intel
```

依赖：`beautifulsoup4`、`PyYAML`（与 nodeseek_deep 相同）。系统需有 `curl`。

## 模块

| 文件 | 作用 |
|------|------|
| `categories.yml` | 分类 → promo（短期）/ learning（三长期）/ mixed |
| `let_funnel.yml` | L2/L3 主题词（**同一固定四方向**；词表可英中混排） |
| `fetch.py` | curl / 本地 HTML；识别 CF challenge |
| `parse.py` | 分类列表 + 单帖（Vanilla `ItemDiscussion`） |
| `route.py` | 双轨路由（长期 vs 短期）+ 学习漏斗 |
| `promo_write.py` | 写 `promos/lowendtalk/<date>/` + `index.csv` |
| `discover_category.py` / `ingest_discussion.py` | CLI |

文档：[docs/LOWENDTALK.md](../../docs/LOWENDTALK.md)。
