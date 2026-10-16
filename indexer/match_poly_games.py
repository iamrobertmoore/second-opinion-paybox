import json, re, sys, datetime, unicodedata
from difflib import SequenceMatcher

OV = sys.argv[1]
world = json.load(open(OV + "/world_events.json"))["events"]
poly = json.load(open(OV + "/poly/p_all_sports.json"))
rules = {m["ticker"]: m for m in json.load(open(OV + "/world_markets_rules.json"))}

PFX = {"WXNFL": "nfl", "WXNHL": "nhl", "WXMLB": "mlb", "WXNCAAFB": "cfb", "WXEPL": "epl", "WXUCL": "ucl", "WXLIG": "lal",
       "WXSERIEA": "sea", "WXBUNDESLIGA": "bun", "WXLIGUE1": "fl1", "WXMLS": "mls", "WXUFCFIGHT": "ufc"}
MLB = {"tampa bay": "Rays", "cleveland": "Guardians", "baltimore": "Orioles", "new york y": "Yankees"}
ALIAS = {"mammoth": "Utah", "rennes": "Stade Rennais", "inter": "Internazionale", "bodoe/glimt": "Bodo Glimt", "slavia prague": "Slavia Praha",
         "lyon": "Olympique Lyonnais", "racing santander": "Real Racing Club", "brest": "Stade Brestois", "fc koeln": "1. FC Koln", "paris saint-germain": "Paris Saint-Germain FC"}
MON = {m: i + 1 for i, m in enumerate("JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split())}

def canon(name, series):
    low = (name or "").strip().lower()
    if series in ("WXNFL", "WXNHL") and len(low.split()) > 1:
        nick = " ".join(low.split()[1:])
        return ALIAS.get(nick, nick)
    if series == "WXMLB" and low in MLB:
        return MLB[low]
    if low in ALIAS:
        return ALIAS[low]
    if series in ("WXNHL", "WXNFL") and low in ALIAS:
        return ALIAS[low]
    if series == "WXNCAAFB":
        return re.sub(r"\bSt\.$", "State", name.strip())
    return name

def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s.replace("&", " and "))
    s = re.sub(r"\b(fc|cf|afc|sc|ac|club|the|hotspur|and hove albion|united|calcio|1913|04|05|ssc|vfb|sv|rb)\b", " ", s)
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

def fnum(x):
    try:
        return float(x)
    except Exception:
        return None

def poly_outcomes(ev):
    outs = []
    for m in ev.get("markets", []):
        if m.get("sportsMarketType") != "moneyline" or m.get("closed") or not m.get("active", True):
            continue
        oc = json.loads(m["outcomes"]) if isinstance(m.get("outcomes"), str) else m.get("outcomes") or []
        bb, ba = fnum(m.get("bestBid")), fnum(m.get("bestAsk"))
        if oc == ["Yes", "No"]:
            name = m.get("groupItemTitle") or m.get("question")
            if name.lower().startswith("draw"):
                name = "Draw"
            outs.append({"name": name, "ask": ba, "bid": bb, "market_id": m["id"], "slug": m.get("slug"), "side": "yes"})
        elif len(oc) == 2:
            outs.append({"name": oc[0], "ask": ba, "bid": bb, "market_id": m["id"], "slug": m.get("slug"), "side": "outcome0"})
            outs.append({"name": oc[1], "ask": (round(1 - bb, 6) if bb else None), "bid": (round(1 - ba, 6) if ba else None), "market_id": m["id"], "slug": m.get("slug"), "side": "outcome1"})
    return outs

pidx = {}
for e in poly:
    m = re.match(r"^([a-z0-9]+)-.*-(\d{4}-\d{2}-\d{2})$", e.get("slug", ""))
    if m:
        pidx.setdefault(m.group(1), []).append((datetime.date.fromisoformat(m.group(2)), e))

matched, unmatched, unsure = [], [], []
SNAP = float(sys.argv[2]) if len(sys.argv) > 2 else 0
for ev in world:
    p = PFX.get(ev["seriesTicker"])
    if not p:
        continue
    if SNAP and max(m.get("closeTime") or 0 for m in ev["markets"]) < SNAP:
        unmatched.append({"world_event": ev["ticker"], "title": ev["title"], "best_poly": None, "score": None, "reason": "World market closeTime already passed (stale game)"})
        continue
    d = wdate(ev["ticker"])
    cands = []
    for pd, pe in pidx.get(p, []):
        if not d or abs((pd - d).days) > 1:
            continue
        outs = poly_outcomes(pe)
        if not outs:
            continue
        res = []
        for wm in ev["markets"]:
            cw = canon(wm["title"], ev["seriesTicker"])
            sc = sorted(((sim(cw, o["name"]), o) for o in outs), key=lambda x: -x[0])
            res.append((wm, sc[0][1], sc[0][0], sc[1][0] if len(sc) > 1 else 0))
        score = sum(r[2] for r in res) / len(res)
        cands.append((score, abs((pd - d).days), pe, res, outs))
    cands.sort(key=lambda x: (-round(x[0], 3), x[1]))
    if not cands or cands[0][0] < 0.75:
        unmatched.append({"world_event": ev["ticker"], "title": ev["title"], "best_poly": cands[0][2]["slug"] if cands else None, "score": round(cands[0][0], 3) if cands else None})
        continue
    score, dd, pe, res, outs = cands[0]
    rec = {"world_event": ev["ticker"], "title": ev["title"], "poly_slug": pe["slug"], "ptitle": pe["title"], "score": round(score, 3)}
    ok = all(((r[2] >= 0.8 and r[3] < 0.85) or (r[2] == 1.0 and r[3] < 1.0)) for r in res) and len({(r[1]["market_id"], r[1]["side"]) for r in res}) == len(res)
    if len(outs) != len(ev["markets"]):
        rec["reason"] = "different outcome count (%d vs %d)" % (len(ev["markets"]), len(outs)); unsure.append(rec); continue
    if not ok:
        rec["reason"] = "participants differ: " + "; ".join("%s->%s(%.2f/%.2f)" % (r[0]["title"], r[1]["name"], r[2], r[3]) for r in res); unsure.append(rec); continue
    for wm, o, s, s2 in res:
        matched.append({"world_event": ev["ticker"], "world_event_title": ev["title"], "world_market": wm["ticker"], "world_outcome": wm["title"],
                        "poly_event_slug": pe["slug"], "poly_event_title": pe["title"], "poly_market_id": o["market_id"], "poly_market_slug": o["slug"],
                        "poly_outcome": o["name"], "poly_side": o["side"], "name_score": round(s, 3), "runner_up": round(s2, 3)})
json.dump({"matched": matched, "unmatched": unmatched, "unsure": unsure}, open(OV + "/poly_game_map.json", "w"), indent=1)
print(len(matched), len({m["world_event"] for m in matched}), len(unmatched), len(unsure))
