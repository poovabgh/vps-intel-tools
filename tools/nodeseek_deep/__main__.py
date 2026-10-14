"""python -m nodeseek_deep …"""
from __future__ import annotations

import sys


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "Usage:\n"
            "  python3 -m nodeseek_deep.archive_posts <pid>…\n"
            "  python3 -m nodeseek_deep.run_bucket_deep_ingest --bucket … --out …\n"
        )
        return 2
    cmd = sys.argv[1]
    rest = sys.argv[2:]
    if cmd in ("archive_posts", "archive"):
        from nodeseek_deep.archive_posts import main as m
        return m(rest)
    if cmd in ("run_bucket", "ingest", "run_bucket_deep_ingest"):
        from nodeseek_deep.run_bucket_deep_ingest import main as m
        return m(rest)
    print(f"unknown command: {cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
