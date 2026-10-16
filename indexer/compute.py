import json, sys, csv, datetime, statistics

OV = sys.argv[1]
SNAP_TS = float(sys.argv[2])          # World snapshot epoch
SNAP_DATE = datetime.datetime.utcfromtimestamp(SNAP_TS).date()
W = json.load(open(OV + "/world_events.json"))
world_events = W["events"]
rules = {m["ticker"]: m for m in json.load(open(OV + "/world_markets_rules.json"))}
kg = json.load(open(OV + "/kalshi_game_map.json"))
kf = json.load(open(OV + "/kalshi_futures_map.json"))
pg = json.load(open(OV + "/poly_game_map.json"))
pf = json.load(open(OV + "/poly_futures_map.json"))
kq = {}
for f in ("k_games_q.json", "k_futures_q.json"):
    for e in json.load(open(OV + "/kalshi/" + f)):
        for m in e.get("markets", []):
            kq[m["ticker"]] = m
pq = json.load(open(OV + "/poly/p_quotes.json"))  # slug -> event

def fl(x):
    try:
        v = float(x)
        return v
    except Exception:
        return None

def valid(a):
    return a is not None and 0 < a < 0.999

# World events excluded for both venues: Kalshi-unsure date mismatches + stale (rules date before snapshot day)
date_mismatch = {u["world_event"] for u in kg["unsure"] if "date" in u.get("reason", "")}
def rules_date(t):
    r = rules.get(t)
    try:
        return datetime.datetime.strptime(r["rulesPrimary"]["tokens"]["date"]["value"], "%B %d, %Y").date()
    except Exception:
        return None

wmk = {}
wev = {}
for e in world_events:
    wev[e["ticker"]] = e
    for m in e["markets"]:
        wmk[m["ticker"]] = (e, m)

kmap = {r["world_market"]: r for r in kg["matched"] + kf["matched"]}
pmap = {r["world_market"]: r for r in pg["matched"] + pf["matched"]}

def poly_ask(r):
    ev = pq.get(r["poly_event_slug"])
    if not ev:
        return None, None
    for m in ev.get("markets", []):
        if m["id"] == r["poly_market_id"]:
            if m.get("closed") or m.get("acceptingOrders") is False:
                return None, m
            bb, ba = fl(m.get("bestBid")), fl(m.get("bestAsk"))
            if r["poly_side"] == "outcome1":
                return (round(1 - bb, 6) if bb else None), m
            return ba, m
    return None, None

rows, excluded = [], {"stale_or_date_mismatch": 0, "world_no_ask": 0, "other_no_quote": 0}
for wt, (e, m) in wmk.items():
    if wt not in kmap and wt not in pmap:
        continue
    rd = rules_date(wt)
    if e["ticker"] in date_mismatch or (e["category"] == "sports" and rd and rd < SNAP_DATE) or (m.get("status") != "active"):
        excluded["stale_or_date_mismatch"] += 1
        continue
    wa = fl(m.get("yesAsk"))
    if not valid(wa):
        excluded["world_no_ask"] += 1
        continue
    ka = pa = None
    km = kmap.get(wt)
    if km:
        q = kq.get(km["kalshi_market"])
        if q and q.get("status") == "active":
            ka = fl(q.get("yes_ask_dollars"))
            if not valid(ka):
                ka = None
    pm = pmap.get(wt)
    if pm:
        pa, _ = poly_ask(pm)
        if not valid(pa):
            pa = None
    if ka is None and pa is None:
        excluded["other_no_quote"] += 1
        continue
    cands = [(v, n) for v, n in ((ka, "Kalshi"), (pa, "Polymarket")) if v is not None]
    best, bv = min(cands)
    spread = (wa - best) * 100
    cheapest = "World" if wa < best - 1e-9 else (bv if wa > best + 1e-9 else "tie")
    rows.append({
        "world_event": e["ticker"], "world_event_title": e["title"], "category": e["category"], "world_market": wt, "outcome": m["title"],
        "world_yes_ask": round(wa, 6), "kalshi_market": km["kalshi_market"] if km else "", "kalshi_yes_ask": ka if ka is not None else "",
        "poly_event_slug": pm["poly_event_slug"] if pm else "", "poly_outcome": pm["poly_outcome"] if pm else "", "poly_yes_ask": pa if pa is not None else "",
        "best_other_venue": bv, "best_other_yes_ask": best, "spread_cents": round(spread, 3), "spread_pct_of_world_ask": round(spread / wa, 2),
        "cheapest_venue": cheapest, "world_event_volume24h_raw": e.get("volume24h"),
    })

