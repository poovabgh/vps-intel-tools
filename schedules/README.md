# 定时任务（Asia/Shanghai / 北京时间）

本仓库只描述 cron 语义；Grok Bot / GitHub Actions 例程尚未创建，需用户确认后再挂。

时区一律 **`Asia/Shanghai`**（BJT，UTC+8）。

## 发现（Discover）— 频繁、只入队

建议每 **15–30 分钟**（或至少每小时）跑一次：

```cron
# 每 20 分钟：TG 增量 + 可选 RSS
*/20 * * * *  cd /path/to/vps-intel-tools && python3 tools/nodeseek_tg_index/fetch_tg_index.py --incremental … && python3 tools/nodeseek_tg_index/classify_index.py …
```

产出：`queue/` 里带 `discovered_at`、`keep`、`brand_tier` 的记录。**此时不深读、不写 vps-intel。**

## 深读处理（Process）— 五个 BJT 槽位

窗口结束后 **再隔约 4 小时** 才处理，让跟帖大致稳定：

| BJT 执行时刻 | 处理「发现时间」落在 |
|--------------|----------------------|
| **08:00** | 前一日 **20:00–00:00** |
| **12:00** | 当日 **00:00–08:00** |
| **16:00** | 当日 **08:00–12:00** |
| **20:00** | 当日 **12:00–16:00** |
| **00:00**（24 点） | 前一日 **16:00–20:00** |

```cron
0 8,12,16,20,0 * * *  cd /path/to/vps-intel-tools && python3 …/process_queue_window.py --slot …
```

（`process_queue_window.py` 尚未实现；语义见 [docs/PIPELINE.md](../docs/PIPELINE.md)。）

## 状态文件（gitignored）

| 文件 | 用途 |
|------|------|
| `state/last_tg_msg_id` | TG 增量游标 |
| `state/last_rss_guid` | RSS 游标 |
| `state/processed_post_ids` | 已深读帖号 |
| `state/failed_404` | 404 / 失败重试列表 |

证据正文只写入 [poovabgh/vps-intel](https://github.com/poovabgh/vps-intel)，不进本仓库。
