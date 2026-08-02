# NEET Rank Estimator

A chat-style widget that estimates a NEET All-India Rank from a score, then
shows sample colleges within reach based on category and domicile state.

**The bundled data is illustrative, not official.** See "Making the data
real" below before treating any output as trustworthy.

## Run it locally

```bash
npm install
npm run dev
```

Opens at `http://localhost:5173`.

## Deploy it (free, ~5 minutes)

1. Push this folder to a new GitHub repo.
2. Go to [vercel.com](https://vercel.com) (or [netlify.com](https://netlify.com)) → New Project → import the repo.
3. Framework preset: **Vite**. Build command: `npm run build`. Output directory: `dist`.
4. Deploy. You get a live `https://your-project.vercel.app` URL, and it
   auto-redeploys every time you push to GitHub.

## Making the data real

All predictor data lives in `public/data.json` — the app fetches it at
runtime (see `DATA_URL` in `src/App.jsx`), so you never have to touch
component code to update numbers.

**`scoreRankTable`**: pairs of `[score, all-India rank]`. Coaching
institutes (Aakash, Allen, Physics Wallah, etc.) publish score-vs-rank
tables from the previous year's actual results — that's the most realistic
source, since NTA doesn't publish a live formula.

**`colleges`**: each entry needs a `name`, `quota` (`"AIQ"` or `"State"`),
`state` (domicile state for State-quota seats, `null` for AIQ), and a
`cutoffs` object with a closing rank per category. Real cutoffs are
published as PDFs:
- All-India Quota: [mcc.nic.in](https://mcc.nic.in)
- State quota: each state's own counselling authority site

These are published **per round** during counselling season, so genuinely
"live" cutoffs mean re-checking after each round, not a one-time update.

### Two ways to update data

- **Redeploy each time**: edit `public/data.json`, commit, push. Vercel/Netlify
  auto-rebuilds. Simple, but the data is frozen until your next push.
- **No redeploy needed**: host `data.json` elsewhere (a GitHub raw file, a
  Supabase storage bucket, your own small API) and change `DATA_URL` in
  `src/App.jsx` to that URL. Now editing the JSON file alone updates the
  live site instantly.

## Project structure

```
public/data.json     ← all predictor data (edit this, not the components)
src/App.jsx           ← the whole app
src/main.jsx           ← React entry point
```
