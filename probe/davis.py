import json, re, urllib.request
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36", "Accept": "*/*"}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40) as r:
        return r.read().decode("utf-8", "replace")
b = get("https://www.daviscup.com/en/draws-results/2026/finals")
srcs = sorted(set(re.findall(r'(/_next/static/chunks/[^"\']+\.js)', b)))
print("chunks", len(srcs))
seen = set()
for s in srcs:
    try: js = get("https://www.daviscup.com" + s)
    except Exception as ex: print("ERR", s, ex); continue
    for m in re.findall(r'["\'`]((?:https?:)?//[a-zA-Z0-9.-]*(?:stadion|itf|api|sports-data|feed)[a-zA-Z0-9./_-]*[^"\'`]{0,120})', js):
        if m not in seen and "Flag" not in m: seen.add(m); print("  ", s.split("/")[-1][:30], m[:200])
    for m in re.findall(r'["\'`](/api/[^"\'`]{0,150})', js):
        if m not in seen: seen.add(m); print("  api", s.split("/")[-1][:30], m)
    for kw in ["tieResult", "tiesBy", "getTies", "ties/", "/ties", "rubbers", "matchCentre", "draws/"]:
        i = js.find(kw)
        if i >= 0 and (s, kw) not in seen: seen.add((s, kw)); print("  kw", kw, s.split("/")[-1][:30], js[max(0, i-250):i+250].replace("\n", " "))
