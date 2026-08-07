const fs = require("fs");
const path = require("path");

const DATA_PATH = path.join(__dirname, "..", "..", "public", "data.json"); // adjust if needed

// ---------------------------------------------------------------------------
// This list was built by manually reviewing the 59 flagged pairs from the
// duplicate report. Each entry says: these two names refer to the SAME real
// college -> keep one, drop the other. Matched by exact name string (safer
// than array index, which can drift). Anything NOT in this list is left
// untouched, including many pairs that LOOK similar but are verified as
// genuinely different colleges (e.g. two different colleges in the same city).
// ---------------------------------------------------------------------------
const MERGES = [
  // [keep name, drop name]
  ["Maulana Azad Medical College, Delhi", "Maulana Azad Medical College"],
  ["Lady Hardinge Medical College, Delhi", "Lady Hardinge Medical College"],
  ["Dr. DY Patil Medical College", "Dr. DY Patil Medical College and Hospt."],
  ["Bangalore Medical College and Research Institute", "Bangalore Medical College & RI"],
  ["Stanley Medical College, Chennai", "STANLEY MEDICAL COLLEGE"],
  ["Netaji Subhash Chandra Bose Medical College, Jabalpur", "NETAJI SUBHASH CHANDRA BOSE MC"],
  ["Andhra Medical College, Visakhapatnam", "Andhra Medical College"],
  ["Tomo Riba Institute of Health & Medical Sciences, Naharlagun", "Tomo Riba Institute Health and Medical Sciences"],
  ["Assam Medical College, Dibrugarh", "ASSAM MEDICAL COLLEGE"],
  ["Patna Medical College, Patna", "PATNA MEDICAL COLLEGE"],
  ["Goa Medical College, Panaji", "GOA MEDICAL COLLEGE"],
  ["B.J. Medical College, Ahmedabad", "B.J. MEDICAL COLLEGE"],
  ["Pt. B.D. Sharma PGIMS, Rohtak", "PT. B.D. SHARMA PGIMS"],
  ["Indira Gandhi Medical College, Shimla", "INDIRA GANDHI MEDICAL COLL."],
  ["Rajendra Institute of Medical Sciences, Ranchi", "RAJENDRA INST. OF MED. SCI."],
  ["Regional Institute of Medical Sciences, Imphal", "REGIONAL INST OF MEDICAL SCI"],
  ["Zoram Medical College, Falkawn", "ZORAM MEDICAL COLLEGE Falkawn"],
  ["Institute of Medical Sciences & SUM Hospital", "Institute of Medical Sciences and SUM Host."],
  ["Agartala Government Medical College", "AGARTALA GOVT. MEDICAL COLLEGE"],
  ["Calcutta National Medical College, Kolkata", "CALCUTTA NATIONAL MED COLL"],
  ["Jawaharlal Institute of Postgraduate Medical Education & Research (JIPMER), Puducherry", "JIPMER PUDUCHERRY"],
  ["ESIC Medical College AND PGIMSR", "Government Medical College and ESIC Hospital"],
  ["MYSORE MED.& RESEARCH INST. MYSORE", "Mysore Medical College and Research Instt. (Prev.name Government Medical College), Mysore"],
  ["KANYAKUMARI GOVT. MED. COLL.", "KanyaKumari Government Medical College, Asaripallam"],
  ["BPS Govt. Med. College", "BPS Government Medical College for Women, Sonepat"],
  ["SBKS Med. Inst. and Res. Centre", "SBKS Medical Instt. & Research Centre, Vadodra"],
  ["DR.RAJENDRA PRASAD MC", "Dr. Rajendar Prasad Government Medical College, Tanda"],
  ["Jagadguru Gangadhar Mahaswamigalu Moorusavirmath Medical College", "Jagadguru Gangadhar Mahaswamigalu Moorusavirma th Medical College"],
  ["Andaman and Nicobar Islands Institute of Medical Sciences, Port Blair", "Andaman and Nicobar Islands Institute of Medical S"],
];

