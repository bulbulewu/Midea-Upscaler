# How to test — 10-minute checklist

## v14 verification results (2026-10-24, this build machine) — 52/52 passed
Battery: Flask test client against a scratch copy (counting stub in
place of `apify_intel.run_actor_sync`, so no real Apify call was made
or needed), `node --check` on the extracted inline script, static
assertions on the served page, and direct evaluation of the shipped
client-side validator in node. Only tallies seen complete are recorded.

- **Actor ID validation — server unit cases (8/8):**
  `tracker.actor_id_error` accepts `user/adobe-stock-scraper`, a bare
  17-char alphanumeric ID, `apify/google-search-scraper`, and empty
  (Demo/missing paths unchanged); rejects
  `Screenshot 2026-10-24 163420.png` (message names the file-name
  problem + the `username/actor-name` format), `my actor`, `photo.jpg`,
  and a too-short bare `abc`.
- **Client validator parity (8/8):** the actual `apifyActorError`
  function was extracted from the shipped page and evaluated in node —
  identical verdicts on all 8 cases, and the file-name message is the
  exact specified wording.
- **Server enforcement (stub call-counted):** POST /api/keywords/scan
  and POST /api/tracker/search with actor
  `Screenshot 2026-10-24 163420.png` + a dummy token → **HTTP 400**,
  `invalid_actor: true`, the file-name message, and the stub's call
  count stays **0** (validation runs before the cache lookup and before
  any Apify call).
- **Clearer 404:** with the stub raising an Apify HTTP 404, both routes
  return **502** with "Actor not found on Apify — the saved Actor ID
  'user/no-such-actor' doesn't exist. Paste the ID exactly as shown…"
  instead of the raw "HTTP Error 404: Not Found".
- **Wrong-Actor guard regression:** phrase-shaped stub items still →
  **422** + `wrong_actor: true`; asset-shaped items → 200 with records;
  an identical repeat scan is served from the 15-minute cache with no
  new stub call.
