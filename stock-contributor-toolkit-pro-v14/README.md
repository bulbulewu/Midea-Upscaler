# Stock Contributor Toolkit Pro

Free, commercial-grade toolkit for microstock contributors — metadata generation,
keyword research, trend intelligence, portfolio tracking, SVG→video, vectorizer,
and a one-click browser extension.

**Live demo:** deploy to Render.com free tier in minutes (guide below).

## Tools (Phase 1)

| Tool | What it does | Cost |
|---|---|---|
| ◈ **Metadata Studio** | Upload up to 20 images → title (≤70 chars), description, up to 49 ordered keywords each. Edit inline, copy, export **CSV for Adobe Stock**. Built-in free engine; optional Gemini AI upgrade via your own free API key (never stored). | Free |
| ⌕ **Keyword Research — Market Tracker** | Scan Adobe Stock by keyword or contributor ID (your own Apify token, or demo mode): **wrong-Actor guard** (a Google-search Actor's phrases are rejected with guidance + a one-click demo run — never shown as results); KPI Row 1 (Total in Adobe Stock, Total Downloads, Average per Asset, Top Performing Asset with click-to-jump); Score Row 2 (Opportunity Index + verdict + rule-based advice, AI Saturation Barometer, Est. Market Revenue, numeric **Keyword Difficulty KD /100** — documented estimate formula); Seasonality Radar strip with concept suggestions and one-click event tracking; trending chips + Pin; format tabs with counts, AI view filter, per-page paging; per-asset downloads, **D/MO velocity**, estimated revenue (default rate **$0.85**/download, editable), age, Evergreen/Seasonal tag; Winning Keywords; **Batch Send to SEO**; **Master Prompt & 100 CSV** downloads; contributor leaderboard; 15-minute scan cache. | Free (own token) |
| 📅 **Trend Calendar** | 19 seasonal selling events with **upload-by deadlines**, demand levels, and ready keyword sets. Computed live from today's date. | Free |
| ✓ **Title Optimizer** | 8-point QA vs Adobe Stock best practices (title length, keyword count 5–49, top-10 weighting, duplicates, brand-risk terms…) with a 0–100 score. | Free |

## Tools (Phase 2)

| Tool | What it does | Cost |
|---|---|---|
| 📈 **Trend Intel** | Live demand pulse per keyword: Google News article volume (7 days) + seasonal mapping → 0–100 demand score, headlines, related keywords. Free, no key. (A proxy for buyer attention — not Adobe download data.) | Free |
| 💼 **Portfolio Tracker** | Private sales ledger: add assets, log downloads/views/earnings from your dashboards, see totals, per-platform and per-asset stats, 30-day chart. Stored locally in `data/portfolio.json`. | Free |
| 🎞 **SVG → Video** | Static SVG → 1080p30 MP4 with smooth Ken Burns zoom (in/out/static), 3–60 s, H.264 + faststart. | Free |
| ✒ **Vectorizer** | PNG/JPG → layered SVG (one layer per color, 2–16 colors, hole-aware tracing, background removal). Best for logos/icons/flat graphics. | Free |
| 🧩 **StockMeta Helper** | Manifest V3 browser extension (Chrome, Edge, Brave, Opera, Firefox): save metadata once, **auto-fill Adobe Stock / Shutterstock upload pages** in one click. Download from the app's Extension tab. | Free |
| 🧩 **StockMeta Helper** | Manifest V3 browser extension (Chrome, Edge, Brave, Opera, Firefox): save metadata once, **auto-fill Adobe Stock / Shutterstock upload pages** in one click. Download from the app's Extension tab. | Free |

## Tools (Phase 3) — NEW

| Tool | What it does | Cost |
|---|---|---|
| 🚀 **Apify Boost** | **The original app had NO Apify support.** Now: paste your own **free Apify token** (Console → Settings → API & Integrations) → Keyword Research & Trend Intel are upgraded with live Google Search data (related searches + SERP phrases) via `apify/google-search-scraper`, plus a generic runner for **any Actor** in the Apify Store (paste Actor ID + JSON input). Token is sent per-request only, never stored (or set server env `APIFY_TOKEN`). If credits run out / no token, everything falls back to the free built-in engines automatically. | Free (your Apify free-plan credits) |
| 🎬 **Motion Video Studio** | International-standard motion video creator, in the class of MotionHero / EffectCraft / PaperLayer / Smooth.video / GizzMotion / EffectSnap — but 100% free, local, **no watermark**. 1–10 images/SVG → templates (Stock B-Roll, Social Reel, Product Showcase, Slideshow Pro, Logo Sting, Minimal), effects (Ken Burns zoom, pan, **parallax**, pulse), transitions (fade, dissolve, slide, wipe, circle, fade black/white), colour grades (cinematic, vibrant, warm, cool, mono), animated title/subtitle, optional music track with fade-out, ratios **16:9 / 9:16 / 1:1 / 4:5**, 24/25/30/60 fps, H.264 MP4 + faststart for stock/social. Runs entirely on local FFmpeg. | Free |

## Tools (Phase 4) — NEW

| Tool | What it does | Cost |
|---|---|---|
| ✨ **Motion Graphics Pack** | Magnific/Freepik-style motion-graphics **categories**, generated as ORIGINAL procedural templates (nothing copied from any stock library): **Backgrounds** — Aurora Gradient, Golden Particles, Neon Light Trails, Hexagon Wave, Audio Visualizer, Bokeh, Wave Layers, Confetti, Geometric Pulse · **Titles** — Cinematic Title, Bold Title, Lower Third · **Intros & Logos** — Logo Reveal (your PNG or text), Intro Sting, Countdown 5→1 · **Overlays** (black-bg, blend Screen) — Light Leak, Film Grain, Sparkles. 6 colour themes, 16:9 / 9:16 / 1:1 / 4:5, optional background photo. Local FFmpeg+Pillow, no watermark. | Free |
| 🤖 **AI Creativity Hub** | Bring your own **free / free-tier AI keys** — **Gemini** (free, AI Studio), **Groq** (free tier; note: Groq ≠ Grok), **Grok by xAI** (your key/credits — no guaranteed free tier), **OpenRouter** (`:free` models = $0), **Hugging Face** (free token), plus any custom OpenAI-compatible endpoint. Generates commercial, international-demand work: Stock Production Briefs, Adobe Metadata Packs (title + 49 keywords), Motion Concepts + scripts, Social Selling Packs, 10 sellable concepts — in 10 languages. Keys sent per-request only, never stored. Plus **Pollinations** concept art with no key at all. | Free / free-tier (your keys) |

## Tools (Phase 5) — NEW

| Tool | What it does | Cost |
|---|---|---|
| 🎥 **AI Image → Video** | One photo → moving clip. **Local 2.5D Depth-Parallax engine** (free, unlimited): estimates pseudo-depth, splits fg/mid/bg, moves layers at different rates with camera push-in/drift — cinematic motion, not generative morphing. **True generative option:** your own **Replicate** token (Stable Video Diffusion; trial credit for new accounts) or **Hugging Face** token + model ID (note: HF free Inference rarely hosts video models — clear error + local fallback). Keys never stored. | Free local / your provider credits |
| 🛍 **Promo Maker** | Slideshow promos for business stock & social commerce: **Sale Hero** (split screen, price + struck-through old price, rotating SALE starburst, CTA), **Catalog** (multi-product slides with price band, crossfades), **Social Ad** (full-frame, price burst, CTA — 9:16/1:1). Products entered as `Name \| $Price \| $OldPrice`. | Free |
| ✨ Motion Graphics additions | From the user's Magnific PDF: **Galaxy Vortex**, **Comic Burst / Sunburst**, **Greeting Card** (Birthday/festival — a whole category on Magnific) → pack now **21 templates**. | Free |

## Tools (Phase 6 / v7) — NEW

| Tool | What it does | Cost |
|---|---|---|
| 📊 **Adobe Tracker** | Market intelligence for Adobe Stock niches: keyword **or** contributor research via **your own free Apify token** + an Adobe Stock scraper Actor *you* choose in the Apify Store (no Actor is hardcoded — none could be verified, so the field ships empty). KPI row with an **Opportunity Score (0–100, documented formula, labelled estimate)**, Assets Grid + detail modal (copy title/keywords/JSON, one-click "Use these keywords in SEO Studio"), Visual Analytics (downloads histogram, AI-vs-human, formats, top-20 keywords), Top Creators table, CSV/JSON export, Saved Library + Watchlist (browser localStorage), and a **Seasonality Radar** (SUBMIT NOW ≤90 days / PREP ≤150 / UPCOMING; Black Friday computed; Ramadan/Eid & Diwali dates are approximate). **Demo mode** with clearly-labelled fictional data is on by default when no token is set. | Free (your Apify free credit) |
| ◈ **SEO Studio** (Metadata Studio upgraded) | Microstock SEO & keyworder for **EPS · SVG · AI · JPG · PNG · WEBP · MP4 · MOV**, batches of **50**, whole-folder upload. **Auto-Extract** reads metadata already in your files (EXIF/IPTC/XMP/SVG/FFmpeg tags) before generating. **9 marketplace targets** (Adobe, Shutterstock, Pond5, Freepik/Magnific, Dreamstime, Vecteezy, Depositphotos, 123RF, Universal) with per-agency title ranges and keyword caps — Adobe titles target **50–80 chars**, first-10 keyword weighting shown in the chip editor. **Trademark shield:** 300+ brand terms (`backend/data/trademarks.txt`) are stripped from titles/keywords and reported per file. **BYOK panel:** Gemini / Groq / **Mistral** / OpenRouter / Grok / Hugging Face / **Ollama (local, no key)** with Validate & Test; keys are sent per-request only (optionally remembered in *your browser only*). **Embed & ZIP:** writes title/description/keywords + XMP Rating 5 **inside** JPG (EXIF+XMP+IPTC), PNG, SVG and MP4/MOV (stream copy, no re-encode); EPS/AI get an XMP sidecar + marked header block. Every embedded file is **re-opened and read back** before it enters the ZIP — originals are never modified. Per-agency **CSV export** (Adobe layout byte-identical to earlier versions) or a ZIP of all 9. **Image to Prompt** per file (BYOK vision, or a labelled basic built-in prompt). | Free / free-tier (your keys) |

## Tools (Phase 7 / v9) — Promo Maker upgrade

| Tool | What it does | Cost |
|---|---|---|
| 🛍 **Promo Maker v9** | Everything from before, rebuilt as a **scene engine**: **13 templates** (Sale Hero, Catalog, Social Ad + Product Showcase, Flash Sale Countdown, Testimonial, Before/After, Compare, Real Estate Tour, Restaurant Menu, Event/Festival Sale, App Promo, Audiogram) in a gallery with **cached previews**, up to **12 photos**, and a **scene editor** (per-scene duration, transitions fade/slide/zoom/wipe, reorder/duplicate/delete). **AI Script Builder** (brief → Hook→Benefits→Offer→CTA; your own free AI key, or a labelled built-in Basic script with no key) + **Paste-a-Script** splitting; **9 text styles** + **Brand Kit** (logo, colours, business info — saved in your browser) + branded outros; **App Promo device mockups** (2.5D phone/tablet/laptop/browser, tap indicator, screen-recording input) with **transparent WebM** export; **voiceover** (free edge-tts, your own TTS key, or an uploaded narration) with music ducking + **styled captions and .SRT export**; **6 built-in music beds**, a **Jingle Maker** with voice-cached free remixes; **Pexels/Pixabay picker** with your own free key; platform presets, **720p/1080p/4K, 60 fps, GIF, poster and multi-version renders**, and an ffprobe stock-readiness readout on every export. Honest limits: no bundled stock library, no true 3D/timeline, no avatars/voice cloning; audiogram bars are decorative. | Free / free-tier (your keys) |

**Where to get each free key/token (also linked beside every key field in the app):**
- Apify token (free monthly credit): https://console.apify.com/settings/integrations — Actors: https://apify.com/store
- Google Gemini (free tier): https://aistudio.google.com/apikey
- Groq (free tier): https://console.groq.com/keys
- Mistral AI (free tier): https://console.mistral.ai/api-keys
- OpenRouter (`:free` models cost $0): https://openrouter.ai/keys
- Grok / xAI (your key — credits may apply): https://console.x.ai
- Hugging Face (free token): https://huggingface.co/settings/tokens
- Ollama: runs on your own machine — no key at all: https://ollama.com
- Pexels API key (free — Promo Maker stock picker): https://www.pexels.com/api/
- Pixabay API key (free — Promo Maker stock picker): https://pixabay.com/api/docs/
- edge-tts voiceover: no key at all — just `pip install edge-tts` (optional; the app runs without it)

**Honest notes (v7):**
- Tracker numbers come from whichever Apify Actor you pick and are **estimates**, not verified Adobe data; the Opportunity Score is a documented heuristic (demand vs competition vs AI saturation), not an Adobe figure.
- Per-agency CSV layouts follow each agency's **published contributor spec at build date** (e.g. Shutterstock's CSV has no Title column — its Description field carries the title). No agency guarantees ranking or approval, and nothing here claims otherwise.
- XMP Rating = 5 on embed is for organising your own library (Lightroom/DAM sorting) — it does **not** affect agency search ranking.
- Seasonality dates for Ramadan/Eid and Diwali are approximate and flagged as such in the tab.

