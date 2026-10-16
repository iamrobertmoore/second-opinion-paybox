// Free check for the judge page: same logic, World price from the last snapshot. Cached briefly at the edge.
import { secondOpinion, searchMarkets, board } from "../lib/check.js";

export default async function handler(req, res) {
  const url = new URL(req.url, `https://${req.headers.host}`);
  res.setHeader("content-type", "application/json");
  res.setHeader("access-control-allow-origin", "*");
  const q = url.searchParams.get("q");
  if (q !== null) {
    res.setHeader("cache-control", "public, s-maxage=300");
    return res.end(JSON.stringify({ results: searchMarkets(q, 10) }));
  }
  if (url.searchParams.get("board") !== null) {
    res.setHeader("cache-control", "public, s-maxage=300");
    return res.end(JSON.stringify(board(14)));
  }
  const ticker = url.searchParams.get("ticker");
  const r = await secondOpinion({ ticker });
  res.statusCode = r.ok ? 200 : 404;
  res.setHeader("cache-control", "public, s-maxage=15, stale-while-revalidate=30");
  res.end(JSON.stringify({ ...r, payment: { amount_usdc: "0", note: "Free preview. Inside PayBox the same check costs 0.01 USDC on Base." } }));
}