// Pairs reviewed and confirmed to be DIFFERENT real colleges despite similar
// names (kept for the record in the printed report, no action taken):
const FALSE_POSITIVES = [
  ["AIIMS Guwahati", "GUWAHATI MEDICAL COLLEGE", "different institutions"],
  ["AIIMS, New Delhi", "Vardhman Mahavir Medical College and Safdarjung Hospital New Delhi", "different institutions"],
  ["CHHATTISGARH INSTITUTE OF MEDICAL SCIENCES", "Government Medical College Mahasamund Chhattisgarh", "different cities/colleges (Bilaspur vs Mahasamund)"],
  ["Malla Reddy Institute of Medical Sciences", "Malla Reddy Medical College for Women", "separate colleges under same trust"],
  ["DR. VAISHAMPAYAM MEMORIAL M.C.", "DR.S.C.GOVT MEDICAL COLLEGE", "different cities (Solapur vs Nanded)"],
  ["Sri Siddhartha Academy T Begur", "Sri Siddhartha Medical College DU", "separate campuses, verify manually"],
  ["RAICHUR INST. OF MEDICAL SCI.", "Navodaya Medical College, Raichur", "govt vs private, different colleges"],
  ["SHIMOGA INST. OF MEDICAL SCI.", "Subbaiah Institute of Medical Sciences, Shimoga, Karnataka", "different private college, same city"],
  ["KANYAKUMARI GOVT. MED. COLL.", "Kanyakumari Medical Mission Research Centre, Kanyakumari District", "different college, same district"],
  ["KANYAKUMARI GOVT. MED. COLL.", "Sree Mookambika Institute of Medical Sciences, Kanyakumari", "different college, same district"],
  ["BELGAUM INST. OF MEDICAL SCI.", "Jawaharlal Nehru Medical College, Belgaum", "govt (BIMS) vs private (JNMC), different colleges"],
  ["Baba Kinaram Autonomous State Medical College", "MAHARSHI DEVRAHA BABA AUTONOMOUS STATE. MEDICAL COLLEGE", "different UP autonomous colleges"],
];

// Low-info placeholder rows worth a manual look (bare/ambiguous names that
// could refer to more than one real college; NOT auto-deleted):
const AMBIGUOUS_PLACEHOLDERS = [
  "ESIC",
  "RIMS",
  "Autonomous State Medical Collage",
  "Autonomous State Medical College",
  "Autonomous State Medical College Society",
  "Autonomous State Medical college Society Hardoi",
];

const data = JSON.parse(fs.readFileSync(DATA_PATH, "utf8"));
const before = data.colleges.length;

let mergedCount = 0;
const mergeLog = [];

for (const [keepName, dropName] of MERGES) {
  const dropIdx = data.colleges.findIndex((c) => c.name === dropName);
  const keepIdx = data.colleges.findIndex((c) => c.name === keepName);
  if (dropIdx === -1 || keepIdx === -1) {
    mergeLog.push(`SKIPPED (name not found exactly): "${keepName}" / "${dropName}"`);
    continue;
  }
  // If the entry being dropped has REAL (non-estimated) cutoff data and the
  // one being kept only has estimated data, prefer keeping the real numbers.
  const keepEntry = data.colleges[keepIdx];
  const dropEntry = data.colleges[dropIdx];
  if (dropEntry.cutoffEstimated === false && keepEntry.cutoffEstimated === true) {
    // swap which one survives, so real data wins
    data.colleges[keepIdx] = { ...dropEntry, name: keepEntry.name };
  }
  data.colleges.splice(dropIdx, 1);
  mergedCount++;
  mergeLog.push(`MERGED: kept "${keepName}", removed "${dropName}"`);
}

fs.writeFileSync(DATA_PATH, JSON.stringify(data, null, 2));

console.log(`=== MERGE SUMMARY ===`);
console.log(`Total colleges before: ${before}`);
console.log(`Pairs merged: ${mergedCount}`);
console.log(`Total colleges after: ${data.colleges.length}\n`);
mergeLog.forEach((l) => console.log(l));

console.log(`\n=== LEFT UNTOUCHED: confirmed different colleges (similar names) ===`);
FALSE_POSITIVES.forEach(([a, b, reason]) => {
  console.log(`"${a}"  vs  "${b}"\n   -> ${reason}`);
});

console.log(`\n=== NEEDS YOUR MANUAL CHECK: ambiguous/low-info entries ===`);
AMBIGUOUS_PLACEHOLDERS.forEach((name) => {
  const matches = data.colleges.filter((c) => c.name === name);
  matches.forEach((c) =>
    console.log(`"${c.name}"  (state: ${c.state || "unknown"}, seats: ${c.totalSeats ?? "?"}) — generic/ambiguous name, may need renaming or removal`)
  );
});
