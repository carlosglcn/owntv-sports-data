import json, sys, urllib.request, urllib.parse, re
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"}
B = "https://www.dakar.live.worldrallyraidchampionship.com/api/"
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40) as r:
        return r.read().decode("utf-8", "replace")
def shape(x, d=0):
    if isinstance(x, dict): return {k: shape(v, d + 1) for k, v in list(x.items())[:45]} if d < 5 else "{..}"
    if isinstance(x, list): return [shape(x[0], d + 1), "len=%d" % len(x)] if x else []
    return x if not isinstance(x, str) or len(x) < 70 else x[:70]
for e in ["category-2026", "lastScore-2026-A-10", "generalRank-2026-A", "allClazz-2026-A", "withdrawal-2026-A", "lastScore-2026-M-13", "generalRank-2026-M"]:
    try:
        body = get(B + e)
        d = json.loads(body) if body.strip() else None
        print("===", e, len(body), "B", type(d).__name__, len(d) if d else 0)
        if e.startswith("category"):
            for c in d: print("   cat", c.get("label"), c.get("reference"), [l["text"] for l in c.get("categoryLangs", []) if l.get("locale") == "es"], c.get("lastStage"), c.get("liveDisplay"))
        else:
            print(json.dumps(shape(d[0] if isinstance(d, list) and d else d), ensure_ascii=False)[:3500])
    except Exception as ex:
        print("===", e, "ERR", ex)
print("=== WIKIPEDIA WRC 2026")
try:
    raw = get("https://en.wikipedia.org/w/index.php?title=2026_World_Rally_Championship&action=raw")
    print(len(raw))
    for h in re.finditer(r"^==+[^=]+==+\s*$", raw, flags=re.M): print("  ", h.group(0).strip())
    i = raw.find("Calendar"); print(raw[i:i+3500])
    j = raw.find("Drivers' championship") ; j = raw.find("{|", j); print(raw[j:j+2500])
    k = raw.find("Season summary"); print(raw[k:k+3000])
except Exception as ex:
    print("wiki ERR", ex)
