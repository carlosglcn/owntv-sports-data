#!/usr/bin/env python3
"""tennis.json: a photo for each player in the ATP and WTA singles rankings (as far as ESPN lists them).

  {"updated", "players": {"<ESPN athlete id>": "<photo url>"},
   "tournaments": [{"names": ["roland garros", "french open"], "logo": "<url>"}]}

"tournaments" is the logo of each big tournament — the feed has only the tour's (ATP, WTA): the picture that leads
its article on the English Wikipedia, asked of Wikipedia's own API. "names" are what the tournament's name in the
feed may contain, lower case and without accents; the app shows the logo of the first entry one of whose names
it finds.

ESPN's own headshot when it has one (the feed's, or its standard address when that answers); otherwise the
player's picture on Wikimedia Commons, found through Wikidata (a tennis player with that name). Rebuilt at
most once a day: rankings move weekly and the pictures hardly ever.
"""
import json, sys, time, unicodedata, urllib.parse, urllib.request

UA = {"User-Agent": "OwnTVFanartBot/1.0 (https://github.com/carlosglcn/owntv-sports-data)"}
ESPN = "https://site.api.espn.com/apis/site/v2/sports/tennis/%s/rankings"
HEADSHOT = "https://a.espncdn.com/i/headshots/tennis/players/full/%s.png"
SPARQL = "https://query.wikidata.org/sparql?format=json&query="
WIKI = ("https://en.wikipedia.org/w/api.php?action=query&format=json&redirects=1&prop=pageimages"
        "&piprop=thumbnail&pithumbsize=320&pilicense=any&titles=")

# What the feed's tournament name may contain -> its article. Finals and "Paris Masters" before the Slams and the
# cities, so "ATP Finals" is not taken for anything else and the Paris indoor event is not Roland Garros.
TOURNAMENTS = [
    (["next gen"], "Next Gen ATP Finals"),
    (["atp finals"], "ATP Finals"),
    (["wta finals"], "WTA Finals"),
    (["davis cup"], "Davis Cup"),
    (["billie jean king"], "Billie Jean King Cup"),
    (["united cup"], "United Cup"),
    (["laver cup"], "Laver Cup"),
    (["paris masters", "rolex paris"], "Paris Masters"),
    (["australian open"], "Australian Open"),
    (["roland garros", "french open"], "French Open"),
    (["wimbledon"], "Wimbledon Championships"),
    (["us open"], "US Open (tennis)"),
    (["indian wells", "bnp paribas open"], "Indian Wells Open"),
    (["miami"], "Miami Open (tennis)"),
    (["monte-carlo", "monte carlo"], "Monte-Carlo Masters"),
    (["madrid"], "Madrid Open (tennis)"),
    (["internazionali", "italian open", "rome"], "Italian Open (tennis)"),
    (["national bank", "canadian open", "montreal", "toronto"], "Canadian Open (tennis)"),
    (["cincinnati", "western & southern"], "Cincinnati Open"),
    (["shanghai"], "Shanghai Masters (tennis)"),
    (["china open", "beijing"], "China Open (tennis)"),
    (["wuhan"], "Wuhan Open"),
    (["dubai"], "Dubai Tennis Championships"),
    (["barcelona", "godo"], "Barcelona Open (tennis)"),
    (["queen"], "Queen's Club Championships"),
    (["halle"], "Halle Open"),
]


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


def is_logo(url):
    """An article may be led by a photograph of the court instead: only a drawn mark is a logo."""
    name = urllib.parse.unquote(url.split("?")[0].rsplit("/", 1)[-1]).lower()
    return "logo" in name or ".svg" in name or name.startswith("bnpparibasopen")


def tournaments(old):
    """The big tournaments' logos. One that Wikipedia does not answer for keeps the logo it had."""
    kept = {tuple(t.get("names", [])): t.get("logo") for t in old or []}
    out = []
    for i in range(0, len(TOURNAMENTS), 20):
        chunk = TOURNAMENTS[i:i + 20]
        found = {}
        try:
            st, body = get(WIKI + urllib.parse.quote("|".join(title for _, title in chunk)))
            q = json.loads(body).get("query", {})
            # A title may be normalised or redirected: follow it to the page that answered.
            moved = {}
            for step in q.get("normalized", []) + q.get("redirects", []):
                moved[step["from"]] = step["to"]
            pages = {p.get("title"): (p.get("thumbnail") or {}).get("source") for p in q.get("pages", {}).values()}
            for _, title in chunk:
                at = title
                for _ in range(3):
                    at = moved.get(at, at)
                found[title] = pages.get(at)
        except Exception as e:
            print("wikipedia chunk failed:", e, file=sys.stderr)
        for names, title in chunk:
            logo = found.get(title) or kept.get(tuple(names))
            if logo and is_logo(logo):
                out.append(dict(names=names, logo=logo))
        time.sleep(1)
    return out


def main():
    try:
        old = json.load(open("tennis.json"))
    except Exception:
        old = {}
    if (old.get("updated", 0) > time.time() * 1000 - 20 * 3600 * 1000 and "tournaments" in old
            and "--force" not in sys.argv):
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
    doc = dict(players=photos, tournaments=tournaments(old.get("tournaments")))
    if {k: v for k, v in old.items() if k != "updated"} == doc:
        print("tennis unchanged")
        return
    doc["updated"] = int(time.time() * 1000)
    json.dump(doc, open("tennis.json", "w"), ensure_ascii=False, separators=(",", ":"))
    print("tennis written:", len(photos), "of", len(players), "players have a photo;",
          sum(1 for p in photos.values() if "espncdn" in p), "from ESPN;",
          len(doc["tournaments"]), "of", len(TOURNAMENTS), "tournaments have a logo")


if __name__ == "__main__":
    main()
