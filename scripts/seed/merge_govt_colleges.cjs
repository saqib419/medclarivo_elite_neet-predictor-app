const fs = require("fs");
const path = require("path");

const DATA_PATH = path.join(__dirname, "..", "..", "public", "data.json");
const CSV_PATH = path.join(__dirname, "govt_colleges.csv");

const CATEGORY_RATIOS = { General: 1, EWS: 1.6, OBC: 2.2, SC: 8, ST: 13, PwD: 16 };

function normalize(name) {
  return name
    .toLowerCase()
    .replace(/[.,&()]/g, " ")
    .replace(/\b(government|govt|medical|college|hospital|institute|institute of|of|medical sciences|and|the|research|sciences|city|memorial|general)\b/g, " ")
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

const anchors = {};
for (const c of data.colleges) {
  if (c.quota === "State" && c.state && c.cutoffs?.General) {
    if (!anchors[c.state] || c.cutoffs.General < anchors[c.state]) {
      anchors[c.state] = c.cutoffs.General;
    }
  }
}
const nationalFallbackAnchor = 5000;

let added = 0, skippedDup = 0, stateIndex = {};

for (const line of csv) {
  const [state, name, seatsStr] = line.split("|");
  if (!state || !name) continue;
  const seats = Number(seatsStr) || null;

  const isDup = data.colleges.some(
    (c) => c.state === state && tokenOverlap(c.name, name) >= 0.6
  );
  if (isDup) { skippedDup++; continue; }

  stateIndex[state] = (stateIndex[state] || 0) + 1;
  const anchor = anchors[state] || nationalFallbackAnchor;
  const multiplier = 1.3 + Math.min(stateIndex[state] * 0.15, 3.5);
  const estGeneral = Math.round(anchor * multiplier);

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
    category: "Government",
  });
  added++;
}

fs.writeFileSync(DATA_PATH, JSON.stringify(data, null, 2));
console.log(`Added: ${added}`);
console.log(`Skipped as likely duplicates: ${skippedDup}`);
console.log(`New total colleges: ${data.colleges.length}`);
