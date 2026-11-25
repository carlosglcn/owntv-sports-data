import json, re, urllib.request
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36", "Accept": "*/*"}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40) as r:
        return r.read().decode("utf-8", "replace")
b = get("https://www.daviscup.com/en/draws-results/2026/finals")
print("page", len(b))
for k in ["Lehecka", "Mensik", "Machac", "Shapovalov", "tieId", "TieId", "rubber", "Rubber", "flag", "nationCode", "NationCode", "eventId"]:
    i = b.find(k); print("--", k, b.count(k), b[max(0, i-300):i+500].replace("\\\"", '"') if i >= 0 else "")
js = get("https://www.daviscup.com/_next/static/chunks/app/%5Blocale%5D/(tennis)/draws-results/%5Bseason%5D/page-cc789cb9ad476b62.js")
print("chunk", len(js))
for m in sorted(set(re.findall(r'["\'`](https?://[^"\'`]+|/api/[^"\'`]+)', js)))[:80]: print("  url", m)
for m in sorted(set(re.findall(r'[a-zA-Z]*[Aa]pi[A-Za-z]*\.[a-z]+\.[a-z]+', js)))[:30]: print("  host", m)