rows.sort(key=lambda r: -abs(r["spread_cents"]))
with open(OV + "/matched_outcomes.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)

def summ(rs, label):
    if not rs:
        return {"label": label, "n": 0}
    sp = [r["spread_cents"] for r in rs]
    ab = [abs(x) for x in sp]
    pc = [abs(r["spread_pct_of_world_ask"]) for r in rs]
    return {"label": label, "n": len(rs),
            "cheaper_elsewhere": sum(1 for r in rs if r["cheapest_venue"] in ("Kalshi", "Polymarket")),
            "cheaper_on_world": sum(1 for r in rs if r["cheapest_venue"] == "World"),
            "tie": sum(1 for r in rs if r["cheapest_venue"] == "tie"),
            "cheaper_elsewhere_by_1c_plus": sum(1 for x in sp if x >= 1), "cheaper_on_world_by_1c_plus": sum(1 for x in sp if x <= -1),
            "within_1c": sum(1 for x in sp if abs(x) < 1),
            "median_signed_spread_c": round(statistics.median(sp), 3), "median_abs_spread_c": round(statistics.median(ab), 3),
            "max_abs_spread_c": round(max(ab), 3), "median_abs_spread_pct": round(statistics.median(pc), 2), "max_abs_spread_pct": round(max(pc), 2),
            "mean_signed_spread_c": round(statistics.mean(sp), 3),
            "by_cheapest_other": {v: sum(1 for r in rs if r["cheapest_venue"] == v) for v in ("Kalshi", "Polymarket")}}

matched_events = {r["world_event"] for r in rows}
vol = sum((wev[t].get("volume24h") or 0) for t in matched_events)
active_events = [e for e in world_events]
out = {
    "snapshot_world_utc": datetime.datetime.utcfromtimestamp(SNAP_TS).isoformat() + "Z",
    "world_active_events": len(active_events), "world_markets_listed": sum(len(e["markets"]) for e in active_events),
    "world_markets_status_active": sum(1 for e in active_events for m in e["markets"] if m.get("status") == "active"),
    "world_markets_with_yes_ask": sum(1 for e in active_events for m in e["markets"] if valid(fl(m.get("yesAsk")))),
    "mapped_world_markets_kalshi": len(kmap), "mapped_world_markets_poly": len(pmap),
    "mapped_world_markets_any": len(set(kmap) | set(pmap)),
    "mapped_world_events_any": len({r["world_event"] for r in list(kmap.values()) + list(pmap.values())}),
    "priced_comparable_outcomes": len(rows), "priced_comparable_events": len(matched_events), "excluded": excluded,
    "all": summ(rows, "all"),
    "excl_longshots_both_le_3c": summ([r for r in rows if not (r["world_yes_ask"] <= 0.03 and r["best_other_yes_ask"] <= 0.03)], "excl both<=3c"),
    "sports_games": summ([r for r in rows if r["category"] == "sports" and not r["world_event"].startswith(("WXMLBCHAMP", "WXNFLCHAMP", "WXF1"))], "games"),
    "futures": summ([r for r in rows if not (r["category"] == "sports" and not r["world_event"].startswith(("WXMLBCHAMP", "WXNFLCHAMP", "WXF1")))], "futures"),
    "vs_kalshi_only": summ([dict(r, spread_cents=round((r["world_yes_ask"] - r["kalshi_yes_ask"]) * 100, 3), spread_pct_of_world_ask=round(100 * (r["world_yes_ask"] - r["kalshi_yes_ask"]) / r["world_yes_ask"], 2),
                                 cheapest_venue=("World" if r["world_yes_ask"] < r["kalshi_yes_ask"] else ("Kalshi" if r["world_yes_ask"] > r["kalshi_yes_ask"] else "tie"))) for r in rows if r["kalshi_yes_ask"] != ""], "vs Kalshi"),
    "vs_poly_only": summ([dict(r, spread_cents=round((r["world_yes_ask"] - r["poly_yes_ask"]) * 100, 3), spread_pct_of_world_ask=round(100 * (r["world_yes_ask"] - r["poly_yes_ask"]) / r["world_yes_ask"], 2),
                               cheapest_venue=("World" if r["world_yes_ask"] < r["poly_yes_ask"] else ("Polymarket" if r["world_yes_ask"] > r["poly_yes_ask"] else "tie"))) for r in rows if r["poly_yes_ask"] != ""], "vs Polymarket"),
    "world_vol24h_raw_matched_events": vol, "world_vol24h_matched_events_div1e6": round(vol / 1e6, 2),
    "world_vol24h_raw_all_events": sum((e.get("volume24h") or 0) for e in world_events),
    "top10": [{k: r[k] for k in ("world_market", "outcome", "world_yes_ask", "kalshi_market", "kalshi_yes_ask", "poly_event_slug", "poly_yes_ask", "spread_cents", "spread_pct_of_world_ask", "cheapest_venue")} for r in rows[:10]],
}
json.dump(out, open(OV + "/summary.json", "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "top10"}, indent=1))
