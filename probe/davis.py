import re, urllib.request
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36", "Accept": "*/*"}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40) as r:
        return r.read().decode("utf-8", "replace")
b = get("https://www.daviscup.com/en/draws-results/2026/finals")
srcs = sorted(set(re.findall(r'(/_next/static/chunks/[^"\']+\.js)', b)))
seen = set()
for s in srcs:
    js = get("https://www.daviscup.com" + s)
    for m in re.findall(r'`\$\{[^}]{1,30}\}/[^`]{2,200}`', js):
        if m not in seen: seen.add(m); print("tpl", s.split("/")[-1][:24], m)
    for m in re.findall(r'"/(?:[a-z0-9-]+/){1,6}[a-z0-9-]*"', js):
        if m not in seen and any(k in m for k in ("tie", "draw", "event", "match", "result", "live", "score", "nation", "player")): seen.add(m); print("path", s.split("/")[-1][:24], m)
