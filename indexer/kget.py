import json, time, urllib.request, urllib.parse, sys, os

BASE = "https://api.elections.kalshi.com/trade-api/v2"

def get(url, tries=8):
    for t in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "research/1.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(1.5 * (t + 1))
                continue
            if e.code == 404:
                return None
            time.sleep(1)
        except Exception:
            time.sleep(1.5)
    raise RuntimeError("failed " + url)

def paged_events(params):
    out = []
    cursor = ""
    while True:
        p = dict(params)
        p["limit"] = 200
        if cursor:
            p["cursor"] = cursor
        d = get(BASE + "/events?" + urllib.parse.urlencode(p))
        if not d:
            break
        out += d.get("events") or []
        cursor = d.get("cursor") or ""
        time.sleep(0.25)
        if not cursor or not d.get("events"):
            break
    return out

if __name__ == "__main__":
    mode = sys.argv[1]
    outp = sys.argv[2]
    if mode == "index":
        ev = paged_events({"status": "open"})
    elif mode == "series":
        ev = []
        for s in sys.argv[3].split(","):
            e = paged_events({"status": "open", "series_ticker": s, "with_nested_markets": "true"})
            print(s, len(e), file=sys.stderr)
            ev += e
    json.dump(ev, open(outp, "w"))
    print(len(ev))
