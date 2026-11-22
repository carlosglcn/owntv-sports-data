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
WIKI = ("https://en.wikipedia.org/w/api.php?action=query&format=json&redirects=1&prop=pageimages"
        "&piprop=thumbnail&pithumbsize=320&pilicense=any&titles=")
RAW = "https://raw.githubusercontent.com/carlosglcn/owntv-sports-data/main/logos/competitions/"
VERSION = 2

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
    "motogp": "MotoGP",
    "f1": "Formula One",
    "uwt": "UCI World Tour",
    "irl": "IndyCar Series",
    "nascar-premier": "NASCAR Cup Series",
    "nascar-secondary": "NASCAR O'Reilly Auto Parts Series",
    "nascar-truck": "NASCAR Craftsman Truck Series",
}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.status, r.read()


def is_logo(url):
    name = urllib.parse.unquote(url.split("?")[0].rsplit("/", 1)[-1]).lower()
    return "logo" in name or ".svg" in name or "wordmark" in name


def any_logo(title, lang="en"):
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
        if src and "logo" in name and "commons-logo" not in name and "wiki" not in name.split(":")[-1][:4]:
            found.append((0 if name.endswith(".svg") else 1, src))
    return sorted(found)[0][1] if found else None


# Where the English article has no logo at all, the Spanish one may.
SPANISH = {"asobal": "Liga ASOBAL", "primerafeb": "Primera FEB", "acb": "Liga ACB"}


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
    kept = old.get("leagues", {})
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
                src = any_logo(title) or (any_logo(SPANISH[slug], "es") if slug in SPANISH else None)
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
