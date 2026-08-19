"""
Inspect the 6 remaining high-confidence (score >= 0.9) duplicate-name
pairs found by find_duplicate_pairs.py, so we can see exactly what
data each side has before deciding how to merge them (unlike the
earlier 6 groups, these didn't show the clean "one has cutoffs, one
has seats" gap -- so we need to look at the actual fields).

Usage:
    python3 inspect_remaining_pairs.py
"""

import json

PAIRS = [
    ("Zoram Medical College, Falkawn", "ZORAM MEDICAL COLLEGE Falkawn"),
    ("ESI-MC&PGIMS&R", "ESI- MC&PGIMS& R"),
    ("GOVERNMENT MEDICAL COLLEGE AND GENERAL HOSPITAL", "Government Medical College and District General Hospital"),
    ("Agartala Government Medical College", "AGARTALA GOVT. MEDICAL COLLEGE"),
    ("Patna Medical College, Patna", "PATNA MEDICAL COLLEGE"),
    ("Government Medical College and Hospital, Chandigarh", "Government Medical College, Chandigarh"),
]

with open("public/data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

by_name = {c.get("name"): c for c in data["colleges"]}

for name_a, name_b in PAIRS:
    a = by_name.get(name_a)
    b = by_name.get(name_b)
    print(f"\n{'='*80}")
    print(f"PAIR: {name_a}  <-->  {name_b}")
    for label, c in [("A", a), ("B", b)]:
        if not c:
            print(f"  {label}: NOT FOUND")
            continue
        print(f"  {label}: {c.get('name')}")
        print(f"     state={c.get('state')}  quota={c.get('quota')}  category={c.get('category')}")
        print(f"     totalSeats={c.get('totalSeats')}  cutoffs={'yes' if c.get('cutoffs') else 'no'}"
              f"  cutoffTrends_len={len(c.get('cutoffTrends') or [])}")
