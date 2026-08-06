const SEARCHES_KEY = "medpredict:recentSearches";
const SHORTLIST_KEY = "medpredict:shortlist";
const LAST_PREDICTION_KEY = "medpredict:lastPrediction";

function read(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}
function write(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage unavailable (private browsing, quota) — fail silently */
  }
}

export function getRecentSearches() {
  return read(SEARCHES_KEY, []);
}
export function addRecentSearch(entry) {
  const existing = getRecentSearches().filter(
    (s) => !(s.state === entry.state && s.category === entry.category && s.score === entry.score)
  );
  const next = [{ ...entry, at: Date.now() }, ...existing].slice(0, 8);
  write(SEARCHES_KEY, next);
  return next;
}
export function clearRecentSearches() {
  write(SEARCHES_KEY, []);
}

export function getShortlist() {
  return read(SHORTLIST_KEY, []);
}
export function isShortlisted(slug) {
  return getShortlist().includes(slug);
}
export function toggleShortlist(slug) {
  const current = getShortlist();
  const next = current.includes(slug) ? current.filter((s) => s !== slug) : [...current, slug];
  write(SHORTLIST_KEY, next);
  return next;
}

export function getLastPrediction() {
  return read(LAST_PREDICTION_KEY, null);
}
export function setLastPrediction(p) {
  write(LAST_PREDICTION_KEY, p);
}
