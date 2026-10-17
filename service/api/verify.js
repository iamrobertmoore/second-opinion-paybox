// Free: check a Second Opinion payment straight from Base. GET /api/verify?tx=0x...
// Reads the transaction receipt from a public Base RPC and decodes the USDC Transfer to the service.
const RPC = process.env.BASE_RPC || "https://mainnet.base.org";
const USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913";
const TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef";

async function rpc(method, params) {
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), 8000);
  try {
    const r = await fetch(RPC, { method: "POST", signal: ctl.signal, headers: { "content-type": "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }) });
    const j = await r.json();
    if (j.error) throw new Error(j.error.message || "rpc error");
    return j.result;
  } finally {
    clearTimeout(t);
  }
}

const addr = (topic) => "0x" + topic.slice(-40);

export default async function handler(req, res) {
  const url = new URL(req.url, `https://${req.headers.host}`);
  const tx = String(url.searchParams.get("tx") || "").trim().toLowerCase();
  res.setHeader("content-type", "application/json");
  res.setHeader("access-control-allow-origin", "*");
  if (!/^0x[0-9a-f]{64}$/.test(tx)) {
    res.statusCode = 400;
    return res.end(JSON.stringify({ ok: false, error: "Pass ?tx= with a Base transaction hash (0x + 64 hex characters)." }));
  }
  try {
    const rc = await rpc("eth_getTransactionReceipt", [tx]);
    if (!rc) { res.statusCode = 404; return res.end(JSON.stringify({ ok: false, error: "Base has no receipt for that transaction yet." })); }
    const block = await rpc("eth_getBlockByNumber", [rc.blockNumber, false]);
    const payTo = String(process.env.PAY_TO || "").toLowerCase();
    const transfers = rc.logs
      .filter((l) => l.address.toLowerCase() === USDC && l.topics[0] === TRANSFER)
      .map((l) => ({ from: addr(l.topics[1]), to: addr(l.topics[2]), usdc: Number(BigInt(l.data)) / 1e6 }));
    const toService = transfers.filter((t) => t.to === payTo);
    const paid = rc.status === "0x1" && toService.some((t) => t.usdc >= 0.01);
    res.setHeader("cache-control", "public, s-maxage=3600");
    res.end(JSON.stringify({
      ok: true,
      tx,
      succeeded: rc.status === "0x1",
      block: parseInt(rc.blockNumber, 16),
      time_utc: new Date(parseInt(block.timestamp, 16) * 1000).toISOString().replace(/\.\d{3}Z$/, "Z"),
      submitted_by: rc.from,
      service_address: payTo,
      usdc_transfers: transfers,
      verdict: paid ? "PAID: USDC reached the Second Opinion service address on Base." : "NOT A SECOND OPINION PAYMENT: no USDC transfer to the service address in this transaction.",
      note: "Read live from a public Base RPC. The x402 facilitator submits the transaction, so submitted_by is the facilitator; the USDC transfer shows who paid.",
    }, null, 2));
  } catch (e) {
    res.statusCode = 502;
    res.end(JSON.stringify({ ok: false, error: `Could not read Base right now: ${e.message}` }));
  }
}
