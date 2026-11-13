#!/usr/bin/env python3
"""More basketball, in the same shape as acb.json (see build.py): EuroCup, Primera FEB (Spain's second tier) and
Lega A (Italy). Each league is written on its own; one failing leaves the others and its last file untouched."""
import html as htmllib, json, os, re, subprocess, sys, time, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from build import get, ms, table, write, LIVE_WINDOW_MS  # noqa: E402

MADRID = ZoneInfo("Europe/Madrid")
SEASON = "2026-27"


def now_ms():
    return int(time.time() * 1000)


def status_by_clock(start, has_score):
    if has_score:
        return "final"
    n = now_ms()
    return "live" if start <= n <= start + LIVE_WINDOW_MS else "scheduled"


# ---------------------------------------------------------------- EuroCup (EuroLeague's API, competition U)

def eurocup():
    data = json.loads(get("https://api-live.euroleague.net/v2/competitions/U/seasons/U2026/games"))["data"]
    teams, seen, matches = [], set(), []
    n = now_ms()
    for g in data:
        sides = {}
        for key in ("local", "road"):
            c = g[key]["club"]
            if c["code"] not in seen:
                seen.add(c["code"])
                teams.append(dict(id=c["code"], name=c["name"], short=c.get("editorialName") or c["abbreviatedName"],
                                  abbr=c.get("tvCode") or c["code"], logo=(c.get("images") or {}).get("crest")))
            sides[key] = (c["code"], g[key].get("score"))
        start = ms(g.get("utcDate") or g["date"])
        st = "final" if g.get("played") else ("live" if start <= n <= start + LIVE_WINDOW_MS else "scheduled")
        hs, as_ = sides["local"][1], sides["road"][1]
        if st != "final" and not hs and not as_:
            hs = as_ = None
        matches.append(dict(id=g["identifier"], round=g["round"], start=start, status=st,
                            home=sides["local"][0], away=sides["road"][0], hs=hs, **{"as": as_}, period=None, tv=[]))
    matches.sort(key=lambda m: m["start"])
    standings = []
    try:
        root = ET.fromstring(get("https://api-live.euroleague.net/v1/standings?seasonCode=U2026&gameNumber=99"))
        groups = root.findall(".//group") or [root]
        for gi, grp in enumerate(groups):
            name = grp.get("name") or grp.findtext("name") or ""
            for t in grp.iter("team"):
                standings.append(dict(team=t.findtext("code"), pos=int(t.findtext("ranking")), p=int(t.findtext("totalgames")),
                                      w=int(t.findtext("wins")), l=int(t.findtext("losses")),
                                      pf=int(t.findtext("ptsfavour")), pa=int(t.findtext("ptsagainst")),
                                      diff=int(t.findtext("difference")), group=name or chr(65 + gi), _g=gi))
        standings.sort(key=lambda r: (r["_g"], r["pos"]))
        for r in standings:
            del r["_g"]
        if len(groups) < 2:
            for r in standings:
                del r["group"]
    except Exception as e:
        print("eurocup standings failed, computing:", e, file=sys.stderr)
        standings = []
    if not standings:
        standings = table(teams, matches)
    return dict(league="eurocup", season=SEASON, teams=teams, matches=matches, standings=standings)


# ---------------------------------------------------------------- Primera FEB (baloncestoenvivo.feb.es, one page)

FEB = "https://baloncestoenvivo.feb.es/calendario/primerafeb/1/2026"
FEB_TIME = re.compile(r"(\d{2})/(\d{2})/(\d{4})\s*<br/?>\s*(\d{1,2}):(\d{2})")
FEB_SCORE = re.compile(r"^\s*(\d+)\s*-\s*(\d+)\s*$")
FEB_TEAM = re.compile(r'<img[^>]+src="([^"]+)"[^>]*/>\s*<a[^>]+Equipo\.aspx\?i=(\d+)">([^<]+)</a>', re.S)
FEB_CELL = re.compile(r"<td class=\"(resultado|fecha)\">\s*<a href='[^']*Partido\.aspx\?p=(\d+)'>(.*?)</a>", re.S)


def feb_name(raw):
    """FEB writes names in capitals: give them ordinary capitals, keeping short words and acronyms."""
    words = htmllib.unescape(raw).strip().split()
    out = []
    for w in words:
        if len(w) <= 3 and w.isalpha() and w not in ("DE", "DEL", "LA", "EL", "Y"):
            out.append(w)
        else:
            out.append(w.capitalize() if w.isupper() else w)
    return " ".join(out).replace(" De ", " de ").replace(" Del ", " del ")