### Verified metadata rules (baked in)
- Adobe Stock: title ideally ≤ 70 characters; **5–49 keywords**; **first 10 keywords weighted most** in search; single concept per keyword; no brand/trademark terms.

## What's new in v8 — sidebar order, Prompt-to-Motion, accounts & licensing

**Sidebar order:** the left menu now starts with 📅 Trend Calendar, 📊 Adobe Tracker,
✨ Motion Graphics and 🛍 Promo Maker (in that order); everything else follows in its
previous order. Trend Calendar is the default tab on load.

**Top-right menu:** ⚙ Settings · 👑 Admin Panel (admins only) · 🔑 Activate Key · Logout /
Sign In, plus an account chip showing your email and plan (Admin / Trial · Nd left /
Licensed · until date / No license).

**🎬 Create Motion from Image + Prompt (Motion Graphics tab):** upload an image/logo,
describe the motion ("slow zoom in with golden particles orbiting the logo, elegant
glow, dark background"), and the app renders it with its own Image-to-Motion templates.
A built-in interpreter works offline with no key; with your own free Gemini/Groq/Grok/
OpenRouter key the provider interprets the prompt instead — every field is validated
against the app's whitelist either way, and the interpreted plan is shown before the
result. Honest note: this interprets prompts into the app's own templates; it is not
generative video. Free keys: Gemini https://aistudio.google.com/apikey · Groq
https://console.groq.com/keys · Grok https://console.x.ai · OpenRouter
https://openrouter.ai/keys

**Accounts, trial & licenses (local to this install):**
- *First-run setup:* with no accounts yet, Sign In shows **Create Admin Account** —
  the owner creates the one admin account (unlimited, never needs a key). Until setup
  exists — and whenever nobody is logged in — the app runs openly, exactly like v7;
  nobody can be locked out by this system.
- *Register:* normal users get a **7-day free trial** (length/limit are admin policy).
- *Activate Key:* the admin generates email-bound keys like `MTK-PRO-XXXX-XXXX-XXXX`
  (period + daily limit); the user activates with 🔑 Activate Key. Keys work only for
  the email they were generated for, once.
- *Admin Panel (👑, visible only to a logged-in admin; the server returns 403 to
  everyone else):* License Keys Generator with search + status filters, Registered
  Users (deactivate/reactivate), Default Policy Settings, Backup & Restore (JSON
  export/import), and an Admin Guide.
- *Light enforcement:* a logged-in non-admin whose trial/license has expired gets a
  friendly "activate a key" message on job/analyze endpoints; a finite daily limit
  counts those calls per day. Admins and logged-out use are never limited.
- *Security (differs from the reference app on purpose):* passwords are stored ONLY
  as salted PBKDF2 hashes and are **never displayed anywhere** — no master password
  is printed in any dialog. All data lives in `data/auth_store.json` in the app
  folder. **Recovery:** delete `data/auth_store.json` (and `data/auth_store.json.secret`)
  to reset all accounts, keys and counters.

**⚙ Settings (browser-only, localStorage `toolkit_settings_v8`):** Motion Graphics
defaults (quality/FPS/format/duration/speed/intensity, applied to the form), Motion
Studio + Promo defaults, FFmpeg/Python status, an AI Inspector panel (your Gemini/Groq/
Grok keys + primary vision provider + inspection rules — the Trademark rule is wired
to the SEO Studio trademark shield; the Faces/Architecture rules are stored and used
as inspection guidance), 4 accent themes, and a bilingual EN/বাংলা user guide.
Reset All to Defaults restores v7 behaviour; settings are never required.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python build_extension.py   # builds static/stockmeta-helper.zip
python app.py               # opens http://127.0.0.1:5000
```

> **Windows note:** the SVG→Video tool needs the Cairo graphics library for SVG rendering.
> Easiest path: use the Render deployment (Dockerfile installs it). For local Windows,
> install GTK3 Runtime from [tschoonj/GTK-for-Windows-Runtime](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases)
> before `pip install cairosvg`. Everything else runs with plain `pip install`.

## Push to GitHub

```bash
cd stock-contributor-toolkit-pro
git init
git add .
git commit -m "Phase 1: metadata studio, keywords, trends, optimizer, extension"
git branch -M main
git remote add origin https://github.com/YOURNAME/stock-contributor-toolkit-pro.git
git push -u origin main
```

## Deploy free on Render.com

**Option A — Blueprint (fastest):**
1. Go to [dashboard.render.com](https://dashboard.render.com) → **New +** → **Blueprint**, connect your repo.
2. Render reads `render.yaml` and deploys. Done — free plan, auto-deploys on every push.

**Option B — manual:**
1. **New +** → **Web Service** → connect the repo.
2. Runtime: **Docker** (Dockerfile is included), plan: **Free**.
3. Start command is in the Dockerfile; no env vars needed.

> Free tier sleeps after ~15 min idle; first visit wakes it in ~30 s. No database, no API keys, no costs — everything in Phase 1 runs on free services.

## Optional: Gemini AI upgrade (still free)

1. Get a free key at Google AI Studio (aistudio.google.com).
2. Paste it in Metadata Studio's "Gemini API key" field. It's sent with that request only and never stored on the server.

## Optional: Apify upgrade (still free)

1. Get a free token at https://console.apify.com/settings/integrations (Apify Console → Settings → API & Integrations → Personal API token).
2. Paste it in the **Apify Boost** tab and click **Test token**.
3. Then Keyword Research / Trend Intel automatically use it for best results. Or run any Actor directly in that tab.
   Server alternative: set environment variable `APIFY_TOKEN` on Render / your host.

### Apify settings for Adobe Tracker + Keyword Research (v14)

The Adobe Tracker tab and the Keyword Research tab share **one** Apify
setting — the same token + Actor ID, stored only in your browser
(localStorage `apify_shared_v1`). Editing it in either place updates
both:

- **Adobe Tracker tab:** edit the token / Actor ID fields, then click
  **💾 Save**. **🗑 Clear** empties the fields and deletes the saved
  setting from both tabs.
- **Keyword Research tab:** **🔑 Manage Apify Key** → **Save & Apply**
  does the same save; **Remove key** clears the setting everywhere —
  both tabs' fields, status lines and error boxes — and both tabs
  return to Demo data.

An **Actor ID** looks like `username/actor-name` (copy it from the
Actor's page in the Apify Store) or is a bare 10+ character Apify ID.
Anything else — for example a pasted file name such as
`Screenshot 2026-10-24 163420.png` — is rejected on save and again on
the server before any Apify call, with a message explaining the
expected format. If a saved ID no longer exists on Apify, the scan
says so plainly ("Actor not found on Apify…") instead of showing a
raw HTTP 404.

> Honest note on "best results": Apify gives *live web search* data, which is richer than Datamuse alone for trends/keywords. It does not give Adobe Stock's private download data — no external tool can. Free-plan credits are limited per month; heavy Actor runs will exhaust them faster.

## System requirement for Motion Studio
FFmpeg must be installed (free). The included Dockerfile installs it automatically (plus DejaVu fonts for titles). Locally: `sudo apt install ffmpeg` / `brew install ffmpeg` / Windows: ffmpeg.org download, add to PATH.

## Roadmap
- Batch XMP metadata embedding
- Multi-user portfolios (login + database)

## License
MIT — use it commercially, no attribution required.

---

## What's new in v11 (Prompt #4 — Jobs A–E)

Built on v10 in a NEW folder, per the version rule. Nothing outside
these five jobs was changed.

**Job A — Trend Calendar merged into Adobe Tracker.** The separate
Trend Calendar tab is gone; Adobe Tracker is now the first tab and the
default view, and it holds three research views in one place:
Seasonality Radar, Month & Year Trend Explorer, and the new **📅 Full
Year Calendar** (every event sorted by days-left, with upload-by
deadline — red when overdue, amber within 30 days — demand, keyword
chips, UPLOAD NOW / SUBMIT NOW / UPCOMING status, and a Track button
that pins the Watchlist and searches the market). The two backend
datasets (`trends.py` EVENTS + the 64-occasion calendar) are merged
and deduped by normalised name + month; the richer entry wins.
Backends are kept — Trend Intel still uses `trends.EVENTS`.

**Job B — Motion Graphics: one AI key, and the AI decides the motion.**
The tab's two separate key fields became ONE panel — **🔑 AI Key for
Motion Graphics** (provider incl. Custom, optional model, ✓ Check Key
with an inline ✅/❌ verdict, 💾 Save Key). The key is stored only in
the browser (`localStorage: mgfx_byok`, mirroring SEO Studio's
`seo_byok`), auto-loads, and its status pill reads No key / Saved ·
not checked / ✅ Saved · validated / ❌ Saved · check failed. With a
validated key, BOTH "Create Motion from Image + Prompt" and the AI
Brain run the AI as a commercial stock-motion **art director**: vision
read of the image (subject + dominant colours) + the prompt → a strict
JSON plan (template, artwork motion, theme, colours, speed, intensity,
duration, headline, subtext) extended with `commercial_angle` (why the
motion sells / where it's used) and `buyer_category` (logo sting /
product ad / social promo / stock background loop / greeting). The
plan appears BEFORE rendering in an editable **🤖 AI Motion Plan**
card — your edits are what renders. No key → the built-in interpreter
fills the same card, labelled "Built-in plan (no AI key)". Saved key
but the AI call fails → the render STOPS with the error visible and
[Retry AI] / [Use built-in interpreter instead] — never a silent
fallback. A saved-but-unchecked key is auto-checked once before its
first AI use.

**Job C — Title Optimizer tab → 🧩 Subtopic Creator.** One Main Topic
+ Search → **exactly 50 subtopics** as a clean numbered column.
Sources in order: (1) your own free Apify token's real Google related
searches (existing enrichment path), (2) free Datamuse expansion,
(3) a code-visible pattern-modifier library (50+ templates) that tops
the list up to 50. Each line is a clean lowercase 2–6-word phrase,
deduped against everything already on screen, so repeat searches never
repeat a line. Each Search appends a NEW column to the right (header:
topic, #, engine, time — plus a ⚠ warning when Apify failed and free
sources filled in). Per column: **📋 Copy All 50** and **⬇ .txt**;
hover a line to copy just it; double-click a line to drill down into
it; Clear-all sits above the row. Columns live for the session only.
The engine label always states honestly which sources contributed.

**Job D — Keyword Research rebuilt on the RA-Tracker pattern.** The
owner supplied the RA-Tracker desktop app (MIT, PyQt) as the working
pattern; its behaviours were ported (no PyQt, no gaming content):
**Connect** validates the Apify token before any research runs (an
invalid token blocks searching); the validated token is saved and
auto-fills with a Connected ✓ state, and **Disconnect** wipes it —
with one deliberate substitution: the desktop app's RSA-encrypted
credential file is replaced by this app's established browser
localStorage pattern (stated in TESTING.md too). Every result is
cached server-side in `data/keyword_cache.json` keyed by seed +
sources: a repeat search returns instantly with an **⚡ Cached ·
<time>** badge and spends NO Apify credit; **Clear cache** forces a
fresh fetch. Results are grouped by seed in collapsible sections
(newest first); each keyword row opens a detail popover (phrase,
source — Apify related / Datamuse, word count, Copy, **Send →
Subtopic Creator as topic**, **Send → SEO Studio extra keywords**).
A stats strip shows seeds researched / total keywords / cached
lookups / last search time, and keywords that also appear in Tracker
top keywords or your Portfolio top sellers carry a subtle ★ proven
marker. The basket workflow (click to collect, copy basket) and the
free Datamuse engine are unchanged.

**Job E1 — the Title Optimizer moved INTO SEO Studio, upgraded.**
Contributor income is decided by (1) whether buyers FIND the asset —
title + first-10 keywords are the ranking gate; weak metadata means
invisible assets and preventable rejections — and (2) whether they
produce more of what sells (Job E2's job). So title QA now lives where
the metadata is written. All limits come from SEO Studio's
`MARKETPLACE_RULES` (single source of truth; Adobe = titles 50–80
chars, max 49 keywords); the old 17-word brand list is replaced by the
real 367-brand trademark shield with the exact terms reported. It
analyses the currently selected file's title + keywords in one click
(or a pasted set), every failed check has its own **Auto-Fix** plus
**Fix All** (trim at word boundary, sentence-case, strip commas,
delete duplicates, delete trademark terms, split multi-concept
keywords, move title terms into the top 10, pad under-minimum keywords
with clearly-marked Datamuse suggestions), shows before → after with
changes highlighted, recomputes the score live, and **Apply fixes**
writes back into the SEO Studio fields. With a saved SEO BYOK key,
"Suggest 3 better titles" uses AI; without one it returns a labelled
template rewrite.

**Job E2 — Portfolio tells you what to make next.** Import instead of
only typing: dashboard **CSV import** with flexible column mapping
(title/date/downloads/views/earnings detected by header synonyms, the
mapping shown, assets auto-created) plus **bulk paste**. Decision
analytics are computed server-side: totals by platform AND asset type
AND month, earnings/download, earnings/asset, views→download
conversion % per asset, a monthly earnings bar chart (inline SVG), and
Top 10 / Bottom 10 performers. Top-10 assets get **double-down**
actions — [Find similar niches → Adobe Tracker] and [Make more like
this → Subtopic Creator]; assets with 0 downloads after 60+ days are
flagged as **sleeping assets** with [Re-optimise → SEO Studio Title
Optimizer] prefilled. Monthly download/earnings **goals** with a
current-month progress bar and a month-end pace projection (labelled
estimate). **Backup**: export/import the full portfolio JSON. The
data file and API shapes stay backward-compatible (new fields only);
a sample import fixture ships at
`backend/fixtures/portfolio_import_sample.csv`.

Final sidebar order: Adobe Tracker · Motion Graphics · Promo Maker ·
Keyword Research · Subtopic Creator · Trend Intel · Portfolio ·
SVG→Video · Motion Studio · Apify Boost · AI Creativity Hub ·
AI Image→Video · Extension · SEO Studio.

## What's new in v13 (Prompt #5 UPDATED — Market Tracker sharpenings)

Built on v12; only the Keyword Research tab changed. The owner's v11
screenshot showed a connected token returning Google-style phrases
("christmas history", "why is christmas celebrated…") — the scan ran a
Google-search Actor. v13 fixes that class of failure and sharpens the
results page (structure sanity-checked against the owner's reference
PDF; nothing copied but functions):

- **Wrong-Actor guard:** if a live scan's records are mostly NOT asset
  records (a real asset has a title AND a downloads value or an asset
  URL), the scan fails visibly — "⚠ This Actor returned web-search
  phrases, not Adobe Stock asset data…" — with a **[Run in Demo mode
  instead]** button. Phrase data is never rendered and never cached.
  The Manage Key modal now tells you to pick an Actor that returns
  asset records, NOT a Google search scraper.
- **KPI Row 1:** Total in Adobe Stock (the Actor's own total when it
  reports one, else —) · Total Downloads · Average per Asset · **Top
  Performing Asset** (click it to jump to that asset's card).
- **Score Row 2:** Opportunity Index with verdict bands and one
  rule-based advice line · AI Saturation Barometer (% Human | % AI) ·
  Est. Market Revenue at the **new default rate $0.85**/download ·
  **Keyword Difficulty as a number, KD /100** (EASY → RED OCEAN), from
  a documented log-scaled formula (tooltip + code; an estimate — the
  reference does not publish its formula, and one term of the written
  spec arrived truncated, so it is marked as a reconstruction in
  TESTING.md).
- **Header:** [📌 Pin] beside [🔍 Track Market], and Trending chips
  (Wood Texture · Geometric Pattern · Isometric 3D · Cyberpunk ·
  Watercolor · Ramadan) that scan on click.
- **Seasonality Radar strip** in the tab (collapsible, remembered):
  the next 6 demand windows with status, days left, concept
  suggestions and a [Track …] button per event — same feed as the
  Adobe Tracker calendar.
- **Toolbar:** format tabs with live counts, an AI & Non-AI view
  filter, per-page 24 / 48 / 96 / All with a pager, **[Batch Send to
  SEO]** (Winning Keywords of the current view) and **[Master Prompt
  & 100 CSV]** (a template-assembled creation brief .txt + the top-100
  CSV of the current view).

## What's new in v12 (Prompt #5 — Keyword Research becomes a Market Tracker)

The v11 Keyword Research build was patterned on the wrong reference
(the owner confirmed the supplied repo was a mistake) and is REMOVED —
Connect panel, collapsible seed sections, detail popover, stats strip,
★ proven markers, basket, `data/keyword_cache.json` research cache.
The tab is rebuilt as a **stock market-intelligence tracker** in the
style of Adobe Tracker Pro / StockMetadata / RA Graphic Studio's
tracker, reusing this app's own `backend/tracker.py` engine. Bring
your own Apify token via **🔑 Manage Apify Key** (validated, saved in
your browser only, shared Actor ID with the Adobe Tracker tab) — or
run in demo mode on the clearly-labelled fictional sample. Scans are
cached server-side for 15 minutes (`data/market_scan_cache.json`,
token never stored): a repeat scan shows **⚡ Cached** and spends no
Apify credit; force-fresh is a toggle; if a live scan fails, the last
cached result is OFFERED, never silently substituted.

Every asset card shows downloads, **D/MO** (downloads ÷ months since
upload — the one velocity metric the references publish), estimated
revenue at an editable per-download rate (default $0.99, clearly an
estimate), age, and an Evergreen/Seasonal tag from this app's
documented keyword heuristic. Sorts: Relevance, Downloads, Newest,
Featured, Undiscovered (young + below-median downloads + rising D/MO),
Velocity. The KPI header adds **Keyword Difficulty** (this app's own
tier heuristic on the top-10 median downloads — labelled estimate;
the references do not publish a formula) beside the existing
Opportunity Score and AI-saturation bar. **Winning Keywords** lists
the top 30 tags with counts and one-click sends to SEO Studio and the
Subtopic Creator. Contributor mode summarises a creator (mix, upload
rhythm, AI share, best seller) and the leaderboard ranks the scanned
set. Cards carry **[SEO]**, **[AI Prompt]** (vision via your own free
key, or a clearly-labelled basic prompt) and **[Motion]** sends, full
detail expansion with copy buttons, bookmarks, saved searches with
re-open, and CSV / Top-100 CSV / JSON export. A seasonality banner
links matching scans to the Adobe Tracker Full Year Calendar. No
accounts, no credits, no paywall — those parts of the references are
deliberately not copied. The Adobe Tracker tab, Subtopic Creator,
SEO Studio, Portfolio and every other tab are exactly as in v11.
