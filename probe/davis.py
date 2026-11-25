import json, re, urllib.request, collections
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36", "Accept": "*/*"}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40) as r:
        return r.read().decode("utf-8", "replace")
b = get("https://www.daviscup.com/en/draws-results/2026/finals")
parts = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', b, flags=re.S)
txt = "".join(json.loads('"' + p + '"') for p in parts)
print("rsc", len(txt))
keys = collections.Counter(re.findall(r'"([a-zA-Z]{3,30})":', txt))
print(keys.most_common(140))
for k in ['"Canada"', '"score"', '"winner', '"startDate"', '"status"', '"courtName"', '"result']:
    i = txt.find(k); print("\n--", k, txt[max(0, i-1500):i+1500] if i >= 0 else "none")
