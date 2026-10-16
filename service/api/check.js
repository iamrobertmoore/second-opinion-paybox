// Paid endpoint: GET /api/check?ticker=WX...&world_ask=0.1055  (0.01 USDC on Base via x402)
import { secondOpinion, findMarket } from "../lib/check.js";
import { requirements, decodePayment, verify, settle, paymentRequired } from "../lib/x402.js";

export default async function handler(req, res) {
  res.setHeader("access-control-allow-origin", "*");
  res.setHeader("access-control-expose-headers", "X-PAYMENT-RESPONSE");
  res.setHeader("cache-control", "no-store");
  if (req.method === "OPTIONS") { res.setHeader("access-control-allow-headers", "X-PAYMENT, content-type"); res.statusCode = 204; return res.end(); }

  const url = new URL(req.url, `https://${req.headers.host}`);
  const ticker = url.searchParams.get("ticker");
  const worldAsk = url.searchParams.get("world_ask");
  const resource = `https://${req.headers.host}/api/check`;
  const reqs = requirements(resource);

  // Refuse unknown markets before any payment is taken.
  if (!findMarket(ticker)) {
    res.statusCode = 404;
    res.setHeader("content-type", "application/json");
    return res.end(JSON.stringify({ ok: false, error: "unknown_market", message: `No matched World market for ${ticker}` }));
  }

  const header = req.headers["x-payment"];
  if (!header) return paymentRequired(res, reqs);
  const payload = decodePayment(header);
  if (!payload) return paymentRequired(res, reqs, "X-PAYMENT is not valid base64 JSON");

  const v = await verify(payload, reqs);
  if (v.status !== 200 || !v.json.isValid) return paymentRequired(res, reqs, `payment not valid: ${v.json.invalidReason || v.status}`);

  const result = await secondOpinion({ ticker, worldAsk, source: "your agent (PayBox World plugin)" });

  const s = await settle(payload, reqs);
  if (s.status !== 200 || !s.json.success) return paymentRequired(res, reqs, `settlement failed: ${s.json.errorReason || s.status}`);

  const receipt = { success: true, transaction: s.json.transaction, network: s.json.network || "base", payer: s.json.payer || v.json.payer };
  res.setHeader("X-PAYMENT-RESPONSE", Buffer.from(JSON.stringify(receipt)).toString("base64"));
  res.statusCode = 200;
  res.setHeader("content-type", "application/json");
  res.end(JSON.stringify({ ...result, payment: { amount_usdc: "0.01", network: "base", transaction: receipt.transaction, payer: receipt.payer } }));
}
