"""
Month-by-month stock-content calendar (v10) — festivals, world /
international days and seasonal shopping moments for EVERY month of the
year, each with stock topics (content ideas / buyer keywords) so a
contributor can plan shoots for any chosen month + year.

Data merged from the app's two existing calendars:
  * backend/trends.py  EVENTS  (Trend Calendar tab)
  * backend/tracker.py EVENTS  (Adobe Tracker Seasonality Radar)
and EXPANDED with additional widely-observed days so every month carries
at least 4-6 entries. Movable / religious dates (Ramadan, Eid, Holi,
Diwali, Lunar New Year, Easter, Thanksgiving…) shift every year — those
entries are flagged ``approx`` and their day is a typical value; verify
the exact date for the year you are planning.
"""

from datetime import date, timedelta

from . import tracker as _tracker
from . import trends as _trends

FESTIVAL, WORLD_DAY, SHOPPING, SEASONAL = (
    "Festival", "World Day", "Shopping", "Seasonal")


def _type_for(name, default=FESTIVAL):
    n = name.lower()
    if "black friday" in n or "cyber" in n or "singles" in n or "sale" in n:
        return SHOPPING
    if "season" in n or "month" in n:
        return SEASONAL
    if ("international" in n or "world" in n) and "day" in n:
        return WORLD_DAY
    return default


def _key(name, month):
    """Dedup key: month-scoped alias rules first (the two source calendars
    name some events differently), else the first two meaningful words."""
    n = name.lower().replace("~", "")
    if "ramadan" in n:
        return f"ramadan-{month}"
    if "earth day" in n:
        return f"earth day-{month}"
    words = [w.strip("~.,'’") for w in n.split() if w.strip("~.,'’")]
    return " ".join(words[:2])


