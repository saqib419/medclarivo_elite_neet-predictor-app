import json

# Load the 154 missing colleges (paste your v7_nmc_missing_from_app.json content here,
# or point this script at the actual file path)
with open("v7_nmc_missing_from_app.json") as f:
    missing = json.load(f)

with open("public/data.json") as f:
    data = json.load(f)

existing_names = {c["name"].strip().lower() for c in data["colleges"]}

generic_infrastructure = [
    {
        "icon": "building",
        "title": "Hostel Facilities",
        "desc": "Details not yet available — please verify with the college."
    },
    {
        "icon": "library",
        "title": "Library & Academic Resources",
        "desc": "Details not yet available — please verify with the college."
    },
    {
        "icon": "stethoscope",
        "title": "Clinical Exposure",
        "desc": "Details not yet available — please verify with the college."
    }
]

added = []
skipped_dupe = []

for m in missing:
    name = m["name"].strip()
    if name.lower() in existing_names:
        skipped_dupe.append(name)
        continue

    entry = {
        "name": name,
        "quota": "AIQ",
        "state": m["state"],
        "cutoffs": None,
        "nirfRank": None,
        "annualFee": None,
        "totalSeats": m["totalSeats"],
        "establishedYear": None,
        "category": m["mgmt"],
        "seatMatrix": None,
        "cutoffTrends": [],
        "infrastructure": generic_infrastructure,
        "dataStatus": "seatsOnly"  # flag so your UI can show "limited data" badge if you want
    }
    data["colleges"].append(entry)
    added.append(name)

with open("public/data.json", "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Added: {len(added)}")
print(f"Skipped (already present): {len(skipped_dupe)}")
if skipped_dupe:
    for n in skipped_dupe:
        print(f"  - {n}")
print(f"New total colleges in data.json: {len(data['colleges'])}")
