import { useState, useRef, useEffect } from "react";
import { Send, RotateCcw, Info, X, Stamp } from "lucide-react";

/* ============================================================
   Data now loads at runtime from DATA_URL instead of being
   hardcoded. Point this at:
     - "/data.json"  (bundled file in public/, editable + redeploy)
     - a remote URL (GitHub raw JSON, Supabase storage, your own
       API) so data can update WITHOUT redeploying the site.
   Either way the JSON shape must match public/data.json.
   ============================================================ */
const DATA_URL = "/data.json";

function estimateRank(score, table) {
  if (score >= table[0][0]) return table[0][1];
  for (let i = 0; i < table.length - 1; i++) {
    const [s1, r1] = table[i];
    const [s2, r2] = table[i + 1];
    if (score <= s1 && score >= s2) {
      const t = (s1 - score) / (s1 - s2 || 1);
      return Math.round(r1 + t * (r2 - r1));
    }
  }
  return table[table.length - 1][1];
}

const CATEGORIES = ["General", "EWS", "OBC", "SC", "ST", "PwD"];
const STATES = [
  "All-India only", "Delhi", "Uttar Pradesh", "Maharashtra", "Karnataka",
  "Tamil Nadu", "Kerala", "Madhya Pradesh", "Punjab", "West Bengal", "Rajasthan",
];

function likelihood(rank, cutoff) {
  if (rank <= cutoff * 0.7) return { label: "Strong", color: "#3F6B4A", bg: "#E7EFE7" };
  if (rank <= cutoff) return { label: "Likely", color: "#1F5A6B", bg: "#E4EEF0" };
  if (rank <= cutoff * 1.3) return { label: "Possible", color: "#A9852B", bg: "#F5EFDC" };
  return { label: "Tough", color: "#8B2635", bg: "#F5E4E6" };
}

function fmt(n) {
  return n.toLocaleString("en-IN");
}

const FONTS = `@import url('https://fonts.googleapis.com/css2?family=PT+Serif:ital,wght@0,400;0,700;1,400&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');`;