def _merged():
    """tracker EVENTS first (they carry ready-made content ideas), then
    trends EVENTS that are not already present, then the expansions."""
    out, seen = [], set()

    def add(month, day, name, typ, approx, demand, topics, note, lead,
            keyword=None, special=None):
        k = _key(name, month)
        if k in seen or not topics:
            return
        seen.add(k)
        out.append({"month": month, "day": day, "name": name, "type": typ,
                    "approx": bool(approx), "demand": demand,
                    "topics": [str(t) for t in topics][:5],
                    "note": note or "", "lead_weeks": int(lead or 8),
                    "keyword": keyword or name.lower().replace(" ~", ""),
                    "special": special})

    # (b) tracker seasonality radar entries
    for ev in _tracker.EVENTS:
        add(ev.get("month", 11), ev.get("day", 27), ev["name"],
            _type_for(ev["name"]), ev.get("approx"), "high",
            ev.get("ideas", []),
            "From the Seasonality Radar — buyers search 60-90 days ahead.",
            9, keyword=ev.get("keyword"),
            special=ev.get("special"))

    # (a) Trend Calendar entries
    for month, day, name, lead, demand, keywords, note in _trends.EVENTS:
        add(month, day, name, _type_for(name),
            name.rstrip().endswith("~") or "~" in name, demand,
            keywords, note, lead)

    # Expansions — every month gets festivals + world days + seasonal
    # shopping topics that stock buyers actually search for.
    X = [
        # month, day, name, type, approx, demand, topics, note, lead
        (1, 7, "Orthodox Christmas", FESTIVAL, False, "medium",
         ["orthodox christmas", "church candles", "winter cathedral",
          "orthodox icons", "family celebration"],
         "Celebrated Jan 7 in many Eastern European / Orthodox markets.", 8),
        (1, 20, "Martin Luther King Jr. Day", WORLD_DAY, True, "medium",
         ["civil rights", "equality concepts", "american history",
          "dream speech themes", "diversity portraits"],
         "US federal holiday — 3rd Monday of January (date approx).", 6),
        (1, 24, "International Day of Education", WORLD_DAY, False, "medium",
         ["online learning", "students studying", "classroom technology",
          "books and laptop", "education icons"],
         "Evergreen education demand spikes each January.", 6),
        (1, 15, "Winter Sports & Cozy Season", SEASONAL, False, "high",
         ["skiing and snowboard", "winter cabin", "hot drinks by fireplace",
          "snow landscapes", "winter fashion"],
         "Peak winter-content month in the northern hemisphere.", 10),
        (2, 4, "World Cancer Day", WORLD_DAY, False, "medium",
         ["health awareness", "pink ribbon concepts", "doctor consultation",
          "support and hope", "medical research"],
         "Health-awareness content; keep it respectful and hopeful.", 6),
        (2, 18, "Ramadan Begins", FESTIVAL, True, "high",
         ["ramadan lantern", "crescent moon", "mosque silhouette",
          "iftar preparation", "prayer beads"],
         "~ Start of Ramadan moves ~11 days earlier each year; verify.", 8),
        (2, 8, "Super Bowl Sunday", SEASONAL, True, "medium",
         ["american football party", "friends watching game", "snacks and tv",
          "sports fans celebrating", "stadium lights"],
         "Early Feb (date approx) — huge US party/food content demand.", 6),
        (2, 21, "International Mother Language Day", WORLD_DAY, False, "low",
         ["multilingual typography", "language learning", "world alphabets",
          "children reading", "cultural diversity"],
         "", 5),
        (3, 20, "First Day of Spring / Nowruz", SEASONAL, False, "high",
         ["spring flowers", "nowruz haft-sin table", "fresh green nature",
          "spring cleaning", "garden awakening"],
         "Persian New Year (Nowruz) falls on the spring equinox.", 8),
        (3, 22, "World Water Day", WORLD_DAY, False, "medium",
         ["clean water concepts", "water splash", "drought and conservation",
          "hands under tap", "blue abstract water"],
         "", 6),
        (4, 1, "April Fool's Day", SEASONAL, False, "low",
         ["funny pranks", "surprise reaction", "humour concepts",
          "office jokes", "playful portraits"],
         "Light, funny content — good for social/editorial buyers.", 4),
        (4, 5, "Easter", FESTIVAL, True, "high",
         ["easter eggs", "spring bunny", "easter brunch table",
          "pastel decorations", "church celebration"],
         "~ Easter Sunday moves (Mar-Apr); verify the year.", 8),
        (4, 7, "World Health Day", WORLD_DAY, False, "medium",
         ["healthy lifestyle", "doctor and patient", "fitness checkup",
          "mental wellbeing", "medical technology"],
         "", 6),
        (4, 15, "Tax Season Deadline (US)", SEASONAL, False, "medium",
         ["tax forms and calculator", "accountant working", "finance stress",
          "paperwork deadline", "money planning"],
         "US filing deadline mid-April — finance content peaks.", 6),
        (5, 1, "International Workers' Day", WORLD_DAY, False, "medium",
         ["workers portraits", "labour day concepts", "team at work",
          "professions collage", "hard hat heroes"],
         "Public holiday in most of the world (May Day).", 6),
        (5, 5, "Cinco de Mayo", FESTIVAL, False, "medium",
         ["mexican food fiesta", "mariachi music", "colorful decorations",
          "tacos and drinks", "mexican flags"],
         "Big in the US/Mexico food & party market.", 6),
        (5, 20, "Graduation Season", SEASONAL, False, "high",
         ["graduation cap toss", "diploma celebration", "students success",
          "graduation party", "new career start"],
         "May-Jun graduations — education & family buyers.", 8),
        (5, 25, "Memorial Day (US)", SEASONAL, True, "medium",
         ["american flags remembrance", "summer kickoff bbq", "patriotic decor",
          "family picnic", "travel weekend"],
         "Last Monday of May (date approx) — start of US summer sales.", 6),
        (6, 5, "World Environment Day", WORLD_DAY, False, "medium",
         ["tree planting", "green energy", "volunteers cleaning nature",
          "sustainability icons", "protect planet concepts"],
         "", 6),
        (6, 8, "World Oceans Day", WORLD_DAY, False, "medium",
         ["ocean waves", "sea turtles", "beach cleanup",
          "underwater world", "plastic pollution concepts"],
         "", 6),
        (6, 1, "Pride Month", SEASONAL, False, "high",
         ["rainbow flags", "pride parade", "diversity celebration",
          "colorful portraits", "inclusion concepts"],
         "All of June — authentic, respectful representation sells.", 8),
        (6, 21, "International Yoga Day / Summer Solstice", WORLD_DAY, False,
         "medium", ["sunrise yoga", "meditation outdoors", "wellness retreat",
                    "summer solstice sun", "healthy morning routine"],
         "Longest day of the year in the northern hemisphere.", 6),
        (7, 7, "World Chocolate Day", WORLD_DAY, False, "low",
         ["chocolate pieces", "dessert flat lay", "cocoa beans",
          "sweet treats", "baking chocolate"],
         "Fun food-content day for social buyers.", 4),
        (7, 15, "Summer Sales Season", SHOPPING, False, "high",
         ["summer sale banners", "shopping bags", "discount tags",
          "retail storefront", "online shopping phone"],
         "Mid-year sales (incl. Prime-Day style promos) peak in July.", 8),
        (7, 17, "World Emoji Day", WORLD_DAY, False, "low",
         ["emoji faces", "social media concepts", "chat bubbles",
          "yellow smiley patterns", "digital communication"],
         "Good for social-media and tech illustration buyers.", 4),
        (7, 30, "International Friendship Day", WORLD_DAY, False, "medium",
         ["friends laughing", "friendship bracelets", "group of friends",
          "friends coffee", "best friends forever"],
         "", 5),
        (8, 12, "International Youth Day", WORLD_DAY, False, "medium",
         ["young people technology", "students future", "youth culture",
          "teen lifestyle", "young entrepreneurs"],
         "", 6),
        (8, 19, "World Photography Day", WORLD_DAY, False, "medium",
         ["photographer at work", "vintage cameras", "photo studio",
          "camera flat lay", "behind the scenes shoot"],
         "Meta-content: photographers buy photography-themed stock too.", 5),
        (8, 26, "Women's Equality Day", WORLD_DAY, False, "medium",
         ["women empowerment", "equality concepts", "business women",
          "voting rights history", "strong women portraits"],
         "US observance; equality themes are evergreen.", 5),
        (9, 7, "Labor Day (US)", SEASONAL, True, "medium",
         ["end of summer bbq", "workers celebration", "autumn transition",
          "family weekend", "labor day sale banners"],
         "1st Monday of September (date approx).", 6),
        (9, 8, "International Literacy Day", WORLD_DAY, False, "medium",
         ["children reading books", "library scenes", "adult education",
          "open book concepts", "reading glasses on book"],
         "", 6),
        (9, 19, "Oktoberfest", FESTIVAL, True, "medium",
         ["beer festival", "bavarian costumes", "pretzels and beer mugs",
          "german celebration", "festival tents"],
         "~ Mid-Sep to early Oct in Munich; verify dates.", 8),
        (9, 22, "Autumn / Fall Season Begins", SEASONAL, False, "high",
         ["autumn leaves", "cozy fall fashion", "pumpkin spice",
          "fall forest road", "harvest season"],
         "Autumn equinox — fall content demand runs Sep-Nov.", 10),
        (9, 27, "World Tourism Day", WORLD_DAY, False, "medium",
         ["travel landmarks", "tourist with map", "airport journeys",
          "wanderlust concepts", "hotel lifestyle"],
         "", 6),
        (10, 5, "World Teachers' Day", WORLD_DAY, False, "medium",
         ["teacher in classroom", "school appreciation", "online teaching",
          "teacher and students", "education heroes"],
         "", 6),
        (10, 10, "World Mental Health Day", WORLD_DAY, False, "medium",
         ["mental wellbeing", "calm meditation", "therapy session",
          "self care routine", "peaceful nature mind"],
         "Keep visuals hopeful and stigma-free.", 6),
        (10, 1, "Breast Cancer Awareness Month", SEASONAL, False, "medium",
         ["pink ribbon", "awareness campaign", "women health support",
          "pink October concepts", "hope and strength"],
         "All of October is 'Pink October' for health buyers.", 8),
        (11, 11, "Singles' Day (11.11) Sale", SHOPPING, False, "high",
         ["online shopping sale", "11.11 banners", "e-commerce discounts",
          "shopping cart phone", "mega sale concepts"],
         "The world's biggest shopping day (China/Asia) — Nov 11.", 9),
        (11, 13, "World Kindness Day", WORLD_DAY, False, "low",
         ["helping hands", "volunteering", "kindness concepts",
          "donation and charity", "community support"],
         "", 5),
        (11, 26, "Thanksgiving (US)", FESTIVAL, True, "high",
         ["thanksgiving dinner", "roast turkey table", "family gratitude",
          "autumn harvest decor", "pumpkin pie"],
         "4th Thursday of November (date approx).", 9),
        (11, 1, "Movember — Men's Health Month", SEASONAL, False, "medium",
         ["moustache portraits", "men's health checkup", "barber grooming",
          "men wellbeing", "movember concepts"],
         "All of November.", 7),
        (12, 10, "Christmas Shopping & Gift Season", SHOPPING, False, "very high",
         ["gift wrapping", "christmas shopping", "holiday offers banners",
          "presents under tree", "festive retail"],
         "Peak retail weeks before Christmas — upload by October.", 12),
        (12, 14, "Hanukkah", FESTIVAL, True, "medium",
         ["menorah candles", "dreidel and gelt", "hanukkah celebration",
          "jewish holiday table", "blue and gold decor"],
         "~ 8 days in Nov/Dec (moves yearly); verify dates.", 8),
        (12, 1, "Cozy Winter & Holiday Season", SEASONAL, False, "very high",
         ["cozy winter home", "christmas markets", "snowy villages",
          "holiday baking", "winter wonderland"],
         "The whole of December is peak holiday-content season.", 12),
    ]
    for m, d, name, typ, approx, demand, topics, note, lead in X:
        add(m, d, name, typ, approx, demand, topics, note, lead)
    return out


