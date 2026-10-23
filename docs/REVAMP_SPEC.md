# AI Newsletter Studio — Revamp Specification & Build Prompt

> This document is the full build prompt for turning the original single-file Streamlit
> prototype into a production-grade, modern web application. It is written so it can be
> handed to an engineer (or an AI agent) as-is.

---

## 0. One-paragraph brief

Build **AI Newsletter Studio**: a web app that turns raw company updates (pasted text,
uploaded documents, or URLs) into a polished, brand-accurate, responsive HTML newsletter in
seconds. Users pick a template and brand kit, generate structured content with an LLM,
edit every section inline with a live preview, and export to standalone HTML, email-safe
HTML, Markdown, JSON, or PDF. The app must be secure against hostile input (uploads, URLs,
LLM output), resilient to provider failures, fast, and pleasant to use on desktop and mobile.

---

## 1. What exists today (audit of the prototype)

| Area | Current state | Problem |
|---|---|---|
| UI | One Streamlit script, every widget always visible | No live edit, whole script reruns on every click, no modern look, no mobile layout |
| LLM | Hard-coded Groq model id, plain prompt, regex JSON extraction | Model id typo in working tree (`qwen/qwen3.8-27b`), `llama-3.3-70b-versatile` no longer served, no retries, no JSON mode, no schema validation |
| Templates | 7 near-duplicate Jinja files (dark/light × generic/AVL + v1s) | Colors and logo hard-coded per file, AVL template embeds a 20 KB base64 logo inline |
| Brand | `themes/avl.py` dict | Only one brand, not user-definable, no persistence |
| Images | Unsplash random photo, up to ~20 sequential HTTP calls | Slow, fails silently, no attribution (Unsplash ToS), writes to a single shared `generated/banner.jpg` (race between users) |
| Uploads | Logo/hero written straight to disk with original extension | **SVG upload can carry `<script>`**, no size limit, no MIME sniffing, shared filenames across users |
| Output | Writes `output/newsletter_*.html`, `os.startfile` on server | Server-side file open is wrong in cloud, shared output file across users |
| Deps | 40+ packages incl. `weasyprint`, `sentence-transformers`, `faiss-cpu`, `langchain` | **This is why Streamlit Cloud deploy broke**: weasyprint needs system Pango/Cairo, sentence-transformers pulls PyTorch (~2 GB) and exceeds build/memory limits |
| Security | None | No rate limiting, no input size caps, no CORS policy, secrets committed in `.env` (gitignored, but present locally with live keys) |
| Tests | None | — |

---

## 2. Decisions

### 2.1 Deployment: **Next.js on Vercel + FastAPI on Render (Docker)** — not Streamlit Cloud

Streamlit Cloud is rejected because:
- The UI ceiling is low: no true live preview/editor, no drag-reorder, no custom design system, full rerun model.
- No auth, no rate limiting, no per-user isolation out of the box.
- The deployment already failed because of the dependency footprint and system libraries.

Chosen architecture:

```
┌────────────────────────┐        HTTPS/JSON        ┌───────────────────────────┐
│  frontend/  (Next.js)  │  ───────────────────────▶│  backend/  (FastAPI)       │
│  Vercel (static+edge)  │  ◀───────────────────────│  Render Web Service (Docker)│
│  Tailwind v4, shadcn   │                          │  Groq/OpenAI/Gemini/Ollama │
└────────────────────────┘                          └───────────────────────────┘
```

- Backend is a **single Docker image** so it runs identically on Render, Railway, Fly.io,
  Hugging Face Spaces, or a VPS. Free Render tier cold-start (~30–50 s) is acceptable for a
  portfolio/internal tool; a `/api/health` ping keeps it warm if needed.
- Frontend is a static-first Next.js app, deploys in one click to Vercel from the repo root
  (`frontend/`), and reads `NEXT_PUBLIC_API_URL`.
- The old Streamlit app is preserved under `legacy/` for reference only.

### 2.2 Default LLM

