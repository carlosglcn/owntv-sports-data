import os, urllib.request
os.makedirs("probe3", exist_ok=True)
for n in (3, 9, 30):
    req = urllib.request.Request("https://www.asobal.es/liga/calendario/%d/" % n, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=40) as r:
        open("probe3/r%d.html" % n, "w", encoding="utf-8").write(r.read().decode("latin-1"))