CALENDAR = _merged()

_MONTH_NAMES = ["January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November",
                "December"]


def month_events(month, year, today=None):
    """All occasions in one month of one year, as API-ready dicts:
    {date, name, type, approx, demand, demand_note, topics, days_left,
     submit_tip, keyword}. Sorted by day."""
    today = today or date.today()
    out = []
    for ev in CALENDAR:
        if ev["month"] != month:
            continue
        if ev.get("special") == "black_friday":
            d = _tracker._black_friday(year)
        else:
            try:
                d = date(year, month, ev["day"])
            except ValueError:  # e.g. Feb 29/30 style edge cases
                d = date(year, month, 28)
        days_left = (d - today).days
        lead = ev["lead_weeks"]
        upload_by = d - timedelta(weeks=lead)
        tip = (f"Upload ~{max(lead - 2, 1)}-{lead} weeks before "
               f"(aim by {upload_by.isoformat()})")
        note = ev["note"]
        demand_note = (f"{str(ev['demand']).capitalize()} demand"
                       + (f" — {note}" if note else ""))
        out.append({
            "date": d.isoformat(), "name": ev["name"], "type": ev["type"],
            "approx": ev["approx"], "demand": ev["demand"],
            "demand_note": demand_note, "topics": ev["topics"],
            "days_left": days_left if days_left >= 0 else None,
            "submit_tip": tip, "keyword": ev["keyword"],
        })
    out.sort(key=lambda e: e["date"])
    return {"month": month, "year": year,
            "month_name": _MONTH_NAMES[month - 1], "items": out,
            "count": len(out)}


