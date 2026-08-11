import { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { Search, ArrowRight } from "lucide-react";
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
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [colleges, setColleges] = useState(null);

  useEffect(() => {
    let cancelled = false;

    if (isMatchMode) {
      fetchMatches({ score: qp.score, category: qp.category, state: qp.state, quota: qp.quota }).then((res) => {
        if (!cancelled) setColleges(res);
      });
      return () => { cancelled = true; };
    }

    fetchColleges({ q: submittedQuery || undefined }).then((res) => {
      if (!cancelled) setColleges(res);
    });

    return () => { cancelled = true; };
  }, [submittedQuery, isMatchMode, qp.score, qp.category, qp.state, qp.quota]);

  function runSearch() {
    setSubmittedQuery(query.trim());
  }

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
            onKeyDown={(e) => { if (e.key === "Enter") runSearch(); }}
            placeholder="Search by name or state…"
            className="w-full pl-9 pr-11 py-2.5 rounded-full border border-outline-variant bg-surface-container-lowest text-[13.5px] focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition"
          />
          <button
            onClick={runSearch}
            aria-label="Search"
            className="absolute right-1.5 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-primary text-on-primary flex items-center justify-center hover:brightness-110 transition"
          >
            <ArrowRight size={15} />
          </button>
        </div>
      )}

      <div className="mt-4 space-y-2.5">
        {colleges === null && <p className="text-on-surface-variant text-sm">Loading…</p>}
        {colleges?.length === 0 && <p className="text-on-surface-variant text-sm">No colleges found.</p>}
        {colleges?.map((c) => <CollegeRow key={c.slug} college={c} />)}
      </div>
    </div>
  );
}
