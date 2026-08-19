"""
Human-assisted matching pass for colleges still showing totalSeats=None.

Unlike the earlier fully-automated merge scripts, this tool does NOT
apply anything by itself. For each unmatched college, it shows the
top 3 candidate matches (by name similarity) from the official NMC
source, with scores, so a human can quickly say yes/no per row rather
than trusting an automated threshold -- which we've now seen produce
real false positives (GSVM/Hapur, Malla Reddy, DY Patil, Sri
Siddhartha) even at seemingly solid scores.

Output: a review file (unmatched_candidates.txt) you can scan quickly
-- most rows will have an obvious right answer, some will have no
good candidate at all (genuinely needs manual research or isn't in
this source), and a few will be genuinely ambiguous.

After reviewing, tell me which candidate numbers to accept (e.g.
"1:A, 2:none, 3:B, 4:A...") and I'll write a small apply script for
just those confirmed ones -- same safe pattern as everything else in
this project.

Usage:
    python3 review_unmatched.py
"""

import json
import re
import difflib
from collections import defaultdict

STOPWORDS = {
    "government", "medical", "college", "institute", "hospital", "of",
    "and", "sciences", "research", "centre", "center", "the", "for",
    "govt", "science", "institution", "dist", "district", "state",
    "new", "national", "university", "regional", "instt", "medicine"
}

def normalize(name):
    name = name.lower()
    name = re.sub(r"\(.*?\)", "", name)
    name = re.sub(r"[.,\-&]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name

def distinctive_tokens(name):
    norm = normalize(name)
    return set(t for t in norm.split() if t not in STOPWORDS)

def score_pair(name_a, name_b):
    tok_a = distinctive_tokens(name_a)
    tok_b = distinctive_tokens(name_b)
    if not tok_a or not tok_b:
        return 0
    overlap = len(tok_a & tok_b)
    if overlap == 0:
        return 0
    union = len(tok_a | tok_b)
    jaccard = overlap / union
    char_score = difflib.SequenceMatcher(None, normalize(name_a), normalize(name_b)).ratio()
    return jaccard * 0.7 + char_score * 0.3

def normalize_state(state):
    if not state:
        return ""
    s = state.lower().strip().replace("&", "and")
    aliases = {"orissa": "odisha", "pondicherry": "puducherry", "uttaranchal": "uttarakhand"}
    return aliases.get(s, s)

with open("public/data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

with open("nmc_total_seats_clean.json", "r", encoding="utf-8") as f:
    official = json.load(f)

official_by_state = defaultdict(list)
for name, entry in official.items():
    st = normalize_state(entry.get("state", ""))
    official_by_state[st].append((name, entry))

unmatched = [c for c in data["colleges"] if c.get("totalSeats") is None]
print(f"{len(unmatched)} colleges with no totalSeats\n")

lines = []
count_with_candidates = 0

for i, college in enumerate(unmatched, 1):
    name = college.get("name", "")
    state = normalize_state(college.get("state", ""))
    candidates = official_by_state.get(state, [])

    scored = []
    for oname, entry in candidates:
        s = score_pair(name, oname)
        if s > 0.3:
            scored.append((s, oname, entry))
    scored.sort(key=lambda x: -x[0])
    top3 = scored[:3]

    block = [f"\n[{i}] {name}  (state: {college.get('state')}, category: {college.get('category')})"]
    if top3:
        count_with_candidates += 1
        for letter, (s, oname, entry) in zip("ABC", top3):
            block.append(f"    {letter} ({s:.3f}): {oname}  -> totalSeats={entry.get('totalSeats')}, mgmt={entry.get('mgmt')}")
    else:
        block.append("    (no candidate above threshold)")
    lines.append("\n".join(block))

output = "\n".join(lines)
with open("unmatched_candidates.txt", "w", encoding="utf-8") as f:
    f.write(output)

print(f"{count_with_candidates} of {len(unmatched)} have at least one candidate match")
print(f"Wrote full list to unmatched_candidates.txt")
print(f"\n=== FIRST 15 FOR PREVIEW ===")
print("\n".join(lines[:15]))
