# 双层路由：电报索引 → 关键词筛服务器帖

## 两层分别干什么

### 第一层：采集（只做索引）
脚本 `fetch_tg_index.py` 从公开页 [t.me/s/nodeseekc](https://t.me/s/nodeseekc) 往回翻，写出标题、时间、论坛链接。  
**不**登录、**不**深读跟帖、**不**写入 brands/evidence。

输出目录示例：`/workspace/vps-intel-review/tg-index-backfill-YYYY-MM-DD/`  
主文件：`index.csv`（本轮约 1000 条连续消息）。

### 第二层：关键词路由（标题级，仍不深读）
脚本 `classify_index.py` + 词库 `keywords.yml`：

1. 读 `index.csv` 的标题和摘要  
2. 按词库打分、打标签  
3. 写出 `index_classified.csv`：`keep_server_y_n`、`category_tags`、`matched_keywords`、`classify_reason`  
4. **只有 `keep_server_y_n=Y` 的帖，才值得你再人工或模型深读**

## 词库怎么分

| 区块 | 含义 | 怎么用 |
|------|------|--------|
| **重点词** `priority` | 重点观测品牌、NQ/TQ、测试留档、快乐鸡、家宽、CN2 GIA… | 命中即倾向保留；深读优先 |
| **通用词** `general` | 通用名单品牌（次要） | 命中也会 keep，标签 `catalog:general`，不与重点混排 |
| **常规词** `regular` | VPS、服务器、NAT、小鸡、合租、线路、年付… | 权重累加，达到 `keep_threshold`（默认 2）才保留 |
| **噪声词** `noise` | GPT/Claude 账号、手表、社保、成品号… | 噪声强且服务器分不够 → 丢掉 |

细则：
- 同时命中重点词和噪声时：若重点分够高（约 ≥5）仍可保留（例如「家宽 VPS 能不能跑 Claude」）。
- 噪声分高、服务器分低：丢掉（例如「用 dmit 登 talkatone」这类以账号为主的帖，若品牌分不够会被盖掉）。

## 10 轮怎么优化的

把约 1000 条按时间切成 10 批（每批 100，从旧到新）。  
每轮：用当时词库自动分类 → **通读该批全部标题** → 记下漏掉（该留没留）和误留（不该留留下了）→ 改 `keywords.yml` → 写 `keyword_rounds/round-NN.md`。

定稿版本见 `keywords.yml` 的 `version` 字段（当前 v5）。

## 怎么跑

```bash
# 第一层（示例：50 页约 1000 条）
python3 tools/nodeseek_tg_index/fetch_tg_index.py --pages 50 \
  --out /workspace/vps-intel-review/tg-index-backfill-2026-10-12

# 第二层（全量）
python3 tools/nodeseek_tg_index/classify_index.py \
  --index /workspace/vps-intel-review/tg-index-backfill-2026-10-12/index.csv \
  --out /workspace/vps-intel-review/tg-index-backfill-2026-10-12/index_classified.csv

# 只跑某一批（1–10）
python3 tools/nodeseek_tg_index/classify_index.py --batch 10
```

## 注意

- 关键词只能做粗筛，商家黑话、无品牌收售贴仍可能漏；**重点商家**补 `priority.brands`，**次要商家**补 `general.brands`（见 `docs/brands-*.md`）。
- 「光帆」映射为 `brand:aws`（Lightsail），不要再用独立 `brand:guangfan`。
- 大体积 CSV 放在 `vps-intel-review/`，默认不进 git；仓库里只留工具、词库、轮次笔记和少量样本。