export default function App() {
  const [data, setData] = useState(null);
  const [loadError, setLoadError] = useState(null);

  const [messages, setMessages] = useState([]);
  const [step, setStep] = useState("score");
  const [scoreText, setScoreText] = useState("");
  const [score, setScore] = useState(null);
  const [category, setCategory] = useState(null);
  const [stateSel, setStateSel] = useState(null);
  const [air, setAir] = useState(null);
  const [showInfo, setShowInfo] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    fetch(DATA_URL)
      .then((r) => {
        if (!r.ok) throw new Error(`Failed to load data (${r.status})`);
        return r.json();
      })
      .then((json) => {
        setData(json);
        setMessages([
          { from: "bot", text: "Namaste! I'll estimate your NEET All-India Rank and a few colleges within reach." },
          { from: "bot", text: "What score did you get, out of 720?" },
        ]);
      })
      .catch((e) => setLoadError(e.message));
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  function pushBot(text) {
    setMessages((m) => [...m, { from: "bot", text }]);
  }
  function pushUser(text) {
    setMessages((m) => [...m, { from: "user", text }]);
  }

  function submitScore() {
    const n = Number(scoreText);
    if (!scoreText || Number.isNaN(n) || n < 0 || n > 720) {
      pushBot("That doesn't look like a valid NEET score — enter a number between 0 and 720.");
      return;
    }
    pushUser(`${n} / 720`);
    setScore(n);
    setScoreText("");
    pushBot("Got it. Which category should I use?");
    setStep("category");
  }

  function selectCategory(cat) {
    pushUser(cat);
    setCategory(cat);
    pushBot("And your state of domicile, for state-quota seats? Pick \"All-India only\" to skip this.");
    setStep("state");
  }

  function selectState(st) {
    pushUser(st);
    setStateSel(st);
    const rank = estimateRank(score, data.scoreRankTable);
    setAir(rank);
    pushBot(`Estimated All-India Rank: around ${fmt(rank)}. Your rank card is on the right — take it as a rough guide, not the final word.`);
    setStep("done");
  }

  function restart() {
    setMessages([{ from: "bot", text: "New estimate — what score did you get, out of 720?" }]);
    setStep("score");
    setScoreText("");
    setScore(null);
    setCategory(null);
    setStateSel(null);
    setAir(null);
  }

  if (loadError) {
    return (
      <div style={{ padding: 40, fontFamily: "sans-serif", color: "#8B2635" }}>
        Couldn't load data.json: {loadError}
      </div>
    );
  }
  if (!data) {
    return (
      <div style={{ padding: 40, fontFamily: "sans-serif", color: "#7A7264" }}>
        Loading…
      </div>
    );
  }

  const matches =
    step === "done"
      ? data.colleges
          .filter((c) => c.quota === "AIQ" || c.state === stateSel)
          .map((c) => ({ ...c, cutoff: c.cutoffs[category], like: likelihood(air, c.cutoffs[category]) }))
          .sort((a, b) => a.cutoff - b.cutoff)
          .slice(0, 7)
      : [];

  return (
    <div style={{ fontFamily: "Inter, sans-serif", background: "#EFE9DA", minHeight: "100vh" }}>
      <style>{`
        ${FONTS}
        @keyframes stampIn {
          0% { opacity: 0; transform: scale(1.6) rotate(-18deg); }
          60% { opacity: 1; transform: scale(0.92) rotate(-10deg); }
          100% { opacity: 1; transform: scale(1) rotate(-10deg); }
        }
        @keyframes cardIn {
          0% { opacity: 0; transform: translateY(12px); }
          100% { opacity: 1; transform: translateY(0); }
        }
        .stamp-anim { animation: stampIn 0.5s ease-out; }
        .card-anim { animation: cardIn 0.4s ease-out; }
        .neet-scroll::-webkit-scrollbar { width: 8px; }
        .neet-scroll::-webkit-scrollbar-thumb { background: #C9BFA2; border-radius: 4px; }
        @media (min-width: 800px) {
          .neet-grid { grid-template-columns: 1fr 1fr !important; }
        }
      `}</style>

      <div style={{ borderBottom: "1px solid #D9CFB2", padding: "20px 24px 18px" }}>
        <div style={{ maxWidth: 980, margin: "0 auto", display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
          <div>
            <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, letterSpacing: "0.14em", color: "#8B2635", marginBottom: 6 }}>
              NEET RANK ESTIMATOR · UNOFFICIAL
            </div>
            <h1 style={{ fontFamily: "'PT Serif', serif", fontSize: 30, color: "#1F2A44", margin: 0, lineHeight: 1.15 }}>
              Know Where You Stand
            </h1>
          </div>
          <button
            onClick={() => setShowInfo(true)}
            style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: "#1F2A44", background: "none", border: "1px solid #C9BFA2", borderRadius: 6, padding: "6px 10px", cursor: "pointer" }}
          >
            <Info size={14} /> About this data
          </button>
        </div>
      </div>

      <div style={{ maxWidth: 980, margin: "0 auto", padding: "24px" }}>
        <div className="neet-grid" style={{ display: "grid", gridTemplateColumns: "1fr", gap: 20 }}>
          <div style={{ background: "#FBF9F3", border: "1px solid #D9CFB2", borderRadius: 10, display: "flex", flexDirection: "column", height: 480 }}>
            <div ref={scrollRef} className="neet-scroll" style={{ flex: 1, overflowY: "auto", padding: 18, display: "flex", flexDirection: "column", gap: 10 }}>
              {messages.map((m, i) => (
                <div key={i} style={{ display: "flex", justifyContent: m.from === "bot" ? "flex-start" : "flex-end" }}>
                  <div
                    style={{
                      maxWidth: "80%",
                      padding: "9px 13px",
                      borderRadius: 10,
                      fontSize: 14.5,
                      lineHeight: 1.45,
                      background: m.from === "bot" ? "#EFE9DA" : "#1F2A44",
                      color: m.from === "bot" ? "#2B2B28" : "#F1EDE4",
                    }}
                  >
                    {m.text}
                  </div>
                </div>
              ))}
            </div>

            <div style={{ borderTop: "1px solid #D9CFB2", padding: 14 }}>
              {step === "score" && (
                <div style={{ display: "flex", gap: 8 }}>
                  <input
                    type="number"
                    min={0}
                    max={720}
                    value={scoreText}
                    onChange={(e) => setScoreText(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && submitScore()}
                    placeholder="e.g. 610"
                    style={{ flex: 1, fontFamily: "'IBM Plex Mono', monospace", fontSize: 15, padding: "9px 12px", border: "1px solid #C9BFA2", borderRadius: 6, background: "#fff" }}
                  />
                  <button
                    onClick={submitScore}
                    style={{ display: "flex", alignItems: "center", gap: 6, background: "#1F2A44", color: "#F1EDE4", border: "none", borderRadius: 6, padding: "0 16px", cursor: "pointer", fontSize: 14 }}
                  >
                    <Send size={14} /> Send
                  </button>
                </div>
              )}

              {step === "category" && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  {CATEGORIES.map((c) => (
                    <button
                      key={c}
                      onClick={() => selectCategory(c)}
                      style={{ border: "1px solid #1F2A44", color: "#1F2A44", background: "#fff", borderRadius: 20, padding: "6px 14px", fontSize: 13.5, cursor: "pointer" }}
                    >
                      {c}
                    </button>
                  ))}
                </div>
              )}

              {step === "state" && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  {STATES.map((s) => (
                    <button
                      key={s}
                      onClick={() => selectState(s)}
                      style={{ border: "1px solid #1F2A44", color: "#1F2A44", background: "#fff", borderRadius: 20, padding: "6px 14px", fontSize: 13.5, cursor: "pointer" }}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}

              {step === "done" && (
                <button
                  onClick={restart}
                  style={{ display: "flex", alignItems: "center", gap: 6, border: "1px solid #1F2A44", color: "#1F2A44", background: "#fff", borderRadius: 6, padding: "8px 14px", cursor: "pointer", fontSize: 13.5 }}
                >
                  <RotateCcw size={14} /> Estimate another score
                </button>
              )}
            </div>
          </div>

          <div style={{ position: "relative" }}>
            {step !== "done" ? (
              <div
                style={{
                  border: "1.5px dashed #C9BFA2",
                  borderRadius: 10,
                  height: 480,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#A69C82",
                  fontFamily: "'IBM Plex Mono', monospace",
                  fontSize: 13,
                  textAlign: "center",
                  padding: 20,
                }}
              >
                Your rank card fills in here<br />once score, category and state are set.
              </div>
            ) : (
              <div className="card-anim" style={{ position: "relative", background: "#FBF9F3", border: "1px solid #1F2A44", borderRadius: 10, overflow: "hidden" }}>
                <div style={{ background: "#1F2A44", color: "#F1EDE4", padding: "10px 18px", fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, letterSpacing: "0.12em" }}>
                  ESTIMATED RANK CARD
                </div>

                <div
                  className="stamp-anim"
                  style={{
                    position: "absolute", top: 46, right: 18, width: 76, height: 76, borderRadius: "50%",
                    border: "2px solid #8B2635", color: "#8B2635", display: "flex", flexDirection: "column",
                    alignItems: "center", justifyContent: "center", transform: "rotate(-10deg)",
                    fontFamily: "'IBM Plex Mono', monospace", fontSize: 9, letterSpacing: "0.05em", textAlign: "center",
                    background: "rgba(255,255,255,0.6)",
                  }}
                >
                  <Stamp size={16} />
                  ESTIMATE
                </div>

                <div style={{ padding: "20px 18px" }}>
                  <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: "#7A7264", marginBottom: 2 }}>ESTIMATED ALL-INDIA RANK</div>
                  <div style={{ fontFamily: "'PT Serif', serif", fontSize: 40, color: "#1F2A44", lineHeight: 1 }}>{fmt(air)}</div>

                  <div style={{ display: "flex", gap: 22, marginTop: 14, marginBottom: 14 }}>
                    <div>
                      <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 10, color: "#7A7264" }}>SCORE</div>
                      <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 15, color: "#2B2B28" }}>{score}/720</div>
                    </div>
                    <div>
                      <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 10, color: "#7A7264" }}>CATEGORY</div>
                      <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 15, color: "#2B2B28" }}>{category}</div>
                    </div>
                    <div>
                      <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 10, color: "#7A7264" }}>DOMICILE</div>
                      <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 15, color: "#2B2B28" }}>{stateSel}</div>
                    </div>
                  </div>

                  <div style={{ borderTop: "1px solid #D9CFB2", paddingTop: 12 }}>
                    <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: "#7A7264", marginBottom: 8 }}>SAMPLE COLLEGES WITHIN REACH</div>
                    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                      {matches.map((c) => (
                        <div key={c.name} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, fontSize: 13, padding: "7px 9px", background: "#F1EDE4", borderRadius: 6 }}>
                          <div style={{ minWidth: 0 }}>
                            <div style={{ color: "#2B2B28", fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.name}</div>
                            <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 10.5, color: "#8A8168" }}>{c.quota} · cutoff ~{fmt(c.cutoff)}</div>
                          </div>
                          <span style={{ flexShrink: 0, fontSize: 11, fontFamily: "'IBM Plex Mono', monospace", padding: "3px 8px", borderRadius: 12, color: c.like.color, background: c.like.bg }}>
                            {c.like.label}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {showInfo && (
        <div onClick={() => setShowInfo(false)} style={{ position: "fixed", inset: 0, background: "rgba(31,42,68,0.45)", display: "flex", alignItems: "center", justifyContent: "center", padding: 20, zIndex: 10 }}>
          <div onClick={(e) => e.stopPropagation()} style={{ background: "#FBF9F3", borderRadius: 10, maxWidth: 460, padding: 22, position: "relative" }}>
            <button onClick={() => setShowInfo(false)} style={{ position: "absolute", top: 12, right: 12, background: "none", border: "none", cursor: "pointer", color: "#7A7264" }}>
              <X size={18} />
            </button>
            <h3 style={{ fontFamily: "'PT Serif', serif", fontSize: 19, color: "#1F2A44", marginTop: 0 }}>About the data</h3>
            <p style={{ fontSize: 13.5, lineHeight: 1.6, color: "#2B2B28" }}>
              This data is loaded live from <code>{DATA_URL}</code>. Right now it's illustrative placeholder
              data shaped like recent NEET trends — not pulled from NTA or MCC records.
            </p>
            <p style={{ fontSize: 13.5, lineHeight: 1.6, color: "#2B2B28" }}>
              For real decisions, check your official NTA rank card and the latest MCC / state counselling
              cutoff lists. See README.md for how to replace this file with real figures.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
