#!/usr/bin/env python3
"""venues.json: where each club plays its home games, and where each big tennis tournament is played.

  {"updated", "v",
   "teams":  {"<the app's league slug>": {"<team id in that league's file>": "<arena, city>"}},
   "tennis": [{"names": ["roland garros", "french open"], "venue": "<venue, city>"}]}

The league files (acb.json, asobal.json…) list the clubs but not their arenas, so each club is looked up once on
Wikidata: the club of that sport whose name matches, its "home venue" (P115) and the place that venue is in (P131).
Sponsors change a club's name every season, so a name that finds nothing is tried again without its first or last
word. What was found — or not found — is kept in venues_cache.json: a club is asked about again only after
RETRY_DAYS. venues_manual.json ({"<slug>": {"<team id>": "<arena, city>"}}) overrides any of it by hand; an empty
text there removes a wrong one.

The tennis venues are written here by hand: the feed names the tournament, never its ground, and they do not move.
"""
import json, os, sys, time, urllib.parse, urllib.request

UA = {"User-Agent": "OwnTVFanartBot/1.0 (https://github.com/carlosglcn/owntv-sports-data)"}
API = "https://www.wikidata.org/w/api.php?format=json&"
VERSION = 1
RETRY_DAYS = 14
MAX_LOOKUPS = 70          # per run: the first runs fill the file a part at a time
BASKETBALL, HANDBALL = "Q5372", "Q8418"

LEAGUES = {
    "acb": BASKETBALL, "euroleague": BASKETBALL, "eurocup": BASKETBALL, "primerafeb": BASKETBALL, "lega": BASKETBALL,
    "asobal": HANDBALL, "ehfcl": HANDBALL, "ehfel": HANDBALL, "hbl": HANDBALL, "lnh": HANDBALL, "hhl": HANDBALL, "khl": HANDBALL,
}

# What the feed's tournament name may contain -> where it is played. Same order as tennis.py: the first match wins.
TENNIS = [
    (["next gen"], "King Abdullah Sports City, Jeddah"),
    (["atp finals"], "Inalpi Arena, Turin"),
    (["wta finals"], "King Saud University Indoor Arena, Riyadh"),
    (["paris masters", "rolex paris"], "Paris La Défense Arena, Nanterre"),
    (["australian open"], "Melbourne Park, Melbourne"),
    (["roland garros", "french open"], "Stade Roland Garros, Paris"),
    (["wimbledon"], "All England Club, London"),
    (["us open"], "USTA Billie Jean King National Tennis Center, New York"),
    (["indian wells", "bnp paribas open"], "Indian Wells Tennis Garden, California"),
    (["miami"], "Hard Rock Stadium, Miami Gardens"),
    (["monte-carlo", "monte carlo"], "Monte-Carlo Country Club, Roquebrune-Cap-Martin"),
    (["madrid"], "Caja Mágica, Madrid"),
    (["internazionali", "italian open", "rome"], "Foro Italico, Rome"),
    (["montreal"], "IGA Stadium, Montreal"),
    (["toronto"], "Sobeys Stadium, Toronto"),
    (["cincinnati", "western & southern"], "Lindner Family Tennis Center, Mason"),
    (["shanghai"], "Qizhong Forest Sports City Arena, Shanghai"),
    (["china open", "beijing"], "National Tennis Center, Beijing"),
    (["wuhan"], "Optics Valley International Tennis Center, Wuhan"),
    (["dubai"], "Aviation Club Tennis Centre, Dubai"),
    (["barcelona", "godo"], "Real Club de Tenis Barcelona, Barcelona"),
    (["queen"], "Queen's Club, London"),
    (["halle"], "OWL Arena, Halle"),
]


def get(params):
    req = urllib.request.Request(API + urllib.parse.urlencode(params), headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode("utf-8"))


def label(entity):
    labels = entity.get("labels", {})
    for lang in ("en", "es", "fr", "de", "it"):
        if lang in labels:
            return labels[lang]["value"]
    return next((v["value"] for v in labels.values()), None)


def claim_ids(entity, prop):
    out = []
    for c in entity.get("claims", {}).get(prop, []):
        if c.get("rank") == "deprecated":
            continue
        # A venue the club has left carries an end date.
        if "P582" in (c.get("qualifiers") or {}):
            continue
        v = ((c.get("mainsnak") or {}).get("datavalue") or {}).get("value") or {}
        if v.get("id"):
            out.append((0 if c.get("rank") == "preferred" else 1, v["id"]))
    return [q for _, q in sorted(out)]


def entities(ids, props="labels|claims"):
    if not ids:
        return {}
    return get(dict(action="wbgetentities", ids="|".join(ids), props=props, languages="en|es|fr|de|it")).get("entities", {})


def variants(name):
    words = name.split()
    out = [name]
    if len(words) >= 3:
        out += [" ".join(words[1:]), " ".join(words[:-1])]
    elif len(words) == 2:
        out += [w for w in words if len(w) >= 5]
    return out


def lookup(name, sport):
    """The home venue of the [sport] club called [name], as "arena, city"; None when Wikidata has none."""
    for text in variants(name):
        hits = get(dict(action="query", list="search", srlimit=5, srsearch=f"{text} haswbstatement:P641={sport}")).get("query", {}).get("search", [])
        clubs = entities([h["title"] for h in hits])
        for h in hits:
            club = clubs.get(h["title"]) or {}
            homes = claim_ids(club, "P115")
            if not homes:
                continue
            arena = entities(homes[:1]).get(homes[0]) or {}
            arena_name = label(arena)
            if not arena_name:
                continue
            places = claim_ids(arena, "P131")
            city = label(entities(places[:1], "labels").get(places[0]) or {}) if places else None
            found = arena_name if not city or city.lower() in arena_name.lower() else f"{arena_name}, {city}"
            return found, label(club)
        time.sleep(0.3)
    return None, None


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def main():
    cache = load("venues_cache.json", {})
    manual = load("venues_manual.json", {})
    now = int(time.time())
    left = MAX_LOOKUPS
    teams = {}
    for slug, sport in LEAGUES.items():
        doc = load(slug + ".json", {})
        known = cache.setdefault(slug, {})
        out = {}
        for t in doc.get("teams", []):
            tid, name = str(t.get("id", "")), (t.get("name") or "").strip()
            if not tid or not name:
                continue
            had = known.get(tid)
            stale = had is None or had.get("name") != name and not had.get("venue") or (not had.get("venue") and now - had.get("at", 0) > RETRY_DAYS * 86400)
            if stale and left > 0:
                left -= 1
                try:
                    venue, club = lookup(name, sport)
                    had = dict(name=name, venue=venue, club=club, at=now)
                    known[tid] = had
                    print(slug, "|", name, "->", venue, "(", club, ")")
                except Exception as e:
                    print("lookup failed:", slug, name, e, file=sys.stderr)
                time.sleep(0.3)
            if had and had.get("venue"):
                out[tid] = had["venue"]
        for tid, venue in (manual.get(slug) or {}).items():
            if venue:
                out[tid] = venue
            else:
                out.pop(tid, None)
        if out:
            teams[slug] = out
    with open("venues_cache.json", "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1, sort_keys=True)
    doc = dict(v=VERSION, teams=teams, tennis=[dict(names=n, venue=v) for n, v in TENNIS])
    old = load("venues.json", {})
    if {k: old.get(k) for k in ("v", "teams", "tennis")} != doc:
        doc["updated"] = now * 1000
        with open("venues.json", "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    print(sum(len(v) for v in teams.values()), "clubs have a venue;", MAX_LOOKUPS - left, "looked up this run")


if __name__ == "__main__":
    main()
