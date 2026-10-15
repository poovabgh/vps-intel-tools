# 例程约定：NodeSeek 时段桶深读入库

AI 例程到点只做这些事；**不管** 5 分钟 RSS 采集。

## 触发（北京时间）

| BJT | 读桶 |
|-----|------|
| 08:00 | `…2000` |
| 12:00 | `…0008` |
| 16:00 | `…0812` |
| 20:00 | `…1216` |
| 00:00 | `…1620` |

桶路径：`/workspace/vps-intel-tools/queue/buckets/`。无文件则跳过并记 SUMMARY。

## 必做步骤

1. 复制/读取桶 CSV → 核对目录 ` /workspace/vps-intel-review/rss-deep-YYYY-MM-DD-HHMM/`。
2. 按 **三层漏斗**（[FUNNEL.md](FUNNEL.md)）深读：
   - 默认第 1 页；**仅 L3** 再抓最多到第 3 页并写入 `vps-intel/raw/nodeseek/<id>/`。
   - 短证据照常入库；L3 另写 `*-thread.md`，不毁旧摘要。
3. 推荐调用：

```bash
cd /workspace/vps-intel-tools
PYTHONPATH=tools python3 -m nodeseek_deep.run_bucket_deep_ingest \
  --bucket <桶csv> --out <核对目录> --repo /workspace/vps-intel \
  --ingest-tag 'rss-bucket-deep-read …; funnel'
```

   完整品牌 CSV / 交叉引用若仍用历史 `run_deep_ingest.py`，须在其后再跑漏斗归档，或把漏斗逻辑并进同一轮；**不得**只短截评、假装已 L3。
4. 写 `SUMMARY.md` + `cost_stats.json`：消耗栏 + **funnel 统计**（l1/l2/l3、多页帖数、raw 归档字节）。平台 token 填「未接入」。
5. `git` 提交并推送 **vps-intel**；删已处理桶文件。
6. **不向用户主动发聊天**；结果留在核对目录 / 仓库。

## 禁止

- 登录、发帖、改帖。
- 交易帖无线路密度时升 L3。
- 把完整 HTML 只留在核对 `raw/` 却声称「已长期归档」（L3 必须进 `vps-intel/raw/nodeseek/`）。

## 观测主题提醒

L2 线路主题含 CN2/软银/家宽等，以及 **IX/伪IEPL/前置+落地 DIY**（见 FUNNEL.md）。
