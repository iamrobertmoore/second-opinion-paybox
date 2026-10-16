import json, re, sys, unicodedata
from difflib import SequenceMatcher

OV = sys.argv[1]
world = {e["ticker"]: e for e in json.load(open(OV + "/world_events.json"))["events"]}
pev = json.load(open(OV + "/poly/p_fut_events.json"))

PAIRS = {
    "WXMLBCHAMP-26": "mlb-world-series-champion-2026", "WXNFLCHAMP-26": "pro-football-2027-champion-20260729185915366",
    "WXF1DC-26WDC": "2026-f1-drivers-champion", "WXF1CC-26WCC": "f1-constructors-champion",
    "WXPRESNOM-28R": "republican-presidential-nominee-2028", "WXPRESNOM-28D": "democratic-presidential-nominee-2028",
    "WXPRESWIN-28": "presidential-election-winner-2028", "WXUSCONTROL-26HOUSE": "which-party-will-win-the-house-in-2026",
    "WXUSCONTROL-26SEN": "which-party-will-win-the-senate-in-2026", "WXUSCONTROL-26BOP": "balance-of-power-2026-midterms",
    "WXBTCYR-26HIGH": "what-price-will-bitcoin-hit-before-2027", "WXBTCYR-26LOW": "what-price-will-bitcoin-hit-before-2027",
    "WXBTCYR-26200K": "what-price-will-bitcoin-hit-before-2027", "WXMANDA-26YE": "which-companies-will-be-acquired-before-2027",
    "WXCAGOV-26": "california-governor-election-2026", "WXFRPRES-27": "next-french-presidential-election",
    "WXHOTTESTYR-26": "where-will-2026-rank-among-the-hottest-years-on-record", "WXIRANLEADER-26YE": "iran-leader-end-of-2026",
    "WXLAMAYOR-26": "los-angeles-mayoral-election-117", "WXLARGESTCO-26YE": "largest-company-end-of-december-2026",
    "WXLARGESTIPO-26YE": "largest-ipo-by-market-cap-in-2026-287", "WXSPACEXLAUNCH-26YE": "how-many-spacex-launches-in-2026",
    "WXTOPGROSS-26YE": "highest-grossing-movie-in-2026", "WXTOPOPENING-26YE": "which-movie-has-biggest-opening-weekend-in-2026",
    "WXVENLEADER-26YE": "venezuela-leader-end-of-2026", "WXOSCARPIC-27": "oscars-2027-best-picture-winner-20260727173620857",
    "WXSPOTIFYTOP-26YE": "top-spotify-artist-2026", "WXARREST-26YE": "who-will-be-arrested-before-2027",
}
OALIAS = {
    ("WXUSCONTROL-26BOP", "Democratic Senate & House"): "Democrats Sweep", ("WXUSCONTROL-26BOP", "Democratic Senate, Republican House"): "D Senate, R House",
    ("WXUSCONTROL-26BOP", "Republican Senate, Democratic House"): "R Senate, D House", ("WXUSCONTROL-26BOP", "Republican Senate & House"): "Republicans Sweep",
    ("WXUSCONTROL-26HOUSE", "Democrats"): "Democratic Party", ("WXUSCONTROL-26HOUSE", "Republicans"): "Republican Party",
    ("WXUSCONTROL-26SEN", "Democrats"): "Democratic Party", ("WXUSCONTROL-26SEN", "Republicans"): "Republican Party",
    ("WXBTCYR-26HIGH", "Above $99,999.99"): "↑ 100,000", ("WXBTCYR-26HIGH", "Above $109,999.99"): "↑ 110,000", ("WXBTCYR-26HIGH", "Above $119,999.99"): "↑ 120,000",
    ("WXBTCYR-26200K", "Bitcoin above $200,000 in 2026"): "↑ 200,000",
    ("WXBTCYR-26LOW", "Below $45,000"): "↓ 45,000", ("WXBTCYR-26LOW", "Below $50,000"): "↓ 50,000", ("WXBTCYR-26LOW", "Below $55,000"): "↓ 55,000",
    ("WXHOTTESTYR-26", "1st hottest"): "1", ("WXHOTTESTYR-26", "2nd hottest"): "2", ("WXHOTTESTYR-26", "3rd hottest"): "3",
    ("WXHOTTESTYR-26", "4th hottest"): "4", ("WXHOTTESTYR-26", "5th hottest"): "5", ("WXHOTTESTYR-26", "6th or cooler"): "6 or lower",
    ("WXSPACEXLAUNCH-26YE", "<100"): "__none__",
    ("WXPRESNOM-28D", "JB Pritzker"): "J.B. Pritzker", ("WXPRESWIN-28", "J.D. Vance"): "JD Vance",
    ("WXCAGOV-26", "Xavier Becerra (D)"): "Xavier Becerra", ("WXCAGOV-26", "Steve Hilton (R)"): "Steve Hilton",
    ("WXF1DC-26WDC", "Does Kimi Antonelli win Formula 1 2026 Drivers' Championship?"): "Kimi Antonelli",
}
NFL = dict(cardinals="Arizona Cardinals", falcons="Atlanta Falcons", ravens="Baltimore Ravens", bills="Buffalo Bills", panthers="Carolina Panthers",
           bears="Chicago Bears", bengals="Cincinnati Bengals", browns="Cleveland Browns", cowboys="Dallas Cowboys", broncos="Denver Broncos",
           lions="Detroit Lions", packers="Green Bay Packers", texans="Houston Texans", colts="Indianapolis Colts", jaguars="Jacksonville Jaguars",
           chiefs="Kansas City Chiefs", raiders="Las Vegas Raiders", chargers="Los Angeles Chargers", rams="Los Angeles Rams", dolphins="Miami Dolphins",
           vikings="Minnesota Vikings", patriots="New England Patriots", saints="New Orleans Saints", giants="New York Giants", jets="New York Jets",
           eagles="Philadelphia Eagles", steelers="Pittsburgh Steelers", **{"49ers": "San Francisco 49ers"}, seahawks="Seattle Seahawks",
           buccaneers="Tampa Bay Buccaneers", titans="Tennessee Titans", commanders="Washington Commanders")
