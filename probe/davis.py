import json, re, urllib.request
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36", "Accept": "application/json", "Origin": "https://www.daviscup.com", "Referer": "https://www.daviscup.com/"}
B = "https://api.itf-production.sports-data.stadion.io"
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40) as r:
        return r.read().decode("utf-8", "replace")
def shape(x, d=0):
    if isinstance(x, dict): return {k: shape(v, d + 1) for k, v in list(x.items())[:45]} if d < 7 else "{..}"
    if isinstance(x, list): return [shape(x[0], d + 1), "len=%d" % len(x)] if x else []
    return x if not isinstance(x, str) or len(x) < 80 else x[:80]
for e in ["2026", "2026/finals", "finals/2026", "2026-finals", "2025"]:
    u = "%s/custom/wcotDrawsModeled/dc/%s" % (B, e)
    try:
        t = get(u); print("==", u, len(t)); d = json.loads(t)
        print(json.dumps(shape(d), ensure_ascii=False)[:5000])
    except Exception as ex:
        print("==", u, "ERR", ex)
