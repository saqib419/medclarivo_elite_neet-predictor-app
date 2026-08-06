import { useEffect, useState } from "react";
import { Search } from "lucide-react";
import CollegeRow from "../components/CollegeRow.jsx";
import { fetchColleges } from "../lib/api.js";

export default function CollegesBrowse() {
  const [query, setQuery] = useState("");
  const [colleges, setColleges] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetchColleges({ q: query || undefined }).then((res) => {
      if (!cancelled) setColleges(res);
    });
    return () => { cancelled = true; };
  }, [query]);

  return (
    <div className="max-w-app mx-auto px-4 sm:px-gutter py-6">
      <h1 className="font-display font-semibold text-2xl text-on-surface">All Colleges</h1>
      <p className="text-on-surface-variant text-sm mt-1">Browse every government medical college in the dataset.</p>

      <div className="relative mt-4">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by name…"
          className="w-full pl-9 pr-3 py-2.5 rounded-full border border-outline-variant bg-surface-container-lowest text-[13.5px] focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition"
        />
      </div>

      <div className="mt-4 space-y-2.5">
        {colleges === null && <p className="text-on-surface-variant text-sm">Loading…</p>}
        {colleges?.length === 0 && <p className="text-on-surface-variant text-sm">No colleges found.</p>}
        {colleges?.map((c) => <CollegeRow key={c.slug} college={c} />)}
      </div>
    </div>
  );
}