Provider abstraction with runtime-selectable models. Default: **Groq `openai/gpt-oss-120b`**
(verified available on the account, supports `response_format: json_object`, ~0.1 s for a
small call). Fallback chain: `qwen/qwen3.8-27b` → `openai/gpt-oss-20b`. Also supports
OpenAI, Gemini (via OpenAI-compatible endpoint), and Ollama for local/offline use.

---

## 3. Feature set

### 3.1 Input
- Paste text (markdown/bullets/paragraphs).
- Upload `.txt`, `.md`, `.docx`, `.pdf` → server-side text extraction.
- Fetch from URL (article / blog / press release) with SSRF-safe fetcher (public IPs only,
  no redirects to private ranges, size cap, timeout) and readability-style extraction.
- Import an RSS/Atom feed (latest N items).
- Multiple sources are concatenated with headers so the LLM can attribute.

### 3.2 Generation controls
- Newsletter type (Corporate, Weekly, Monthly, Product Launch, Investor, Internal, HR,
  Marketing, Custom instruction).
- Tone (Professional, Executive, Friendly, Technical, Marketing, Minimal, Inspirational).
- Target language (any; output in that language).
- Reading time target, number of highlights, number of sections.
- Optional overrides: hero title, summary, publication date, CTA (label + URL).
- Toggle "include call-to-action block", "include quote/pull-quote", "include stats row".
- Model picker (provider + model) and temperature, with sane defaults.

### 3.3 Brand kit
- Named brand kits stored client-side (localStorage) and exportable/importable as JSON.
- Fields: company, tagline, logo (upload or URL), primary/secondary/accent colors, font pair,
  website, email, phone, address, social links, footer legal text.
- Built-in presets: **Generic** and **AVL** (ported from the prototype).
- Auto-palette: pick a primary color and the app derives a harmonious gradient and
  dark/light surfaces.

### 3.4 Templates
- Template registry in the backend, each a Jinja2 file + metadata (name, description,
  supports dark/light, thumbnail).
- Ship four: **Editorial** (serif, magazine), **Modern** (gradient header, cards),
  **Minimal** (single column, email-friendly), **Bold** (big hero, stats row).
- Every template consumes the **same `Newsletter` JSON schema and the same CSS token set**
  (`--primary`, `--bg`, `--surface`, …). Dark/light is a token swap, not a separate file.
- Email-safe export: tables + inline CSS via `premailer`.

### 3.5 Editing & preview
- After generation, the JSON is the source of truth. Right-hand editor lets the user edit
  hero title, subtitle, summary, each highlight/section (title, icon, body), reorder by
  drag, delete, add, and **"Regenerate this section"** (LLM rewrites one section only).
- Live preview re-renders through `/api/render` on debounce (no LLM call).
- Preview toolbar: desktop/tablet/mobile widths, dark/light toggle, open in new tab.

### 3.6 Images
- Hero: upload, Unsplash search (with required photographer attribution), or generated
  SVG gradient banner (zero network, always works).
- Uploaded raster images are re-encoded through Pillow (strips metadata/polyglots),
  resized to max 1600 px, converted to WebP/JPEG. Uploaded SVGs are sanitized
  (scripts, event handlers, external refs, `foreignObject` removed).
- All images are inlined as data URIs in exports so the HTML is self-contained.

### 3.7 Export & sharing
- Standalone HTML, email-safe HTML, Markdown, JSON, plain text, PDF (browser print with
  print stylesheet; server PDF optional via Playwright in Docker).
- Copy HTML to clipboard; "Open in new tab".
- Local history (last 25 generations) with restore and diff-free re-render.

### 3.8 Quality of life
- Keyboard: `Ctrl/⌘+Enter` generate, `Ctrl/⌘+S` download HTML.
- Streaming progress steps (prepare → generate → validate → images → render).
- Example content button, empty states, skeleton loaders, toasts, error boundaries.
- Fully responsive; panels collapse into tabs under 1024 px.
- Dark/light app theme (system default), reduced-motion respected, accessible focus rings.

---

## 4. Robustness requirements

