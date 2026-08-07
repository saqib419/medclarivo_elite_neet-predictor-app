const fs = require("fs");
const path = require("path");

const DATA_PATH = path.join(__dirname, "..", "..", "public", "data.json"); // adjust if needed
const CSV_PATH = path.join(__dirname, "nmc_seat_matrix_2026_27_all_823.csv");

const CATEGORY_RATIOS = { General: 1, EWS: 1.6, OBC: 2.2, SC: 8, ST: 13, PwD: 16 };

function normalize(name) {
  return name
    .toLowerCase()
    .replace(/[.,&()]/g, " ")
    .replace(/\b(government|govt|medical|college|hospital|institute|institute of|of|medical sciences|and|the|research|sciences|city|memorial|general|private)\b/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function tokenOverlap(a, b) {
  const ta = new Set(normalize(a).split(" ").filter(Boolean));
  const tb = new Set(normalize(b).split(" ").filter(Boolean));
  if (ta.size === 0 || tb.size === 0) return 0;
  let shared = 0;
  for (const t of ta) if (tb.has(t)) shared++;
  return shared / Math.min(ta.size, tb.size);
}

const data = JSON.parse(fs.readFileSync(DATA_PATH, "utf8"));
const csv = fs.readFileSync(CSV_PATH, "utf8").trim().split("\n");

// Anchor: cheapest real General cutoff per state (govt colleges), and a separate
// national anchor for private colleges (private cutoffs run differently than govt)
const govtAnchors = {};
const privateAnchors = [];
for (const c of data.colleges) {
  if (c.state && c.cutoffs?.General && !c.cutoffEstimated) {
    if (c.category !== "Private" ) {
      if (!govtAnchors[c.state] || c.cutoffs.General < govtAnchors[c.state]) {
        govtAnchors[c.state] = c.cutoffs.General;
      }
    } else {
      privateAnchors.push(c.cutoffs.General);
    }
  }
}
const nationalGovtFallback = 5000;
const nationalPrivateFallback = 45000; // private colleges typically close much later

let added = 0, skippedDup = 0, stateIndex = {};

for (const line of csv) {
  const parts = line.split("|");
  if (parts.length < 4) continue;
  const [state, name, seatsStr, mgmt] = parts;
  if (!state || !name) continue;
  const seats = Number(seatsStr) || null;
  const isGovt = mgmt.trim() === "Government";

  const isDup = data.colleges.some(
    (c) => c.state === state && tokenOverlap(c.name, name) >= 0.6
  );
  if (isDup) { skippedDup++; continue; }

  const key = state + (isGovt ? "_G" : "_P");
  stateIndex[key] = (stateIndex[key] || 0) + 1;

  let estGeneral;
  if (isGovt) {
    const anchor = govtAnchors[state] || nationalGovtFallback;
    const multiplier = 1.3 + Math.min(stateIndex[key] * 0.15, 3.5);
    estGeneral = Math.round(anchor * multiplier);
  } else {
    const anchor = privateAnchors.length
      ? privateAnchors.reduce((a,b)=>a+b,0) / privateAnchors.length
      : nationalPrivateFallback;
    const multiplier = 0.9 + Math.min(stateIndex[key] * 0.08, 2.0);
    estGeneral = Math.round(anchor * multiplier);
  }

  const cutoffs = {};
  for (const [cat, ratio] of Object.entries(CATEGORY_RATIOS)) {
    cutoffs[cat] = Math.round(estGeneral * ratio);
  }

  data.colleges.push({
    name,
    quota: "State",
    state,
    cutoffs,
    cutoffEstimated: true,
    totalSeats: seats,
    category: isGovt ? "Government" : "Private",
  });
  added++;
}

fs.writeFileSync(DATA_PATH, JSON.stringify(data, null, 2));
console.log(`Added: ${added}`);
console.log(`Skipped as likely duplicates: ${skippedDup}`);
console.log(`New total colleges: ${data.colleges.length}`);
