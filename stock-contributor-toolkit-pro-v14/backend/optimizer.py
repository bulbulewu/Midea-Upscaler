"""
Title & keyword optimizer — rule-based QA against marketplace best
practices. v11 (Prompt #4, Job E1): the old standalone "Title Optimizer"
tab moved INTO SEO Studio and was upgraded:

  * ALL limits come from backend/metadata.py MARKETPLACE_RULES — the
    single source of truth shared with SEO Studio generation/validation
    (Adobe target = titles 50-80 chars, max 49 keywords; other agencies
    use their own published ranges). The old duplicated constants
    (TITLE_MAX etc. lived in metadata but were Adobe-only) are gone from
    the decision path.
  * The trademark shield is the REAL one: backend/data/trademarks.txt
    (367 brands) via metadata.load_trademarks() — the old 17-word
    BRAND_HINTS list is deleted. Exact terms found are reported.
  * Auto-Fix per failed check + Fix All, with before -> after.
  * Optional AI title suggestions via the user's own BYOK key (ai_hub);
    without a key, one template-based rewrite, labelled as such.
"""

import re

from . import ai_hub
from .metadata import (FIRST_N_WEIGHTED, MARKETPLACE_RULES, MIN_KEYWORDS,
                       expand_keywords, fit_title, load_trademarks,
                       screen_trademarks, _contains_term)

# Check ids (the UI keys its per-check Auto-Fix buttons off these).
C_TITLE_LENGTH = "title_length"
C_TITLE_NATURAL = "title_natural"
C_KW_COUNT = "keyword_count"
C_DUPES = "duplicates"
C_SINGLE = "single_concept"
C_TITLE_TERMS = "title_terms_top10"
C_TRADEMARK = "trademarks"
C_FIRST10 = "first10_filled"


def _rules(marketplace):
    return MARKETPLACE_RULES.get(marketplace or "adobe",
                                 MARKETPLACE_RULES["adobe"])


def _split_keywords(raw):
    if isinstance(raw, list):
        items = raw
    else:
        items = re.split(r"[,\n;]+", raw or "")
    return [k.strip().lower() for k in items if k.strip()]


def trademark_hits(title, kws):
    """Exact trademark terms (from the 367-brand shield list) present in
    the title or any keyword — reported verbatim, never silently."""
    hits = []
    for term in load_trademarks():
        if _contains_term(title, term) or \
                any(_contains_term(k, term) for k in kws):
            hits.append(term)
    return hits


def analyze(title, keywords_raw, marketplace="adobe"):
    rules = _rules(marketplace)
    tmin, tmax = rules["title_min"], rules["title_max"]
    max_kw = rules["max_keywords"]
    label = rules["label"]
    title = (title or "").strip()
    kws = _split_keywords(keywords_raw)
    checks = []

    def add(cid, name, ok, tip):
        checks.append({"id": cid, "check": name,
                       "status": "pass" if ok else "fail", "tip": tip})

    add(C_TITLE_LENGTH, "Title length",
        tmin <= len(title) <= tmax,
        f"{len(title)} characters — {label} wants {tmin}-{tmax}." +
        (" Shorten it." if len(title) > tmax else
         " Lengthen it." if len(title) < tmin else " Good."))
    add(C_TITLE_NATURAL, "Title reads naturally",
        "," not in title and len(title.split()) >= 3,
        "Write a sentence, not a keyword pile. Avoid commas in titles.")
    add(C_KW_COUNT, "Keyword count",
        MIN_KEYWORDS <= len(kws) <= max_kw,
        f"{len(kws)} keywords (need {MIN_KEYWORDS}-{max_kw} for {label})." +
        (" Add more." if len(kws) < MIN_KEYWORDS else
         " Trim weakest." if len(kws) > max_kw else " Good."))
    dupes = len(kws) - len(set(kws))
    add(C_DUPES, "No duplicates", dupes == 0,
        f"{dupes} duplicate(s) found — remove them." if dupes else "Clean.")
    long_ones = [k for k in kws if len(k.split()) > 3]
    add(C_SINGLE, "Single-concept keywords", not long_ones,
        ("Split these: " + ", ".join(long_ones[:3])) if long_ones
        else "Good — one concept per keyword.")
    title_words = {w.lower() for w in re.findall(r"[a-zA-Z]{3,}", title)}
    overlap = sum(1 for k in kws[:FIRST_N_WEIGHTED]
                  if any(w in k for w in title_words))
    add(C_TITLE_TERMS, "Title terms in top keywords", overlap >= 2,
        f"{overlap} of the first {FIRST_N_WEIGHTED} keywords echo the title. "
        "Mirror 2-3 title terms up front for ranking.")
    hits = trademark_hits(title, kws)
    add(C_TRADEMARK, "No brand/trademark terms", not hits,
        ("Trademark terms found: " + ", ".join(hits[:6]) +
         " — remove unless you own them.") if hits else "Clean.")
    add(C_FIRST10, f"First {FIRST_N_WEIGHTED} keywords set",
        len(kws) >= FIRST_N_WEIGHTED,
        "Agencies weight the first 10 most — put subject, action, setting there."
        if len(kws) < FIRST_N_WEIGHTED else
        f"Top 10: {', '.join(kws[:FIRST_N_WEIGHTED])}")

    score = round(100 * sum(c["status"] == "pass" for c in checks) / len(checks))
    return {"score": score, "checks": checks,
            "keyword_count": len(kws), "title_length": len(title),
            "marketplace": marketplace or "adobe",
            "marketplace_label": label,
            "title_range": [tmin, tmax], "max_keywords": max_kw,
            "trademark_terms": hits}


