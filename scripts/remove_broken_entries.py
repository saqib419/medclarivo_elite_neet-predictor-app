#!/usr/bin/env python3
"""
remove_broken_entries.py

Deletes specific college entries by EXACT name from data.json. Used to
clean up corrupted entries where an earlier parser run truncated several
different colleges' names down to the same short acronym (e.g. "AIIMS",
"ESIC"), causing their data to collide and overwrite each other under one
fake combined record — while the real, correctly-named per-campus entries
(e.g. "AIIMS, New Delhi", "AIIMS Bathinda") were unaffected and stay as-is.

USAGE
  python remove_broken_entries.py --data public/data.json
"""

import argparse
import json
import sys
from pathlib import Path

# Exact names to remove. Add more here if you find other broken
# collapsed-acronym entries later.
BROKEN_NAMES = {"AIIMS", "ESIC"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="public/data.json")
    args = ap.parse_args()

    data_path = Path(args.data)
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)

    colleges = data.get("colleges", [])
    before = len(colleges)
    removed = [c["name"] for c in colleges if c["name"] in BROKEN_NAMES]
    data["colleges"] = [c for c in colleges if c["name"] not in BROKEN_NAMES]
    after = len(data["colleges"])

    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Removed {before - after} broken entries: {removed}", file=sys.stderr)
    print(f"Colleges: {before} -> {after}", file=sys.stderr)


if __name__ == "__main__":
    main()
