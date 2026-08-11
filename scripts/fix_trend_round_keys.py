#!/usr/bin/env python3
"""
fix_trend_round_keys.py

One-off fix: earlier cutoffTrends entries got written with keys like
"round3" (matching whichever actual counselling round the source PDF
was), but the UI only ever reads "round1" and "round2" from each entry.
This moves any non-standard round key's value into round1 (or round2 if
round1 is already taken), then removes the original key.

USAGE
  python fix_trend_round_keys.py --data public/data.json
"""

import argparse
import json
import sys
from pathlib import Path

DISPLAY_KEYS = {"round1", "round2"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="public/data.json")
    args = ap.parse_args()

    data_path = Path(args.data)
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)

    fixed = 0
    for college in data.get("colleges", []):
        for entry in college.get("cutoffTrends", []):
            stray_keys = [k for k in list(entry.keys()) if k not in DISPLAY_KEYS and k != "year"]
            for k in stray_keys:
                value = entry.pop(k)
                if entry.get("round1") is None:
                    entry["round1"] = value
                elif entry.get("round2") is None:
                    entry["round2"] = value
                # else: both slots full, drop the stray value — shouldn't
                # normally happen, but don't crash on it.
                fixed += 1

    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Fixed {fixed} stray round-key entries in {data_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
