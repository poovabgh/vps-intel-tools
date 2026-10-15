# 日程

## 脚本（不耗 token）

- 每 5 分钟：RSS → 去重 → 关键词筛 → 追加当前 BJT 时段桶文件（见 `docs/PIPELINE.md`）。

## AI 例程（到点读桶）

北京时间：08 / 12 / 16 / 20 / 00  
只读已关闭窗对应文件 → **三层漏斗深读**（[FUNNEL.md](../docs/FUNNEL.md)、[ROUTINE_DEEP_INGEST.md](../docs/ROUTINE_DEEP_INGEST.md)）→ 入库 → 删文件。

- L3 才多页（≤3）并写入 `vps-intel/raw/nodeseek/`。  
- SUMMARY 必含消耗统计 + funnel 计数。

例程未挂载前，可手动触发同一逻辑。

观测主题（漏斗 L2）：除 CN2/软银/家宽等外，**IX/伪IEPL/前置+落地 DIY** 也长期关注（见 `docs/FUNNEL.md`、`funnel.yml`）。
