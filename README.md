# AI Newsletter Studio

Turn raw company updates into polished, brand-accurate newsletters in seconds.
Paste text, drop in a document, or import a URL or RSS feed; pick a template and brand kit;
generate with an LLM; edit every block with a live preview; export as standalone HTML,
email-safe HTML, Markdown, JSON, plain text or PDF.

**Live app:** https://ai-newsletter-livid.vercel.app

The site is private. Open the key icon in the header and either enter the access key you were
given (generation then runs on the site's AI account), or paste your own Groq, OpenAI or Gemini
key to generate on your own account. Personal keys are sent only with your requests and never
stored. The API runs on Render's free tier at https://ai-newsletter-api-v175.onrender.com, so the
first request after a quiet period can take up to a minute while it wakes up.

> v2 is a complete rewrite of the original Streamlit prototype (kept under [`legacy/`](legacy/)).
> The full design brief lives in [`docs/REVAMP_SPEC.md`](docs/REVAMP_SPEC.md).

```
┌────────────────────────┐        HTTPS/JSON        ┌───────────────────────────┐
│  frontend/  Next.js 16 │  ───────────────────────▶│  backend/  FastAPI         │
│  Vercel                │  ◀───────────────────────│  Render (Docker)           │
│  Tailwind v4, zustand  │                          │  Groq / OpenAI / Gemini /  │
│                        │                          │  Ollama · Jinja2 templates │
└────────────────────────┘                          └───────────────────────────┘
```

## Features

- **Inputs**: paste text, upload `.txt/.md/.docx/.pdf`, import an article URL (SSRF-safe) or an RSS/Atom feed; combine several sources.
- **Generation**: newsletter type, tone, output language, reading time, highlight/section counts, optional stats row, pull quote and CTA, headline/summary overrides, free-form editorial instructions, model picker and temperature.
- **Brand kits**: presets (Generic, AVL, …), your own saved kits, logo upload (SVG sanitised, rasters re-encoded), three brand colours with auto-palette, font pairs, contact details, social links, footer legal text. Export/import as JSON.
- **Templates**: Modern, Editorial, Minimal, Bold. All share one JSON schema and one CSS token set, so dark/light is a toggle, not a second file.
- **Editing**: edit headline, summary, highlights, stats, sections, quote, CTA and footer; reorder and delete; "Rewrite" a single section with an instruction; swap the hero image (upload, Unsplash search with attribution, or a generated banner). The preview re-renders live.
- **Export**: standalone HTML (images inlined), email-safe HTML (CSS inlined, variables resolved), Markdown, plain text, JSON, copy to clipboard, open in tab, print/PDF.
- **Robustness**: JSON mode + tolerant extraction + automatic repair pass + schema validation; retries with backoff and a model fallback chain; bounded image fetching with a zero-network fallback banner; stateless backend.
- **Security**: SVG/raster sanitisation, Markdown allow-list, Jinja autoescape, SSRF guard, rate limiting, body-size caps, optional access key, security headers, non-root Docker image, secrets only in env.

## Quick start (local)

Backend:

```bash
cd backend
python -m venv .venv && . .venv/Scripts/activate      # Windows; use .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp .env.example .env                                   # add GROQ_API_KEY (and optionally UNSPLASH_ACCESS_KEY)
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
cp .env.example .env.local                             # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

Open http://localhost:3000, press **Load example**, then **Generate** (or `Ctrl/⌘ + Enter`).

## Deployment

| Part | Where | How |
|---|---|---|
| Backend | [Render](https://render.com) (or Railway / Fly / HF Spaces / any Docker host) | "New → Blueprint" on this repo picks up [`render.yaml`](render.yaml). It prompts for `GROQ_API_KEY`, `UNSPLASH_ACCESS_KEY` (optional) and `APP_ACCESS_KEY` (optional). After the frontend is up, add `CORS_ORIGINS` (plural) in the service's Environment tab with the exact Vercel URL, no trailing slash. |
| Frontend | [Vercel](https://vercel.com) | Import the repo, set **Root Directory** to `frontend` (Next.js is auto-detected), add `NEXT_PUBLIC_API_URL=https://<your-render-service>.onrender.com`. Security headers come from `frontend/next.config.ts`. |

Why not Streamlit Cloud? The original deployment failed because the dependency list pulled in
`weasyprint` (needs system Pango/Cairo) and `sentence-transformers` (PyTorch). Beyond that,
Streamlit cannot provide a live editor, a real design system, per-user isolation or an API.
See the spec for the full decision.

Free-tier note: Render spins the backend down after idling; the first request then takes
~30–50 s. The UI shows a "server may be waking up" message and you can simply retry.

## Environment variables

Backend ([`backend/.env.example`](backend/.env.example)):

| Variable | Purpose |
|---|---|
| `GROQ_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY` | At least one provider. Ollama needs no key (`OLLAMA_BASE_URL`). |
| `DEFAULT_PROVIDER`, `DEFAULT_MODEL`, `FALLBACK_MODELS` | Default `groq` / `openai/gpt-oss-120b` / `qwen/qwen3.8-27b,openai/gpt-oss-20b`. |
| `UNSPLASH_ACCESS_KEY` | Enables stock photo search. Without it a generated banner is used. |
| `CORS_ORIGINS` | Comma-separated browser origins allowed to call the API. |
| `APP_ACCESS_KEY` | Optional shared secret. When set, only people with the key can use the server's provider keys (entered under the key icon in the UI). |
| `ALLOW_BYOK` | Default `true`. Lets visitors paste their own Groq/OpenAI/Gemini key (sent as `X-LLM-Key`, used only for that request, never stored). Such visitors bypass the access key and pay for their own usage. |
| `RATE_LIMIT_GENERATE`, `RATE_LIMIT_DEFAULT` | Per-IP limits, default `10/minute` and `60/minute`. |
| `ENVIRONMENT` | `production` hides `/docs` and disables the Ollama option. |

Frontend: `NEXT_PUBLIC_API_URL`.

## API

Interactive docs at `http://localhost:8000/docs` in development.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Status, version, configured providers |
| GET | `/api/templates` · `/api/brands/presets` · `/api/models` · `/api/fonts` | Catalogs |
| POST | `/api/generate` | Sources + options + brand → validated `Newsletter` JSON + rendered HTML |
| POST | `/api/regenerate-section` | Rewrite one section with an instruction |
| POST | `/api/render` | Re-render edited JSON (no LLM call) |
| POST | `/api/export` | `html` · `email` · `markdown` · `text` · `json` as a download |
| POST | `/api/upload/image?kind=logo\|hero` | Sanitised data URI |
| POST | `/api/extract` · `/api/fetch-url` · `/api/fetch-feed` | Import content |
| POST | `/api/images/search` · `/api/images/select` · `/api/images/generated` | Hero images |

## Development

```bash
# backend
cd backend && ruff check app tests && pytest -q
# frontend
cd frontend && npx tsc --noEmit && npm run lint && npm run build
```

CI runs the same in [`.github/workflows/ci.yml`](.github/workflows/ci.yml) plus a Docker build.

### Adding a template

1. Create `backend/app/templates/<id>.html` that `{% extends "_base.html" %}` and fills `{% block styles %}` (override structural blocks only if needed).
2. Register it in `TEMPLATES` in [`backend/app/services/renderer.py`](backend/app/services/renderer.py).
3. Use only the CSS tokens (`--primary`, `--bg`, `--surface`, `--text`, …) so dark/light and brand colours work automatically.

## Repository layout

```
backend/     FastAPI service (app/, tests/, Dockerfile, requirements.txt)
frontend/    Next.js app (src/app, src/components, src/lib)
docs/        REVAMP_SPEC.md — the design brief / build prompt
legacy/      the original Streamlit prototype, for reference
render.yaml  one-click backend deploy on Render
frontend/next.config.ts  frontend build + security headers (deploy on Vercel with root dir = frontend)
```

## License

MIT
