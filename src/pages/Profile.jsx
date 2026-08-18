import { useEffect, useState } from "react";
import { User, Info } from "lucide-react";
import CollegeRow from "../components/CollegeRow.jsx";
import { fetchColleges } from "../lib/api.js";
import { getShortlist } from "../lib/storage.js";

export default function Profile() {
  const [shortlist, setShortlist] = useState([]);

  useEffect(() => {
    const slugs = getShortlist();
    if (slugs.length === 0) return;
    fetchColleges().then((all) => {
      setShortlist(all.filter((c) => slugs.includes(c.slug)));
    });
  }, []);

  return (
    <div className="max-w-app mx-auto px-4 sm:px-gutter py-6">
      <div className="flex items-center gap-3">
        <div className="w-14 h-14 rounded-full bg-surface-container-high flex items-center justify-center text-on-surface-variant">
          <User size={24} />
        </div>
        <div>
          <h1 className="font-display font-semibold text-xl text-on-surface">Your Profile</h1>
          <p className="text-[13px] text-on-surface-variant">Stored on this device only</p>
        </div>
      </div>

      <div className="flex items-start gap-2 bg-secondary-fixed/40 text-on-secondary-fixed rounded-lg p-3 mt-4 text-[12.5px]">
        <Info size={15} className="shrink-0 mt-0.5" />
        Accounts and sign-in aren't built yet — your shortlist and search history are saved locally in this browser only.
      </div>

      <h2 className="font-display font-semibold text-on-surface mt-6 mb-2.5">Shortlisted Colleges</h2>
      {shortlist.length === 0 ? (
        <p className="text-[13px] text-on-surface-variant">Nothing shortlisted yet — tap "Add to Shortlist" on a college's detail page.</p>
      ) : (
        <div className="space-y-2.5">
          {shortlist.map((c) => <CollegeRow key={c.slug} college={c} />)}
        </div>
      )}
    </div>
  );
}
