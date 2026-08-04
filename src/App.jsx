import { useState, useRef, useEffect, useCallback } from "react";
import { Send, RotateCcw, Info, X, ShieldCheck, Check } from "lucide-react";

/* ============================================================
   DATA
   Loads from DATA_URL at runtime. Falls back to a small inline
   sample if the fetch fails, so this component also renders
   standalone (e.g. in a preview) without a server behind it.
   ============================================================ */
const DATA_URL = "/data.json";

const FALLBACK_DATA = {
  scoreRankTable: [
    [720, 1], [650, 3900], [600, 17400], [550, 51000], [500, 120000],
    [450, 236000], [400, 416000], [350, 678000], [300, 1038000], [200, 1940000], [0, 2100000],
  ],
  colleges: [
    { name: "AIIMS, New Delhi", quota: "AIQ", state: null, cutoffs: { General: 80, EWS: 120, OBC: 150, SC: 600, ST: 900, PwD: 1200 } },
    { name: "Maulana Azad Medical College, Delhi", quota: "AIQ", state: null, cutoffs: { General: 150, EWS: 250, OBC: 300, SC: 1200, ST: 2000, PwD: 2600 } },
    { name: "Lady Hardinge Medical College, Delhi", quota: "AIQ", state: null, cutoffs: { General: 500, EWS: 800, OBC: 950, SC: 3200, ST: 5200, PwD: 6000 } },
  ],
};

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

function likelihood(rank, cutoff) {
  if (rank <= cutoff * 0.7) return { label: "Strong", tone: "success" };
  if (rank <= cutoff) return { label: "Likely", tone: "info" };
  if (rank <= cutoff * 1.3) return { label: "Possible", tone: "warn" };
  return { label: "Tough", tone: "danger" };
}

function fmt(n) {
  return n.toLocaleString("en-IN");
}

const CATEGORIES = ["General", "EWS", "OBC", "SC", "ST", "PwD"];
const STATES = [
  "All-India only",
  "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
  "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
  "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
  "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim",
  "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand",
  "West Bengal",
  "Andaman and Nicobar Islands", "Chandigarh", "Delhi",
  "Jammu and Kashmir", "Ladakh", "Puducherry",
];
const STEP_LABELS = ["Score", "Category", "State", "Result"];
const STEP_INDEX = { score: 0, category: 1, state: 2, computing: 3, done: 3 };

const prefersReducedMotion = () =>
  typeof window !== "undefined" &&
  window.matchMedia &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/* ============================================================
   Count-up hook for the rank number reveal
   ============================================================ */
function useCountUp(target, active) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (!active || target == null) return;
    if (prefersReducedMotion()) {
      setValue(target);
      return;
    }
    let raf;
    const start = performance.now();
    const duration = 900;
    const ease = (t) => 1 - Math.pow(1 - t, 3); // ease-out-cubic
    const tick = (now) => {
      const t = Math.min(1, (now - start) / duration);
      setValue(Math.round(target * ease(t)));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, active]);
  return value;
}

/* ============================================================
   Small presentational pieces
   ============================================================ */
function ProgressSteps({ currentIndex }) {
  return (
    <ol className="steps" aria-label="Progress">
      {STEP_LABELS.map((label, i) => {
        const state = i < currentIndex ? "done" : i === currentIndex ? "active" : "pending";
        return (
          <li key={label} className={`step step--${state}`}>
            <span className="step__dot" aria-hidden="true">
              {state === "done" ? <Check size={11} strokeWidth={3} /> : i + 1}
            </span>
            <span className="step__label">{label}</span>
            {i < STEP_LABELS.length - 1 && <span className="step__line" aria-hidden="true" />}
          </li>
        );
      })}
    </ol>
  );
}

function TypingDots() {
  return (
    <div className="bubble bubble--bot bubble--typing" aria-label="Calculating">
      <span className="dot" />
      <span className="dot" />
      <span className="dot" />
    </div>
  );
}

function Chip({ children, onClick, autoFocus }) {
  return (
    <button type="button" className="chip" onClick={onClick} autoFocus={autoFocus}>
      {children}
    </button>
  );
}

