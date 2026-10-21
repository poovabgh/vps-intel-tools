"""python -m lowendtalk <cmd> …"""
from __future__ import annotations

import sys


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(
            "Usage:\n"
            "  PYTHONPATH=tools python3 -m lowendtalk discover_category --category offers --limit 30\n"
            "  PYTHONPATH=tools python3 -m lowendtalk ingest_discussion --url https://lowendtalk.com/discussion/…\n"
            "  PYTHONPATH=tools python3 -m lowendtalk discover_category --html tools/lowendtalk/fixtures/offers_p1.html --write-promo 5 --sample\n"
        )
        return 0
    cmd = sys.argv[1]
    rest = sys.argv[2:]
    if cmd in ("discover_category", "discover"):
        from lowendtalk.discover_category import main as m
        return m(rest)
    if cmd in ("ingest_discussion", "ingest"):
        from lowendtalk.ingest_discussion import main as m
        return m(rest)
    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
