import json, time, urllib.request, urllib.parse, sys

G = "https://gamma-api.polymarket.com"

def get(url, tries=6):
    for t in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "research/1.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2 * (t + 1)); continue
            if e.code in (404, 422):
                return None
            time.sleep(1)
        except Exception:
            time.sleep(1.5)
    return None

if __name__ == "__main__":
    mode, outp = sys.argv[1], sys.argv[2]
    res = {}
    if mode == "tags":
        for tag in sys.argv[3].split(","):
            off = 0
            while True:
                d = get(G + "/events?" + urllib.parse.urlencode({"tag_slug": tag, "closed": "false", "limit": 100, "offset": off}))
                if not d:
                    break
                for e in d:
                    res[e["id"]] = e
                if len(d) < 100:
                    break
                off += 100
                time.sleep(0.2)
            print(tag, len(res), file=sys.stderr)
        json.dump(list(res.values()), open(outp, "w"))
    elif mode == "search":
        qs = json.load(open(sys.argv[3]))
        out = {}
        for q in qs:
            d = get(G + "/public-search?" + urllib.parse.urlencode({"q": q, "limit_per_type": 10, "events_status": "active"}))
            out[q] = (d or {}).get("events") or []
            time.sleep(0.3)
        json.dump(out, open(outp, "w"))
    elif mode == "slugs":
        slugs = json.load(open(sys.argv[3]))
        out = {}
        for s in slugs:
            d = get(G + "/events?" + urllib.parse.urlencode({"slug": s}))
            if d:
                out[s] = d[0]
            time.sleep(0.15)
        json.dump(out, open(outp, "w"))
    print(len(res) if res else "done")
