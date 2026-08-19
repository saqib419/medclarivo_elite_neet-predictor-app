import { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { Search } from "lucide-react";
import CollegeRow from "../components/CollegeRow.jsx";
import { fetchColleges, fetchMatches } from "../lib/api.js";

function useQueryParams() {
  const { search } = useLocation();
  return useMemo(() => Object.fromEntries(new URLSearchParams(search)), [search]);
}

export default function CollegesBrowse() {
  const qp = useQueryParams();
  const isMatchMode = Boolean(qp.score && qp.category);

  const [query, setQuery] = useState("");
  const [colleges, setColleges] = useState(null);
  const [visibleCount, setVisibleCount] = useState(50);

  useEffect(() => {
    let cancelled = false;
    setVisibleCount(50);

    if (isMatchMode) {
      fetchMatches({ score: qp.score, category: qp.category, state: qp.state, quota: qp.quota }).then((res) => {
        if (!cancelled) setColleges(res);
      });
      return () => { cancelled = true; };
    }

    // Debounce free-text search so we don't fire a request on every keystroke.
    const timer = setTimeout(() => {
      fetchColleges({ q: query || undefined }).then((res) => {
        if (!cancelled) setColleges(res);
      });
    }, 300);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query, isMatchMode, qp.score, qp.category, qp.state, qp.quota]);

  const visibleColleges = colleges?.slice(0, visibleCount);

  return (
    <div className="max-w-app mx-auto px-4 sm:px-gutter py-6">
      <h1 className="font-display font-semibold text-2xl text-on-surface">{isMatchMode ? "Matching Colleges" : "All Colleges"}</h1>
      <p className="text-on-surface-variant text-sm mt-1">
        {isMatchMode
          ? `Colleges matching your ${qp.category} category${qp.state ? ` in ${qp.state}` : ""}, sorted by cutoff.`
          : "Browse every government medical college in the dataset."}
      </p>

      {!isMatchMode && (
        <div className="relative mt-4">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by name…"
            className="w-full pl-9 pr-3 py-2.5 rounded-full border border-outline-variant bg-surface-container-lowest text-[13.5px] focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition"
          />
        </div>
      )}

      <div className="mt-4 space-y-2.5">
        {colleges === null && <p className="text-on-surface-variant text-sm">Loading…</p>}
        {colleges?.length === 0 && <p className="text-on-surface-variant text-sm">No colleges found.</p>}
        {visibleColleges?.map((c) => <CollegeRow key={c.slug} college={c} />)}
        {colleges && visibleCount < colleges.length && (
          <button onClick={() => setVisibleCount((count) => count + 50)} className="w-full py-3 mt-3 rounded-lg border border-outline-variant text-sm font-semibold text-on-surface hover:bg-surface-container-low transition">
            Load More ({colleges.length - visibleCount} remaining)
          </button>
        )}
      </div>
    </div>
  );
}
