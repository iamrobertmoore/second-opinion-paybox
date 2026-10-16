import { McpServer } from "@modelcontextprotocol/server";
import { serveStdio } from "@modelcontextprotocol/server/stdio";
import * as z from "zod/v4";
import { proposeX402, x402OutputSchema } from "./paybox.js";

const PROTOCOL_VERSION = "2026-07-28";
const SERVICE = "https://second-opinion-paybox.vercel.app";
const PRICE_ATOMIC = "10000"; // 0.01 USDC on Base

const worldTicker = z
  .string()
  .regex(/^WX[A-Z0-9-]{3,120}$/, "Use a World market ticker, for example WXPRESWIN-28-GNEW")
  .describe("World market ticker (the YES/NO market, not the event), as returned by the World plugin.");

async function getJson(path: string): Promise<unknown> {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), 4000);
  try {
    const r = await fetch(`${SERVICE}${path}`, { signal: ctl.signal, headers: { accept: "application/json" } });
    if (!r.ok) throw new Error(`Second Opinion service returned HTTP ${r.status}`);
    return await r.json();
  } finally {
    clearTimeout(timer);
  }
}

const boardRow = z.object({
  ticker: z.string(),
  event: z.string(),
  outcome: z.string(),
  world_cents: z.number(),
  best_other: z.string(),
  best_other_cents: z.number(),
  premium_cents: z.number(),
});

function createServer() {
  const server = new McpServer(
    { name: "second-opinion", version: "1.2.0" },
    { supportedProtocolVersions: [PROTOCOL_VERSION] },
  );

  server.registerTool(
    "second_opinion",
    {
      title: "Second Opinion: 1-cent price check (a data fee, not a trade)",
      description:
        "A 1-cent data fee, not a trade: nothing is bought or sold on World. " +
        "Before buying a World prediction-market outcome, pay 0.01 USDC on Base for a second opinion on its price. " +
        "STEP 1: get the live YES ask from the World plugin first (world_search to find the market, then world_orderbook or world_get_markets for that exact ticker). " +
        "STEP 2: call this tool with the ticker and that live ask as a decimal (0.1055 for 10.55c). " +
        "STEP 3: this returns an x402 payment proposal for the 0.01 USDC fee and PayBox creates a request. Immediately call reopen_signing_window with that request_id " +
        "so the PayBox approval panel is shown to the user, without waiting to be asked; the request expires in about four minutes. Then poll get_request until success. " +
        "The paid response is the receipt: the same outcome's live YES ask on Kalshi and Polymarket, World's premium against World's usual premium " +
        "(median 0.56c across 793 matched outcomes), and a verdict: BEST_PRICE, FAIR_PRICE, STRETCHED (with a limit price) or CHECK_RULES (the other venues disagree, so the rules may differ), plus how the market settles.",
      inputSchema: z
        .object({
          world_ticker: worldTicker,
          world_yes_ask: z
            .number()
            .gt(0)
            .lt(1)
            .describe("World's live YES ask from the World plugin, as a decimal between 0 and 1 (0.1055 for 10.55c)."),
        })
        .strict(),
      outputSchema: x402OutputSchema,
      annotations: { readOnlyHint: false, destructiveHint: false, idempotentHint: false, openWorldHint: true },
    },
    async ({ world_ticker, world_yes_ask }) => {
      const url = new URL(`${SERVICE}/api/check`);
      url.searchParams.set("ticker", world_ticker);
      url.searchParams.set("world_ask", String(world_yes_ask));
      const proposal = proposeX402({ chain: "eip155:8453", url: url.toString(), maxAmount: PRICE_ATOMIC, method: "GET" });
      return {
        ...proposal,
        content: [
          {
            type: "text" as const,
            text: `Data fee only, not a trade: 0.01 USDC on Base for a Second Opinion price check on ${world_ticker} at World's ask of ${Math.round(world_yes_ask * 10000) / 100}c. Nothing is bought on World. Next: call reopen_signing_window with this request's id now so the user sees the PayBox approval panel (it expires in about four minutes), then poll get_request; the receipt arrives as the paid response.`,
          },
        ],
      };
    },
  );

  server.registerTool(
    "stretched_now",
    {
      title: "Most stretched World prices",
      description:
        "Free. Lists the World outcomes whose price sat furthest above Kalshi and Polymarket at the last Second Opinion scan, " +
        "with World's usual premium for context. Use it to pick markets worth a paid second_opinion check. Prices move: confirm with second_opinion before buying.",
      inputSchema: z.object({ limit: z.number().int().min(1).max(14).optional() }).strict(),
      outputSchema: z
        .object({
          snapshot_utc: z.string(),
          usual_premium_cents: z.number(),
          matched_outcomes: z.number(),
          rows: z.array(boardRow),
        })
        .strict(),
      annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: true },
    },
    async ({ limit }) => {
      const data = (await getJson("/api/preview?board")) as {
        snapshot_utc: string;
        baseline: { median_premium_cents: number; n: number };
        rows: z.infer<typeof boardRow>[];
      };
      const rows = data.rows.slice(0, limit ?? 8).map((r) => boardRow.parse(r));
      const out = {
        snapshot_utc: data.snapshot_utc,
        usual_premium_cents: data.baseline.median_premium_cents,
        matched_outcomes: data.baseline.n,
        rows,
      };
      const text = rows
        .map((r) => `${r.event} / ${r.outcome} (${r.ticker}): World ${r.world_cents}c vs ${r.best_other} ${r.best_other_cents}c, +${r.premium_cents}c`)
        .join("\n");
      return { content: [{ type: "text" as const, text: `Usual World premium: ${out.usual_premium_cents}c. Most stretched at ${out.snapshot_utc}:\n${text}` }], structuredContent: out };
    },
  );

  server.registerTool(
    "covered_markets",
    {
      title: "Find World markets Second Opinion covers",
      description: "Free. Search the World markets Second Opinion has matched to Kalshi or Polymarket, by words in the event or outcome (for example 'newsom', 'nhl panthers').",
      inputSchema: z.object({ query: z.string().min(2).max(80) }).strict(),
      outputSchema: z
        .object({ results: z.array(z.object({ ticker: z.string(), event_title: z.string(), outcome: z.string() }).strict()) })
        .strict(),
      annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: true },
    },
    async ({ query }) => {
      const data = (await getJson(`/api/preview?q=${encodeURIComponent(query)}`)) as {
        results: { ticker: string; event_title: string; outcome: string }[];
      };
      const results = data.results.map((r) => ({ ticker: r.ticker, event_title: r.event_title, outcome: r.outcome }));
      const text = results.length
        ? results.map((r) => `${r.ticker}: ${r.event_title} / ${r.outcome}`).join("\n")
        : "No covered World market matches that search.";
      return { content: [{ type: "text" as const, text }], structuredContent: { results } };
    },
  );

  return server;
}

serveStdio(createServer, { legacy: "reject" });
