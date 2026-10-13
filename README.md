# vps-intel-tools

Collectors and classifiers for **[poovabgh/vps-intel](https://github.com/poovabgh/vps-intel)**  
NodeSeek：**电报/RSS 发现 → 关键词分类 → 延迟深读 →（再）写入证据库**

本仓只管脚本、词库、队列与日程；**证据文档只进 vps-intel**。

---

## 你提出的两种设计

### A）官方 RSS 持续抓 + 北京时间定点处理

- 发现：官方 RSS 滚动新帖 + 关键词筛选。  
- 处理：每天 BJT **08 / 12 / 16 / 20 / 00（24点）**；例如 **12 点处理 00–08 发现的帖**，**16 点处理 08–12**，以此类推——窗末到处理约 **4 小时**，跟帖更成熟。

### B）同一钟点，TG 从上一轮游标拉到最新 → 关键词筛选后立刻深读入库

- 发现：电报频道增量（可翻历史）。  
- 处理：筛完马上深读并写入 vps-intel。

---

## 推荐（长期成熟方案）：**Hybrid — 不要单独用 A 或单独用 B**

| | A 单独 | B 单独 | **Hybrid** |
|--|--------|--------|------------|
| 发现完整性 | RSS≈20 条窗，易漏 | TG 游标强 | **TG 主 + RSS 辅** |
| 跟帖成熟度 | 延迟窗好 | 新帖常 0 回复 | **沿用 A 的 4h 延迟槽** |
| 可恢复/补历史 | 弱 | 强 | **强（TG `?before=`）** |
| 证据质量 | 较好但易漏帖 | 发现全但证据薄 | **全发现 + 成熟后再读** |

### 推荐流水线（三步）

1. **Discover（每 5 分钟，纯脚本）**  
   官方 RSS → 关键词筛选 → 追加 `queue/buckets/{YYYYMMDD}….csv`（见 `docs/PIPELINE.md`）。**此刻不深读、不耗模型。** 电报索引仅作漏帖兜底。

2. **Process（BJT 五个槽）**  
   只处理「上一关闭发现窗」里的 keep（见下表）。论坛 **首页** 深读；高信号可自动 commit 到 vps-intel；纯收售/券 → 核对文件或带时间窗的 soft-ingest。

3. **State**  
   `state/`（gitignore）：游标、`processed_post_ids`、`failed_404`。证据正文永不进本仓。

### BJT 槽位映射（与约定一致）

| BJT 执行时刻 | 处理 discovered_at ∈ |
|--------------|----------------------|
| **08:00** | **20:00–00:00**（前一晚） |
| **12:00** | **00:00–08:00** |
| **16:00** | **08:00–12:00** |
| **20:00** | **12:00–16:00** |
| **00:00** | **16:00–20:00** |

例：08:00–12:00 发现的帖，在 **16:00** 才深读 → 最短约 4h 评论窗口。

完整论证见 **[docs/PIPELINE.md](docs/PIPELINE.md)**；cron 草案见 **[schedules/README.md](schedules/README.md)**。

---

## 仓库结构

```
tools/nodeseek_tg_index/   # TG 索引采集 + 关键词路由（已迁入）
tools/nodeseek_rss/        # 官方 RSS → BJT 时段桶（日常主发现）
schedules/                 # BJT cron 说明
docs/PIPELINE.md           # 混合流水线定稿
state/  queue/             # 运行时（gitignore）
```

### 现成用法（TG）

```bash
python3 tools/nodeseek_tg_index/fetch_tg_index.py --pages 5 --out /tmp/tg-index
python3 tools/nodeseek_tg_index/classify_index.py \
  --index /tmp/tg-index/index.csv \
  --keywords tools/nodeseek_tg_index/keywords.yml \
  --out /tmp/tg-index
```

详见 [tools/nodeseek_tg_index/README.md](tools/nodeseek_tg_index/README.md)。

---

## 与 vps-intel 的分工

| 仓库 | 职责 |
|------|------|
| **vps-intel-tools**（本仓） | 采集、分类、词库、日程、队列状态 |
| **[vps-intel](https://github.com/poovabgh/vps-intel)** | 品牌页、证据、学习库、重点/通用名单 |
| vps-watchlist | 关注表；不接入本流水线 |

`vps-intel/tools/nodeseek_tg_index/` 仍保留副本并指向本仓；**以本仓为 canonical**。

---

## 尚未做（需你确认后再上）

- Grok Bot / Actions 定时例程  
- `process_queue_window.py`（按槽深读）  
- RSS 轮询实现  

当前提交只完成：**建仓、迁脚本、定稿混合日更设计**。