# ------------------------------------------------------------- auto-fix

def _sentence_case(t):
    t = re.sub(r"\s+", " ", (t or "").strip())
    if not t:
        return t
    if t.isupper():
        t = t.lower()
    return t[:1].upper() + t[1:]


def _split_long_keyword(kw):
    """Split a >3-word keyword into <=3-word single-concept chunks."""
    parts = re.split(r"\s+(?:and|with|on|in|of|for)\s+", kw)
    out = []
    for p in parts:
        words = p.split()
        if len(words) <= 3:
            if p.strip():
                out.append(p.strip())
            continue
        chunks = [words[i:i + 3] for i in range(0, len(words), 3)]
        if len(chunks) > 1 and len(chunks[-1]) == 1:
            chunks[-2] = chunks[-2] + chunks[-1]
            chunks.pop()
        out.extend(" ".join(c) for c in chunks)
    return [o for o in out if o]


def autofix(title, keywords_raw, marketplace="adobe", only=None):
    """Apply the automatic fixes (all of them, or only the check ids in
    `only`). Returns {title, keywords, fixes[], before, after,
    added_suggestions[]} — every change listed with before -> after."""
    rules = _rules(marketplace)
    tmin, tmax, max_kw = rules["title_min"], rules["title_max"], \
        rules["max_keywords"]
    before = analyze(title, keywords_raw, marketplace)
    t = (title or "").strip()
    kws = _split_keywords(keywords_raw)
    fixes = []
    added_suggestions = []

    def want(cid):
        return only is None or cid in only

    def record(cid, action, b, a):
        if b != a:
            fixes.append({"check": cid, "action": action,
                          "before": b, "after": a})

    # 1) trademark terms out of title + keywords (the real 367-brand shield)
    if want(C_TRADEMARK):
        hits = trademark_hits(t, kws)
        if hits:
            nt, nk, _removed = screen_trademarks(t, kws)
            record(C_TRADEMARK,
                   "Removed trademark terms: " + ", ".join(hits),
                   f"title: {t!r} · keywords: {', '.join(kws)}",
                   f"title: {nt!r} · keywords: {', '.join(nk)}")
            t, kws = nt, nk
    # 2) strip commas from the title
    if want(C_TITLE_NATURAL) and "," in t:
        nt = re.sub(r"\s+", " ", t.replace(",", " ")).strip()
        record(C_TITLE_NATURAL, "Removed commas from title", t, nt)
        t = nt
    # 3) sentence-case
    if want(C_TITLE_NATURAL):
        nt = _sentence_case(t)
        record(C_TITLE_NATURAL, "Sentence-cased title", t, nt)
        t = nt
    # 4) title length: trim at word boundary / pad with strong keywords
    if want(C_TITLE_LENGTH) and not (tmin <= len(t) <= tmax):
        nt = fit_title(t, rules, kws)
        record(C_TITLE_LENGTH,
               f"Fitted title into {tmin}-{tmax} chars "
               "(trimmed at a word boundary / padded with keywords)", t, nt)
        t = nt
    # 5) duplicate keywords out
    if want(C_DUPES):
        seen, nk = set(), []
        for k in kws:
            if k not in seen:
                seen.add(k)
                nk.append(k)
        record(C_DUPES, "Deleted duplicate keywords",
               ", ".join(kws), ", ".join(nk))
        kws = nk
    # 6) split multi-concept keywords
    if want(C_SINGLE):
        nk = []
        for k in kws:
            nk.extend(_split_long_keyword(k) if len(k.split()) > 3 else [k])
        nk = list(dict.fromkeys(nk))
        record(C_SINGLE, "Split multi-concept keywords",
               ", ".join(kws), ", ".join(nk))
        kws = nk
    # 7) move title-term keywords into the top 10
    if want(C_TITLE_TERMS):
        title_words = {w.lower() for w in re.findall(r"[a-zA-Z]{3,}", t)}
        head, tail = kws[:FIRST_N_WEIGHTED], kws[FIRST_N_WEIGHTED:]
        movers = [k for k in tail
                  if any(w in k for w in title_words)]
        if movers:
            tail = [k for k in tail if k not in movers]
            if len(head) + len(movers) <= FIRST_N_WEIGHTED:
                nk = head + movers + tail
            else:  # displace the weakest head items so movers land in top 10
                keep = FIRST_N_WEIGHTED - len(movers)
                nk = head[:keep] + movers + head[keep:] + tail
            record(C_TITLE_TERMS,
                   "Moved title-term keywords into the top 10: " +
                   ", ".join(movers), ", ".join(kws), ", ".join(nk))
            kws = nk
    # 8) pad under-minimum keyword count with Datamuse suggestions —
    #    clearly marked, the contributor reviews before use
    if want(C_KW_COUNT) and len(kws) < MIN_KEYWORDS:
        seeds = [w for w in re.findall(r"[a-zA-Z]{3,}", t.lower())][:4] or \
            kws[:2]
        for s in expand_keywords(seeds, per_seed=6):
            if len(kws) >= MIN_KEYWORDS:
                break
            if s not in kws:
                kws.append(s)
                added_suggestions.append(s)
        if added_suggestions:
            record(C_KW_COUNT,
                   "Padded keyword count with Datamuse SUGGESTIONS "
                   "(marked — review before use): " +
                   ", ".join(added_suggestions),
                   f"{len(kws) - len(added_suggestions)} keywords",
                   f"{len(kws)} keywords")
    # 9) enforce the marketplace keyword cap last
    if len(kws) > max_kw:
        record(C_KW_COUNT, f"Trimmed keywords to the {rules['label']} "
               f"maximum of {max_kw}", f"{len(kws)} keywords",
               f"{max_kw} keywords")
        kws = kws[:max_kw]

    after = analyze(t, kws, marketplace)
    return {"title": t, "keywords": kws,
            "keywords_str": ", ".join(kws), "fixes": fixes,
            "before": before, "after": after,
            "added_suggestions": added_suggestions,
            "marketplace": marketplace or "adobe"}


