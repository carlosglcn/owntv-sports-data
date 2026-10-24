#!/usr/bin/env python3
"""One-off probe: saves what asobal.es serves, to learn where its calendar, results and table live."""
import os, re, urllib.request, urllib.parse

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36", "Accept-Language": "es-ES,es;q=0.9"}
OUT = "probe"
os.makedirs(OUT, exist_ok=True)


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.status, r.geturl(), r.read().decode("utf-8", "replace")


def save(name, text):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write(text)


def slug(u):
    return re.sub(r"[^A-Za-z0-9]+", "_", u)[:80]


log = []
seen = set()
queue = ["https://www.asobal.es/", "https://asobal.es/", "https://www.asobal.es/calendario", "https://www.asobal.es/clasificacion"]
KEY = re.compile(r"calend|result|clasif|compet|partid|directo|live|jornada|liga|standings|api|json", re.I)
n = 0
while queue and n < 30:
    u = queue.pop(0)
    if u in seen:
        continue
    seen.add(u)
    try:
        st, final, body = get(u)
    except Exception as e:
        log.append(f"FAIL {u} {e}")
        continue
    n += 1
    log.append(f"OK {st} {u} -> {final} ({len(body)} bytes)")
    save(slug(u) + ".html", body[:250000])
    base = final
    links = set(re.findall(r'(?:href|src|data-url|action)=["\']([^"\']+)["\']', body))
    links |= set(re.findall(r'https?://[^\s"\'<>\\]+', body))
    save(slug(u) + ".links.txt", "\n".join(sorted(urllib.parse.urljoin(base, l) for l in links)))
    if n <= 6:
        for l in sorted(links):
            full = urllib.parse.urljoin(base, l)
            host = urllib.parse.urlparse(full).netloc
            if "asobal" in host and KEY.search(full) and not re.search(r"\.(css|png|jpe?g|svg|gif|woff2?|ico|webp)(\?|$)", full):
                queue.append(full.split("#")[0])
save("log.txt", "\n".join(log))