function SkeletonCard() {
  return (
    <div className="card card--result" aria-hidden="true">
      <div className="card__header card__header--skeleton">
        <span className="skel skel--eyebrow" />
      </div>
      <div className="card__body">
        <span className="skel skel--label" />
        <span className="skel skel--figure" />
        <div className="fact-row">
          <span className="skel skel--fact" />
          <span className="skel skel--fact" />
          <span className="skel skel--fact" />
        </div>
        <div className="skel-list">
          {[0, 1, 2].map((i) => (
            <span key={i} className="skel skel--row" style={{ animationDelay: `${i * 90}ms` }} />
          ))}
        </div>
      </div>
    </div>
  );
}

function EmptyResultState() {
  return (
    <div className="empty-state">
      <div className="empty-state__badge" aria-hidden="true">
        <ShieldCheck size={20} strokeWidth={1.75} />
      </div>
      <h2 className="t-heading">Your estimate appears here</h2>
      <p className="t-body empty-state__copy">
        Answer three quick questions on the left — score, category, and state — and
        we'll estimate your rank and show colleges within reach.
      </p>
    </div>
  );
}

function RankCard({ score, category, stateSel, air, matches, revealed }) {
  const count = useCountUp(air, revealed);
  return (
    <div className={`card card--result ${revealed ? "card--revealed" : ""}`}>
      <div className="card__header">
        <span className="t-eyebrow">Estimated rank card</span>
        <span className="seal" aria-hidden="true">
          <svg viewBox="0 0 60 60" className="seal__ring">
            <circle cx="30" cy="30" r="27" />
          </svg>
          <ShieldCheck size={16} strokeWidth={1.75} />
        </span>
      </div>

      <div className="card__body">
        <span className="t-eyebrow t-eyebrow--muted">Estimated all-india rank</span>
        <div className="rank-figure">{fmt(count)}</div>

        <div className="fact-row">
          <div className="fact">
            <span className="t-caption">Score</span>
            <span className="t-mono">{score}/720</span>
          </div>
          <div className="fact">
            <span className="t-caption">Category</span>
            <span className="t-mono">{category}</span>
          </div>
          <div className="fact">
            <span className="t-caption">Domicile</span>
            <span className="t-mono">{stateSel}</span>
          </div>
        </div>

        <div className="divider" />

        <span className="t-caption card__section-label">Colleges within reach</span>
        <ul className="college-list">
          {matches.map((c, i) => (
            <li key={c.name} className="college-row" style={{ animationDelay: `${140 + i * 55}ms` }}>
              <div className="college-row__main">
                <span className="college-row__name">{c.name}</span>
                <span className="t-mono college-row__meta">
                  {c.quota} &middot; cutoff ~{fmt(c.cutoff)}
                </span>
              </div>
              <span className={`badge badge--${c.like.tone}`}>{c.like.label}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function InfoModal({ onClose }) {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="modal-scrim" onClick={onClose} role="presentation">
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        onClick={(e) => e.stopPropagation()}
      >
        <button className="icon-btn modal__close" onClick={onClose} aria-label="Close">
          <X size={18} />
        </button>
        <h2 id="modal-title" className="t-display modal__title">About this data</h2>
        <p className="t-body">
          The score-to-rank curve and college cutoffs are illustrative placeholders shaped
          like recent NEET trends — not pulled from NTA or MCC records. Treat every number
          as a rough guide, not a guarantee.
        </p>
        <p className="t-body">
          For real decisions, check your official NTA rank card and the latest MCC or
          state-counselling cutoff lists.
        </p>
      </div>
    </div>
  );
}

/* ============================================================
   App
   ============================================================ */
export default function App() {
  const [data, setData] = useState(null);
  const [loadError, setLoadError] = useState(null);

  const [messages, setMessages] = useState([]);
  const [step, setStep] = useState("score");
  const [scoreText, setScoreText] = useState("");
  const [scoreInvalid, setScoreInvalid] = useState(false);
  const [score, setScore] = useState(null);
  const [category, setCategory] = useState(null);
  const [stateSel, setStateSel] = useState(null);
  const [air, setAir] = useState(null);
  const [showInfo, setShowInfo] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const scrollRef = useRef(null);
  const resultRef = useRef(null);

  useEffect(() => {
    fetch(DATA_URL)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`${r.status}`))))
      .then((json) => setData(json))
      .catch(() => setData(FALLBACK_DATA))
      .finally(() => {
        setMessages([
          { from: "bot", text: "Namaste! I'll estimate your NEET All-India Rank and colleges within reach." },
          { from: "bot", text: "What score did you get, out of 720?" },
        ]);
        requestAnimationFrame(() => setLoaded(true));
      });
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: prefersReducedMotion() ? "auto" : "smooth" });
  }, [messages]);

  useEffect(() => {
    if (step === "done" && resultRef.current && window.innerWidth < 880) {
      resultRef.current.scrollIntoView({ behavior: prefersReducedMotion() ? "auto" : "smooth", block: "start" });
    }
  }, [step]);

  const pushBot = useCallback((text) => setMessages((m) => [...m, { from: "bot", text }]), []);
  const pushUser = useCallback((text) => setMessages((m) => [...m, { from: "user", text }]), []);

  function submitScore() {
    const n = Number(scoreText);
    if (!scoreText || Number.isNaN(n) || n < 0 || n > 720) {
      setScoreInvalid(true);
      pushBot("That doesn't look like a valid NEET score — enter a number between 0 and 720.");
      return;
    }
    setScoreInvalid(false);
    pushUser(`${n} / 720`);
    setScore(n);
    setScoreText("");
    pushBot("Got it. Which category should I use?");
    setStep("category");
  }

  function selectCategory(cat) {
    pushUser(cat);
    setCategory(cat);
    pushBot('And your state of domicile, for state-quota seats? Pick "All-India only" to skip this.');
    setStep("state");
  }

  function selectState(st) {
    pushUser(st);
    setStateSel(st);
    setStep("computing");
    const rank = estimateRank(score, data.scoreRankTable);
    setTimeout(() => {
      setAir(rank);
      pushBot(`Estimated All-India Rank: around ${fmt(rank)}. Your rank card is ready — treat it as a rough guide, not the final word.`);
      setStep("done");
    }, prefersReducedMotion() ? 0 : 700);
  }

  function restart() {
    setMessages([{ from: "bot", text: "New estimate — what score did you get, out of 720?" }]);
    setStep("score");
    setScoreText("");
    setScoreInvalid(false);
    setScore(null);
    setCategory(null);
    setStateSel(null);
    setAir(null);
  }

  if (!data) {
    return (
      <div className="neet-app">
        <GlobalStyle />
        <div className="boot-loading" role="status" aria-live="polite">Loading…</div>
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
    <div className={`neet-app ${loaded ? "is-loaded" : ""}`}>
      <GlobalStyle />

      <header className="app-header">
        <div className="app-header__inner">
          <div className="app-header__titles">
            <span className="t-eyebrow t-eyebrow--accent">NEET Rank Estimator · Unofficial</span>
            <h1 className="t-display app-header__title">Know where you stand</h1>
          </div>
          <button className="btn btn--ghost" onClick={() => setShowInfo(true)}>
            <Info size={15} /> About this data
          </button>
        </div>
        <div className="app-header__inner app-header__inner--steps">
          <ProgressSteps currentIndex={STEP_INDEX[step]} />
        </div>
      </header>

      <main className="layout">
        <section className="card card--chat" aria-label="Estimator conversation">
          <div className="chat-scroll" ref={scrollRef} aria-live="polite">
            {messages.map((m, i) => (
              <div
                key={i}
                className={`bubble-row bubble-row--${m.from}`}
                style={{ animationDelay: `${Math.min(i, 4) * 40}ms` }}
              >
                <div className={`bubble bubble--${m.from}`}>{m.text}</div>
              </div>
            ))}
            {step === "computing" && (
              <div className="bubble-row bubble-row--bot">
                <TypingDots />
              </div>
            )}
          </div>

          <div className="composer">
            {step === "score" && (
              <div className="composer__row">
                <div className={`field ${scoreInvalid ? "field--invalid" : ""}`}>
                  <input
                    type="number"
                    min={0}
                    max={720}
                    value={scoreText}
                    onChange={(e) => {
                      setScoreText(e.target.value);
                      if (scoreInvalid) setScoreInvalid(false);
                    }}
                    onKeyDown={(e) => e.key === "Enter" && submitScore()}
                    placeholder="e.g. 610"
                    aria-label="Your NEET score out of 720"
                    aria-invalid={scoreInvalid}
                  />
                </div>
                <button className="btn btn--primary" onClick={submitScore} aria-label="Submit score">
                  <Send size={15} />
                </button>
              </div>
            )}

            {step === "category" && (
              <div className="composer__chips">
                {CATEGORIES.map((c, i) => (
                  <Chip key={c} onClick={() => selectCategory(c)} autoFocus={i === 0}>
                    {c}
                  </Chip>
                ))}
              </div>
            )}

            {step === "state" && (
              <div className="composer__chips">
                {STATES.map((s, i) => (
                  <Chip key={s} onClick={() => selectState(s)} autoFocus={i === 0}>
                    {s}
                  </Chip>
                ))}
              </div>
            )}

            {step === "computing" && (
              <div className="composer__row composer__row--muted t-caption">Calculating your estimate…</div>
            )}

            {step === "done" && (
              <button className="btn btn--ghost" onClick={restart}>
                <RotateCcw size={14} /> Estimate another score
              </button>
            )}
          </div>
        </section>

        <section className="result-slot" ref={resultRef} aria-label="Estimated result">
          {step === "score" || step === "category" || step === "state" ? (
            <EmptyResultState />
          ) : step === "computing" ? (
            <SkeletonCard />
          ) : (
            <RankCard
              score={score}
              category={category}
              stateSel={stateSel}
              air={air}
              matches={matches}
              revealed={step === "done"}
            />
          )}
        </section>
      </main>

      {showInfo && <InfoModal onClose={() => setShowInfo(false)} />}
    </div>
  );
}

