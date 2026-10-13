#!/usr/bin/env bash
# 每 300s 跑一轮 RSS→时段桶；flock 防重叠。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
mkdir -p "$ROOT/queue/buckets" "$ROOT/state"
LOCK="$ROOT/state/rss_loop.lock"
PIDFILE="$ROOT/state/rss_loop.pid"
LOG="$ROOT/state/rss_loop.log"
INTERVAL="${RSS_INTERVAL_SEC:-300}"
PY="${PYTHON:-python3}"
SCRIPT="$ROOT/tools/nodeseek_rss/fetch_rss_buckets.py"

echo $$ > "$PIDFILE"
echo "$(date -Iseconds) loop start pid=$$ interval=${INTERVAL}s" >> "$LOG"

while true; do
  # 单轮采集互斥；循环本身不因单轮失败退出
  if flock -n "$LOCK" -c "$PY \"$SCRIPT\"" >>"$LOG" 2>&1; then
    :
  else
    echo "$(date -Iseconds) skip: previous fetch still holding lock" >> "$LOG"
  fi
  sleep "$INTERVAL"
done
