import json

with open("v7_nmc_missing_from_app.json") as f:
    missing = json.load(f)

print(f"Total entries in missing-colleges list: {len(missing)}")

names = [m["name"].strip() for m in missing]
seen = set()
dupes = []
for n in names:
    key = n.lower()
    if key in seen:
        dupes.append(n)
    seen.add(key)

print(f"Duplicate names within the missing-list itself: {len(dupes)}")
for d in dupes:
    print(f"  - {d}")