MLB = {"Tampa Bay": "Tampa Bay Rays", "Cleveland": "Cleveland Guardians", "Milwaukee": "Milwaukee Brewers"}

def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9$.,%<> ]", " ", s)
    s = " ".join(s.split())
    s = re.sub(r"^does (.*) win formula 1 2026 (drivers|constructors) championship\??$", r"\1", s)
    return s

def sim(a, b):
    a, b = norm(a), norm(b)
    return 1.0 if a == b else SequenceMatcher(None, a, b).ratio()

def poly_markets(ev):
    out = []
    for m in ev.get("markets", []):
        if m.get("closed"):
            continue
        name = m.get("groupItemTitle") or m.get("question")
        out.append((name, m))
    return out

matched, unsure = [], []
for wt, slug in PAIRS.items():
    ev, pe = world[wt], pev.get(slug)
    if not pe:
        continue
    pm = poly_markets(pe)
    for wm in ev["markets"]:
        title = wm["title"]
        if wt == "WXNFLCHAMP-26":
            title = NFL.get(" ".join(title.lower().split()[1:]), title)
        if wt == "WXMLBCHAMP-26":
            title = MLB.get(title, title)
        target = OALIAS.get((wt, wm["title"]))
        sc = sorted((((1.0 if target and name == target else sim(title, name)), name, m) for name, m in pm), key=lambda x: -x[0])
        if not sc:
            continue
        s, name, m = sc[0]
        s2 = sc[1][0] if len(sc) > 1 else 0
        rec = {"world_event": wt, "world_event_title": ev["title"], "world_market": wm["ticker"], "world_outcome": wm["title"],
               "poly_event_slug": slug, "poly_event_title": pe["title"], "poly_market_id": m["id"], "poly_market_slug": m.get("slug"),
               "poly_outcome": name, "poly_side": "yes", "name_score": round(s, 3), "runner_up": round(s2, 3)}
        if s >= 0.95 and s2 < 0.95:
            matched.append(rec)
        elif s >= 0.75:
            rec["reason"] = "outcome wording close but not identical"
            unsure.append(rec)
json.dump({"matched": matched, "unsure": unsure}, open(OV + "/poly_futures_map.json", "w"), indent=1)
print(len(matched), len(unsure))
