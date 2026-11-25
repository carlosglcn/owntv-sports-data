import json, re, urllib.request
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36", "Accept": "*/*", "Origin": "https://www.daviscup.com", "Referer": "https://www.daviscup.com/"}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40) as r:
        return r.read().decode("utf-8", "replace")
b = get("https://www.daviscup.com/en/draws-results/2026/finals")
srcs = sorted(set(re.findall(r'(/_next/static/chunks/[^"\']+\.js)', b)))
for s in srcs:
    js = get("https://www.daviscup.com" + s)
    i = js.find("cQ:function(){return i}")
    if i >= 0:
        j = js.find('let i="', i)
        print("consts", js[j:j+900])
    k = js.find("wcotDrawsModeled")
    if k >= 0:
        print("caller", s, js[max(0, k-1500):k+400])
parts = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', b, flags=re.S)
txt = "".join(json.loads('"' + p + '"') for p in parts)
for k in ["eventId", "EventId", "tournamentId", "TournamentId", "drawsId", "wcot", "\"id\":\"8"]:
    for m in list(re.finditer(re.escape(k), txt))[:3]:
        print("rsc", k, txt[max(0, m.start()-200):m.start()+250].replace("\n", " "))
