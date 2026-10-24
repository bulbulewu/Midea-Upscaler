"""
Editorial / seasonal trend calendar for stock contributors.

Each entry: the selling event, when buyers search, and how many weeks
BEFORE the event contributors should upload (agencies review + index lag).
`days_until` is computed live from today's date.

Dates marked ~ move each year (Ramadan, Eid, Holi, Diwali, Chinese New Year);
the note field says so.
"""

import datetime

EVENTS = [
    # (month, day, name, upload_lead_weeks, demand, keywords, note)
    (1, 1, "New Year", 10, "high",
     ["new year", "2027", "celebration", "fireworks", "resolutions", "party", "confetti"],
     "Upload Oct-Nov; finance & resolution concepts sell too."),
    (2, 14, "Valentine's Day", 8, "high",
     ["valentine", "love", "romance", "hearts", "couple", "roses", "gift"],
     ""),
    (3, 8, "International Women's Day", 6, "medium",
     ["woman", "diversity", "empowerment", "business woman", "equality"],
     ""),
    (3, 17, "St. Patrick's Day", 6, "medium",
     ["shamrock", "green", "irish", "beer", "luck", "clover"],
     ""),
    (4, 22, "Earth Day", 8, "medium",
     ["eco", "environment", "recycling", "sustainability", "green energy", "nature"],
     "Evergreen topic; spikes each April."),
    (5, 12, "Mother's Day", 8, "medium",
     ["mother", "family", "flowers", "gift", "mom", "love"],
     "Date varies by country; US = 2nd Sunday of May."),
    (6, 1, "Summer Travel Season", 12, "high",
     ["travel", "beach", "vacation", "summer", "tourism", "passport", "suitcase"],
     "Upload Feb-Apr for northern-hemisphere summer."),
    (6, 16, "Father's Day", 8, "medium",
     ["father", "dad", "family", "gift", "barbecue"],
     "US = 3rd Sunday of June."),
    (7, 4, "US Independence Day", 8, "medium",
     ["america", "flag", "fireworks", "freedom", "bbq", "patriotic"],
     ""),
    (8, 15, "Back to School", 10, "high",
     ["school", "education", "students", "backpack", "classroom", "kids"],
     "Upload May-Jun; huge education-buyer demand."),
    (10, 31, "Halloween", 10, "high",
     ["halloween", "pumpkin", "spooky", "horror", "costume", "autumn", "witch"],
     "Vectors & spooky 4K b-roll sell early."),
    (11, 29, "Black Friday / Cyber Monday", 10, "high",
     ["black friday", "sale", "shopping", "discount", "cyber monday", "retail"],
     "~ last Fri/Mon of November; upload Sep."),
    (12, 25, "Christmas", 12, "very high",
     ["christmas", "holiday", "winter", "gift", "santa", "snow", "bokeh", "decorations"],
     "Biggest stock season; upload Sep-Oct."),
    (12, 31, "New Year's Eve", 10, "high",
     ["new year eve", "party", "countdown", "champagne", "fireworks"],
     ""),
    # moving dates (approximate; verify each year)
    (3, 20, "Ramadan ~", 8, "high",
     ["ramadan", "islamic", "mosque", "crescent", "iftar", "eid", "lantern"],
     "~ moves ~11 days earlier each year; verify dates."),
    (4, 21, "Eid al-Fitr ~", 8, "high",
     ["eid", "celebration", "mosque", "family", "gifts", "islamic"],
     "~ end of Ramadan; verify dates each year."),
    (3, 4, "Holi ~", 6, "medium",
     ["holi", "colors", "festival", "india", "powder", "celebration"],
     "~ March; verify dates each year."),
    (11, 8, "Diwali ~", 8, "high",
     ["diwali", "diya", "festival of lights", "india", "lantern", "celebration"],
     "~ Oct/Nov; verify dates each year."),
    (2, 17, "Chinese New Year ~", 8, "medium",
     ["chinese new year", "lunar new year", "dragon", "lantern", "red", "zodiac"],
     "~ Jan/Feb; verify the zodiac animal each year."),
]


def get_calendar(year=None):
    today = datetime.date.today()
    year = year or today.year
    out = []
    for month, day, name, lead, demand, keywords, note in EVENTS:
        try:
            event = datetime.date(year, month, day)
        except ValueError:
            continue
        if event < today:  # roll to next year if passed
            try:
                event = datetime.date(year + 1, month, day)
            except ValueError:
                continue
        days_until = (event - today).days
        upload_by = event - datetime.timedelta(weeks=lead)
        status = ("upload now" if upload_by <= today <= event
                  else "upcoming" if days_until > 30 else "submit now")
        out.append({
            "event": name, "date": event.isoformat(),
            "days_until": days_until,
            "upload_by": upload_by.isoformat(),
            "upload_overdue": upload_by < today,
            "demand": demand, "keywords": keywords, "note": note,
            "status": status,
        })
    out.sort(key=lambda e: e["days_until"])
    return out
