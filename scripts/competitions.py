#!/usr/bin/env python3
"""competitions.json: the logo of each competition whose scores do not come with one (ESPN's do).

  {"updated", "v", "leagues": {"<the app's league slug>": "<logo url>"}}

The logo is the drawn mark that leads the competition's article on the English Wikipedia, copied into
logos/competitions/ and served from this repository (Wikimedia refuses clients that do not name themselves,
which is how an app's image loader asks). A competition whose article is led by a photograph keeps no logo.
Rebuilt at most once a day.
"""
import json, os, re, sys, time, urllib.parse, urllib.request

UA = {"User-Agent": "OwnTVFanartBot/1.0 (https://github.com/carlosglcn/owntv-sports-data)"}
BROWSER = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
WIKI = ("https://en.wikipedia.org/w/api.php?action=query&format=json&redirects=1&prop=pageimages"
        "&piprop=thumbnail&pithumbsize=320&pilicense=any&titles=")
RAW = "https://raw.githubusercontent.com/carlosglcn/owntv-sports-data/main/logos/competitions/"
VERSION = 7

# The app's league slug -> the competition's article.
LEAGUES = {
    "acb": "Liga ACB",
    "euroleague": "EuroLeague",
    "eurocup": "EuroCup Basketball",
    "primerafeb": "Primera FEB",
    "lega": "Lega Basket Serie A",
    "asobal": "Liga ASOBAL",
    "ehfcl": "EHF Champions League",
    "ehfel": "EHF European League",
    "hbl": "Handball-Bundesliga",
    "lnh": "LNH Division 1",
    "hhl": "Herrehåndboldligaen",
    "khl": "Nemzeti Bajnokság I (men's handball)",
    "snooker": "World Snooker Tour",
    "davis": "Davis Cup",
    "motogp": "MotoGP",
    "f1": "Formula One",
    "uwt": "UCI World Tour",
    "irl": "IndyCar Series",
    "nascar-premier": "NASCAR Cup Series",
    "nascar-secondary": "NASCAR O'Reilly Auto Parts Series",
    "nascar-truck": "NASCAR Craftsman Truck Series",
}


def get(url):
    # TheSportsDB's image host turns away clients that do not look like a browser.
    headers = BROWSER if "thesportsdb.com" in url else UA
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
        return r.status, r.read()


def is_logo(url):
    name = urllib.parse.unquote(url.split("?")[0].rsplit("/", 1)[-1]).lower()
    return "logo" in name or ".svg" in name or "wordmark" in name


def any_logo(title, lang="en", hints=(), avoid=()):
    """When the article is led by a photograph: the first file on the page named as a logo (an SVG first)."""
    url = ("https://%s.wikipedia.org/w/api.php?action=query&format=json&redirects=1&generator=images&gimlimit=50"
           "&prop=imageinfo&iiprop=url&iiurlwidth=320&titles=" % lang) + urllib.parse.quote(title)
    try:
        st, body = get(url)
        pages = json.loads(body).get("query", {}).get("pages", {}).values()
    except Exception as e:
        print("images failed:", title, e, file=sys.stderr)
        return None
    found = []
    for p in pages:
        name = p.get("title", "").lower()
        info = (p.get("imageinfo") or [{}])[0]
        src = info.get("thumburl") or info.get("url")
        hinted = any(h in name for h in hints)
        named = "logo" in name or hinted
        # A file found only by a word of its name may be anything (a photo of the club's offices): drawn marks only.
        if hinted and "logo" not in name and not (name.endswith(".svg") or name.endswith(".png")):
            continue
        if any(a in name for a in avoid):
            continue
        if src and named and "commons-logo" not in name and "wiki" not in name.split(":")[-1][:4]:
            found.append((0 if name.endswith(".svg") else 1, src))
    return sorted(found)[0][1] if found else None


# Logos whose file is not called a logo ("F1.svg"): words their file names carry.
HINTS = {
    "f1": ("f1.svg", "f1 logo", "formula 1"),
    "asobal": ("asobal",),
    "primerafeb": ("primera feb", "feb.", "leb"),
    "hbl": ("hbl", "handball-bundesliga", "handball bundesliga"),
    "lnh": ("lnh", "starligue", "liqui moly"),
    "khl": ("k&h", "nb i", "férfi"),
    "davis": ("davis",),
}

# Files a page carries that are another competition's mark (the MotoGP article shows Moto2's and Moto3's too).
AVOID = {"motogp": ("moto2", "moto3", "motoe", "moto 2", "moto 3")}

