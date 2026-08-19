"""
Systematically scan data.json for likely duplicate-row pairs -- the
same real college represented as two separate entries with
complementary data (like the SKIMS / Sher-I-Kashmir case: one row had
real cutoffs but no seats, the other had seats but no cutoffs).

Approach:
  1. Group colleges by state (comparing only within the same state
     keeps this fast and avoids absurd cross-state false positives).
  2. For each pair within a state, score name similarity using the
     same distinctive-token + char-similarity approach used in the
     NMC merge scripts.
  3. Flag high-scoring pairs, and separately note which ones show the
     "complementary data" pattern (one has cutoffs, the other has
     seats/category) -- that pattern is strong secondary evidence of
     a genuine duplicate, since real distinct colleges essentially
     never have BOTH a very similar name AND perfectly complementary
     missing fields.

This is a DETECTION tool only -- it does not merge or delete
anything. Review the output and merge confirmed pairs by hand (or
ask for a merge script) the same way we did for SKIMS.

Usage:
    python3 find_duplicate_pairs.py
    python3 find_duplicate_pairs.py --threshold 0.5
"""

import json
import re
import sys
import argparse
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
        return 0, 0
    overlap = len(tok_a & tok_b)
    union = len(tok_a | tok_b)
    jaccard = overlap / union if union else 0
    char_score = difflib.SequenceMatcher(None, normalize(name_a), normalize(name_b)).ratio()
    combined = jaccard * 0.7 + char_score * 0.3
    return combined, overlap

def has_complementary_gap(a, b):
    """True if one college has cutoffs but not seats, and the other
    has seats but not cutoffs -- the exact pattern that flagged
    SKIMS/Sher-I-Kashmir as a real duplicate."""
    a_has_cutoffs = bool(a.get("cutoffs"))
    a_has_seats = a.get("totalSeats") is not None
    b_has_cutoffs = bool(b.get("cutoffs"))
    b_has_seats = b.get("totalSeats") is not None

    pattern1 = a_has_cutoffs and not a_has_seats and b_has_seats and not b_has_cutoffs
    pattern2 = b_has_cutoffs and not b_has_seats and a_has_seats and not a_has_cutoffs
    return pattern1 or pattern2

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="public/data.json")
    parser.add_argument("--threshold", type=float, default=0.45)
    args = parser.parse_args()

    with open(args.data, "r", encoding="utf-8") as f:
        data = json.load(f)

    colleges = data.get("colleges", [])
    by_state = defaultdict(list)
    for c in colleges:
        state = c.get("state") or "UNKNOWN"
        by_state[state].append(c)

    strong_candidates = []   # high score + complementary data gap
    other_candidates = []    # high score but no clear complementary pattern

    for state, group in by_state.items():
        n = len(group)
        for i in range(n):
            for j in range(i + 1, n):
                a, b = group[i], group[j]
                if a.get("name") == b.get("name"):
                    continue  # exact-name dupes are a different, simpler bug -- not handled here
                score, overlap = score_pair(a.get("name", ""), b.get("name", ""))
                if score >= args.threshold and overlap > 0:
                    gap = has_complementary_gap(a, b)
                    entry = (score, state, a, b, gap)
                    if gap:
                        strong_candidates.append(entry)
                    else:
                        other_candidates.append(entry)

    strong_candidates.sort(key=lambda x: -x[0])
    other_candidates.sort(key=lambda x: -x[0])

    print(f"\n=== STRONG CANDIDATES (name match + complementary data gap) ===")
    print(f"{len(strong_candidates)} found -- these look like SKIMS-style true duplicates\n")
    for score, state, a, b, gap in strong_candidates:
        print(f"[{state}] score {score:.3f}")
        print(f"  A: {a['name']}")
        print(f"     cutoffs={'yes' if a.get('cutoffs') else 'no'}  totalSeats={a.get('totalSeats')}  quota={a.get('quota')}")
        print(f"  B: {b['name']}")
        print(f"     cutoffs={'yes' if b.get('cutoffs') else 'no'}  totalSeats={b.get('totalSeats')}  quota={b.get('quota')}")
        print()

    print(f"\n=== OTHER SIMILAR-NAME PAIRS (no clear complementary gap -- review manually) ===")
    print(f"{len(other_candidates)} found -- may be duplicates, may be genuinely different colleges\n")
    for score, state, a, b, gap in other_candidates[:40]:
        print(f"[{state}] score {score:.3f}:  {a['name']}  <-->  {b['name']}")

    if len(other_candidates) > 40:
        print(f"\n... and {len(other_candidates) - 40} more (raise --threshold to narrow, or ask to see the rest)")

if __name__ == "__main__":
    main()
