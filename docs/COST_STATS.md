# 深读轮次消耗统计约定

目标：每轮核对 `SUMMARY.md` 有可比的「消耗」栏，方便问「这一档重不重」。

## 能自动记的

- 队列条数、主证据数、`raw/` HTML 体积、`_parsed.json` 体积、脚本墙钟

采集脚本（5 分钟 RSS）**不**记模型消耗。

## 不能自动记的

- 平台 input/output token、额度余额、美元费用  
  原因：Grok Bot 没有按次用量 API；[Usage](settings) 是账户总览，拆不出某一档例程。

例程结束后若用户贴了 Usage 截图或数字，可手工补一行 `平台备注`，仍不要虚构 token。

## 与漏斗一起记

- `l1` / `l2` / `l3` 计数、多页抓取帖数、`raw/nodeseek` 归档字节（见 FUNNEL.md）
