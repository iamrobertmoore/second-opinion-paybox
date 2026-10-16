"""Build service/data/index.json: World market -> matched Kalshi / Polymarket outcome, plus a World
price snapshot and the World premium baseline. Inputs are the scan files produced by the match_* scripts."""
import json, csv, sys, statistics, re
OV, OUT = sys.argv[1], sys.argv[2]
rows = list(csv.DictReader(open(f"{OV}/matched_outcomes.csv")))
rules = {m["ticker"]: m for m in json.load(open(f"{OV}/world_markets_rules.json"))}
W = json.load(open(f"{OV}/world_events.json"))
ev = {e["ticker"]: e for e in W["events"]}
km = {r["world_market"]: r for f in ["kalshi_game_map.json", "kalshi_futures_map.json"] for r in json.load(open(f"{OV}/{f}"))["matched"]}
pm = {r["world_market"]: r for f in ["poly_game_map.json", "poly_futures_map.json"] for r in json.load(open(f"{OV}/{f}"))["matched"]}

def render_rules(r):
    rp = (r or {}).get("rulesPrimary") or {}
    t = rp.get("template") or ""
    for k, v in (rp.get("tokens") or {}).items():
        t = t.replace("{" + k + "}", str(v.get("value", "")) if isinstance(v, dict) else str(v))
    return re.sub(r"\s+", " ", t).strip()[:600]

def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None

DISAGREE = 0.03  # Kalshi and Polymarket more than 3c apart: likely different rules, left out of the baseline

markets, prem = [], []
for r in rows:
    t = r["world_market"]; e = ev.get(r["world_event"], {}); ru = rules.get(t, {})
    wmk = next((m for m in e.get("markets", []) if m["ticker"] == t), {})
    k = km.get(t); p = pm.get(t)
    markets.append({
        "ticker": t, "event": r["world_event"], "event_title": r["world_event_title"], "outcome": r["outcome"],
        "category": r["category"], "close_time": wmk.get("closeTime") or ru.get("closeTime"),
        "world_yes_ask": float(r["world_yes_ask"]), "world_yes_bid": float(wmk["yesBid"]) if wmk.get("yesBid") else None,
        "kalshi": {"ticker": k["kalshi_market"], "title": k.get("kalshi_event_title"), "outcome": k.get("kalshi_outcome")} if k else None,
        "polymarket": {"id": p["poly_market_id"], "slug": p.get("poly_market_slug"), "event_slug": p["poly_event_slug"], "title": p.get("poly_event_title"),
                        "outcome": p.get("poly_outcome"), "side": p["poly_side"]} if p else None,
        "rules": render_rules(ru), "dispute_window_s": ru.get("disputeWindowSeconds"),
        "oracle": "chainlink" if (ru.get("metadata") or {}).get("chainlink_market_id") else None,
        "volume24h_raw": int(e.get("volume24h") or 0),
        "snap": {"best_other": r["best_other_venue"], "best_other_ask": float(r["best_other_yes_ask"]), "spread_cents": float(r["spread_cents"]),
                 "kalshi_ask": fnum(r["kalshi_yes_ask"]), "poly_ask": fnum(r["poly_yes_ask"])},
    })
    k_, p_ = fnum(r["kalshi_yes_ask"]), fnum(r["poly_yes_ask"])
    markets[-1]["venues_disagree"] = bool(k_ and p_ and abs(k_ - p_) > DISAGREE)
    if not markets[-1]["venues_disagree"]:
        prem.append(float(r["spread_cents"]))
prem.sort()
q = lambda f: prem[min(len(prem) - 1, int(f * len(prem)))]
out = {"snapshot_utc": W["snapshot_utc"], "count": len(markets),
       "baseline": {"median_premium_cents": round(statistics.median(prem), 3), "p90_premium_cents": round(q(0.9), 3),
                    "two_cents_or_more": sum(1 for x in prem if x >= 2), "largest_cents": round(max(prem), 2), "n": len(prem),
                    "excluded_rules_mismatch": len(markets) - len(prem)},
       "markets": markets}
json.dump(out, open(OUT, "w"), separators=(",", ":"))
print(out["count"], out["baseline"], round(len(json.dumps(out)) / 1024), "KiB")
