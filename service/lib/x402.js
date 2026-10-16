// Minimal x402 v1 "exact" seller on Base USDC, settled through a public facilitator.
// Flow: no X-PAYMENT -> 402 with requirements. With X-PAYMENT -> verify, do the work, settle, respond.
const FACILITATOR = process.env.X402_FACILITATOR || "https://facilitator.payai.network";
const USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";

export const PRICE_ATOMIC = process.env.PRICE_ATOMIC || "10000"; // 0.01 USDC

export function requirements(resource) {
  const payTo = process.env.PAY_TO;
  if (!payTo) throw new Error("PAY_TO is not configured");
  return {
    scheme: "exact",
    network: "base",
    maxAmountRequired: PRICE_ATOMIC,
    resource,
    description: "Second Opinion: one World price checked against Kalshi and Polymarket",
    mimeType: "application/json",
    payTo,
    maxTimeoutSeconds: 120,
    asset: USDC_BASE,
    extra: { name: "USD Coin", version: "2" },
  };
}

async function facilitator(path, body) {
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), 15000);
  try {
    const r = await fetch(`${FACILITATOR}/${path}`, {
      method: "POST", signal: ctl.signal,
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
    const text = await r.text();
    let json; try { json = JSON.parse(text); } catch { json = { raw: text.slice(0, 300) }; }
    return { status: r.status, json };
  } finally {
    clearTimeout(t);
  }
}

export function decodePayment(header) {
  try { return JSON.parse(Buffer.from(header, "base64").toString("utf8")); } catch { return null; }
}

export async function verify(payload, req) {
  return facilitator("verify", { x402Version: 1, paymentPayload: payload, paymentRequirements: req });
}

export async function settle(payload, req) {
  return facilitator("settle", { x402Version: 1, paymentPayload: payload, paymentRequirements: req });
}

export function paymentRequired(res, req, error = "X-PAYMENT header is required") {
  res.statusCode = 402;
  res.setHeader("content-type", "application/json");
  res.end(JSON.stringify({ x402Version: 1, error, accepts: [req] }));
}
