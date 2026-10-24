# Changelog — Stock Contributor Toolkit Pro v14

## v14 (2026-10-24) — Apify settings bug fix (owner-reported)
Built on v13 in a new folder; scope is ONLY the Apify token/Actor
settings shared by the Adobe Tracker and Keyword Research tabs, plus
one layout fix. Everything else is byte-identical to v13.
- **Pre-delivery amendment (same day, before first delivery):**
  `/api/tracker/search` originally read only `apify_token`/`actor`,
  but the Adobe Tracker tab's UI sends `token`/`actor_id` — so the
  Tracker form was silently treated as "no token supplied" (visible
  in the owner's screenshot). The route now accepts both spellings;
  verified: UI-key payloads reach validation (bad actor → 400) and
  the live-run path (dummy token → Apify 401), demo path unchanged.
- **One shared Apify settings store** (`apify_shared_v1` in the
  browser): both tabs' token/Actor fields are two views of the same
  {token, actor}. Page load initialises both tabs from it; a v13
  keyword-only store is adopted once if the shared store is empty.
  The Keyword scan/modal no longer silently fall back to the Tracker
  tab's field — the store is the only source.
- **Tracker tab gains 💾 Save and 🗑 Clear** next to its token/Actor
  fields (it previously had no way to persist or delete them, so a bad
  value kept resurrecting). Save validates + writes the shared store
  with a confirmation; Clear empties the fields and the store and
  resets the Keyword tab. Test still tests the current field values.
- **Keyword "Remove key" now clears everything:** shared store, legacy
  store, both tabs' fields and status lines, and any visible scan
  error/guard/stale boxes. Both tabs report Demo mode afterwards.
- **Actor ID validation** on every Save (client) and on the server
  (`/api/keywords/scan`, `/api/tracker/search` → HTTP 400 before any
  Apify call): a valid ID is `username/actor-name` or a bare 10+
  character alphanumeric ID; anything with spaces or a file extension
  (e.g. a pasted `Screenshot 2026-10-24 163420.png`) is rejected with
  "That doesn't look like an Actor ID — it looks like a file name…".
  `autocomplete="off"` on all four inputs stops the browser from
  resurrecting old values.
- **Clearer Apify 404:** when a run 404s, both routes now answer
  "Actor not found on Apify — the saved Actor ID '…' doesn't exist.
  Paste the ID exactly as shown on the Actor's Apify Store page…"
  instead of the raw "HTTP Error 404: Not Found".
- **Stale errors clear:** starting a scan in either tab hides that
  tab's previous error box; Clear/Remove hides them immediately.
- **Layout:** the Keyword Research "Contributor" mode button was
  clipped/overlapped by the keyword input — the toggle buttons now
  flex properly inside their column.

## v13 (2026-10-24) — Prompt #5 UPDATED: Market Tracker sharpenings
Built on v12 in a new folder; only the Keyword Research tab, the scan
route and additive `backend/tracker.py` helpers changed. The reference
PDF supplied by the owner (StockMetadata Studio captures) was used to
sanity-check structure only — no theme, branding, wording or data
copied; this app keeps its light theme.
- **Wrong-Actor guard (the headline fix):** a live scan whose normalised
  records are < 50% real assets (title + downloads/asset URL) fails with
  HTTP 422 and the exact guidance message, shows a [Run in Demo mode
  instead] button, never renders phrase data as results and is never
  cached as a successful scan.
- **Revenue default rate $0.85**/download (the reference's implied rate,
  confirmed against its published card arithmetic), still editable.
- **KPI Row 1:** Total in Adobe Stock (Actor-reported total threaded
  through when present, else —) · Total Downloads · Average per Asset ·
  Top Performing Asset mini-card (click scrolls to + highlights the
  asset's card).
- **Score Row 2:** Opportunity Index with verdict bands (LOW / MODERATE /
  HIGH POTENTIAL / VERY HIGH) + one deterministic rule-based advice
  line · AI Saturation Barometer (% Human | % AI + advice) · Est.
  Market Revenue (Avg $/asset subtext) · **numeric Keyword Difficulty
  KD /100** with EASY / MODERATE / HARD / RED OCEAN bands, documented
  log-scaled formula in code + tooltip (the 0.15-weighted third term is
  a documented reconstruction of a truncated spec — see TESTING.md).
- **Search header:** [📌 Pin] (same Saved Searches store as Bookmark) ·
  [🔍 Track Market] · Trending chips (Wood Texture · Geometric Pattern ·
  Isometric 3D · Cyberpunk · Watercolor · Ramadan).
- **Seasonality Radar strip** in the tab: collapsible (state in
  localStorage), fed by the same `tracker.seasonality()` +
  calendar_data topics as the Adobe Tracker calendar (new
  `GET /api/keywords/radar`), [Track <event>] scans in this tab.
- **Results toolbar:** format tabs with live counts (All / Photos /
  Vectors / Illustrations / Videos / Templates / 3D / Audio) · AI &
  Non-AI view filter · per-page 24 / 48 / 96 / All with pager ·
  [Batch Send to SEO] (Winning Keywords of the current view) ·
  [Master Prompt & 100 CSV] (template-assembled master-prompt .txt +
  top-100 CSV — button spec reconstructed from the truncated prompt,
  see TESTING.md).
- Manage Key modal guidance now says: pick an Actor that returns asset
  records (title, downloads, keywords), NOT a Google search scraper.
- Tests: 75/75 in the v13 battery (TESTING.md). Deliberately NOT copied:
  studio accounts / credits / paywalls; unpublished reference formulas
  remain this app's documented heuristics, labelled estimates.

## v12 (2026-10-24) — Prompt #5: Keyword Research → Market Tracker
Built on v11 in a new folder; only the Keyword Research tab changed.
- **Part A — removed the v11 Keyword Research build** (wrong-reference
  RA-Tracker pattern, confirmed a mistake by the owner): Connect panel,
  collapsible seed sections, detail popover, stats strip, ★ proven
  markers, basket UI and their `data/keyword_cache.json` UX.
  `/api/keywords/expand` still responds (Subtopic Creator shares it).
- **Part B — Market Tracker:** Manage Apify Key modal (Test / Save &
  Apply, browser-only `kw_market_byok`, shared Actor ID); keyword +
  contributor scans reusing `backend/tracker.py` (extended additively:
  D/MO, age, lifecycle, est. revenue, Keyword Difficulty, Undiscovered,
  contributor summary, winning keywords); StockMetadata-style cards
  with [SEO] / [AI Prompt] / [Motion] sends; KPI header with Avg D/MO,
  Difficulty and AI saturation; 15-minute server-side scan cache
  (`backend/market_cache.py`) with ⚡ Cached note, force-fresh toggle
  and an explicit stale-cache offer on failure; demo mode on the
  fictional sample (which already carries upload_date values).
  New routes: `POST /api/keywords/scan`, `POST /api/keywords/asset-prompt`.
  Deliberately NOT copied: studio accounts / credits / paywalls.

## v11 (2026-10-24) — Prompt #4: merge + upgrade (Jobs A–E)
Built on v10 in a new folder; nothing outside these five jobs changed.
- **Job A — Trend Calendar merged into Adobe Tracker:** the separate tab is
  gone; Adobe Tracker is now the first/default tab and gains a
  📅 Full Year Calendar panel (merged trends + 64-occasion dataset, deduped
  by normalised name + month) with upload-by deadlines and
  UPLOAD NOW / SUBMIT NOW / UPCOMING status. Backends (`trends.py`,
  `calendar_data.py`, `/api/trends`) kept — Trend Intel still uses them.
- **Job B — Motion Graphics, one AI key:** the two per-panel key fields are
  replaced by a single shared panel (✓ Check Key via `/api/ai/test`,
  💾 Save to browser `localStorage: mgfx_byok`, status pill). With a
  validated key the AI acts as art director and returns an editable
  AI Motion Plan card (now incl. subtext, colours, commercial_angle,
  buyer_category) BEFORE rendering; saved-key AI failure stops the render
  with HTTP 409 — no silent fallback. No key = built-in plan, labelled.
- **Job C — Title Optimizer tab renamed 🧩 Subtopic Creator:** one topic →
  exactly 50 deduped subtopics per search as append-only columns
  (Apify related → Datamuse → pattern-modifier filler; honest engine
  label; ⚠ header warning when Apify fails). New `backend/subtopics.py`,
  `POST /api/subtopics`.
- **Job D — Keyword Research rebuilt RA-Tracker-style:** validate-then-save
  Connect (localStorage substitution for the desktop app's encrypted store,
  stated in TESTING.md), server-side result cache
  (`data/keyword_cache.json`) so repeat seeds cost no Apify credit,
  collapsible per-seed groups with source-labelled rows, detail popover
  (Copy / → Subtopic Creator / → SEO Studio), stats strip, ★ proven markers.
- **Job E1 — Title Optimizer moved into SEO Studio, upgraded:** limits from
  `MARKETPLACE_RULES` (single source; Adobe title 50–80, max 49 keywords),
  full 367-brand trademark shield, per-check Auto-Fix + Fix All with
  before/after, Apply writes back into the result cards, AI/template
  title suggestions via the SEO BYOK key.
- **Job E2 — Portfolio upgraded:** dashboard CSV import (flexible column
  mapping, sample fixture in `backend/fixtures/`) + bulk paste, decision
  analytics (by platform/type/month, earnings/download, conversion %,
  monthly earnings chart, Top/Bottom 10), double-down actions,
  sleeping-asset → re-optimise link, monthly goals + pace projection
  (labelled estimate), JSON backup export/restore. Data shapes compatible.

# Changelog — Stock Contributor Toolkit Pro v10

## v10 (2026-10-24) — three requested fixes only
- **Adobe Tracker — Month & Year Trend Explorer:** new panel under the
  Seasonality Radar. Pick any month + year and see that month's festivals,
  world/international days and seasonal shopping moments, each with stock
  topics, a demand note, days-left and an upload-by tip, plus a Track button
  that runs the Tracker search for it. Data lives in
  `backend/calendar_data.py` (merges the Trend Calendar + Seasonality Radar
  datasets and expands them — every month has 4–6 entries; movable dates
  are marked approx). Endpoint: `GET /api/tracker/month?month=1&year=2028`.
- **Motion Graphics — Create Motion from Image + Prompt (fixed):**
  (a) the image drop zone now accepts **Ctrl+V paste** and **drag & drop**,
  with a thumbnail preview; (b) when you paste an API key, the AI now really
  **sees the image** (subject + dominant colours, which feed the plan's
  colours when your prompt names none) — and if the AI call fails, the
  reason is shown in a visible warning instead of falling back silently;
  (c) the artwork **itself now moves**: plans carry an `art_motion`
  (zoom-in / zoom-out / pan-left / pan-right / sway / breathe) parsed from
  your prompt by both interpreters, combined with the template effect and
  loop-safe; prompt renders also draw the artwork bigger (up to ~88% of
  frame width / ~75% of height via the new `art_scale` parameter).
- **Sidebar:** SEO Studio moved to the **bottom** of the left sidebar
  (after Extension). Nothing else changed.

# Changelog — Stock Contributor Toolkit Pro v9

## v9 (2026-10-24) — Promo Maker upgrade (Promo.com / InVideo / VEED / AI Jingle Maker / Previewed study)
Everything below is inside the **Promo Maker** tab only; all other tabs, the v8
sidebar order, Settings/Admin/auth are unchanged. The three original templates
(sale-hero, catalog, social-ad) keep their exact pre-v9 behaviour — plain calls
still take the untouched legacy engine.
- **Template gallery:** 13 templates with category chips + cached 480p previews —
  new: Product Showcase, Flash Sale Countdown, Testimonial, Before/After,
  Compare, Real Estate Tour, Restaurant Menu, Event/Festival Sale, App Promo,
  Audiogram (plus the original 3). Up to **12 photos** per promo.
- **Scene engine + editor:** promos are now scenes (photo, texts, price,
  duration, transition fade/slide/zoom/wipe/none, voiceover line) with an
  in-page editor (reorder / duplicate / delete / per-scene timing).
- **AI Script Builder + Paste-a-Script:** brief → Hook→Benefits→Offer→CTA
  script via your own free key (Gemini/Groq/OpenRouter/Grok/Mistral through the
  existing AI hub), or a labelled built-in **Basic** script with no key; any
  script splits into editable scenes and applies to the editor in one click.
  Slogan/jingle-line ideas ×3 the same way.
- **Text styles & Brand Kit:** 9 text styles, headline scale, custom
  text/highlight colours, outro styles (simple/website/classic), and a Brand
  Kit (logo + position/size/opacity/watermark, brand colours, business info)
  saved in your browser (localStorage).
- **App Promo:** pure-Python 2.5D device mockups (phone/tablet/laptop/browser
  frame, 7 motion presets, tap indicator, drawn store-badge placeholder or
  your own badge image, screen-recording input) and **transparent WebM**
  export (VP9 alpha, verified) for overlay use.
- **Voiceover & captions:** free **edge-tts** narration (optional package —
  the app runs without it), your own OpenAI-compatible TTS key, or an uploaded
  narration file; scenes auto-extend to fit speech; music **ducking**
  (sidechain, volume fallback); styled captions (karaoke, Hormozi, bold-pop,
  clean ×2, comics) burned in + a downloadable **.SRT**.
- **Music:** 6 built-in license-clean generated beds, upload, a browser-local
  "My Music" list, and a **Jingle Maker** (bed + SFX intro/outro + voice;
  the voice is cached so remixes with a new bed/SFX are free and instant).
- **Stock picker:** search Pexels/Pixabay with **your own free key** and add
  photos (or a screen-recording video) to the promo in one click, with
  creator attribution shown. (No stock library is bundled.)
- **Export:** platform presets (YouTube/TikTok/Reels/Shorts/Feed/Square),
  720p/1080p/4K, 60 fps, GIF + poster frame, **multi-version render**
  (several ratios in one job), and an on-screen ffprobe stock-readiness
  readout on every result.
- Honest limits: no bundled stock mega-library (own-key picker instead), no
  true 3D or multitrack timeline (2.5D mockups + scene list instead), no AI
  avatars or voice cloning (TTS voiceover instead). Audiogram bars are a
  decorative animation, not audio-reactive.

## v8 (2026-10-24) — requested changes only
- **Sidebar reordered:** Trend Calendar, Adobe Tracker, Motion Graphics, Promo Maker
  first (in that order); all other menus follow in their previous order. Trend
  Calendar is now the default tab.
- **Motion Graphics:** new "Create Motion from Image + Prompt" panel — built-in
  offline prompt interpreter + optional own-key AI interpretation (whitelist-
  validated) rendered through the existing Image-to-Motion templates.
- **Top-right menu + local accounts:** Settings / Admin Panel (admin only,
  server-enforced) / Activate Key / Logout / Sign In, account chip; first-run
  admin setup; register with free trial; email-bound MTK-PRO license keys;
  admin key generator, user management, policy settings, backup/restore;
  light daily-limit enforcement for logged-in non-admin users only.
  Passwords are salted PBKDF2 hashes — never stored or shown in plain text.
- **Settings modal:** this app's options only (Motion Graphics defaults,
  render defaults + FFmpeg status, AI Inspector keys/rules, themes, EN/বাংলা
  guide), stored in the browser.

# Changelog — Stock Contributor Toolkit Pro v6

## v6 (2026-10-24) — requested changes only
### App-wide (user requests)
- **Sidebar:** all app menus moved into a fixed left sidebar (collapses to a top bar on narrow screens).
- **Vectorizer removed** completely (tab, page section and API route) — it could not trace screenshots/text acceptably.
- **SVG rendering fixed for modern stock SVGs** (e.g. glass-orbs with gradients/filters): new primary engine
  **resvg** (pip wheel, no DLLs) in `backend/svg_render.py`, ahead of cairosvg / FFmpeg / Edge fallbacks.
  Added `resvg-py` to requirements.txt.

### Motion Graphics — MotionHero-standard rebuild (backend/mgfx.py)
- **Image to Motion (new category):** Breathing Loop, Particle Orbit, Light Sweep Reveal, Parallax Float,
  Ken Burns Photo — the uploaded PNG/logo/photo itself animates (alpha respected, soft shadow, glow).
- **Typography:** bundled OFL fonts (Montserrat, Playfair Display, Poppins) in `assets/fonts/` — no more
  tiny bitmap-font titles on Windows; staggered letter reveals, tracking, word-wrap.
- **Motion system:** easing library (linear / easeInOut / easeOut / easeOutBack / easeOutElastic / smoothstep)
  + keyframe helper; true speed control via quantised integer cycles.
- **Seamless loops by construction** — every periodic motion completes whole cycles (frame-level test in TESTING.md).
- **Visual quality:** supersampling (1.5x HD backgrounds, 2x titles/logos, 1.25–1.5x at 4K), precomputed
  gradients & glow sprites, vignette, resolution-scaled particle counts (>=240 at 1080p) and sizes.
- **Controls:** fast 480p **Preview**, **Intensity** slider, **Speed** slider (0.25–2x), **custom colours**
  (primary/accent/background) overriding themes, **60 FPS**, duration up to 20s.
- **Export:** MP4 or **MOV** (H.264 High, yuv420p, faststart; 4K bitrate-targeted to stay under ~90 MB),
  with an **ffprobe stock-compliance check** returned after every render ("Adobe Stock ready" only when
  codec / resolution / fps / duration all pass).
- All 21 v5 templates kept and upgraded (real rotating confetti, stable film grain, glow/depth on
  Neon Trails & Galaxy Vortex, easeOutBack countdown pop, fixed cinematic subtext path).

### Unchanged
Every other tab (Metadata, Keywords, Trends, Optimizer, Intel, Portfolio, SVG→Video, Motion Studio,
Apify Boost, AI Hub, AI Image→Video, Promo Maker, Extension) works exactly as in v5.
Promo Maker keeps using mgfx THEMES/fonts via compatibility aliases (`_font`, `_ease`, `_text_size`).