# ------------------------------------------------------------------ v11
# Full Year Calendar — Job A of Prompt #4: the old Trend Calendar tab is
# merged INTO Adobe Tracker. One list = trends.get_calendar() (per-event
# days_until / upload_by / status) MERGED with this module's 64-occasion
# dataset, deduped by normalised name + month (same rule as _merged):
# the entry carrying MORE stock topics/keywords wins.

def full_year_calendar(today=None):
    """Merged, deduped full-year calendar sorted by days-until.

    Each item: {event, date, days_until, upload_by, upload_overdue,
    demand, keywords, note, status, keyword} where status is one of
    "UPLOAD NOW" / "SUBMIT NOW" / "UPCOMING" (same computation as
    trends.get_calendar: upload-by reached -> UPLOAD NOW, <=30 days to
    the event -> SUBMIT NOW, otherwise UPCOMING). Upload-by turns red in
    the UI when overdue and amber when it falls within 30 days."""
    from datetime import date as _date
    today = today or _date.today()
    best = {}

    def consider(rec):
        month = int(rec["date"][5:7])
        k = _key(rec["event"], month)
        cur = best.get(k)
        if cur is None or len(rec["keywords"]) > len(cur["keywords"]):
            best[k] = rec

    # (a) Trend Calendar events — dates/deadlines already computed live
    for e in _trends.get_calendar():
        consider({
            "event": e["event"], "date": e["date"],
            "days_until": e["days_until"], "upload_by": e["upload_by"],
            "upload_overdue": e["upload_overdue"], "demand": e["demand"],
            "keywords": list(e["keywords"]), "note": e["note"],
            "status": e["status"].upper(),  # upload now -> UPLOAD NOW …
            "keyword": e["keywords"][0] if e["keywords"] else
                       e["event"].lower(),
        })

    # (b) the expanded 64-occasion dataset — roll each occasion to its
    # next occurrence (this year, else next), exactly like get_calendar
    for ev in CALENDAR:
        year = today.year
        if ev.get("special") == "black_friday":
            d = _tracker._black_friday(year)
            if d < today:
                d = _tracker._black_friday(year + 1)
        else:
            try:
                d = _date(year, ev["month"], ev["day"])
            except ValueError:
                d = _date(year, ev["month"], 28)
            if d < today:
                try:
                    d = _date(year + 1, ev["month"], ev["day"])
                except ValueError:
                    d = _date(year + 1, ev["month"], 28)
        days_until = (d - today).days
        upload_by = d - timedelta(weeks=ev["lead_weeks"])
        if upload_by <= today <= d:
            status = "UPLOAD NOW"
        elif days_until <= 30:
            status = "SUBMIT NOW"
        else:
            status = "UPCOMING"
        note = ev["note"]
        if ev["approx"]:
            note = (note + " " if note else "") + "(date approx — verify yearly)"
        consider({
            "event": ev["name"], "date": d.isoformat(),
            "days_until": days_until, "upload_by": upload_by.isoformat(),
            "upload_overdue": upload_by < today,
            "demand": ev["demand"], "keywords": list(ev["topics"]),
            "note": note.strip(), "status": status,
            "keyword": ev["keyword"],
        })

    out = sorted(best.values(), key=lambda e: e["days_until"])
    return {"today": today.isoformat(), "count": len(out), "events": out}
