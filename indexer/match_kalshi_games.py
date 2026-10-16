import json, re, sys, datetime, unicodedata
from difflib import SequenceMatcher

OV = sys.argv[1]
world = json.load(open(OV + "/world_events.json"))["events"]
kal = json.load(open(OV + "/kalshi/k_games.json"))
rules = {m["ticker"]: m for m in json.load(open(OV + "/world_markets_rules.json"))}

SERIES = {
    "WXNFL": "KXNFLGAME", "WXNHL": "KXNHLGAME", "WXMLB": "KXMLBGAME", "WXNCAAFB": "KXNCAAFGAME",
    "WXEPL": "KXEPLGAME", "WXUCL": "KXUCLGAME", "WXLIG": "KXLALIGAGAME", "WXSERIEA": "KXSERIEAGAME",
    "WXBUNDESLIGA": "KXBUNDESLIGAGAME", "WXLIGUE1": "KXLIGUE1GAME", "WXMLS": "KXMLSGAME", "WXUFCFIGHT": "KXUFCFIGHT",
}
NHL = dict(ducks="Anaheim", bruins="Boston", sabres="Buffalo", flames="Calgary", hurricanes="Carolina", blackhawks="Chicago",
           avalanche="Colorado", **{"blue jackets": "Columbus"}, stars="Dallas", **{"red wings": "Detroit"}, oilers="Edmonton",
           panthers="Florida", kings="Los Angeles", wild="Minnesota", canadiens="Montreal", predators="Nashville", devils="New Jersey",
           islanders="New York I", rangers="New York R", senators="Ottawa", flyers="Philadelphia", penguins="Pittsburgh",
           sharks="San Jose", kraken="Seattle", blues="St. Louis", lightning="Tampa Bay", **{"maple leafs": "Toronto"},
           mammoth="Utah", canucks="Vancouver", **{"golden knights": "Vegas"}, capitals="Washington", jets="Winnipeg")
NFL = dict(cardinals="Arizona", falcons="Atlanta", ravens="Baltimore", bills="Buffalo", panthers="Carolina", bears="Chicago",
           bengals="Cincinnati", browns="Cleveland", cowboys="Dallas", broncos="Denver", lions="Detroit", packers="Green Bay",
           texans="Houston", colts="Indianapolis", jaguars="Jacksonville", chiefs="Kansas City", raiders="Las Vegas",
           chargers="Los Angeles C", rams="Los Angeles R", dolphins="Miami", vikings="Minnesota", patriots="New England",
           saints="New Orleans", giants="New York G", jets="New York J", eagles="Philadelphia", steelers="Pittsburgh",
           **{"49ers": "San Francisco"}, seahawks="Seattle", buccaneers="Tampa Bay", titans="Tennessee", commanders="Washington")
ALIAS = {"paris saint-germain": "psg", "borussia moenchengladbach": "m gladbach", "m´gladbach": "m gladbach",
         "hamburger sv": "hamburg", "sabah fk": "sabah masazir", "rennes": "stade rennais", "draw": "tie",
         "borussia dortmund": "dortmund", "timmy cuamba": "timothy angel cuamba"}