# ------------------------------------------------------- title suggestions

def _template_titles(title, kws, rules):
    """Deterministic no-key rewrites built from the existing keywords,
    each fitted into the marketplace's title range. Labelled template."""
    tmin, tmax = rules["title_min"], rules["title_max"]
    singles = [k for k in kws if " " not in k][:6]
    phrases = [k for k in kws if " " in k][:4]
    cands = []
    if len(singles) >= 3:
        cands.append(f"{singles[0]} {singles[1]} and {singles[2]} scene")
    if phrases and singles:
        cands.append(f"{phrases[0]} with {singles[0]}")
    if len(singles) >= 2:
        cands.append(f"{singles[0]} concept with {singles[1]} elements")
    out = []
    for c in cands:
        c = fit_title(_sentence_case(c), rules, kws)
        if c and c not in out and len(c) <= tmax:
            out.append(c)
    return out[:3]


def suggest_titles(title, keywords_raw, marketplace="adobe",
                   provider=None, key=None, model=None, base_url=None):
    """3 better titles inside the marketplace's char range.
    With the user's own BYOK key: real AI suggestions (source 'ai').
    Without: template-based rewrite(s), honestly labelled (source
    'template'). Never raises for AI problems — falls back + says so."""
    rules = _rules(marketplace)
    tmin, tmax = rules["title_min"], rules["title_max"]
    kws = _split_keywords(keywords_raw)
    # never build suggestions out of trademark terms or duplicates
    _ct, kws, _removed = screen_trademarks(title or "", kws)
    kws = list(dict.fromkeys(kws))
    if provider and (key or "").strip():
        prov = (provider or "").strip().lower()
        if prov in ai_hub.PROVIDERS:
            prompt = (
                f"You are a microstock title expert for {rules['label']}. "
                f"Current title: {title!r}. Keywords: {', '.join(kws[:30])}. "
                f"Write EXACTLY 3 alternative titles, one per line, no "
                f"numbering, no quotes. Each must be a natural sentence of "
                f"{tmin}-{tmax} characters, built from the keywords, no "
                f"commas, no brand/trademark names.")
            try:
                if ai_hub.PROVIDERS[prov]["kind"] == "gemini":
                    text = ai_hub._gemini(key.strip(), model, prompt,
                                          timeout=60)
                else:
                    text = ai_hub._openai_style(prov, key.strip(), model,
                                                prompt, base_url, timeout=60)
                lines = [re.sub(r"^\s*[\d\-\.\)]+\s*", "", ln).strip()
                         for ln in text.splitlines() if ln.strip()]
                lines = [ln for ln in lines if 0 < len(ln) <= tmax][:3]
                if lines:
                    return {"titles": lines, "source": "ai",
                            "provider": prov}
            except Exception as exc:  # noqa: BLE001
                return {"titles": _template_titles(title, kws, rules),
                        "source": "template",
                        "note": f"AI suggestion failed ({exc}); "
                                "template rewrite shown instead."}
    return {"titles": _template_titles(title, kws, rules),
            "source": "template",
            "note": "Template-based rewrite (no AI key) — add your free "
                    "BYOK key in SEO Studio for AI suggestions."}
