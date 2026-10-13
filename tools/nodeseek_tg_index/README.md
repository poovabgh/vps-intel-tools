# NodeSeek 官方电报频道索引 + 关键词路由

> **Canonical:** [poovabgh/vps-intel-tools](https://github.com/poovabgh/vps-intel-tools) `tools/nodeseek_tg_index/`. Evidence → [vps-intel](https://github.com/poovabgh/vps-intel). Pipeline → [docs/PIPELINE.md](../../docs/PIPELINE.md).


## 双层设计

详见 [KEYWORD_ROUTER.md](./KEYWORD_ROUTER.md)。

1. **采集** `fetch_tg_index.py` → 标题 / 时间 / 论坛链接  
2. **路由** `classify_index.py` + `keywords.yml` → 是否服务器相关、分类标签  

深读跟帖与写入 evidence **不在本工具内**。

## 采集

```bash
python3 tools/nodeseek_tg_index/fetch_tg_index.py --pages 5 \
  --out /workspace/vps-intel-review/tg-index-trial-YYYY-MM-DD

python3 tools/nodeseek_tg_index/fetch_tg_index.py --pages 50 \
  --out /workspace/vps-intel-review/tg-index-backfill-YYYY-MM-DD

python3 tools/nodeseek_tg_index/fetch_tg_index.py --pages 20 --before 941500 \
  --out /workspace/vps-intel-review/tg-index-cont
```

页间默认等待约 1.5–2.5 秒。

## 分类

```bash
python3 tools/nodeseek_tg_index/classify_index.py \
  --index /workspace/vps-intel-review/tg-index-backfill-2026-10-12/index.csv \
  --keywords tools/nodeseek_tg_index/keywords.yml \
  --out /workspace/vps-intel-review/tg-index-backfill-2026-10-12/index_classified.csv
```

依赖：系统包 `python3-yaml`（`apt install python3-yaml`）。

## 目录

| 路径 | 含义 |
|------|------|
| `fetch_tg_index.py` | 第一层采集 |
| `classify_index.py` | 第二层关键词分类 |
| `keywords.yml` | 重点词 / 常规词 / 噪声词 |
| `KEYWORD_ROUTER.md` | 双层说明（白话） |
| `keyword_rounds/` | 10 轮标题核对笔记 |
| `samples/` | 分类结果小样本（大 CSV 在 review 目录） |

## 注意

- 公开预览约 20 条/页；翻页 `?before=<消息id>`。
- 频道可能漏贴或慢于论坛；索引只做发现源。

## 品牌分层（词库）

- `priority.brands`：重点观测
- `general.brands`：通用名单（keep + `catalog:general`）
- 光帆 → `brand:aws`（Lightsail）

详见仓库根目录 `docs/brands-priority.md` / `docs/brands-general.md`。
