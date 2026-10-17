// Second Opinion: compare a World outcome's YES price with the same outcome on Kalshi and Polymarket,
// against World's own usual premium, and return a receipt an agent can act on.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const INDEX = JSON.parse(readFileSync(join(here, "..", "data", "index.json"), "utf8"));
const BY_TICKER = new Map(INDEX.markets.map((m) => [m.ticker, m]));

export const BASELINE = { ...INDEX.baseline, median_premium_cents: Math.round(INDEX.baseline.median_premium_cents * 100) / 100, p90_premium_cents: Math.round(INDEX.baseline.p90_premium_cents * 100) / 100 };
export const SNAPSHOT_UTC = INDEX.snapshot_utc;

// Thresholds. FAIR means within World's normal premium; STRETCHED means a premium a buyer should not pay.
const STRETCH_CENTS = 1.6; // about the 90th percentile of World's premium over the best other venue
const DISAGREE_CENTS = 3; // Kalshi and Polymarket this far apart usually means the rules differ
const STRETCH_SHARE = 0.15; // or, from 1c up, more than 15% on top of the best other price
const MIN_STRETCH_CENTS = 1.0; // the percentage test only applies from 1c up

async function getJson(url, ms = 3500) {
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), ms);
  try {
    const r = await fetch(url, { signal: ctl.signal, headers: { accept: "application/json" } });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return await r.json();
  } finally {
    clearTimeout(t);
  }
}

const num = (x) => {
  const v = typeof x === "string" ? parseFloat(x) : x;
  return Number.isFinite(v) && v > 0 && v < 1 ? v : null;
};

async function kalshiQuote(k) {
  if (!k) return { venue: "Kalshi", status: "not_listed" };
  try {
    const { market: m } = await getJson(`https://api.elections.kalshi.com/trade-api/v2/markets/${encodeURIComponent(k.ticker)}`);
    const ask = m.status === "active" ? num(m.yes_ask_dollars) : null;
    return { venue: "Kalshi", status: ask ? "quoted" : "no_quote", yes_ask: ask, yes_bid: num(m.yes_bid_dollars), market: k.ticker,
      url: `https://kalshi.com/markets/${k.ticker.split("-")[0].toLowerCase()}`, rules: (m.rules_primary || "").slice(0, 400) };
  } catch (e) {
    return { venue: "Kalshi", status: "unreachable", market: k.ticker };
  }
}

async function polyQuote(p) {
  if (!p) return { venue: "Polymarket", status: "not_listed" };
  try {
    const m = await getJson(`https://gamma-api.polymarket.com/markets/${encodeURIComponent(p.id)}`);
    const live = !m.closed && m.acceptingOrders !== false;
    let ask = null, bid = null;
    if (live) {
      if (p.side === "outcome1") { ask = m.bestBid ? num(1 - m.bestBid) : null; bid = m.bestAsk ? num(1 - m.bestAsk) : null; }
      else { ask = num(m.bestAsk); bid = num(m.bestBid); }
    }
    return { venue: "Polymarket", status: ask ? "quoted" : "no_quote", yes_ask: ask, yes_bid: bid, market: p.slug,
      url: `https://polymarket.com/event/${p.event_slug}`, rules: (m.description || "").slice(0, 400) };
  } catch (e) {
    return { venue: "Polymarket", status: "unreachable", market: p.slug };
  }
}

const c = (x) => Math.round(x * 10000) / 100; // dollars -> cents, 2dp

// Taker fees per share, in dollars. World's quote already includes its cost (no separate fee line).
// Kalshi: 0.07 x p x (1-p), rounded up to the cent per order (ignored here, so small orders pay a little more).
// Polymarket: rate x p x (1-p), rate by category (docs.polymarket.com/trading/fees). World's category stands in for Polymarket's.
const POLY_RATE = { crypto: 0.07, sports: 0.05, economics: 0.05, culture: 0.05, finance: 0.04, politics: 0.04, tech: 0.04 };
export const takerFee = (venue, p, category) => (venue === "Kalshi" ? 0.07 : POLY_RATE[category] ?? 0.05) * p * (1 - p);

// World's premium after the other venues' taker fees, across the same 793 outcomes as the baseline.
export const AFTER_FEES = (() => {
  const prem = [];
  for (const m of INDEX.markets) {
    const s = m.snap;
    if (!s || m.venues_disagree) continue;
    const all = [];
    if (s.kalshi_ask) all.push(s.kalshi_ask + takerFee("Kalshi", s.kalshi_ask, m.category));
    if (s.poly_ask) all.push(s.poly_ask + takerFee("Polymarket", s.poly_ask, m.category));
    if (all.length) prem.push((m.world_yes_ask - Math.min(...all)) * 100);
  }
  prem.sort((a, b) => a - b);
  return { n: prem.length, median_premium_cents: Math.round(prem[Math.floor((prem.length - 1) / 2)] * 100) / 100,
    world_cheapest: prem.filter((x) => x <= 0).length, two_cents_or_more: prem.filter((x) => x >= 2).length };
})();

export function findMarket(ticker) {
  return BY_TICKER.get(String(ticker || "").trim().toUpperCase()) || null;
}

export function searchMarkets(q, limit = 8) {
  const terms = String(q || "").toLowerCase().split(/\s+/).filter(Boolean);
  if (!terms.length) return [];
  return INDEX.markets
    .filter((m) => terms.every((t) => `${m.ticker} ${m.event_title} ${m.outcome}`.toLowerCase().includes(t)))
    .slice(0, limit)
    .map((m) => ({ ticker: m.ticker, event_title: m.event_title, outcome: m.outcome }));
}

