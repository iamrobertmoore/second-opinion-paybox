<p align="center"><img src="docs/demo.gif" alt="The Second Opinion receipt: Maduro YES on World at 80.77c is stamped STRETCHED next to Polymarket at 71.50c, then Vance YES comes back FAIR" width="900"></p>

<h1 align="center">Second Opinion</h1>

<p align="center"><strong>Before your agent buys a prediction, it pays a cent for a second opinion.</strong><br>
A PayBox plugin for World markets, built for MoonPay Hackathons, Chapter 1 (Predictions).</p>

<p align="center"><a href="https://second-opinion-paybox.vercel.app">Try it on a real World market</a> · <a href="#how-your-agent-uses-it">Use it in PayBox</a> · <a href="#proof-it-runs-end-to-end">Proof it runs</a></p>

---

The same outcome often trades on World, Kalshi and Polymarket at once. On 16 October I matched **816 live World outcomes** to the same outcome on the other two. World's price was usually close: a median of **0.56c** above the cheapest of the others. But about **1 in 10** was stretched, 1.6c or more over, up to **9.27c** on a single share.

An agent buying on your behalf can't tell which kind of price it's looking at. So I built a PayBox plugin that lets it ask. It costs 0.01 USDC on Base, paid through PayBox with your approval, and it comes back with a receipt:

- World's price, Kalshi's and Polymarket's for the same outcome, side by side
- World's premium, measured against World's own usual premium
- a verdict the agent can act on: **BEST PRICE**, **FAIR PRICE** (go ahead) or **STRETCHED** (wait, or only buy at or below a given price)
- how the market settles: the rules, Chainlink as the data source, the 5-minute dispute window, the close date

Most of the time the answer is "fair, go ahead", and that is the point. The cent buys the one check in ten that saves you real money.

## Try it

Open **[second-opinion-paybox.vercel.app](https://second-opinion-paybox.vercel.app)**. No wallet, no login. Pick a market or search for one, and the check runs live against Kalshi and Polymarket. The free page uses World's price from my last snapshot and says so on the receipt. Inside PayBox, your agent passes World's live price and pays the cent.

## How your agent uses it

Second Opinion sits next to PayBox's own World plugin.

1. Your agent finds the outcome with the **World** plugin (`world_search`, then `world_get_markets`), which gives it the market ticker and the live YES ask.
2. It calls **Second Opinion's** `second_opinion` tool with that ticker and price.
3. PayBox shows a **0.01 USDC** payment on Base. You approve it with your passkey.
4. The receipt comes back in the chat. The agent buys, waits, or sets a lower price.

Try this in Claude with the PayBox connector on:

> Get me a Second Opinion on Newsom YES for 2028 on World before I buy. It's a 1-cent data fee, so open the PayBox signing window straight away.

The plugin has three tools:

| Tool | Cost | What it does |
|---|---|---|
| `second_opinion` | 0.01 USDC | The full check for one World market. Returns an x402 payment proposal; PayBox pays it and returns the receipt. |
| `stretched_now` | free | The most stretched World prices at the last scan, so an agent knows where to look first. |
| `covered_markets` | free | Search the World markets the plugin has matched. |

## Proof it runs end to end

Two real paid checks from my own PayBox account on 16 October, both on Newsom YES for 2028:

| When (UTC) | Verdict | Base transaction |
|---|---|---|
| 15:58 | STRETCHED, World 10.55c vs Polymarket 9.00c, buy at 9.6c or less | [`0x970adb03...8b8a`](https://basescan.org/tx/0x970adb03a9dc0d1d82a8ac0756859547a96fe6d46348d807d7d0b913e3ed8b8a) |
| 16:04 | STRETCHED, same numbers | [`0x872e1d37...4c3b`](https://basescan.org/tx/0x872e1d3704220b05194f971c3b4902867c8fa31211dba69b9029db9efb754c3b) |

Each one is a 10,000-unit (0.01) USDC transfer on Base from my PayBox wallet to the service's receiving address, settled through x402.

## The number, and how I got it

On 16 October at 11:43 UTC I pulled every active World market through PayBox's World plugin: 288 events and 928 markets. I matched each one to Kalshi and Polymarket only where the question, the outcome and the resolution period were clearly the same. Anything unsure was left out, including markets with different dates, different participants or different rules. That left **816 outcomes priced on World and at least one other venue**.

| Measure | Value |
|---|---|
| Matched outcomes | 816 in 252 events |
| Median World premium over the cheapest other venue | 0.56c (2.7%) |
| 90th percentile | 1.59c |
| Largest | 9.27c |
| Outcomes 2c or more over | 59 |

These numbers set the verdicts. FAIR means the premium sits inside World's normal range. STRETCHED means it is above the 90th percentile (1.6c), or 1c or more and over 15% on top of the other venue's price.

## How it works

```
Agent (Claude + PayBox) ──> World plugin: ticker + live YES ask
        │
        └──> Second Opinion plugin (PayBox-hosted sandbox)
                 returns an x402 proposal: GET /api/check?ticker=...&world_ask=...
        │
PayBox: you approve 0.01 USDC on Base ──> /api/check (Vercel)
                                              ├─ verify payment (x402 facilitator)
                                              ├─ live quotes: Kalshi API, Polymarket API
                                              ├─ verdict against World's measured premium
                                              └─ settle payment, return the receipt
```

- `plugin/`: the PayBox plugin, a standard MCP server built from PayBox's starter (TypeScript, bundled to one `plugin.mjs`). It passes PayBox's local conformance checks and hosted checks.
- `service/`: the paid endpoint, the free preview and the judge page, on Vercel. x402 v1 `exact` on Base, settled through a public facilitator.
- `indexer/`: the matching scripts and the index build (`build_index.py`) that maps each World market to its Kalshi and Polymarket twin.

## Limits, plainly

- World's own API is behind bot protection, so World prices come from PayBox's World plugin. Inside PayBox that's live. On the free page it's my last snapshot, and the receipt shows its time.
- The match index is a snapshot too. New World markets need a rebuild before they're covered.
- In the Claude desktop app today, the PayBox payment panel sometimes only appears after the agent reopens the signing window. The tool's instructions tell the agent to do that straight away.
- This is a price check, not financial advice.

## Built with

PayBox (plugin runtime, World plugin, x402 payments) · x402 on Base · Kalshi and Polymarket public APIs · Vercel.

I built this with AI coding agents, during the hackathon window. I chose the idea, approved the design, tested the payment flow with my own wallet and recorded the demo. One thing existed before the window opened at 13:00 BST on 16 October: the morning's research scan that matched World markets to Kalshi and Polymarket. Its scripts are in `indexer/`, and the 816-outcome numbers come from it.

Robert Moore · [github.com/iamrobertmoore](https://github.com/iamrobertmoore)