1. **Schema-validated LLM output.** Pydantic `Newsletter` model with field constraints
   (lengths, counts, emoji icon, enum tone). Invalid → one automatic "repair" call with the
   validation errors fed back → if still invalid, deterministic fallback (normalize what is
   usable, fill defaults) and surface a warning, never a crash.
2. **JSON mode + extraction.** Use provider JSON mode when available; still run a tolerant
   extractor (code fences, leading prose, trailing commas) as the second line of defense.
3. **Retries with backoff** on 429/5xx/timeouts (3 attempts, jitter), per-provider timeouts,
   automatic model fallback chain.
4. **No shared mutable files.** Everything is in-memory per request; uploads live in the
   request or are returned to the client as data URIs. Stateless backend → horizontal scale.
5. **Image fetching is bounded**: max 3 Unsplash queries, 8 s total budget, async, cached
   by query for 1 h, graceful fallback to generated banner.
6. **Typed API contract** (OpenAPI generated by FastAPI; TS types generated from it).
7. **Tests**: parser/repair, sanitizer, renderer snapshot per template, API smoke tests with
   mocked LLM. CI runs `ruff`, `pytest`, `tsc`, `next build`.
8. **Structured logging** with request id, latency, model, token usage; no content logged.

---

## 5. Security requirements

| Threat | Control |
|---|---|
| Malicious SVG logo (XSS when opened as HTML) | Allow-list SVG sanitizer; logos embedded only via `<img src="data:">` |
| Image polyglots / decompression bombs | Pillow re-encode, `MAX_IMAGE_PIXELS`, 5 MB cap, MIME sniff vs. extension |
| Prompt injection via pasted content/URLs | Content is wrapped in delimiters and labelled as untrusted data in the system prompt; output is schema-validated; LLM has no tools |
| HTML injection from LLM output | Jinja autoescape **on**; section bodies pass through `markdown-it` → `nh3` allow-list sanitizer (no scripts, no event handlers, safe URL schemes only) |
| SSRF via "fetch URL" | Resolve DNS first, reject private/link-local/loopback/metadata ranges, http(s) only, no redirect across hosts, 2 MB cap, 10 s timeout |
| Abuse / cost | Per-IP rate limit (`slowapi`), max body 256 KB text, max 4 sources, optional shared `APP_ACCESS_KEY` header for private deployments |
| Secrets | Never in repo; `.env.example` documents them; `.env` stays gitignored; keys only server-side |
| Headers | CORS allow-list from env, `X-Content-Type-Options`, `Referrer-Policy`, `Content-Security-Policy` on app pages; preview iframe is `sandbox`ed |
| Dependency hygiene | Minimal pinned requirements; Docker runs as non-root |

---

## 6. UI specification (frontend)

**Visual language:** calm, editorial, high contrast. Neutral slate surfaces with one
accent (indigo→violet gradient) used sparingly for primary actions and progress. Inter
for UI, generous 8-pt spacing, 12–16 px radii, soft layered shadows, subtle borders.
Dark mode is first-class (system default, toggle in header).

**Layout (≥1280 px):** three columns.
1. **Compose** (left, 380 px): tabs *Content · Settings · Brand*. Sticky "Generate" button
   with model badge and `⌘↵` hint.
2. **Preview** (center, fluid): device-width toggle, theme toggle, zoom-to-fit, open in tab.
   Renders the newsletter in a sandboxed iframe.
3. **Editor** (right, 360 px, appears after generation): outline of the newsletter;
   click a block to edit; drag handles to reorder; per-section regenerate; export panel.

**Layout (<1024 px):** single column with a bottom tab bar: Compose · Preview · Edit.

**Header:** logo + name, template picker (dropdown with thumbnails), history popover,
theme toggle, "Export" split button.

**States:** empty (illustrated hint + "Load example"), generating (stepper with live
status), error (inline, retry), success (toast + editor slides in).

---

## 7. API contract (backend)

