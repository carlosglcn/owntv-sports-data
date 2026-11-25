import json, urllib.request
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40) as r:
        return json.loads(r.read().decode("utf-8", "replace"))
def shape(x, d=0):
    if isinstance(x, dict): return {k: shape(v, d + 1) for k, v in list(x.items())[:40]} if d < 6 else "{..}"
    if isinstance(x, list): return [shape(x[0], d + 1), "len=%d" % len(x)] if x else []
    return x if not isinstance(x, str) or len(x) < 90 else x[:90]
for lg in ["atp", "wta"]:
    for dt in ["20261124", "20261125", "20261124-20261129"]:
        u = "https://site.api.espn.com/apis/site/v2/sports/tennis/%s/scoreboard?dates=%s" % (lg, dt)
        try:
            d = get(u)
            print("===", lg, dt, [(e.get("id"), e.get("name")) for e in d.get("events", [])])
            for e in d.get("events", []):
                if "davis" in (e.get("name") or "").lower():
                    print(json.dumps(shape(e), ensure_ascii=False)[:6000])
        except Exception as ex:
            print("===", lg, dt, "ERR", ex)
for u in ["https://site.api.espn.com/apis/site/v2/sports/tennis/davis-cup/scoreboard",
          "https://site.api.espn.com/apis/site/v2/sports/tennis/scoreboard?dates=20261125",
          "https://sports.core.api.espn.com/v2/sports/tennis/leagues?limit=50"]:
    try:
        d = get(u); print("===", u); print(json.dumps(shape(d), ensure_ascii=False)[:2500])
    except Exception as ex:
        print("===", u, "ERR", ex)
