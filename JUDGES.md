# For judges

Three ways to check Second Opinion, from quickest to most thorough.

## 1. See it in two minutes, no wallet

1. Open [second-opinion-paybox.vercel.app](https://second-opinion-paybox.vercel.app) and press **Check** on any chip. The same check runs live against Kalshi and Polymarket (World's price comes from the 16 October snapshot on this free page).
2. Scroll to **Proof it runs**. Each paid run has a **Check on Base** link that reads the payment straight from a public Base RPC.
3. Watch the demo video on X: two real paid runs in Claude with PayBox, one STRETCHED and one FAIR PRICE.

## 2. Check it yourself from a terminal

The paid endpoint answers with a real x402 payment request for 0.01 USDC on Base:

```
curl -s "https://second-opinion-paybox.vercel.app/api/check?ticker=WXPRESWIN-28-GNEW&world_ask=0.1055"
```

It refuses a market it doesn't cover before asking for any money (HTTP 404):

```
curl -s -i "https://second-opinion-paybox.vercel.app/api/check?ticker=WXNOTAMARKET-1"
```

When Kalshi and Polymarket disagree, it says so instead of calling a price fair or stretched:

```
curl -s "https://second-opinion-paybox.vercel.app/api/preview?ticker=WXVENLEADER-26YE-MADURO"
# verdict: CHECK_RULES ("Kalshi and Polymarket are 6.5c apart ... their rules differ")
```

Any of the four payments, decoded from Base:

```
curl -s "https://second-opinion-paybox.vercel.app/api/verify?tx=0xfe21763115c16c17f3c276e120affb8d9dbb875903b86f217e79d03479023300"
```

## 3. Run it in PayBox

Once PayBox approves the plugin, enable **Second Opinion** at [app.paybox.sh/plugins](https://app.paybox.sh/plugins) with the World plugin, then ask your agent:

> Get me a Second Opinion on Karen Bass YES for LA mayor on World before I buy. It's a 1-cent data fee, so open the PayBox signing window straight away.

## What each claim rests on

| Claim | Evidence | How to check |
|---|---|---|
| The plugin is submitted and passes PayBox's checks (3 tools) | Developer portal screenshot, 17 Oct | [docs/portal-submitted.png](docs/portal-submitted.png) |
| Four checks were paid through PayBox, 0.01 USDC each, on Base | Base transactions, 16 and 17 Oct | `/api/verify?tx=...`, or Basescan |
| In the last two runs the agent used World's live price from PayBox's World plugin | The receipts say `source: your agent (PayBox World plugin)`; recorded in the video | Video; receipt JSON in each run |
| The endpoint asks for payment and refuses unknown markets first | Live HTTP responses | The curl commands above |
| Median World premium 0.56c, 49 of 793 at 2c or more | Measured on the 16 Oct 11:43 UTC snapshot | `indexer/`, `service/data/index.json` |
| After the other venues' taker fees, World is cheapest on 408 of 793 | Computed from the same snapshot with the venues' published fee formulas | `service/lib/check.js` (`AFTER_FEES`) |

Not claimed: that the plugin is listed publicly yet (it is pending PayBox's review), that World prices on the free page are live (they are from the snapshot, and each receipt says so), or that a check is financial advice.