export async function secondOpinion({ ticker, worldAsk, source }) {
  const m = findMarket(ticker);
  if (!m) return { ok: false, error: "unknown_market", message: `No matched World market for ${ticker}. Use a World market ticker such as WXPRESWIN-28-GNEW.` };
  const w = num(worldAsk) ?? m.world_yes_ask;
  const worldSource = num(worldAsk) ? (source || "caller") : `snapshot ${SNAPSHOT_UTC}`;
  const [k, p] = await Promise.all([kalshiQuote(m.kalshi), polyQuote(m.polymarket)]);
  const quoted = [k, p].filter((v) => v.status === "quoted");
  const best = quoted.sort((a, b) => a.yes_ask - b.yes_ask)[0] || null;
  let verdict, line, limit = null, premium = null, premiumPct = null;
  const both = quoted.length === 2 ? Math.abs(c(quoted[0].yes_ask - quoted[1].yes_ask)) : 0;
  if (!best) {
    verdict = "NO_SECOND_PRICE";
    line = "Nobody else is quoting this outcome right now, so there's nothing to compare. Use World's own spread as your guide.";
  } else if (both > DISAGREE_CENTS) {
    verdict = "CHECK_RULES";
    premium = c(w - best.yes_ask);
    premiumPct = Math.round(((w - best.yes_ask) / best.yes_ask) * 1000) / 10;
    line = `Kalshi and Polymarket are ${Math.round(both * 100) / 100}c apart on this outcome, which usually means their rules differ. Read the rules below before trusting any gap.`;
  } else {
    premium = c(w - best.yes_ask);
    premiumPct = Math.round(((w - best.yes_ask) / best.yes_ask) * 1000) / 10;
    const fairCap = best.yes_ask + BASELINE.median_premium_cents / 100;
    if (premium <= 0) {
      verdict = "BEST_PRICE";
      line = `World matches or beats the other venues on this outcome (${c(w)}c vs ${c(best.yes_ask)}c on ${best.venue}).`;
    } else if (premium <= STRETCH_CENTS && (premium < MIN_STRETCH_CENTS || premium / 100 <= best.yes_ask * STRETCH_SHARE)) {
      verdict = "FAIR_PRICE";
      line = `World's price is ${premium}c above ${best.venue}, within World's usual premium (median ${BASELINE.median_premium_cents}c). A fair price.`;
    } else {
      verdict = "STRETCHED";
      limit = Math.round(fairCap * 1000) / 10;
      line = `World is ${premium}c (${premiumPct}%) above ${best.venue}, well past its usual ${BASELINE.median_premium_cents}c. Worth waiting, or only buying at ${limit}c or less.`;
    }
  }
  // The same comparison after the other venues' taker fees (World's quote is all-in).
  let afterFees = null;
  if (quoted.length) {
    const all = quoted.map((v) => ({ venue: v.venue, all_in: v.yes_ask + takerFee(v.venue, v.yes_ask, m.category) }))
      .sort((a, b) => a.all_in - b.all_in);
    const p = c(w - all[0].all_in);
    afterFees = { best_venue: all[0].venue, best_all_in_cents: c(all[0].all_in), premium_cents: p,
      venues: all.map((a) => ({ venue: a.venue, all_in_cents: c(a.all_in) })) };
    if (verdict !== "CHECK_RULES") line += p <= 0
      ? ` After Kalshi's and Polymarket's taker fees, World is the cheapest (${all[0].venue} costs ${c(all[0].all_in)}c all-in).`
      : ` After their taker fees, World is ${p}c above ${all[0].venue}.`;
  }
  return {
    ok: true,
    checked_at: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
    market: { ticker: m.ticker, event: m.event_title, outcome: m.outcome, category: m.category,
      closes: m.close_time ? new Date(m.close_time * 1000).toISOString().slice(0, 10) : null },
    world: { yes_ask_cents: c(w), source: worldSource },
    venues: [k, p].map(({ rules, ...v }) => ({ ...v, yes_ask_cents: v.yes_ask ? c(v.yes_ask) : null })),
    verdict, line, premium_cents: premium, after_fees: afterFees, premium_pct: premiumPct, buy_at_or_below_cents: limit,
    baseline: { median_premium_cents: BASELINE.median_premium_cents, p90_premium_cents: BASELINE.p90_premium_cents,
      measured_on: `${BASELINE.n} matched World outcomes, ${SNAPSHOT_UTC}` },
    note: "The verdict compares YES asks. after_fees adds Kalshi's and Polymarket's taker fees (World's quote is all-in). A price check, not financial advice.",
    settlement: { world_rules: m.rules, oracle: m.oracle === "chainlink" ? "Chainlink data, written on chain by World" : "World",
      dispute_window_minutes: m.dispute_window_s ? Math.round(m.dispute_window_s / 60) : null,
      kalshi_rules: k.rules || null },
  };
}

export function board(limit = 12) {
  // From the index snapshot: the most stretched World prices when it was built. Live checks may differ.
  const rows = INDEX.markets
    .filter((m) => m.snap && m.snap.spread_cents > 0 && !m.venues_disagree && m.snap.kalshi_ask && m.snap.poly_ask && !m.event.startsWith("WXARREST"))
    .sort((a, b) => b.snap.spread_cents - a.snap.spread_cents)
    .slice(0, limit)
    .map((m) => ({ ticker: m.ticker, event: m.event_title, outcome: m.outcome, world_cents: c(m.world_yes_ask),
      best_other: m.snap.best_other, best_other_cents: c(m.snap.best_other_ask), premium_cents: Math.round(m.snap.spread_cents * 100) / 100 }));
  return { snapshot_utc: SNAPSHOT_UTC, baseline: BASELINE, rows };
}