# Where the English article has no logo at all, the Spanish (or the league's own country's) one may.
SPANISH = {"asobal": ("es", "Liga ASOBAL"), "primerafeb": ("es", "Primera FEB"), "acb": ("es", "Liga ACB"),
           "f1": ("es", "Campeonato Mundial de Fórmula 1"),
           "lnh": ("fr", "Championnat de France masculin de handball"), "khl": ("hu", "Nemzeti Bajnokság I (férfi kézilabda)")}


# Where Wikipedia has no mark of the league's own (the HBL's articles show the clubs' crests; the Hungarian league's
# none at all): TheSportsDB's league badge. Its API answers 403 to a client like this one, so the badges' own
# addresses are named here (from thesportsdb.com/league/4533 and /4535).
SPORTSDB = {
    "hbl": "https://r2.thesportsdb.com/images/media/league/badge/yt21x11783630443.png",
    "khl": "https://r2.thesportsdb.com/images/media/league/badge/wl72r61560678493.png",
    # The Davis Cup's mark is not a free file, so its Wikipedia article offers none (from thesportsdb.com/league/5347).
    "davis": "https://r2.thesportsdb.com/images/media/league/badge/i0qscy1672325773.png",
}


def sportsdb_badge(slug):
    return SPORTSDB.get(slug)


def mirror(slug, url):
    ext = ".png" if ".png" in url.lower() else ".jpg"
    path = "logos/competitions/" + slug + ext
    try:
        st, body = get(url)
        if st == 200 and len(body) > 200:
            os.makedirs("logos/competitions", exist_ok=True)
            open(path, "wb").write(body)
    except Exception as e:
        print("logo not copied:", slug, e, file=sys.stderr)
    return RAW + slug + ext if os.path.exists(path) else None


def main():
    try:
        old = json.load(open("competitions.json"))
    except Exception:
        old = {}
    if (old.get("updated", 0) > time.time() * 1000 - 20 * 3600 * 1000 and old.get("v") == VERSION
            and "--force" not in sys.argv):
        print("competitions fresh")
        return
    # What an older version of this script chose is not kept: it may be what this one learned to refuse.
    kept = old.get("leagues", {}) if old.get("v") == VERSION else {}
    for f in os.listdir("logos/competitions") if os.path.isdir("logos/competitions") and old.get("v") != VERSION else []:
        os.remove(os.path.join("logos/competitions", f))
    items = list(LEAGUES.items())
    out = {}
    for i in range(0, len(items), 20):
        chunk = items[i:i + 20]
        found = {}
        try:
            st, body = get(WIKI + urllib.parse.quote("|".join(t for _, t in chunk)))
            q = json.loads(body).get("query", {})
            moved = {s["from"]: s["to"] for s in q.get("normalized", []) + q.get("redirects", [])}
            pages = {p.get("title"): (p.get("thumbnail") or {}).get("source") for p in q.get("pages", {}).values()}
            for _, title in chunk:
                at = title
                for _ in range(3):
                    at = moved.get(at, at)
                found[title] = pages.get(at)
        except Exception as e:
            print("wikipedia chunk failed:", e, file=sys.stderr)
        for slug, title in chunk:
            src = found.get(title)
            if not (src and is_logo(src)):
                hints = HINTS.get(slug, ())
                avoid = AVOID.get(slug, ())
                src = any_logo(title, hints=hints, avoid=avoid) or (any_logo(SPANISH[slug][1], SPANISH[slug][0], hints, avoid) if slug in SPANISH else None)
            if src and any(a in urllib.parse.unquote(src).lower() for a in AVOID.get(slug, ())):
                src = None
            # The HBL's article only ever shows clubs' crests: its own badge comes from TheSportsDB first.
            if slug == "hbl" or (not src and slug in SPORTSDB):
                src = sportsdb_badge(slug) or (None if slug == "hbl" else src)
            served = mirror(slug, src) if src else None
            logo = served or kept.get(slug)
            if logo:
                out[slug] = logo
            else:
                print("no logo:", slug, "(", title, "->", src, ")")
        time.sleep(1)
    doc = dict(v=VERSION, leagues=out)
    if {k: v for k, v in old.items() if k != "updated"} == doc:
        print("competitions unchanged")
        return
    doc["updated"] = int(time.time() * 1000)
    json.dump(doc, open("competitions.json", "w"), ensure_ascii=False, separators=(",", ":"))
    print("competitions written:", len(out), "of", len(LEAGUES), "have a logo")


if __name__ == "__main__":
    main()