MON = {m: i + 1 for i, m in enumerate("JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split())}

def canon(name, series):
    n = (name or "").strip()
    low = n.lower()
    if series in ("WXNHL", "WXNFL"):
        tbl = NHL if series == "WXNHL" else NFL
        nick = " ".join(low.split()[1:])  # drop abbreviation
        if nick in tbl:
            return tbl[nick]
    return ALIAS.get(low, n)

def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s.replace("&", " and "))
    s = re.sub(r"\b(fc|cf|afc|sc|ac|club|the|hotspur|and hove albion|united)\b", " ", s)
    return " ".join(s.split())

def sim(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    ta, tb = set(a.split()), set(b.split())
    r = SequenceMatcher(None, a, b).ratio()
    if ta <= tb or tb <= ta:
        r = max(r, 0.9)
    return r

def wdate(t):
    m = re.search(r"-(\d{2})([A-Z]{3})(\d{2})", t)
    if m:
        return datetime.date(2000 + int(m.group(1)), MON[m.group(2)], int(m.group(3)))
    m = re.search(r"-(\d{2})(\d{2})(\d{2})", t)
    if m:
        return datetime.date(2000 + int(m.group(1)), int(m.group(2)), int(m.group(3)))

def rules_date(wm):
    r = rules.get(wm["ticker"])
    try:
        return datetime.datetime.strptime(r["rulesPrimary"]["tokens"]["date"]["value"], "%B %d, %Y").date()
    except Exception:
        return None

def assign(ev, kev):
    ws = ev["markets"]
    ks = kev["markets"]
    pairs = []
    for wm in ws:
        cw = canon(wm["title"], ev["seriesTicker"])
        sc = sorted(((sim(cw, canon(km.get("yes_sub_title", ""), "")), km) for km in ks), key=lambda x: -x[0])
        pairs.append((wm, sc))
    used, res = set(), []
    for wm, sc in pairs:
        best = sc[0] if sc else (0, None)
        second = sc[1][0] if len(sc) > 1 else 0
        res.append((wm, best[1], best[0], second))
    return res

kidx = {}
for e in kal:
    kidx.setdefault(e["series_ticker"], []).append(e)

matched, unmatched, unsure = [], [], []
for ev in world:
    ks = SERIES.get(ev["seriesTicker"])
    if not ks:
        continue
    d = wdate(ev["ticker"])
    cands = []
    for kev in kidx.get(ks, []):
        kd = wdate(kev["event_ticker"])
        if not (d and kd):
            continue
        res = assign(ev, kev)
        score = sum(r[2] for r in res) / len(res)
        occ = [km.get("occurrence_datetime") for km in kev["markets"] if km.get("occurrence_datetime")]
        wct = ev["markets"][0].get("closeTime") or 0
        tdiff = abs(datetime.datetime.fromisoformat(occ[0].replace("Z", "+00:00")).timestamp() - wct) if occ else 9e9
        cands.append((score, abs((kd - d).days), kev, res, tdiff))
    cands.sort(key=lambda x: (-round(x[0], 3), x[4]))
    if not cands or cands[0][0] < 0.75:
        unmatched.append({"world_event": ev["ticker"], "title": ev["title"], "best_kalshi": (cands[0][2]["event_ticker"] + " | " + cands[0][2]["title"]) if cands else None,
                          "score": round(cands[0][0], 3) if cands else None, "reason": "no Kalshi event with the same participants"})
        continue
    score, dd, kev, res, _t = cands[0]
    rec = {"world_event": ev["ticker"], "title": ev["title"], "kalshi_event": kev["event_ticker"], "ktitle": kev["title"], "score": round(score, 3)}
    ok_names = all(r[1] is not None and ((r[2] >= 0.8 and r[3] < 0.85) or (r[2] == 1.0 and r[3] < 1.0)) for r in res) and len({r[1]["ticker"] for r in res}) == len(res)
    wrd = {rules_date(r[0]) for r in res} - {None}
    kocc = {(datetime.datetime.fromisoformat(r[1]["occurrence_datetime"].replace("Z", "+00:00")) - datetime.timedelta(hours=4)).date().isoformat() for r in res if r[1] and r[1].get("occurrence_datetime")}
    kocc_d = {datetime.date.fromisoformat(x) for x in kocc if x}
    date_ok = dd <= 1 and all(any(abs((a - b).days) <= 1 for b in kocc_d) for a in wrd) if kocc_d else dd <= 1
    if len(kev["markets"]) != len(ev["markets"]):
        rec["reason"] = "different outcome count (%d vs %d)" % (len(ev["markets"]), len(kev["markets"]))
        unsure.append(rec); continue
    if not ok_names:
        rec["reason"] = "participants differ: " + "; ".join("%s->%s(%.2f)" % (r[0]["title"], r[1].get("yes_sub_title") if r[1] else None, r[2]) for r in res)
        unsure.append(rec); continue
    if not date_ok:
        rec["reason"] = "scheduled date differs (World rules %s vs Kalshi %s)" % (sorted(map(str, wrd)), sorted(kocc))
        unsure.append(rec); continue
    for wm, km, s, s2 in res:
        matched.append({"world_event": ev["ticker"], "world_event_title": ev["title"], "world_market": wm["ticker"], "world_outcome": wm["title"],
                        "kalshi_event": kev["event_ticker"], "kalshi_event_title": kev["title"], "kalshi_market": km["ticker"],
                        "kalshi_outcome": km.get("yes_sub_title"), "name_score": round(s, 3), "runner_up": round(s2, 3)})

json.dump({"matched": matched, "unmatched": unmatched, "unsure": unsure}, open(OV + "/kalshi_game_map.json", "w"), indent=1)
print(len(matched), len({m["world_event"] for m in matched}), len(unmatched), len(unsure))