def primerafeb():
    page = get(FEB)
    teams, matches = {}, []
    blocks = re.split(r'<h1 class="titulo-modulo">', page)[1:]
    for b in blocks:
        head = re.match(r"\s*Jornada\s+(\d+)\s+(\d{2})/(\d{2})/(\d{4})", b)
        if not head:
            continue
        rnd = int(head.group(1))
        day = datetime(int(head.group(4)), int(head.group(3)), int(head.group(2)), 19, 0, tzinfo=MADRID)
        for row in re.split(r"<tr>", b)[2:]:
            sides = FEB_TEAM.findall(row)
            cell = FEB_CELL.search(row)
            if len(sides) < 2 or not cell:
                continue
            for logo, tid, name in sides[:2]:
                if tid not in teams:
                    nm = feb_name(name)
                    teams[tid] = dict(id=tid, name=nm, short=nm, abbr="", logo=htmllib.unescape(logo))
            kind, pid, text = cell.groups()
            hs = as_ = None
            score = FEB_SCORE.match(re.sub(r"<[^>]+>", "", text))
            t = FEB_TIME.search(text)
            if t:
                d, mo, y, hh, mm = map(int, t.groups())
                start = int(datetime(y, mo, d, hh, mm, tzinfo=MADRID).timestamp() * 1000)
            else:
                start = int(day.timestamp() * 1000)
            if score:
                hs, as_ = int(score.group(1)), int(score.group(2))
            st = status_by_clock(start, score is not None)
            matches.append(dict(id=pid, round=rnd, start=start, status=st, home=sides[0][1], away=sides[1][1],
                                hs=hs, **{"as": as_}, period=None, tv=[]))
    if not matches:
        raise RuntimeError("no FEB matches found")
    matches.sort(key=lambda m: m["start"])
    tl = list(teams.values())
    return dict(league="primerafeb", season=SEASON, teams=tl, matches=matches, standings=table(tl, matches))


REPO_LOGOS = "https://raw.githubusercontent.com/carlosglcn/owntv-sports-data/main/logos/"


def small_logo(folder, key, url):
    """Lega's crests are 2600-pixel PNGs: keep a 160-pixel copy in this repo and point at it (the big one if that fails)."""
    path = "logos/%s/%s.png" % (folder, key)
    if not os.path.exists(path):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            big = path + ".src"
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as r:
                open(big, "wb").write(r.read())
            subprocess.check_call(["convert", big, "-trim", "-resize", "160x160", "-strip", path])
            os.remove(big)
        except Exception as e:
            print("logo", key, "failed:", e, file=sys.stderr)
            return url
    return REPO_LOGOS + "%s/%s.png" % (folder, key)


# ---------------------------------------------------------------- Lega A (legabasket.it JSON, one call per round)

LEGA = "https://www.legabasket.it/api/championships/get-championships-calendar-by-id?id=602"


def lega():
    first = json.loads(get(LEGA))
    cdn = first.get("cdn_url") or "https://lba-media.s3.eu-south-1.amazonaws.com"
    days = (first.get("filters") or {}).get("days") or []
    raw, seen = [], set()

    def take(doc):
        tvs = doc.get("broadcasters") or {}
        for m in doc.get("matches") or []:
            if m["id"] not in seen:
                seen.add(m["id"])
                m["_tv"] = [b["name"] for b in tvs.get(str(m["id"]), []) if b.get("name") and b["name"] != "LBATV"]
                raw.append(m)

    take(first)
    for d in days:
        try:
            take(json.loads(get(LEGA + "&d=" + str(d["id"]))))
        except Exception as e:
            print("lega day", d.get("code"), "failed:", e, file=sys.stderr)
    teams, matches = {}, []
    for m in raw:
        for side, key in (("h", "home_logo_key"), ("v", "v_logo_key")):
            tid = str(m[side + "_team_id"])
            if tid not in teams:
                logo = m.get(key)
                teams[tid] = dict(id=tid, name=m[side + "_team_name"], short=m[side + "_team_name"],
                                  abbr=m.get(side + "_club_code") or "", logo=small_logo("lega", logo, cdn + "/" + logo) if logo else None)
        start = int(datetime.fromisoformat(m["match_datetime"]).timestamp() * 1000)
        gs = str(m.get("game_status"))
        hs, as_ = m.get("home_final_score"), m.get("visitor_final_score")
        if gs == "0":
            st = "scheduled"; hs = as_ = None
        elif gs in ("2", "3", "4") or (hs or as_) and now_ms() > start + LIVE_WINDOW_MS:
            st = "final"
        else:
            st = "live"
        matches.append(dict(id=str(m["id"]), round=m.get("day_serial") or m.get("number"), start=start, status=st,
                            home=str(m["h_team_id"]), away=str(m["v_team_id"]), hs=hs, **{"as": as_},
                            period=None, tv=m["_tv"]))
    matches.sort(key=lambda m: m["start"])
    tl = list(teams.values())
    return dict(league="lega", season=SEASON, teams=tl, matches=matches, standings=table(tl, matches))


JOBS = {"eurocup": eurocup, "primerafeb": primerafeb, "lega": lega}

if __name__ == "__main__":
    failed = 0
    for name in sys.argv[1:] or JOBS:
        try:
            write(name, JOBS[name]())
        except Exception as e:
            failed += 1
            print(name, "FAILED", repr(e), file=sys.stderr)
    sys.exit(1 if failed == len(sys.argv[1:] or JOBS) else 0)
