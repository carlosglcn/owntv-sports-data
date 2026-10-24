#!/usr/bin/env python3
"""One-off probe: saves what asobal.es serves for the pages the reader needs."""
import os, re, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36", "Accept-Language": "es-ES,es;q=0.9"}
OUT = "probe2"
os.makedirs(OUT, exist_ok=True)
URLS = [
    "https://www.asobal.es/liga/calendario/8/",
    "https://www.asobal.es/liga/calendario/1/",
    "https://www.asobal.es/indexproximos/?jor=8&modal=1",
    "https://www.asobal.es/indexproximos/?jor=7&modal=1",
    "https://www.asobal.es/liga/calendario/indexproximos/?jor=8&modal=1",
    "https://www.asobal.es/liga/resultados/8/",
    "https://www.asobal.es/equipos/BAR/",
    "https://www.asobal.es/estadisticas/35405652/",
]
log = []
for u in URLS:
    try:
        req = urllib.request.Request(u, headers=UA)
        with urllib.request.urlopen(req, timeout=40) as r:
            raw = r.read()
            ct = r.headers.get("Content-Type")
    except Exception as e:
        log.append(f"FAIL {u} {e}")
        continue
    log.append(f"OK {u} {ct} {len(raw)}")
    name = re.sub(r"[^A-Za-z0-9]+", "_", u)[:90] + ".html"
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write(raw.decode("latin-1")[:200000])
with open(os.path.join(OUT, "log.txt"), "w") as f:
    f.write("\n".join(log))
