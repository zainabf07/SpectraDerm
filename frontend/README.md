# SpectraDerm — frontend

React + Vite interface for the SpectraDerm API. One flow, no visible model
boundaries: home → scan → analysis → result → explanation → next action.

## Running it

The API first, from your project root:

```bash
uvicorn spectraderm.api.app:app --reload --port 8000
```

Then this frontend:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The dev server proxies `/api` and `/health` to
`http://127.0.0.1:8000`, so the browser stays on one origin and CORS never comes
into play. If your API listens elsewhere, copy `.env.example` to `.env` and set
`VITE_API_PROXY_TARGET`.

`npm run build` writes a static bundle to `dist/`. When serving that bundle from
somewhere other than the API host, set `VITE_API_BASE_URL` to the full versioned
API URL and make sure that origin is in `SPECTRADERM_CORS_ORIGINS`.

## How screens map to the API

| Screen | Call |
| --- | --- |
| First load | `POST /api/v1/users` — one anonymous user per browser, id kept in localStorage |
| New scan | `POST /users/{user}/image-artifacts` → `POST /users/{user}/scans` |
| Analyzing | `POST /scans/{scan}/analyze?user_id=` |
| Result | reads `result.metadata.pipeline`, `vision_result`, `monitoring_result` |
| Why flagged | reads `evidence_result` from the same analyze response |
| Next action | reads `safety_result.professional_assessment_recommended` |
| Find a dermatologist | `POST /scans/{scan}/referrals?user_id=` |
| General skincare | `GET /scans/{scan}/products?user_id=` |
| History | `GET /users/{user}/history` |
| Full report | `GET /scans/{scan}/report?user_id=` |

## Things worth knowing

**The spectral view is real output, not a filter.** The false-colour image, the
representative band and the ROI spectrum all come from
`metadata.pipeline.spectral_visualization`, which the API builds from the MST++
reconstruction. When `SPECTRADERM_MSTPP_CHECKPOINT` is not configured, the API
reports the reconstruction as unavailable and the viewer says so instead of
faking an image. Nothing is invented client-side.

**The quality gate runs before the result.** If `vision_result.overall_status` is
`insufficient_quality`, the app routes to the retake screen and never shows a
score for that photo.

**Scores are cached locally for the timeline.** `GET /users/{id}/history` returns
scan records without change scores or thumbnails, so the history screen merges in
a small localStorage cache written after each analysis. It is display-only; the
API stays the source of truth. Opening an old scan re-runs `analyze`, so its
score can shift as your history grows.

**The safety agent owns the branching.** The frontend never decides between the
referral path and the skincare path — `professional_assessment_recommended` does,
and the backend already closes off whichever path does not apply.

**Wording is deliberate.** The product observes, records and compares — it never
detects, flags, warns or alerts. "Estimated spectral information", never "NIR
image" or "hyperspectral photo". The difference score is framed as distance from
your own baseline, never as a probability. That language lives in
`src/lib/analysis.js` so it cannot drift screen to screen; the full table is in
`DESIGN.md`.

## Design system

`DESIGN.md` is the visual constitution: tokens, type scale, spacing, component
rules and the language table. Every future feature inherits it. If something new
needs a value that is not there, extend `src/styles.css` rather than styling a
screen on its own.

## Layout

```
src/
  api/client.js        every endpoint, one place
  lib/analysis.js      orchestrator payload → plain-language view model
  lib/store.js         localStorage: user id, thumbnails, score cache
  components/          ScoreMeter, SpectralViewer, TrendChart, primitives
  screens/             one file per screen in the flow
  App.jsx              routing + the scan flow
  styles.css           design tokens and all styling
```

No CSS framework and no router dependency — React and Vite only. All styling
comes from the tokens in `src/styles.css`.
