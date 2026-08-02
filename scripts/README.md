# Cutoff PDF → data.json pipeline

Two scripts, run in order, per PDF you process.

## Requirements (one-time)
```
pip install pdfplumber
```

## Step 1: Get the official PDF
- All-India Quota: mcc.nic.in → counselling → round-wise "Allotment Result"
- State quota: your state's medical counselling authority site, same idea

These are candidate-wise lists (rank, category, quota, allotted college),
not a ready-made cutoff table — that's what step 2 builds.

## Step 2: Extract and aggregate
```
python scripts/parse_cutoff_pdf.py path/to/downloaded.pdf --out extracted.csv --course MBBS
```
`--course MBBS` filters out BDS/other courses if the PDF covers more than one.

**Open `extracted.csv` and spot-check a few rows against the PDF itself**
before trusting it — PDF table extraction isn't 100% reliable, and the
script tells you in the terminal if it had to skip unreadable tables.

## Step 3: Merge into your app's data
```
# All-India Quota PDF
python scripts/build_data_json.py extracted.csv --quota AIQ --data public/data.json

# A state PDF
python scripts/build_data_json.py extracted.csv --quota State --state "Uttar Pradesh" --data public/data.json
```
This updates cutoffs for colleges already in `data.json` and adds new ones
it doesn't recognize by name. Always run `git diff public/data.json`
afterward to review what changed before committing.

## Repeat
Run steps 1–3 again for each state PDF, and again after each new
counselling round (cutoffs shift round to round).

## Note on the score→rank table
This pipeline only handles college cutoffs. The `scoreRankTable` in
data.json (score → estimated rank) isn't published this way — it comes
from coaching institutes' (Aakash, Allen, etc.) previous-year score-vs-rank
tables, which are small enough (~40-50 rows) to copy in by hand.
