const fs = require("fs");
const path = require("path");

const DATA_PATH = path.join(__dirname, "..", "..", "public", "data.json"); // adjust if needed

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
const colleges = data.colleges;

console.log(`Total colleges in file: ${colleges.length}`);

// Group by state first (duplicates only matter within the same state)
const byState = {};
colleges.forEach((c, idx) => {
  const st = c.state || "UNKNOWN";
  if (!byState[st]) byState[st] = [];
  byState[st].push({ ...c, _idx: idx });
});

const THRESHOLD = 0.6; // same threshold the merge scripts used
const pairs = [];

for (const [state, list] of Object.entries(byState)) {
  for (let i = 0; i < list.length; i++) {
    for (let j = i + 1; j < list.length; j++) {
      const score = tokenOverlap(list[i].name, list[j].name);
      if (score >= THRESHOLD) {
        pairs.push({
          state,
          score: score.toFixed(2),
          a: list[i].name,
          aIdx: list[i]._idx,
          aEst: !!list[i].cutoffEstimated,
          b: list[j].name,
          bIdx: list[j]._idx,
          bEst: !!list[j].cutoffEstimated,
        });
      }
    }
  }
}

pairs.sort((a, b) => b.score - a.score);

console.log(`\nPotential duplicate pairs found (overlap >= ${THRESHOLD}): ${pairs.length}\n`);
for (const p of pairs) {
  console.log(`[${p.score}] (${p.state})`);
  console.log(`   #${p.aIdx} "${p.a}"  ${p.aEst ? "(estimated)" : "(real)"}`);
  console.log(`   #${p.bIdx} "${p.b}"  ${p.bEst ? "(estimated)" : "(real)"}`);
  console.log("");
}

// Write full report to a file too, for long lists
const outPath = path.join(__dirname, "duplicate_report.txt");
const lines = pairs.map(p =>
  `[${p.score}] (${p.state})\n   #${p.aIdx} "${p.a}"  ${p.aEst ? "(estimated)" : "(real)"}\n   #${p.bIdx} "${p.b}"  ${p.bEst ? "(estimated)" : "(real)"}\n`
);
fs.writeFileSync(outPath, `Total colleges: ${colleges.length}\nPotential duplicate pairs: ${pairs.length}\n\n` + lines.join("\n"));
console.log(`Full report written to ${outPath}`);
