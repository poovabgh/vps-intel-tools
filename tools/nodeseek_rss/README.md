# NodeSeek 官方 RSS（预留）

官方 RSS 只保留约最近 **20** 条滚动窗口，适合做「最新信号」补充，**不能**单独承担长期发现。

## 计划职责

- 轮询 `https://rss.nodeseek.com/`（或站点公布的 feed URL）
- 记录 `last_rss_guid` / 已见链接到 `state/`
- 新条目写入队列（与 TG 发现共用同一 queue 格式），只做标题级关键词分类，**不做深读**

## 与 TG 的关系

| 来源 | 角色 |
|------|------|
| 电报频道 `t.me/s/nodeseekc` | **主发现**：可用 `?before=` 翻历史、增量游标稳定 |
| 官方 RSS | **辅发现**：补漏最新窗；任务宕机或突发 >20 条时会漏 |

实现脚本尚未迁入；当前深读流水线仍以 TG 索引为准。见仓库根 [README.md](../../README.md) 与 [docs/PIPELINE.md](../../docs/PIPELINE.md)。
