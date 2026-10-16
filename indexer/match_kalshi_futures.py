import json, re, sys, unicodedata
from difflib import SequenceMatcher

OV = sys.argv[1]
world = {e["ticker"]: e for e in json.load(open(OV + "/world_events.json"))["events"]}
kal = {e["event_ticker"]: e for e in json.load(open(OV + "/kalshi/k_futures.json"))}

EMAP = {
    "WXMLBCHAMP-26": "KXMLB-26", "WXNFLCHAMP-26": "KXSB-27", "WXF1DC-26WDC": "KXF1-26", "WXF1CC-26WCC": "KXF1CONSTRUCTORS-26",
    "WXPRESNOM-28R": "KXPRESNOMR-28", "WXPRESNOM-28D": "KXPRESNOMD-28", "WXPRESWIN-28": "KXPRESPERSON-28",
    "WXBTCYR-26HIGH": "KXBTCMAXY-26DEC31", "WXBTCYR-26200K": "KXBTCMAXY-26DEC31", "WXBTCYR-26LOW": "KXBTCMINY-27JAN01",
    "WXUSCONTROL-26HOUSE": "CONTROLH-2026", "WXUSCONTROL-26SEN": "CONTROLS-2026", "WXWTIMAX-26YE": "KXWTIMAX-26DEC31",
    "WXNDX-26YE": "KXNASDAQ100Y-26DEC31H1600", "WXSPX-26YE": "KXINXY-26DEC31H1600", "WXSPXPOS-26YE": "KXINXPOS-26DEC31H1900",
    "WXLAYOFFS-26YE": "KXLAYOFFSYINFO-26", "WXFEDCUTS-26YE": "KXRATECUTCOUNT-26DEC31", 
    "WXGASMAX-26YE": "KXAAAGASMAX-26DEC31", "WXLEADERS-26YE": "KXLEADERSOUT-27JAN01", "WXMUSKNW-26YE": "KXMUSKNW-26DEC31",
    "WXCAGOV-26": "KXGOVCA-26", "WXFRPRES-27": "KXFRENCHPRES-27",
    "WXARREST-26YE": "KXARREST-27JAN", "WXOSCARPIC-27": "KXOSCARPIC-27", "WXVENLEADER-26YE": "KXVENEZUELALEADER-26DEC31",
    "WXLAMAYOR-26": "KXMAYORLA-26", "WXMESENATE-26": "SENATEME-26", "WXNCSENATE-26": "SENATENC-26", "WXTXSENATE-26": "SENATETX-26",
    "WXU3MAX-26YE": "KXU3MAX-27", 
}
# explicit outcome aliases World title -> Kalshi yes_sub_title (only where wording is equivalent)
OALIAS = {
    ("WXNDX-26YE", "Below 19,000"): "18,999.99 or below",
    ("WXBTCYR-26200K", "Bitcoin above $200,000 in 2026"): "Above $199,999.99",
    ("WXMUSKNW-26YE", "More than $1.4T"): "Above $1.4 trillion",
    ("WXPRESNOM-28R", "Donald Trump Jr."): "Donald J. Trump Jr.", ("WXPRESNOM-28R", "Donald Trump"): "Donald J. Trump",
    ("WXPRESNOM-28D", "JB Pritzker"): "J.B. Pritzker", ("WXPRESWIN-28", "Donald Trump Jr."): "Donald J. Trump Jr.", ("WXPRESWIN-28", "JB Pritzker"): "J.B. Pritzker",
    ("WXBTCYR-26LOW", "Below $45,000"): "Below $45,000.00", ("WXBTCYR-26LOW", "Below $50,000"): "Below $50,000.00", ("WXBTCYR-26LOW", "Below $55,000"): "Below $55,000.00",
    ("WXU3MAX-26YE", "Above 5.0%"): "Above 5%", ("WXLAYOFFS-26YE", "More tech-sector layoffs in 2026 than 2025"): "Yes",
    ("WXSPXPOS-26YE", "S&P 500 closes 2026 higher than 2025"): "Positive Growth",
    ("WXF1DC-26WDC", "Does Kimi Antonelli win Formula 1 2026 Drivers' Championship?"): "Andrea Kimi Antonelli",
    ("WXF1DC-26WDC", "Does Carlos Sainz win Formula 1 2026 Drivers' Championship?"): "Carlos Sainz Jr.",
    ("WXUSCONTROL-26HOUSE", "Democrats"): "Democratic party", ("WXUSCONTROL-26HOUSE", "Republicans"): "Republican party",
    ("WXUSCONTROL-26SEN", "Democrats"): "Democratic party", ("WXUSCONTROL-26SEN", "Republicans"): "Republican party",
    ("WXMESENATE-26", "Democratic"): "Democratic party", ("WXMESENATE-26", "Republican"): "Republican party",
    ("WXNCSENATE-26", "Democratic"): "Democratic party", ("WXNCSENATE-26", "Republican"): "Republican party",
    ("WXTXSENATE-26", "Democratic"): "Democratic party", ("WXTXSENATE-26", "Republican"): "Republican party",
}

NFLC = dict(cardinals="Arizona", falcons="Atlanta", ravens="Baltimore", bills="Buffalo", panthers="Carolina", bears="Chicago",
           bengals="Cincinnati", browns="Cleveland", cowboys="Dallas", broncos="Denver", lions="Detroit", packers="Green Bay",
           texans="Houston", colts="Indianapolis", jaguars="Jacksonville", chiefs="Kansas City", raiders="Las Vegas",
           chargers="Los Angeles C", rams="Los Angeles R", dolphins="Miami", vikings="Minnesota", patriots="New England",
           saints="New Orleans", giants="New York G", jets="New York J", eagles="Philadelphia", steelers="Pittsburgh",
           **{"49ers": "San Francisco"}, seahawks="Seattle", buccaneers="Tampa Bay", titans="Tennessee", commanders="Washington")

def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\((d|r)\)", " ", s)
    s = re.sub(r"[^a-z0-9$.,% ]", " ", s)
    s = " ".join(s.split())
    s = re.sub(r"^does (.*) win formula 1 2026 (drivers|constructors) championship$", r"\1", s)
    return s

def sim(a, b):
    a, b = norm(a), norm(b)
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()

matched, unsure, notes = [], [], []
for wt, kt in EMAP.items():
    ev, kev = world.get(wt), kal.get(kt)
    if not ev or not kev:
        notes.append((wt, kt, "missing"))
        continue
    for wm in ev["markets"]:
        target = OALIAS.get((wt, wm["title"]))
        best = None
        for km in kev["markets"]:
            sub = km.get("yes_sub_title") or ""
            wt_title = NFLC.get(" ".join(wm["title"].lower().split()[1:]), wm["title"]) if wt == "WXNFLCHAMP-26" else wm["title"]
            s = 1.0 if target and norm(sub) == norm(target) else sim(wt_title, sub)
            if best is None or s > best[0]:
                best = (s, km)
        s, km = best
        rec = {"world_event": wt, "world_event_title": ev["title"], "world_market": wm["ticker"], "world_outcome": wm["title"],
               "kalshi_event": kt, "kalshi_event_title": kev["title"], "kalshi_market": km["ticker"], "kalshi_outcome": km.get("yes_sub_title"), "name_score": round(s, 3)}
        if s >= 0.97:
            matched.append(rec)
        elif s >= 0.75:
            rec["reason"] = "outcome wording close but not identical"
            unsure.append(rec)
json.dump({"matched": matched, "unsure": unsure, "notes": notes}, open(OV + "/kalshi_futures_map.json", "w"), indent=1)
print(len(matched), len(unsure), notes)
