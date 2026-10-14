# nodeseek_deep — 三层漏斗深读

NodeSeek 论坛深读与 L3 原文归档。无登录、curl SSR only。

## 漏斗（详见 [docs/FUNNEL.md](../../docs/FUNNEL.md)）

| 层 | 含义 | 动作 |
|----|------|------|
| **L1** | 服务器相关（RSS keep） | 抓第 1 页；噪音跳过；可入库短证据 |
| **L2** | 近期线路学习主题 | 升档关注正文/评论密度 |
| **L3** | 高价值观点/测速/路由讨论 | 最多 3 页评论；完整正文；`raw/nodeseek/<id>/` + `thread.json` + `*-thread.md` |

交易帖默认可 L1，不轻易 L3。

## 例程怎么调用

到点读已关闭时段桶后：

```bash
cd /workspace/vps-intel-tools
PYTHONPATH=tools python3 -m nodeseek_deep.run_bucket_deep_ingest \
  --bucket /workspace/vps-intel-tools/queue/buckets/YYYYMMDDHHmm.csv \
  --out /workspace/vps-intel-review/rss-deep-YYYY-MM-DD-HHMM \
  --repo /workspace/vps-intel \
  --ingest-tag 'rss-bucket-deep-read YYYY-MM-DD-HHMM; funnel'
```

SUMMARY / `cost_stats.json` 会含 funnel：`l1` / `l2` / `l3`、多页抓取数、仓库 raw 归档字节。

按帖补归档（样例回填）：

```bash
PYTHONPATH=tools python3 -m nodeseek_deep.archive_posts \
  981768 981828 981812 981058 \
  --repo /workspace/vps-intel
```

## 模块

| 文件 | 作用 |
|------|------|
| `funnel.yml` / `funnel_rules.py` | L2 主题词、L3 密度词、升降档 |
| `fetch_thread.py` | `post-{id}-{page}` 多页拉取 |
| `parse_thread.py` | OP 全文 + 评论全文（BeautifulSoup） |
| `archive.py` | L3 写入 evidence / raw / notes |
| `run_bucket_deep_ingest.py` | 桶深读骨架 |
| `archive_posts.py` | 按 pid 样例归档 |

## 存储路径（vps-intel）

- `brands/<slug>/evidence/<date>-…-thread.md` — 全文旁路（不毁旧摘要）
- `raw/nodeseek/<post_id>/page-1.html` … `page-N.html`
- `raw/nodeseek/<post_id>/thread.json`
- `docs/learning/routing/notes/<date>-ns-<id>-judgment.md` — 短判断（有线路观点时）
