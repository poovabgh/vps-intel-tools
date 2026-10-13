# NodeSeek 官方 RSS → BJT 时段桶

**日常主发现**：每 5 分钟拉 `https://rss.nodeseek.com/`，按 `post_id` 去重，用 `tools/nodeseek_tg_index/keywords.yml` + `classify_index` 做关键词筛选，**只把 keep=Y** 追加进当前北京时间时段 CSV。AI **不参与**采集。

约定见 [docs/PIPELINE.md](../../docs/PIPELINE.md)。电报索引脚本仅作漏帖兜底，日常可不跑。

## 时段文件（`queue/buckets/`）

| BJT 发现窗 | 文件名 |
|------------|--------|
| 00:00–08:00 | `{YYYYMMDD}0008.csv` |
| 08:00–12:00 | `{YYYYMMDD}0812.csv` |
| 12:00–16:00 | `{YYYYMMDD}1216.csv` |
| 16:00–20:00 | `{YYYYMMDD}1620.csv` |
| 20:00–次日00:00 | `{YYYYMMDD}2000.csv`（日期=起点日） |

列：`post_id,url,title,pub_date_utc,category,creator,snippet,discovered_at_bjt,matched_keywords,server_score,category_tags`

`state/seen_post_ids.txt`：feed 里出现过的 id 一律记入（含噪声），避免反复重评；最多保留最近约 5000 条。

## 用法

```bash
# 单轮
python3 tools/nodeseek_rss/fetch_rss_buckets.py

# 后台每 5 分钟（推荐）
nohup tools/nodeseek_rss/run_loop.sh >/dev/null 2>&1 &
# 日志：state/rss_loop.log ；PID：state/rss_loop.pid
```

环境变量：`RSS_INTERVAL_SEC`（默认 300）、`PYTHON`。

到点分析由 bot 例程读已关闭桶文件完成；入库后应删除对应桶文件。
