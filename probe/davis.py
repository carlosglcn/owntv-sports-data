import json, re, urllib.request
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36", "Accept": "*/*"}
def get(u, h=UA):
    with urllib.request.urlopen(urllib.request.Request(u, headers=h), timeout=40) as r:
        return r.read().decode("utf-8", "replace")
b = get("https://www.daviscup.com/en/draws-results/2026/finals")
parts = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', b, flags=re.S)
txt = "".join(json.loads('"' + p + '"') for p in parts)
for m in sorted(set(re.findall(r'"([a-zA-Z]*(?:[Ii]d|Code|Key|draw[A-Za-z]*))":"?([A-Za-z0-9-]{4,40})"?', txt)))[:150]:
    if not re.fullmatch(r'[A-Za-z0-9]{22}', m[1]): print("kv", m)
i = txt.find("Draws"); print("ctx", txt[max(0,i-500):i+800])
js = get("https://www.daviscup.com/_next/static/chunks/9099-812ee833097a101f.js")
k = js.find("wcotDrawsModeled"); k2 = js.find("g(", k + 200)
for m in re.finditer(r'\bg\(([^)]{1,80})\)', js): print("call", js[max(0, m.start()-400):m.start()+120])
