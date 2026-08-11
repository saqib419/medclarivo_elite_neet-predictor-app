const fs = require("fs");
const path = require("path");

const DATA_PATH = path.join(__dirname, "..", "..", "public", "data.json"); // adjust if needed

// ---------- Step 1: identify and remove junk (non-college) rows ----------
// These are leftover rows from an MCC round-wise seat ALLOTMENT result
// (rank/priority labels), not colleges. Pattern: contains "Allotted(" or
// "Upgraded(" or starts with "Fresh Allotted".
function isJunkRow(name) {
  if (!name) return true;
  const n = name.trim();
  if (/allotted\s*\(/i.test(n)) return true;
  if (/^upgraded\s*\(/i.test(n)) return true;
  if (/^fresh allotted/i.test(n)) return true;
  // rows that are just a rank/priority label with no alphabetic college-like words
  if (/^(cw rank|nri priority)/i.test(n)) return true;
  return false;
}

const data = JSON.parse(fs.readFileSync(DATA_PATH, "utf8"));
const before = data.colleges.length;

const junk = data.colleges.filter((c) => isJunkRow(c.name));
const kept = data.colleges.filter((c) => !isJunkRow(c.name));

console.log(`=== CLEANUP ===`);
console.log(`Total colleges before: ${before}`);
console.log(`Junk (non-college) rows removed: ${junk.length}`);
if (junk.length) {
  console.log(`Examples of removed rows:`);
  junk.slice(0, 8).forEach((c) => console.log(`   - "${c.name}"`));
}
console.log(`Total colleges after cleanup: ${kept.length}`);

data.colleges = kept;
fs.writeFileSync(DATA_PATH, JSON.stringify(data, null, 2));

// ---------- Step 2: re-run duplicate check with improved normalization ----------
function normalize(name) {
  return name
    .toLowerCase()
    .replace(/[.,&()]/g, " ")
    .replace(/\binst\b/g, "institute")
    .replace(/\bsci\b/g, "sciences")
    .replace(/\bcoll\b/g, "college")
    .replace(/\bmed\b/g, "medical")
    .replace(/\bgovt\b/g, "government")
    .replace(/\br\s*i\b/g, "research institute")
    .replace(/\bmc\b/g, "medical college")
    .replace(/\b(government|medical|college|hospital|institute|of|medical sciences|and|the|research|sciences|city|memorial|general|private)\b/g, " ")
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

const byState = {};
kept.forEach((c, idx) => {
  const st = c.state || "UNKNOWN";
  if (!byState[st]) byState[st] = [];
  byState[st].push({ ...c, _idx: idx });
});

const THRESHOLD = 0.6;
const pairs = [];
for (const [state, list] of Object.entries(byState)) {
  for (let i = 0; i < list.length; i++) {
    for (let j = i + 1; j < list.length; j++) {
      const score = tokenOverlap(list[i].name, list[j].name);
      if (score >= THRESHOLD) {
        pairs.push({
          state, score: score.toFixed(2),
          a: list[i].name, aIdx: list[i]._idx, aEst: !!list[i].cutoffEstimated,
          b: list[j].name, bIdx: list[j]._idx, bEst: !!list[j].cutoffEstimated,
        });
      }
    }
  }
}
pairs.sort((a, b) => b.score - a.score);

console.log(`\n=== DUPLICATE RE-CHECK (post-cleanup) ===`);
console.log(`Potential duplicate pairs found (overlap >= ${THRESHOLD}): ${pairs.length}\n`);
for (const p of pairs) {
  console.log(`[${p.score}] (${p.state})`);
  console.log(`   #${p.aIdx} "${p.a}"  ${p.aEst ? "(estimated)" : "(real)"}`);
  console.log(`   #${p.bIdx} "${p.b}"  ${p.bEst ? "(estimated)" : "(real)"}`);
  console.log("");
}

const outPath = path.join(__dirname, "duplicate_report_cleaned.txt");
const lines = pairs.map(p =>
  `[${p.score}] (${p.state})\n   #${p.aIdx} "${p.a}"  ${p.aEst ? "(estimated)" : "(real)"}\n   #${p.bIdx} "${p.b}"  ${p.bEst ? "(estimated)" : "(real)"}\n`
);
fs.writeFileSync(outPath, `Total colleges after cleanup: ${kept.length}\nPotential duplicate pairs: ${pairs.length}\n\n` + lines.join("\n"));
console.log(`Full report written to ${outPath}`);