/* ============================================================
   Design system — tokens, type, components, motion
   ============================================================ */
function GlobalStyle() {
  return (
    <style>{`
      @import url('https://fonts.googleapis.com/css2?family=PT+Serif:ital,wght@0,400;0,700;1,400&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

      .neet-app {
        --paper: #F6F4EF;
        --surface: #FFFFFF;
        --surface-sunken: #EEEAE0;
        --ink-900: #1B2A4A;
        --ink-700: #45506B;
        --ink-400: #8B92A3;
        --line: #E3DED0;
        --line-strong: #D3CBB4;
        --accent: #8B2635;
        --accent-soft: #F4E3E1;
        --success: #2F6F4E;    --success-soft: #E3EFE7;
        --info: #2B6070;       --info-soft: #E1EDF0;
        --warn: #93701C;       --warn-soft: #F6EFDC;
        --danger: #A13D3D;     --danger-soft: #F5E3E2;

        --radius-sm: 6px; --radius-md: 10px; --radius-lg: 18px; --radius-full: 999px;

        --shadow-xs: 0 1px 2px rgba(27,20,10,.05);
        --shadow-sm: 0 2px 8px rgba(27,20,10,.06), 0 1px 2px rgba(27,20,10,.04);
        --shadow-md: 0 14px 32px rgba(27,20,10,.10), 0 2px 8px rgba(27,20,10,.05);
        --shadow-focus: 0 0 0 3px rgba(27,42,74,.16);

        --ease-out: cubic-bezier(.16,1,.3,1);
        --d1: 120ms; --d2: 200ms; --d3: 320ms; --d4: 560ms;

        font-family: 'Inter', -apple-system, sans-serif;
        color: var(--ink-900);
        background: var(--paper);
        min-height: 100vh;
        -webkit-font-smoothing: antialiased;
        opacity: 0;
        transition: opacity var(--d3) var(--ease-out);
      }
      .neet-app.is-loaded { opacity: 1; }
      .neet-app *, .neet-app *::before, .neet-app *::after { box-sizing: border-box; }
      .neet-app button { font-family: inherit; }

      @media (prefers-reduced-motion: reduce) {
        .neet-app, .neet-app * { animation-duration: .001ms !important; transition-duration: .001ms !important; }
      }

      /* Typography */
      .t-eyebrow { font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: .1em; text-transform: uppercase; color: var(--ink-400); }
      .t-eyebrow--accent { color: var(--accent); }
      .t-eyebrow--muted { color: var(--ink-400); }
      .t-display { font-family: 'PT Serif', Georgia, serif; color: var(--ink-900); margin: 0; }
      .t-heading { font-family: 'PT Serif', Georgia, serif; font-size: 18px; margin: 0 0 6px; color: var(--ink-900); }
      .t-body { font-size: 14.5px; line-height: 1.6; color: var(--ink-700); margin: 0 0 10px; }
      .t-caption { font-family: 'IBM Plex Mono', monospace; font-size: 10.5px; letter-spacing: .04em; color: var(--ink-400); display: block; margin-bottom: 3px; }
      .t-mono { font-family: 'IBM Plex Mono', monospace; font-size: 14px; color: var(--ink-900); }

      .boot-loading { padding: 48px; font-size: 14px; color: var(--ink-400); text-align: center; }

      /* Header */
      .app-header { border-bottom: 1px solid var(--line); background: var(--paper); }
      .app-header__inner { max-width: 1040px; margin: 0 auto; padding: 22px 24px 16px; display: flex; align-items: flex-end; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
      .app-header__inner--steps { padding-top: 0; padding-bottom: 18px; }
      .app-header__title { font-size: clamp(22px, 3vw, 30px); margin-top: 6px; line-height: 1.1; }

      /* Steps */
      .steps { display: flex; align-items: center; list-style: none; margin: 0; padding: 0; gap: 0; }
      .step { display: flex; align-items: center; gap: 8px; }
      .step__dot { width: 22px; height: 22px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-family: 'IBM Plex Mono', monospace; font-size: 11px; border: 1.5px solid var(--line-strong); color: var(--ink-400); background: var(--surface); transition: all var(--d2) var(--ease-out); flex-shrink: 0; }
      .step__label { font-size: 12.5px; color: var(--ink-400); font-weight: 500; transition: color var(--d2) var(--ease-out); white-space: nowrap; }
      .step__line { width: 28px; height: 1.5px; background: var(--line-strong); margin: 0 10px; transition: background var(--d2) var(--ease-out); }
      .step--active .step__dot { border-color: var(--accent); color: var(--accent); background: var(--accent-soft); }
      .step--active .step__label { color: var(--ink-900); }
      .step--done .step__dot { border-color: var(--success); color: #fff; background: var(--success); }
      .step--done .step__line { background: var(--success); }
      .step--done .step__label { color: var(--ink-700); }

      /* Layout */
      .layout { max-width: 1040px; margin: 0 auto; padding: 24px; display: grid; grid-template-columns: 1fr; gap: 20px; }
      @media (min-width: 880px) { .layout { grid-template-columns: 1fr 1.05fr; align-items: start; } }

      /* Card base */
      .card { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-lg); box-shadow: var(--shadow-sm); }

      /* Chat */
      .card--chat { display: flex; flex-direction: column; height: 520px; overflow: hidden; }
      .chat-scroll { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 10px; }
      .chat-scroll::-webkit-scrollbar { width: 8px; }
      .chat-scroll::-webkit-scrollbar-thumb { background: var(--line-strong); border-radius: 4px; }

      .bubble-row { display: flex; opacity: 0; animation: bubbleIn var(--d3) var(--ease-out) forwards; }
      .bubble-row--bot { justify-content: flex-start; }
      .bubble-row--user { justify-content: flex-end; }
      @keyframes bubbleIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }

      .bubble { max-width: 82%; padding: 10px 14px; border-radius: var(--radius-md); font-size: 14.5px; line-height: 1.5; }
      .bubble--bot { background: var(--surface-sunken); color: var(--ink-900); border-bottom-left-radius: 4px; }
      .bubble--user { background: var(--ink-900); color: #fff; border-bottom-right-radius: 4px; }

      .bubble--typing { display: flex; gap: 4px; align-items: center; padding: 12px 16px; }
      .bubble--typing .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--ink-400); animation: dotPulse 1.1s ease-in-out infinite; }
      .bubble--typing .dot:nth-child(2) { animation-delay: .15s; }
      .bubble--typing .dot:nth-child(3) { animation-delay: .3s; }
      @keyframes dotPulse { 0%, 60%, 100% { opacity: .3; transform: translateY(0); } 30% { opacity: 1; transform: translateY(-2px); } }

      /* Composer */
      .composer { border-top: 1px solid var(--line); padding: 14px; background: var(--surface); }
      .composer__row { display: flex; gap: 8px; }
      .composer__row--muted { color: var(--ink-400); padding: 8px 4px; }
      .composer__chips { display: flex; flex-wrap: wrap; gap: 8px; }

      .field { flex: 1; position: relative; }
      .field input { width: 100%; font-family: 'IBM Plex Mono', monospace; font-size: 15px; padding: 10px 12px; border: 1.5px solid var(--line-strong); border-radius: var(--radius-sm); background: var(--surface); color: var(--ink-900); transition: border-color var(--d2) var(--ease-out), box-shadow var(--d2) var(--ease-out); }
      .field input:focus { outline: none; border-color: var(--ink-900); box-shadow: var(--shadow-focus); }
      .field--invalid input { border-color: var(--danger); animation: shake .32s var(--ease-out); }
      .field--invalid input:focus { box-shadow: 0 0 0 3px rgba(161,61,61,.16); }
      @keyframes shake { 0%,100% { transform: translateX(0); } 25% { transform: translateX(-4px); } 75% { transform: translateX(4px); } }

      /* Buttons + chips */
      .btn { display: inline-flex; align-items: center; gap: 6px; font-size: 13.5px; font-weight: 500; border-radius: var(--radius-sm); border: 1.5px solid transparent; cursor: pointer; transition: transform var(--d1) var(--ease-out), background var(--d2), border-color var(--d2), box-shadow var(--d2); }
      .btn:active { transform: scale(.96); }
      .btn--primary { background: var(--ink-900); color: #fff; padding: 0 16px; height: 40px; }
      .btn--primary:hover { box-shadow: var(--shadow-sm); }
      .btn--ghost { background: var(--surface); color: var(--ink-900); border-color: var(--line-strong); padding: 8px 14px; }
      .btn--ghost:hover { border-color: var(--ink-400); background: var(--surface-sunken); }
      .icon-btn { background: none; border: none; cursor: pointer; color: var(--ink-400); padding: 6px; border-radius: var(--radius-sm); transition: background var(--d2), color var(--d2); }
      .icon-btn:hover { background: var(--surface-sunken); color: var(--ink-900); }

      .chip { border: 1.5px solid var(--line-strong); color: var(--ink-900); background: var(--surface); border-radius: var(--radius-full); padding: 7px 15px; font-size: 13.5px; font-weight: 500; cursor: pointer; transition: all var(--d1) var(--ease-out); }
      .chip:hover { border-color: var(--ink-900); background: var(--surface-sunken); }
      .chip:active { transform: scale(.96); }
      .chip:focus-visible, .btn:focus-visible, .icon-btn:focus-visible { outline: none; box-shadow: var(--shadow-focus); }

      /* Empty state */
      .empty-state { border: 1.5px dashed var(--line-strong); border-radius: var(--radius-lg); min-height: 460px; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 32px; }
      .empty-state__badge { width: 44px; height: 44px; border-radius: 50%; background: var(--surface-sunken); color: var(--ink-400); display: flex; align-items: center; justify-content: center; margin-bottom: 14px; }
      .empty-state__copy { max-width: 280px; margin: 0 auto; }

      /* Result card */
      .card--result { overflow: hidden; }
      .card__header { display: flex; align-items: center; justify-content: space-between; padding: 14px 20px; background: var(--ink-900); }
      .card__header .t-eyebrow { color: rgba(255,255,255,.65); }
      .card__body { padding: 22px 20px; }

      .seal { width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #fff; position: relative; }
      .seal__ring { position: absolute; inset: 0; width: 100%; height: 100%; }
      .seal__ring circle { fill: none; stroke: rgba(255,255,255,.35); stroke-width: 1.5; stroke-dasharray: 170; stroke-dashoffset: 170; animation: sealDraw var(--d4) var(--ease-out) forwards; animation-delay: .1s; }
      @keyframes sealDraw { to { stroke-dashoffset: 0; } }

      .rank-figure { font-family: 'PT Serif', serif; font-size: clamp(34px, 5vw, 46px); line-height: 1; color: var(--ink-900); margin: 2px 0 18px; font-variant-numeric: tabular-nums; }

      .fact-row { display: flex; gap: 24px; margin-bottom: 18px; flex-wrap: wrap; }
      .fact { display: flex; flex-direction: column; }

      .divider { height: 1px; background: var(--line); margin: 4px 0 16px; }

      .card__section-label { margin-bottom: 10px; }

      .college-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 7px; }
      .college-row { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 10px 12px; background: var(--surface-sunken); border-radius: var(--radius-sm); opacity: 0; animation: rowIn var(--d3) var(--ease-out) forwards; transition: background var(--d2); }
      .college-row:hover { background: var(--line); }
      @keyframes rowIn { from { opacity: 0; transform: translateX(-4px); } to { opacity: 1; transform: translateX(0); } }
      .college-row__main { min-width: 0; }
      .college-row__name { display: block; font-size: 13.5px; font-weight: 500; color: var(--ink-900); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .college-row__meta { font-size: 10.5px; color: var(--ink-400); }

      .badge { flex-shrink: 0; font-family: 'IBM Plex Mono', monospace; font-size: 10.5px; padding: 4px 9px; border-radius: var(--radius-full); font-weight: 500; }
      .badge--success { color: var(--success); background: var(--success-soft); }
      .badge--info { color: var(--info); background: var(--info-soft); }
      .badge--warn { color: var(--warn); background: var(--warn-soft); }
      .badge--danger { color: var(--danger); background: var(--danger-soft); }

      /* Skeleton */
      .skel { display: block; background: linear-gradient(90deg, var(--surface-sunken) 25%, var(--line) 37%, var(--surface-sunken) 63%); background-size: 400% 100%; border-radius: var(--radius-sm); animation: shimmer 1.4s ease infinite; }
      @keyframes shimmer { 0% { background-position: 100% 0; } 100% { background-position: -100% 0; } }
      .card__header--skeleton { background: var(--surface-sunken); }
      .skel--eyebrow { width: 140px; height: 11px; }
      .skel--label { width: 160px; height: 11px; margin-bottom: 10px; }
      .skel--figure { width: 200px; height: 42px; margin-bottom: 18px; }
      .skel--fact { width: 64px; height: 30px; }
      .skel--row { height: 44px; border-radius: var(--radius-sm); animation-name: shimmer, rowIn; animation-duration: 1.4s, var(--d3); animation-timing-function: ease, var(--ease-out); animation-iteration-count: infinite, 1; animation-fill-mode: none, forwards; }
      .skel-list { display: flex; flex-direction: column; gap: 7px; margin-top: 16px; }

      /* Modal */
      .modal-scrim { position: fixed; inset: 0; background: rgba(27,42,74,.4); backdrop-filter: blur(3px); display: flex; align-items: center; justify-content: center; padding: 20px; z-index: 20; animation: scrimIn var(--d2) var(--ease-out); }
      @keyframes scrimIn { from { opacity: 0; } to { opacity: 1; } }
      .modal { position: relative; background: var(--surface); border-radius: var(--radius-lg); max-width: 460px; width: 100%; padding: 28px; box-shadow: var(--shadow-md); animation: modalIn var(--d3) var(--ease-out); }
      @keyframes modalIn { from { opacity: 0; transform: translateY(8px) scale(.98); } to { opacity: 1; transform: translateY(0) scale(1); } }
      .modal__close { position: absolute; top: 14px; right: 14px; }
      .modal__title { font-size: 19px; margin-bottom: 12px; }
    `}</style>
  );
}