```
GET  /api/health                      → { status, version, providers:[…] }
GET  /api/templates                   → [{ id, name, description, supports:["dark","light"], thumbnail }]
GET  /api/brands/presets              → [BrandKit]
GET  /api/models                      → [{ provider, id, label, default }]
POST /api/extract                     multipart file (.txt/.md/.docx/.pdf) → { text, meta }
POST /api/fetch-url                   { url } → { title, text, site }
POST /api/fetch-feed                  { url, limit } → { items:[{title, summary, link, date}] }
POST /api/upload/image                multipart (logo|hero) → { data_uri, width, height, mime }
POST /api/images/search               { query, per_page } → [{ id, thumb, url, author, author_url, download_location }]
POST /api/generate                    GenerateRequest → { newsletter: Newsletter, html, warnings:[…], usage }
POST /api/regenerate-section          { newsletter, section_index, instruction? } → { section }
POST /api/render                      { newsletter, template, theme, brand } → { html }
POST /api/export                      { newsletter, template, theme, brand, format } → file
```

`Newsletter` schema (abridged):

```json
{
  "company_name": "str", "newsletter_type": "str", "language": "en",
  "hero_title": "≤ 90 chars", "subtitle": "≤ 160 chars", "summary": "60–200 words",
  "date": "str", "estimated_read_time": "e.g. 5 min read",
  "highlights": [{ "icon": "emoji", "title": "≤ 60", "subtitle": "≤ 140" }],
  "sections": [{ "id": "uuid", "icon": "emoji", "title": "≤ 80", "content": "markdown 60–220 words" }],
  "stats": [{ "value": "100k", "label": "active users" }],
  "quote": { "text": "…", "attribution": "…" } | null,
  "cta": { "label": "…", "url": "https://…" } | null,
  "image_keywords": ["2–4 words", "…"],
  "hero_image": { "kind": "upload|unsplash|generated", "data_uri|url": "…", "credit": {...} | null },
  "footer": { "tagline": "", "website": "", "contact_email": "", "phone": "", "address": "",
              "socials": { "linkedin": "", "x": "", "instagram": "", "facebook": "", "youtube": "", "github": "" },
              "copyright": "", "subscription_note": "", "privacy_url": "", "terms_url": "", "unsubscribe_url": "" }
}
```

---

## 8. Repository layout

```
AI-newsletter/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, middleware, routers
│   │   ├── config.py          # pydantic-settings
│   │   ├── schemas.py         # Newsletter, BrandKit, GenerateRequest…
│   │   ├── routers/           # health, generate, render, upload, sources, images
│   │   ├── services/          # llm, prompts, parser, renderer, sanitize, images, extract, fetch
│   │   ├── templates/         # editorial.html, modern.html, minimal.html, bold.html, _base.css
│   │   └── assets/brands/     # bundled preset logos
│   ├── tests/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/                  # Next.js 16, TypeScript, Tailwind v4
│   └── src/{app,components,lib,store}
├── docs/REVAMP_SPEC.md        # this file
├── legacy/                    # original Streamlit prototype (reference only)
├── render.yaml                # one-click backend deploy
├── vercel.json                # frontend root config
└── README.md
```

---

## 9. Delivery phases

1. **Foundation** — backend skeleton, schemas, LLM service with JSON mode + repair, sanitizers,
   four templates on shared tokens, `/generate` + `/render`, tests, Docker. Frontend
   scaffold, design system, three-pane layout, generate → preview → download HTML.
2. **Editing** — JSON editor panel, reorder, per-section regenerate, debounced live render,
   history, brand kits with presets, image upload + Unsplash search with attribution.
3. **Sources & export** — file extraction, URL/RSS import, email-safe HTML, Markdown/PDF,
   share links.
4. **Polish & ops** — CI, rate limiting, access key, analytics-free telemetry, docs.

Phase 1 and the core of Phase 2 are implemented in this repository now; the remainder is
scaffolded with clear extension points.

---

## 10. Acceptance criteria

- A first-time user can paste five bullets, press Generate, and download a self-contained
  HTML newsletter in under 15 s with no configuration.
- A malicious SVG upload containing `<script>` never reaches the output HTML.
- Killing the Unsplash key still yields a good-looking hero banner.
- The LLM returning prose + fenced JSON, or JSON with a missing field, still renders.
- `pytest` and `next build` pass in CI.
- The app is usable on a 390 px-wide phone.