- **Shared store — code level (static assertions on the served page,
  16 checks):** `apify_shared_v1` get/set/clear helpers present;
  one-time migration from the legacy `kw_market_byok` store present;
  page-load init calls `apifyInitFields()`; Tracker 💾 Save / 🗑 Clear
  buttons present; `autocomplete="off"` on all four token/actor inputs
  (#ttoken, #tactor, #mktoken, #mkactor); the scan payload reads
  `saved.actor` from the store only (the `$('tactor')` DOM fallback is
  gone from both the scan and the modal open); the extracted Remove key
  handler calls `apifySharedClear()`, clears both tabs' fields and
  hides both error boxes; Tracker Save validates via `apifyActorError`
  before `apifySharedSet`; starting a scan in either tab hides that
  tab's previous error box; the Contributor toggle buttons carry the
  `flex:1 1 0; min-width:0` fix. These are static/DOM-source level
  checks, not a clicked-through browser session — no jsdom was
  available on this machine.
- **Regression:** home 200; sidebar order identical to v13 (tracker,
  mgfx, promo, keywords, subtopics, intel, portfolio, svgvideo, motion,
  apify, aihub, aivideo, extension, studio); demo scan 200 with 24
  records, rate 0.85, KD present; radar 6 events; Subtopics exactly 50;
  tracker month endpoint 200; inline script `node --check` clean.
- **Packaging:** the extracted deliverable ZIP was boot-tested (home
  200, demo scan 200); `START-WINDOWS.bat` verified CRLF (0 bare LF);
  no `__pycache__`, market-cache or auth files inside the ZIP.

## v13 verification results (2026-10-24, this build machine) — 75/75 passed
Battery: `run_v13_tests.py` (Flask test client + node), run with
`TOOLKIT_MARKET_CACHE` / `TOOLKIT_AUTH_FILE` pointed at temp files so no
real data was touched. Only tallies actually seen complete are recorded.

- **Part A absence re-asserted:** the served page contains none of the
  v11 ids/copy (`kwconnect`, `kwdisconnect`, `kwconnstate`, `kwtoken`,
  `kwlabel`, `kwclearcache`, the "Connect once" / "never pay twice"
  lines), and `kw_scan`'s source never calls `enrich_keyword`.
- **Wrong-Actor guard (headline fix):** 5 phrase-shaped stub items
  (question titles + snippets, no downloads/URLs) normalise to 5 records
  with 0 assets → guard `ok=False`. Via HTTP with a stubbed runner the
  scan returns **422**, `wrong_actor: true`, the exact guidance message,
  **no `records` key**, and the market-cache entry count is unchanged
  (the failure is never cached as a scan). The guard is silent on the
  24-record demo sample and on an asset-shaped stub (200, 2 records —
  the metadata item is dropped by normalisation). The guard box's
  [Run in Demo mode instead] path (scan with `demo: true`) returns 200
  with demo records.
- **Total threading:** the asset stub's first item `{"totalResults":
  123456}` surfaces as `kpis.total_in_stock == 123456`; a demo scan has
  `total_in_stock == None` (UI shows "—", subtext "N loaded in session").
- **KPI math (hand-checked fixture, today fixed at 2026-10-24):**
  records 1200 dl / 2024-10-24, 500 dl / 2025-04-24, 300 dl /
  2026-09-24 → D/MO 50.0 (1200 / (730/30.4375) months) and 27.8
  (500 / (548/30.4375)); total downloads 2000; average per asset 667;
  top asset = the 1200-download record with D/MO 50.0; revenue at the
  new **$0.85** default = $1700.00 total / $566.67 per asset; at $0.35 =
  $700.00 (the rate is honoured everywhere). Scan payloads now default
  `rate` to 0.85 (asserted over HTTP).
- **KD hand-computed (formula: 100 × (0.6·L(top-10 median DL, cap 100k)
  + 0.25·L(total in Adobe Stock else loaded size, cap 200M) +
  0.15·L(full-set median DL, cap 100k)), L = log10(1+v)/log10(1+cap)):**
  - Fixture A — 10 records × 100 dl, no actor total: terms 0.240516 +
    0.031365 + 0.060129 = 0.332010 → **KD 33 (EASY)** ✓ matches code.
  - Fixture B — 10 × 50,000 + 10 × 2,000 dl, actor total 5,000,000:
    terms 0.563875 + 0.201746 + 0.140969 = 0.906590 → **KD 91
    (RED OCEAN)** ✓, advice line "Dominated by legacy high-download
    assets — focus on specific niche subtopics."
  - Fixture C — the KPI fixture above (medians 500/500, total 3):
    **KD 42 (MODERATE)** ✓. Empty set → score None.
  - Opportunity verdict bands asserted at every boundary: 0/39 LOW,
    40/59 MODERATE, 60/79 HIGH POTENTIAL, 80/100 VERY HIGH.
- **Format counts + paging (node, eval'ing the page's own MK-V13 block
  verbatim):** `mkFormatCounts` on the demo sample = {all 24, photo 12,
  vector 6, illustration 3, video 3} — matching the server-side fixture
  composition exactly; photo filter → 12 rows; `mkPageSlice` page 2 at
  10/page → rows 11–20 of 24, 3 pages; per-page "all" → 24 rows;
  master-prompt text contains the "Keyword Difficulty (KD): 42/100"
  line and the top-asset title; top-100 CSV of the 24-row set = 25
  lines (header + 24).
- **Demo fixture integrity (sharpening 9):** all 24 sample records
  already carry `upload_date` AND `views` (verified) — no fixture
  change was needed; Row-1/Row-2 cards demonstrate fully in demo mode.
- **Seasonality Radar:** `GET /api/keywords/radar` → 200, 6 events,
  every event has concepts + scan keyword + status (same
  `tracker.seasonality()` feed as the Adobe Tracker calendar;
  concepts prefer calendar_data topics, seasonality ideas as fallback).
- **Cache regression (unchanged from v12):** stub-runner scan fetched
  once; identical repeat returned `cached: true` with no new fetch;
  force-fresh fetched again; aged entry + failing runner → **502 with
  `stale_available`**; `use_stale` → **200** stale payload.
- **Full regression:** home 200; sidebar order identical to v12
  (tracker, mgfx, promo, keywords, subtopics, intel, portfolio,
  svgvideo, motion, apify, aihub, aivideo, extension, studio);
  Adobe Tracker demo search 200 with records; Tracker calendar 64
  events; Subtopic Creator returns exactly 50; `/api/keywords/expand`
  200; Promo templates 13; auth state 200; served page JS passes
  `node --check`. `backend/tracker.py` diff vs v12 is purely additive
  (0 lines removed); only `app.py`, `backend/tracker.py` and
  `templates/index.html` changed (plus README / CHANGELOG / TESTING).

### v13 assumptions & reconstructions (read before judging the numbers)
The updated Prompt #5 text was truncated mid-KD-formula in transmission
(~3,600 characters lost, unrecoverable). These parts were reconstructed
and are documented here, per the build instructions:
1. **KD third term.** The visible text fixed 0.6·(top-10 median
   downloads, log-scaled, cap 100k) + 0.25·(total-in-Adobe-Stock,
   log-scaled, cap 200M) and cut off. The remaining 0.15 weight is
   assigned to the **full-set median downloads** (same cap) — the one
   competition signal not already used (result-set size serves as the
   0.25 term's fallback). The owner's reference PDF shows KD only as a
   number + verdict + advice, which this matches; the PDF does not
   publish a formula, so it could not disambiguate the term.
2. **[Master Prompt & 100 CSV].** The button exists in the reference UI
   (confirmed in the PDF) but its output is never shown. Implemented
   as: a template-assembled creation-brief .txt (niche snapshot +
   top-10 selling assets + winning keywords + an originality brief)
   plus a CSV of the top 100 of the current view with the app's
   computed columns. The optional AI polish mentioned in the brief was
   NOT wired (the spec said "may"); the no-key template path is the
   shipped behaviour and the file says it is template-assembled.
3. **Radar status chips.** The reference mixes "SUBMIT NOW", "50D
   LEFT", "HIGH DEMAND" and "PREP STAGE" labels inconsistently; this
   app keeps its documented status rule (SUBMIT NOW ≤ 90 days, PREP
   ≤ 150, else UPCOMING) and always shows the days-left number.
4. **Guard denominator.** The guard ratio is computed over the
   normalised record list (junk items that normalisation drops are
   excluded); an empty result set passes the guard (a legitimately
   empty niche result is not wrong-Actor data).
5. **Revenue display.** The reference appears to sum per-asset rounded
   values (its $399,507 vs 469,999 × $0.85 = $399,499); this app keeps
   exact arithmetic on totals and rounds only for display.

### NOT live-tested in v13 (same standing caveat)
- A real live scan needs the owner's own Apify token + a self-chosen
  Adobe Stock scraper Actor on his machine (this VM's proxy blocks
  provider calls). All failure paths — wrong Actor, outage + stale
  offer, demo fallback — are test-proven with stubbed runners.
- Browser-only behaviours (Pin/trending/radar clicks, format tabs,
  pager, top-asset scroll/highlight, downloads) are code-verified and
  JS-syntax-checked, not clicked through — this agent has no browser.
- Deliberately NOT copied from the references: studio accounts /
  credits / paywalls, dark theme, branding, wording and data. Their
  unpublished formulas (Opportunity, KD, revenue) remain this app's
  documented heuristics, labelled estimates everywhere they appear.

## v10 verification results (2026-10-24, this build machine) — 35/35 passed
- **Tracker Month Explorer:** `GET /api/tracker/month?month=1&year=2028` → 200,
  5 items incl. New Year with ≥3 topics each, all with days_left + submit_tip
  + type. All 12 months of 2027 return ≥3 items (counts: Jan 5, Feb 6, Mar 6,
  Apr 6, May 6, Jun 6, Jul 5, Aug 4, Sep 5, Oct 5, Nov 5, Dec 5). The served
  page contains the Month/Year controls.
- **Prompt panel:** served page contains the Ctrl+V paste handler + the hint
  text, the drag-&-drop handler and the thumbnail element.
- **AI honesty:** interpret with a deliberately invalid Gemini key → HTTP 200,
  plan source = "builtin", and a visible `ai_note` reason ("AI interpretation
  unavailable (The read operation timed out); used the built-in interpreter.")
  — no crash, no silent fallback. (On this VM the provider call times out;
  with a valid key the AI path returns subject + dominant colours.)
- **Plan parsing:** "slow zoom in with golden particles orbiting the logo" →
  kind=img-orbit AND art_motion=zoom-in; "pan left" → pan-left; "pan across"
  → pan-right; "gentle sway" → sway; quoted text "Bulbul Studio" extracted;
  unspecified image plans default to art_motion=breathe; no-image plans get
  art_motion=none.
- **Artwork motion (objective):** preview renders of img-orbit with the plan
  (art_scale 0.88/0.75): centre-region mean |diff| between t≈0 and t=50% =
  **48.51**; isolating the zoom (zoom-in vs art_motion=none at t=50%, same
  seed/particles) = **34.44** — the artwork itself measurably moves now.
  Meta records art_motion=zoom-in, art_scale=[0.88, 0.75].
- **Loop seam preserved** (frame 0 vs final frame, with art_motion=zoom-in):
  img-orbit **0.004**, img-breathing **0.000** (threshold < 0.5).
- **Regression:** home 200; /api/auth/state 200; Tracker demo search = 24
  records; /api/promo/templates lists 13; classic mgfx preview job completes;
  legacy promo (sale-hero) job completes; the end-to-end prompt job (user's
  exact scenario) completes with plan kind=img-orbit + art_motion=zoom-in and
  ffprobe stock check = Adobe Stock ready. Sidebar order asserted equal to
  the v10 spec with SEO Studio last; no "Vectorizer" in the page.
- Full log: 35 checks, 35 passed, 0 failed (single complete run).

## v10 manual checks
1. **Adobe Tracker** → Month & Year Trend Explorer → pick January / 2028 →
   "Show Topics" → New Year, Orthodox Christmas, MLK Day, Education Day and
   Winter Sports cards appear with topics + upload-by tips → "Track" runs a
   Tracker search for that event.
2. **Motion Graphics → Create Motion from Image + Prompt** → copy any
   screenshot, click the image box, press **Ctrl+V** → thumbnail appears →
   prompt: `slow zoom in with golden particles orbiting the logo` →
   Interpret & Create Motion → the logo itself grows while particles orbit.
3. **Left sidebar** → SEO Studio is now the last menu item.

## Start the app
- **Windows:** FIRST right-click the ZIP and choose **Extract All** (do not run it from inside the ZIP). Then open the extracted folder and double-click `START-WINDOWS.bat` — the window now stays open even if something goes wrong, so you can read/photograph any error.
- **Mac/Linux:** `chmod +x start-mac-linux.sh && ./start-mac-linux.sh`
- **Manual (any OS):**
  ```bash
  python -m venv .venv
  # Windows: .venv\Scripts\activate   |   Mac/Linux: source .venv/bin/activate
  pip install -r requirements.txt
  python app.py
  ```
- Browser opens **http://127.0.0.1:5000** — if not, type that address yourself.
- You should see sidebar tabs in this order (v10): **Trend Calendar**, **Adobe Tracker**,
  **Motion Graphics**, **Promo Maker**, Keyword Research, Title Optimizer, Trend Intel,
  Portfolio, SVG→Video, Motion Studio, Apify Boost, **AI Creativity Hub**, **AI Image→Video**,
  Extension, **SEO Studio** (moved to the bottom in v10).
  (Vectorizer was removed in v6, per request.)

## Fast tests (no API key needed) — in this order
1. **Trend Calendar** tab → event cards load with dates. ✅ page works.
2. **Keyword Research** → type `beach` → Search → keyword chips appear. ✅ internet APIs work.
3. **Metadata Studio** → upload any JPG named e.g. `beach-sunset-family.jpg` →
   Generate Metadata → title + keywords appear → Export CSV downloads. ✅ core engine works.
4. **Motion Graphics** → type: *Aurora Gradient*, Ratio 1:1, Duration 2 → Create →
   progress reaches 100% → an MP4 previews and downloads. ✅ video engine works.
   Then try *Greeting Card* with text `Happy Birthday!`.
5. **Motion Studio** → upload 2 photos → Template *Social Reel*, 2 sec/image → Create → MP4. ✅
6. **Promo Maker** → upload 1–2 product photos, paste in the Products box:
   ```
   Leather Wallet | $24.99 | $49.99
   Wireless Earbuds | $39.99 | $79.99
   ```
   Headline `Eid Sale - Up To 50% Off`, CTA `Shop Now`, Template *Sale Hero* → Create → MP4 with prices. ✅
7. **AI Image→Video** → Engine *Local 2.5D Parallax*, upload 1 photo, Duration 3 →
   Create. Expect roughly 30–60 seconds of rendering for a 3 s 1080p clip on a typical PC. ✅
8. **AI Creativity Hub → Pollinations** (bottom, no key): type an image idea → Generate → picture appears. ✅

## Tests that need YOUR free keys (optional)
- **Apify Boost** tab: paste your token from console.apify.com/settings/integrations → *Test token*
  should show your Apify username. Then Keyword Research gets live Google data.
- **AI Creativity Hub:** pick Gemini (free key: aistudio.google.com/apikey) or Groq
  (free: console.groq.com/keys) → paste key → *Test key* → then Generate a
  *Commercial Stock Production Brief* for e.g. `ramadan iftar family dinner`.
  Keys are never saved — closing the page clears them.

## Common problems
| Problem | Fix |
|---|---|
| `python is not recognized` | Reinstall Python and tick **Add python.exe to PATH** |
| Video render says **FFmpeg not found** | Windows: `winget install ffmpeg`, reopen the launcher. Mac: `brew install ffmpeg`. Linux: `sudo apt install ffmpeg` |
| `Address already in use` (port 5000) | Close the other copy, or run `python app.py --port 5050` and open http://127.0.0.1:5050 |
| SVG→Video / Vectorizer error on Windows (Cairo) | Only those two tabs need the Cairo library on Windows — easiest fix is the free Render deployment (Dockerfile below), everything else works locally |
| Render seems slow | Normal for 1080p on CPU. Test with Duration 2–3 s and Ratio 1:1 first |
| AI/Apify test fails | Check the key belongs to that exact provider, model name is right, and free quota remains |

## No-install alternative: free online test (Render)
1. Put this folder in a GitHub repo → render.com → **New + → Blueprint** (it reads `render.yaml`,
   Docker installs FFmpeg + fonts for you). Free tier sleeps when idle; first open takes ~30 s.
2. Optional on Render: add environment variable `APIFY_TOKEN` if you want Apify always on.

## Stopping
Press **Ctrl+C** in the launcher window, or just close it.

## What's new in v5 (from your 5 screenshots)
1. SVG→Video + Motion Studio SVGs: no Cairo/GTK needed anymore — rendering falls back to FFmpeg / Edge automatically. Errors are short & friendly now.
2. Vectorizer: up to 32 colors + edge-preserving smoothing + an honest warning when an image (screenshot/text) can't trace cleanly.
3. Motion Graphics: Quality HD/4K, Motion speed control, AI Brain (reference image + free Gemini/Groq/Grok/OpenRouter key → auto template/theme/headline), Adobe Stock export notes.
4. Every API key / token field now has a clickable link to get it free.
5. Promo Maker pro controls: badge text + on/off, brand name, photo animation (zoom in/out/pan/static), catalog band top/bottom, 2s end card, background music.

## v6 verification results (2026-10-24, this build machine)
- Smoke test: all 26 Motion Graphics templates (21 upgraded + 5 Image to Motion) render at preview size
  and pass the built-in ffprobe stock check.
- Loop-seam test (frame-level, first vs final frame mean abs difference, threshold < 0.5):
  bg-gradient 0.097, bg-particles 0.0, bg-bokeh 0.0, bg-waves 0.0, bg-confetti 0.0 (after wrap fix),
  bg-geometric 0.0, bg-light-trails 0.0, bg-hexwave 0.0, bg-equalizer 0.0, bg-vortex 0.0, bg-burst 0.0,
  overlay-leak 0.11, overlay-sparkle 0.0, img-breathing 0.0, img-orbit 0.0, img-parallax 0.0.
  overlay-grain = 5.38 by design (film grain is random per frame — it is not meant to match).
- ffprobe validation: HD 1080p30 OK; 4K 3840x2160 OK; 60 FPS (fps=60.0 measured) OK; MOV container h264 OK.
- Other tabs: home loads with sidebar, Vectorizer absent; Promo Maker and Motion Studio jobs complete via HTTP.
- SVG: glass-orbs style SVG (radial gradients + feGaussianBlur) renders via resvg and converts to video.
- Performance note: v6 quality rendering (supersampling + glow) is heavier than v5's flat drawing —
  on a slow VM a 3 s HD clip can take ~1 min; use Preview (480p) to check motion first. A gaming laptop is much faster.

## v7 verification results (2026-10-24, this build machine — automated suite, 27/27 passed)

Part C self-tests from Prompt #2, run offline against the v7 folder:

- **(a) Tracker normaliser + Opportunity Score** on `backend/fixtures/apify_adobe_sample.json`:
  5/5 heterogeneous actor records normalised (string downloads "920"→920, contributor-as-dict,
  keywords-as-CSV-string split, three different AI-flag field styles). Opportunity Score = 63,
  matching the documented formula recomputed independently (total downloads 8500, median 1840).
  Analytics: AI-vs-human 2/3, histogram sums to 5, top keyword "ramadan" ×5, top creator
  "Pattern House Demo" (3120 downloads). Seasonality: 10 events, statuses valid, Black Friday
  2026-11-27 computed (not hardcoded), Hijri/Diwali entries flagged approximate.
- **(b) Embed round-trip:** JPG / PNG / SVG / MP4 embedded with a known title + 3 keywords —
  all 4 validated by read-back; XMP `Rating="5"` + title bytes present in JPG/PNG/SVG outputs;
  JPG carries the IPTC block + EXIF description; MP4 tags written via stream copy (no re-encode);
  EPS produced an `.xmp` sidecar + marked header comment block with the PostScript body intact.
  **Originals untouched** — bytes and mtimes identical after embedding.
  Auto-Extract read the embedded JPG back: exact title, all 3 keywords, rating 5.
- **(c) CSV:** generated for all **9** marketplace targets (Adobe, Shutterstock, Pond5, Freepik,
  Dreamstime, Vecteezy, Depositphotos, 123RF, Universal). Adobe output is **byte-identical** to the
  legacy `to_csv` for the same rows (backwards compatibility kept). Shutterstock layout verified:
  title carried in the Description column per Shutterstock's published CSV spec.
- **(d) Trademark shield:** `backend/data/trademarks.txt` holds **367 brands**; test sentence +
  keyword list containing Nike, Apple, Coca-Cola, Lego and Disney → all 5 removed from keywords
  AND title, and reported in the removed list.
- **(e) 50-file mixed batch** via `/api/metadata/analyze` (47 JPG + 1 SVG + 1 MP4 + 1 corrupt JPG):
  50 results returned, exactly **1 error row (the corrupt file)**, the other 49 generated normally
  with types image/vector/video, source badges and Adobe title range 50–80 chars enforced.
- **(f) Regression:** home page 200 with all **15 tabs** (incl. new Adobe Tracker, Vectorizer absent);
  legacy analyze call (no v7 fields) returns the unchanged response shape; legacy
  `/api/metadata/csv` output unchanged (utf-8-sig BOM for Excel, as in v6); csv-multi "all"
  returns a ZIP of 9 agency CSVs; tracker demo search via API returns 24 records, score 68;
  embed API round-trip + ZIP download 200. Page JavaScript passes `node --check`.
- New dependency: `piexif>=1.1.3` (pure Python, Windows-safe) added to requirements.txt.
- Bugs found & fixed by these tests: piexif string-vs-int EXIF tag keys on JPG embed; seasonality
  status label aligned to spec ("PREP"); Shutterstock Description column now carries the title;
  corrupt image files now return an isolated error row instead of invented metadata.
- Not testable on this machine: a live Apify Adobe Stock run (needs the user's own token + a
  chosen Actor — the demo mode covers the full UI offline), and Windows execution itself.

## v8 verification results (2026-10-24, this build machine)
Suite: Flask test client + a TEMP auth store (TOOLKIT_AUTH_FILE pointed at a
temp dir — real data/auth_store.json was never touched). Full output:

```
PASS a1 setup_needed on fresh store
PASS a2 setup-admin creates admin
PASS a3 second setup-admin rejected
PASS a4 register -> 7-day trial
PASS a5 duplicate register rejected
PASS a6 wrong password rejected
PASS a7 login + state shows trial
PASS b1 non-admin -> 403 on /api/admin/keys
PASS b2 logged-out -> 403 on /api/admin/keys
PASS b3 admin -> 200 on /api/admin/keys
PASS b4 non-admin -> 403 on /api/admin/users
PASS c1 admin generates key, format MTK-PRO-XXXX-XXXX-XXXX
PASS c2 activate with wrong email fails
PASS c3 activate correct email -> Licensed + expiry
PASS c4 second activation of same key fails
PASS c5 revoke unused key works
PASS c6 revoked key cannot activate
PASS d1 expired trial user -> friendly 403 on job endpoint
PASS d2 admin unaffected (400 no-file, not 403)
PASS d3 logged-out unaffected (400 no-file, not 403)
PASS d4 daily limit 1 -> 2nd call 429
PASS d5 not-set-up store -> never gated (400 no-file)
PASS e1 sidebar order exact  [trends,tracker,mgfx,promo,studio,keywords,optimizer,intel,portfolio,svgvideo,motion,apify,aihub,aivideo,extension]
PASS e2 Trend Calendar section is the active default
PASS e3 Admin button present but hidden + gated by is_admin in script
PASS f1 slow zoom -> img-kenburns + speed<1  [img-kenburns/0.5]
PASS f2 golden particles orbiting -> img-orbit + gold
PASS f3 parallax dark teal -> img-parallax + teal + dark bg  [#04141a]
PASS f4 quoted text -> overlay text  [Bulbul Studio]
PASS f5 confetti + fast + 8s + vertical
PASS f6 AI plan validation cannot escape whitelist
PASS g1 home 200
PASS g2 tracker demo 24 records + score
PASS g3 legacy metadata analyze works
PASS g4 trademark shield still catches brands
PASS g5 mgfx-prompt job completes with interpreted plan  [standalone run: done in 225s on this VM, plan img-orbit/gold, 1920x1080, adobe_stock_ready=True]
PASS g6 classic mgfx preview job completes  [standalone run: done in 16s, 854x480 PREVIEW, adobe_stock_ready=True]
PASS g7 no Vectorizer anywhere in page
PASS g8 auth store has NO plaintext passwords
==== 39 checks — all verified passing (see run note below) ====
```

Run note (honesty): two full-suite runs scored 38/39 and 37/39. In both, g5
hit the suite's own 120 s poll limit while still rendering — an HD
Image-to-Motion render takes ~225 s for a 5 s clip on this slow build VM
(the user's gaming laptop is far faster; the classic panel's 480p Preview
exists for quick checks). In the second run g6 also errored once while
the g5 render thread was still consuming the VM. Both were therefore
re-run STANDALONE, one at a time, with a 900 s poll: g5 done in 225 s
(plan img-orbit / gold / builtin, stock check all-true), g6 done in 16 s.
No app code changed as a result — the failures were test-harness timing
and VM contention, not app defects.

Notes / decisions recorded for v8:
- Password security: passwords exist ONLY as salted PBKDF2-HMAC-SHA256 hashes
  (200k rounds) in data/auth_store.json — test g8 greps the store file for the
  test passwords and finds neither. No password is ever displayed in any UI
  (the reference app's login dialog printed a master password; NOT copied).
- Enforcement scope: only a logged-in NON-admin with an expired trial/license
  (403) or over the daily limit (429) is gated, and only on /api/jobs/* +
  /api/metadata/analyze. Admins, logged-out visitors and the not-set-up state
  are never gated (d2/d3/d5); the gate also fails open on internal errors.
- Settings trademark wiring: the Settings "Detect Trademark & Brand Logos"
  rule is sent as inspector_trademark with every SEO Studio analyze call;
  process_asset(trademark_shield=...) then applies or skips the existing
  shield. (Side effect, verified by g3-style flows: when the browser sends
  the field, analyze uses the v7 pipeline — a superset returning the legacy
  fields plus extras; requests WITHOUT any v7 fields keep the exact legacy
  path.) The Faces / Architecture rules are persisted in the settings object
  and documented in the Settings UI as AI-inspection guidance.
- Prompt-to-motion: built-in parser is deterministic and offline (f1–f5);
  the AI path merges provider JSON over the built-in plan through
  _validate_plan, which whitelists kind/theme and clamps speed/intensity/
  duration (f6). Live AI interpretation is untested (needs the user's own
  key — keys are never entered in chat/tests); the no-key path is the
  required one and is fully covered.
- The ZIP ships WITHOUT data/auth_store.json or its .secret file: first run
  on the user's PC starts in "not set up" mode and creates them locally.
- Packaging check (run on the built ZIP): 54 entries under top-level folder
  stock-contributor-toolkit-pro-v8; START-WINDOWS.bat inside the ZIP is CRLF
  (0 bare LF); no auth_store.json / .secret / outputs / uploads / __pycache__
  in the ZIP; served page contains the Tracker tab, prompt panel and admin
  modal, and no "Vectorizer".

---

# v9 Promo Maker upgrade — test record (2026-10-24)

Environment: this Linux VM (Python 3.11 test venv, FFmpeg with libflite),
Flask test client + direct engine calls. Windows behaviour is unchanged from
v8 except the Promo tab; the launcher in the ZIP was re-verified CRLF.

## Engine / module tests (direct calls)
- Legacy contract: `create_promo` with the exact pre-v9 call shape renders
  sale-hero at 1920×1080 (legacy engine, meta keys unchanged). ✅
- All 13 templates render at preview size; every render's ffprobe
  `stock_check` reported `adobe_stock_ready=True` in the smoke batches. ✅
- App Promo WebM: VP9 stream carries the `alpha_mode=1` tag; transparency
  verified on the source frames with PIL — 370,367 of 409,920 pixels at
  alpha=0. (FFmpeg itself decodes VP9-alpha WebM back as yuv420p — a known
  FFmpeg limitation; browsers and editors read the alpha channel.) ✅
- Voiceover + captions: narration clips 4.07s + 3.92s; scenes auto-extended
  (2s → 4.42s / 4.27s) to fit speech; mixer used `sidechaincompress`
  ducking; 2 caption cues; exported SRT is monotonic and inside the video
  duration; output has h264 + aac streams. ✅
- Jingle Maker: jingle 6.68s (intro SFX + voice + outro SFX + tail as
  designed); a remix with a different bed/intro/outro **reused the cached
  voice** (`voice_cached=True`) and produced a different mix file; MP3 and
  WAV durations agree within 0.3s. ✅
- Built-in music beds: 6 beds in `assets/music/`, each exactly 30.0s,
  distinct file hashes, generated locally (no downloaded audio). ✅

## HTTP regression suite (Flask test client, real job threads) — 25/25 ✅
Home 200 · sidebar/section order trends < tracker < mgfx < promo · promo
gallery + script markup present · new promo JS present · auth state 200 ·
`/api/promo/templates` returns 13 templates + 6 beds + voice lists · legacy
3 templates listed · script without a key → labelled Basic script ·
split-script local · slogans ×3 basic · stock-search without a key →
friendly 400 · template preview job completes · preview is cached on the
second call · **v8-style promo form (legacy fields only) completes** with
1920×1080 meta · main download OK · v9 scenes+captions job completes with
GIF + poster + SRT extras · multi-version 1:1 rendered and downloadable ·
GIF/SRT/version download routes OK · Motion Graphics preview job still
completes · SEO Studio metadata analyze still 200. Full page JS passes
`node --check`.

## SKIPPED — with reasons (never silently dropped)
- **edge-tts live synthesis: SKIPPED from this sandbox.** The package
  installs (7.3.1) and the app's guarded integration is in place, but
  Microsoft's speech endpoint is unreachable through this VM's egress proxy
  (SSL `CERTIFICATE_VERIFY_FAILED` / `WRONG_VERSION_NUMBER` to
  speech.platform.bing.com). Per Part H, the sample narration was produced
  with this FFmpeg's offline **libflite** voice and fed through the app's
  own supported voice inputs (voice upload / voice cache), so the whole
  voiceover → ducking → captions → SRT pipeline is genuinely exercised.
  On the user's PC (normal internet) edge-tts is expected to work; if the
  package is missing, the Promo tab says so and voice upload / own-key TTS
  still work.
- **Live Pexels/Pixabay search: not run** (needs the user's own free key —
  keys are never handled in testing). The no-key path is tested (friendly
  error); search/download code follows the providers' documented APIs.
- **Live AI script generation: not run** (needs a user key). The no-key
  Basic path is fully tested; the AI path goes through the same
  `backend/ai_hub.py` used (and tested) by the AI Creativity Hub since v3.

## Samples
Rendered into `v9-promo-samples/` (companion folder next to the v9 ZIP):
one 1080p sample per new template, the 3 originals via the legacy engine,
an alpha WebM, the voiceover+captions promo + its .srt, jingle MP3 +
remix MP3, and a 3-ratio multi-version set. ffprobe table: see
`SAMPLES.md` in that folder.

## Known simplifications (honest list)
- No bundled stock mega-library — own-key Pexels/Pixabay picker instead.
- No true 3D or multitrack timeline — 2.5D perspective device mockups and
  a scene-list editor instead.
- No AI avatars/presenters and no voice cloning — TTS voiceover instead.
- Audiogram bars are a decorative sine-based animation, not audio-reactive.
- Brand Kit and My Music names persist in browser localStorage; My Music
  audio files themselves must be re-picked after a browser data clear
  (browsers cannot retain file handles).
- Screen-recording device frames are sampled at 2 fps into the mockup.

---

# v11 TESTING (Prompt #4 — Jobs A–E) — 2026-10-24

Method: the app was booted from the v11 folder (Flask, test venv) and
driven over HTTP with a scripted battery in two runs, plus static checks.
Tallies below are exactly what the runs printed — nothing rounded up.

## Battery 1 — 36 checks: 35 PASS, 1 FAIL (explained), then the TEST
## SCRIPT (not the app) crashed on a buggy 75-char title builder before
## the remaining checks; those were re-run in Battery 2.

Job A — Trend Calendar merged into Adobe Tracker:
- PASS sidebar order exact: tracker, mgfx, promo, keywords, subtopics,
  intel, portfolio, svgvideo, motion, apify, aihub, aivideo, extension,
  studio (asserted on the served page).
- PASS no trends tab/section; no tool-optimizer section left.
- PASS Adobe Tracker is the FIRST tab and the default active one
  (button + section both carry .active).
- PASS Tracker page contains Seasonality Radar (#seasons) + Month
  Explorer (#tmresults) + Full Year Calendar (#fyc).
- PASS no "Trend Calendar tab" cross-reference text remains.
- PASS GET /api/tracker/calendar: 64 merged events.
- PASS no duplicated event (normalised name + month key checked
  programmatically over all 64).
- PASS statuses all in {UPLOAD NOW, SUBMIT NOW, UPCOMING}; list sorted
  by days_until; every event carries event/date/days_until/upload_by/
  demand/keywords/note/keyword.
- PASS /api/trends still returns its 19 events (backend kept).
- PASS Trend Intel brief still returns 200 with a demand score.

Job B — one AI key + AI-decides-the-motion:
- PASS POST /api/ai/test with a deliberately wrong Gemini key returned
  ok=false with a plain reason (on this VM the reason was a network
  read timeout — the VM's proxy cannot reach the provider; on the
  owner's PC an invalid key returns the provider's own auth error.
  Either way: ok=false + reason, and Check Key renders nothing by
  construction — it only calls the test endpoint).
- PASS no-key interpret -> plan source "builtin", plan carries the v11
  fields (subtext, commercial_angle, buyer_category in the whitelist,
  art_motion).
- PASS mgfx-prompt job with a key whose provider is unreachable ->
  HTTP 409 {ai_failed: true} and NO job was started (no silent
  fallback, nothing rendered).
- PASS an EDITED plan posted from the card ({text: "EDITED HEADLINE",
  speed: 0.5, kind: bg-particles, duration: 2}) was accepted, the render
  completed, and the job meta shows the EDITED values — the card is
  what renders.
- The mgfx_byok save/restore + status-pill behaviour is browser-side
  and was verified by code inspection + `node --check` (see static
  checks); this agent has no live browser. It mirrors SEO Studio's
  seo_byok pattern, in production since v7.
- NOT live-tested: the valid-key AI art-director path (needs the
  owner's real key; provider calls time out through this VM's proxy).
  Failure paths are proven above; the success path should work on the
  owner's OMEN with a valid key.

Job C — Subtopic Creator:
- PASS POST /api/subtopics {topic: "ramadan"} (no token): EXACTLY 50
  subtopics, engine "datamuse + patterns (no Apify token)" — honest.
- PASS every subtopic is lowercase, 2-6 words.
- PASS second search with exclude = the first 50: 50 more, ZERO overlap.
- PASS Copy-All shape: the 50 lines join to exactly 50 newline lines
  (Clipboard code falls back to a textarea copy where needed).
- PASS bad Apify token: still 50 lines, apify_failed = true, engine
  label says "(Apify failed — free sources used)" — the column header
  shows the ⚠ warning. No silent fallback.
- PASS empty topic -> HTTP 400 with a clear error.

Job D — Keyword Research, RA-Tracker pattern:
- PASS POST /api/apify/check with a bad token: ok=false + reason
  (again a VM network timeout reason; the UI blocks searching with an
  unvalidated token — code path verified).
- FAIL (battery 1) -> PASS (battery 2): grouped-results check first ran
  with the nonsense seed "zqxjwvtest", for which Datamuse legitimately
  has NO related words (0 items — the app returned the group honestly).
  Re-run with a real seed ("beach"): 20 items, every item carries a
  source ("Datamuse"), and `suggestions` mirrors the grouped items.
- PASS first search for a seed: cached=false; repeat search:
  cached=true with the ORIGINAL cache timestamp (proves no second
  fetch / no second Apify spend).
- PASS cache stats after the pair: {fetches: 1, hits: 1, searches: 2}.
- PASS Clear Cache removed the entry; the next search fetched fresh
  (cached=false again).
- Pattern note (required): RA-Tracker stores credentials in an
  RSA-encrypted desktop file; this web app substitutes the app's
  established pattern — the token is saved ONLY in browser localStorage
  (`kw_apify`) on Connect, auto-fills on open, and Disconnect wipes it.
  The disk-cache / collapsible-group / validate-before-use behaviours
  are ported faithfully; RSA + PyQt are not (browser app). Disconnect
  wiping is browser-side (code-verified).

Job E1 — Optimizer inside SEO Studio:
- PASS deliberately bad set (86-char comma title with "Nike", duplicate
  keywords, a 4-word keyword): Adobe score 25, trademark_terms = ["nike"]
  (real 367-brand shield, not the old 17-word list).
- PASS Fix All: score 25 -> 88, 6 fixes listed with before -> after;
  fixed title has no trademark, no comma; keywords deduped; no keyword
  over 3 words.
- PASS a 75-char title: title_length PASSES for Adobe (50-80) and FAILS
  for Dreamstime (max 70) — marketplace switching changes the verdict,
  and all limits come from MARKETPLACE_RULES (title_range [50, 80],
  max_keywords 49 asserted).
- PASS Suggest with no key: source "template", labelled as such.
  (After this run the template suggester was hardened to screen
  trademark terms + duplicates out of its inputs; verified live:
  "Running shoes with marathon" — clean.)

Job E2 — Portfolio:
- PASS shipped fixture CSV imports: mapping shown (Title/Platform/Type/
  Date/Downloads/Views/Earnings all detected), 3 entries, 2 assets
  auto-created.
- PASS analytics match hand-computed values: 18 downloads, 410 views,
  $68.25 earnings; earnings/download $3.79; by_type {image, video};
  by_month {2026-10}; Top 10 first = "Beach Sunrise" (conversion 4.7%).
- PASS backup export -> wipe (restore empty) -> restore backup:
  identical stats afterwards (18 / 410 / $68.25).
- PASS goals save (100 downloads / $500) and the pace projection comes
  back labelled "estimate — month-end at current pace".

Regression:
- PASS GET /api/auth/state (v8 auth alive; setup state returned).
- PASS GET /api/promo/templates: 13 templates (v9).
- PASS a v9 Promo job (sale-hero, 1 photo, 720p) started and COMPLETED.
- PASS the Job B edited-plan render above doubles as the v10
  prompt-to-motion regression (job done, stock meta present).
- PASS SEO Studio Adobe CSV byte-identical between v10 and v11 for the
  same input (separate processes, `cmp` clean).

## Battery 2 — 14 checks: 14 PASS (D2 redo, E1e-g, E2a-e, R1-R4).

## Static checks
- Page JavaScript extracted and parsed with `node --check`: OK.
- All edited/new Python modules compile (`py_compile`): OK.
- Sidebar order asserted on the served HTML (see Job A).
- START-WINDOWS.bat inside the ZIP: CRLF verified (62 CRLF, 0 bare LF).
- ZIP ships with NO runtime data: data/ holds only .gitkeep; no
  auth_store, no portfolio.json, no keyword_cache.

## Honest NOT-done / simplified list
- Live valid-key tests (Job B AI art director, Job D Apify-boosted
  groups, Job C Apify-first ordering) need the owner's own keys/tokens
  on his machine — this VM's proxy blocks/times out those providers.
  All failure paths are test-proven above and fail VISIBLY.
- Browser-only behaviours (localStorage restore, pills, plan-card
  editing, column/copy interactions, popovers, collapsibles) are
  code-verified + syntax-checked, not clicked through — this agent has
  no live browser.
- Job D "Google" as a keyword source label is realised through the
  Apify related-searches source ("Apify related") — Google suggestions
  are not fetched directly.
- Full Year Calendar merges two datasets whose dates can disagree by a
  few days for movable feasts; those entries keep their "approx" note.

---

# v12 test record (Prompt #5 — Keyword Research → Market Tracker)

Suite: `/tmp/test_v12.py` (Flask test client + node), run once,
complete: **47 passed, 0 failed.** All runtime files were redirected
to /tmp via env overrides; the app folder ships clean. Scope guard:
`diff -rq` v11 → v12 shows ONLY `app.py`, `backend/tracker.py`,
`templates/index.html` changed and `backend/market_cache.py` added —
both Python diffs are purely additive (zero removed lines), so the
Adobe Tracker tab and every other tab are behaviour-identical to v11.

## Metric arithmetic (fixed today = 2026-10-24; days/month = 30.4375)
- D/MO, <1 month old: 930 downloads, uploaded 2026-10-10 → 14 days =
  0.46 months → clamp to 1 → 930 / 1 = **930.0** ✓
- D/MO, 24 months: 1200 downloads, uploaded 2024-10-24 → 730 days =
  23.98 months → 1200 / 23.98 = **50.0** ✓
- D/MO, 18 months: 500 downloads, uploaded 2025-04-24 → 548 days =
  18.00 months → 500 / 18.00 = **27.8** ✓
- Est. revenue: 1200 × $0.99 = **$1188.00** ✓; at edited rate $0.35:
  1200 × 0.35 = **$420.00** ✓. Age label for the 24-month asset:
  "2 years ago" ✓
- Lifecycle: "Christmas snow village" (title term) → Seasonal ✓;
  "Desert landscape" + keyword "ramadan" → Seasonal ✓; "Business team
  meeting in modern office" → Evergreen ✓
- Keyword Difficulty (top-10 median downloads): 100 → Easy,
  1000 → Moderate, 5000 → Hard, 20000 → Red Ocean ✓ (all four tiers)
- Undiscovered fixture (6 assets; downloads [300, 480, 100, 5000,
  6000, 900] → median 900): result order [U1, U2] — U1 (300 dl, 6 mo
  old, D/MO 50.0) first, U2 (480 dl, 12 mo, D/MO 40.0) second; the
  2019 asset excluded by age, the 5000/6000/900 assets excluded as
  not below the median ✓

## Cache proof (counters, server-side `data/market_scan_cache.json`)
- Demo scan ×2: fetches=1, hits=1, second response `cached=true` —
  identical repeat spends zero fetches ✓. Force-fresh → fetches=2 ✓
- Live path with a counting monkeypatched Apify runner: scan 1 →
  apify_calls=1, records normalised + D/MO-enriched; scan 2 (cached)
  → apify_calls still 1 ✓. Entry then expired by hand (ts −1200 s)
  and the runner made to raise: response **502 with
  stale_available=true**; `use_stale` → 200 with the stale payload
  flagged `stale=true` ✓ (offered, never silent)

## Product checks
- Part A removal: served page contains none of the v11 keyword IDs
  or copy (kwtoken, kwconnect, kwconnstate, kwlabel, kwclearcache,
  kwresults, kwstats, basket, seed, kgo, kw_apify, "Connect once",
  "never pay twice", ★-proven copy) ✓; new UI present (mkgo, mkmodal,
  mkgrid, mkkpis, mkwin, mkpmodal, kw_market_byok) ✓
- Demo scan: 24 records, KPI avg_dmo + difficulty present, Winning
  Keywords = 30, season banner matched the query ✓
- Contributor mode: summary matches hand-computed values from the
  sample (modal creator "Lumina Stock Lab", 3 assets, 3529 downloads,
  best seller 2578) ✓; leaderboard sorted by total downloads desc ✓
- Asset prompt: no key → basic prompt, labelled ✓; key + no thumbnail
  → basic + "no reachable thumbnail" note ✓; key + unreachable
  thumbnail → basic + "AI vision failed" note ✓ (never a crash)
- Exports (the page's own `mkCsvText` evaluated in node): 150 rows →
  151 lines (header + 150) ✓; Top-100 variant → 101 lines ✓; header
  contains dmo / est_revenue / lifecycle; a 1200-download row exports
  est_revenue "1188.00" ✓
- Card-action wiring present in the served page (SEO send writes
  #extra/#opttitle/#optkws; Motion send prefills #ppprompt with
  "Animate this concept: …") ✓

## Regression
- GET / 200; page JS passes `node --check` ✓
- Sidebar order identical to v11 (tracker, mgfx, promo, keywords,
  subtopics, intel, portfolio, svgvideo, motion, apify, aihub,
  aivideo, extension, studio) ✓
- Adobe Tracker demo search still 24 records with opportunity_score ✓
- /api/tracker/calendar 200 ✓; Subtopic Creator still exactly 50 ✓
- /api/keywords/expand 200 ✓; /api/auth/state 200 ✓
- Promo templates still 13 ✓; a classic MGFX preview job completes
  (state done) ✓

## Fixture note
`backend/tracker_sample.json` was left UNTOUCHED: all 24 demo records
already carry plausible fictional `upload_date` values
(2025-01-01…2025-12-24), so D/MO / age / lifecycle demonstrate without
editing the fixture (editing it risked the Tracker demo regression).
The records remain clearly fictional and the DEMO banner is shown.

## Honest NOT-done / simplified list (v12)
- RA Graphic Studio's studio-provisioned accounts and credit system
  were NOT copied — this app stays key-free / BYOK by design.
- Formulas the references do not publish (their Opportunity /
  Keyword Difficulty numbers) are this app's own documented
  heuristics, labelled estimates in the UI and in code comments.
  Only D/MO and top-keyword frequency are publicly defined by
  RA Graphic Studio; both are implemented exactly as defined.
- A live scan with a REAL Apify token + owner-chosen Actor could not
  run from this VM (provider calls time out through its proxy, same
  caveat as v8/v10/v11). The live path is proven end-to-end with a
  counting stub runner; demo mode and every failure path (including
  the stale-cache offer) are test-proven. First real run happens on
  the owner's machine with his own token.
- Featured sort: scraped data carries no reliable featured flag, so
  the UI falls back to Relevance order and says so in a visible note.
- Browser-only behaviours (modal save/restore, chip copy, card
  expansion, saved-search re-open) are code-verified + JS
  syntax-checked, not clicked through — this agent has no live browser.

## v14 pre-delivery amendment (2026-10-24, parent-verified)
After the 52/52 run, a payload-key mismatch was caught in review:
the Adobe Tracker tab's UI sends `token`/`actor_id`, but
`/api/tracker/search` read only `apify_token`/`actor`. The route now
accepts both spellings. Parent re-test (Flask test client):
home 200; tracker demo 200 (24 records); tracker search with the
UI's own keys + actor `Screenshot 2026-10-24 163420.png` → 400
invalid_actor with the file-name message; same via original keys →
400; valid actor via UI keys → reaches the Apify run (dummy token →
502 "Apify run failed: HTTP Error 401"), proving the credentials now
flow; keyword scan bad actor → 400; demo scan 200 (24 records, rate
0.85, KD 53 MODERATE); radar 6 events; subtopics exactly 50;
tracker month 200. ZIP repackaged after this amendment and
re-verified (entries, CRLF, extracted boot test).
