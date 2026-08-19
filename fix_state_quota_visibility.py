"""
Fix state-quota visibility for Government colleges that are wrongly
tagged quota="AIQ" only, when in reality they participate in BOTH
AIQ and their state's own counselling (so should show up in
state-quota predictions too).

IMPORTANT DATA-MODEL LIMITATION: this app stores one quota value per
college row, but reality has many Government colleges offering BOTH
AIQ (15%) and State quota (85%) seats simultaneously, often with
different cutoffs for each. This script does NOT attempt to build a
real dual-quota model or invent separate AIQ/State cutoff numbers --
it only flips the `quota` field to "State" for colleges verified to
run real state-level counselling, so they at least become VISIBLE in
state-quota predictions again (previously invisible). Their cutoffs/
seatMatrix fields are untouched.

Classification used (verified 2026-08-19):

  LEAVE AS AIQ (Institutes of National Importance -- no state quota,
  100% central MCC counselling only):
    - AIIMS (all campuses)
    - JIPMER, Puducherry

  LEAVE UNCHANGED, NEEDS SEPARATE VERIFICATION (ESIC runs its own
  distinct ESIC-quota system, not standard state counselling -- do
  NOT assume State without confirming per-college):
    - Employees State Insurance Corporation Medical College (all)

  FLIP TO STATE (confirmed or high-confidence state/UT government
  colleges running real state-level counselling):
    - Delhi DGHS/FMSC-counselled colleges (MAMC, LHMC, ABVIMS-RML,
      UCMS) -- verified MAMC runs 85% Delhi State Quota via FMSC
    - All "Autonomous State Medical College" / "Rajkiya" UP colleges
    - All GMERS (Gujarat Medical Education & Research Society) colleges
    - Named state government medical colleges (GMC Jammu, SKIMS
      Srinagar, Sikkim Govt Medical College, Shillong Medical
      College, Nagaland Institute of Medical Sciences, etc.)

Usage:
    python3 fix_state_quota_visibility.py --dry-run
    python3 fix_state_quota_visibility.py --apply
"""

import json
import sys
import argparse

# Colleges to leave untouched -- true Central/INI institutions with
# no state-quota participation at all.
LEAVE_AS_AIQ_SUBSTRINGS = [
    "aiims",
    "jawaharlal institute of postgraduate medical education",  # JIPMER
]

# Colleges to leave untouched pending separate research -- ESIC runs
# its own distinct quota system, not standard state counselling.
NEEDS_SEPARATE_VERIFICATION_SUBSTRINGS = [
    "employees state insurance corporation",
]

def classify(name):
    lname = name.lower()
    for s in LEAVE_AS_AIQ_SUBSTRINGS:
        if s in lname:
            return "leave_aiq"
    for s in NEEDS_SEPARATE_VERIFICATION_SUBSTRINGS:
        if s in lname:
            return "needs_verification"
    return "flip_to_state"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--data", default="public/data.json")
    args = parser.parse_args()

    if not args.apply and not args.dry_run:
        print("Specify --dry-run or --apply")
        sys.exit(1)

    with open(args.data, "r", encoding="utf-8") as f:
        data = json.load(f)

    colleges = data.get("colleges", [])
    govt_aiq_only = [c for c in colleges if c.get("category") == "Government" and c.get("quota") == "AIQ"]

    leave_aiq = []
    needs_verification = []
    flip_to_state = []

    for c in govt_aiq_only:
        cls = classify(c.get("name", ""))
        if cls == "leave_aiq":
            leave_aiq.append(c)
        elif cls == "needs_verification":
            needs_verification.append(c)
        else:
            flip_to_state.append(c)

    print(f"\n=== SUMMARY ===")
    print(f"Government colleges currently tagged AIQ-only: {len(govt_aiq_only)}")
    print(f"  Leave as AIQ (confirmed Central/INI, no state quota): {len(leave_aiq)}")
    print(f"  Needs separate verification (ESIC -- not touched): {len(needs_verification)}")
    print(f"  Flip to State (state/UT govt colleges): {len(flip_to_state)}")

    print(f"\n=== LEAVE AS AIQ (unchanged) ===")
    for c in leave_aiq:
        print(f"  - {c['name']}")

    print(f"\n=== NEEDS SEPARATE VERIFICATION (unchanged -- ESIC) ===")
    for c in needs_verification:
        print(f"  - {c['name']}")

    print(f"\n=== FLIP TO STATE ({len(flip_to_state)}) ===")
    for c in flip_to_state:
        print(f"  - {c['name']}  ({c.get('state')})")
        if args.apply:
            c["quota"] = "State"

    if args.apply:
        with open(args.data, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"\n✅ Flipped {len(flip_to_state)} colleges from AIQ to State quota tag in {args.data}")
    else:
        print(f"\n(Dry run — nothing written. Review the FLIP TO STATE list carefully before applying --"
              f" especially any college you don't personally recognize.)")

if __name__ == "__main__":
    main()
