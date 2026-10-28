#!/usr/bin/env python3
"""tennis.json: a photo for each player in the ATP and WTA singles rankings (as far as ESPN lists them).

  {"updated", "players": {"<ESPN athlete id>": "<photo url>"}}

ESPN's own headshot when it has one (the feed's, or its standard address when that answers); otherwise the
player's picture on Wikimedia Commons, found through Wikidata (a tennis player with that name). Rebuilt at
most once a day: rankings move weekly and the pictures hardly ever.
"""
import json, sys, time, unicodedata, urllib.parse, urllib.request

UA = {"User-Agent": "OwnTVFanartBot/1.0 (https://github.com/carlosglcn/owntv-sports-data)"}
ESPN = "https://site.api.espn.com/apis/site/v2/sports/tennis/%s/rankings"
HEADSHOT = "https://a.espncdn.com/i/headshots/tennis/players/full/%s.png"
SPARQL = "https://query.wikidata.org/sparql?format=json&query="


def get(url, headers=None, method="GET"):
    h = dict(UA)
    h.update(headers or {})
    req = urllib.request.Request(url, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, r.read()


def fold(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


def has_headshot(pid):
    try:
        st, body = get(HEADSHOT % pid, method="HEAD")
        return st == 200
    except Exception:
        return False


def wikidata(names):
    """name (folded) -> Commons picture, for tennis players called exactly that (label or alias)."""
    out = {}
    for i in range(0, len(names), 80):
        chunk = names[i:i + 80]
        values = " ".join('"%s"@en' % n.replace('"', "") for n in chunk)
        q = ("SELECT ?name ?img WHERE { VALUES ?name { %s } ?p rdfs:label|skos:altLabel ?name; "
             "wdt:P106 wd:Q10833314; wdt:P18 ?img. }" % values)
        try:
            st, body = get(SPARQL + urllib.parse.quote(q), {"Accept": "application/sparql-results+json"})
            for b in json.loads(body)["results"]["bindings"]:
                key = fold(b["name"]["value"])
                img = b["img"]["value"].replace("http://", "https://")
                out.setdefault(key, img + "?width=400")
        except Exception as e:
            print("wikidata chunk failed:", e, file=sys.stderr)
        time.sleep(1)
    return out


def main():
    try:
        old = json.load(open("tennis.json"))
    except Exception:
        old = {}
    if old.get("updated", 0) > time.time() * 1000 - 20 * 3600 * 1000 and "--force" not in sys.argv:
        print("tennis fresh")
        return
    players = {}
    for tour in ("atp", "wta"):
        st, body = get(ESPN % tour)
        for r in json.loads(body)["rankings"][0]["ranks"]:
            a = r.get("athlete") or {}
            if a.get("id"):
                shot = a.get("headshot")
                shot = shot if isinstance(shot, str) else (shot or {}).get("href")
                players[a["id"]] = (a.get("displayName") or "", shot or None)
    photos, missing = {}, []
    for pid, (name, shot) in players.items():
        if shot:
            photos[pid] = shot
        elif has_headshot(pid):
            photos[pid] = HEADSHOT % pid
        else:
            missing.append((pid, name))
    found = wikidata(sorted({n for _, n in missing if n} | {fold(n) for _, n in missing if n}))
    for pid, name in missing:
        img = found.get(fold(name))
        if img:
            photos[pid] = img
    doc = dict(players=photos)
    if {k: v for k, v in old.items() if k != "updated"} == doc:
        print("tennis unchanged")
        return
    doc["updated"] = int(time.time() * 1000)
    json.dump(doc, open("tennis.json", "w"), ensure_ascii=False, separators=(",", ":"))
    print("tennis written:", len(photos), "of", len(players), "players have a photo;",
          sum(1 for p in photos.values() if "espncdn" in p), "from ESPN")


if __name__ == "__main__":
    main()
