#!/usr/bin/env python3
"""Handball leagues beyond the ASOBAL, in the same shape as the other files (see build.py):

  {"league", "season", "updated", "teams":[{id,name,short,abbr,logo}],
   "matches":[{id,round,stage,start,status,home,away,hs,as,period,tv}],
   "standings":[{team,group,pos,pts,p,w,d,l,pf,pa,diff}]}

"stage" (optional) names the phase when a competition has more than plain rounds ("Fase de grupos · Grupo A");
"group" (optional) splits the table into several. Each league is read from its own public site:

  ehfcl, ehfel   EHF Champions League / European League (eurohandball.com's own JSON)
  ehfeuro        Men's EHF EURO (same site), once its matches are published
  lnh            Liqui Moly / Daikin StarLigue (lnh.fr)
  hhl            Danish Herreligaen (tophaandbold.dk)
  khl            Hungarian K&H Férfi Liga (the federation's public API, mksz.hu)
  hbl            German Handball-Bundesliga (sportschau.de's results service)
"""
import html, json, re, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
      "Accept-Language": "en"}
DAY = 86400 * 1000


def fetch(url, data=None, headers=None, retries=3):
    h = dict(UA)
    h.update(headers or {})
    for i in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=h)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(3)


def now_ms():
    return int(time.time() * 1000)


def utc_ms(iso):
    iso = iso.replace("Z", "").split(".")[0]
    return int(datetime.fromisoformat(iso).replace(tzinfo=timezone.utc).timestamp() * 1000)


def local_ms(dt, tz):
    return int(dt.replace(tzinfo=ZoneInfo(tz)).timestamp() * 1000)


def text(t):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))).strip()


def slug(name):
    import unicodedata
    plain = unicodedata.normalize("NFKD", name.lower().replace("ø", "o").replace("æ", "ae")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", plain).strip("-")


def team(tid, name, short=None, abbr=None, logo=None):
    return dict(id=str(tid), name=name, short=short or name, abbr=abbr or "", logo=logo)


def match(mid, start, status, home, away, hs=None, aw=None, rnd=0, stage=None, period=None, tv=None):
    d = dict(id=str(mid), round=rnd, start=start, status=status, home=str(home), away=str(away),
             hs=hs if status != "scheduled" else None, period=period if status == "live" else None, tv=tv or [])
    d["as"] = aw if status != "scheduled" else None
    if stage:
        d["stage"] = stage
    return d


def row(tid, pos, p, w, d, l, pf, pa, pts=None, group=None):
    r = dict(team=str(tid), pos=pos, pts=pts if pts is not None else 2 * w + d, p=p, w=w, d=d, l=l,
             pf=pf, pa=pa, diff=pf - pa)
    if group:
        r["group"] = group
    return r


# ----------------------------------------------------------------------------------------------- EHF

EHF_TERMS = {
    "group phase": "Fase de grupos", "main round": "Ronda principal", "preliminary round": "Primera fase",
    "quarter-finals": "Cuartos de final", "semi-finals": "Semifinales", "finals": "Final", "final": "Final",
    "play-offs": "Play-off", "knockout phase": "Eliminatorias", "last 16": "Octavos de final",
    "placement matches": "Partidos por puestos", "qualification round 1": "Clasificación 1",
    "qualification round 2": "Clasificación 2", "round 1": "Ronda 1", "round 2": "Ronda 2",
}


def ehf_stage(m):
    comp = m.get("comp") or {}
    phase = ((comp.get("phase") or {}).get("name") or (comp.get("round") or {}).get("name") or "").strip()
    name = EHF_TERMS.get(phase.lower(), phase)
    group = ((comp.get("group") or {}).get("name") or "").strip()
    if group and len(group) <= 3:
        return name + " · Grupo " + group if name else "Grupo " + group
    return name or None


def ehf(site):
    """[site] is the competition's season site, e.g. https://ehfcl.eurohandball.com/men/2026-27/."""
    page = fetch(site + "standings/")
    found = re.search(r'data-groupmatchesurl="([^"]+)"', page)
    if not found:
        raise RuntimeError("no match list on " + site)
    base = "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(site))
    data = json.loads(fetch(base + html.unescape(found.group(1))))
    teams, matches, groups = {}, [], {}
    for m in data.get("matches", []):
        h, a = m["homeTeam"]["team"], m["guestTeam"]["team"]
        if not h.get("id") or not a.get("id"):
            continue   # a knockout slot not drawn yet ("P01-A")
        for t in (h, a):
            teams[t["id"]] = team(t["id"], t["name"], t.get("shortName") or t["name"], None, t.get("logoSmall"))
        date = (m.get("venue") or {}).get("date") or {}
        if not date.get("utc") or not date.get("hasDate", True):
            continue
        status = "final" if m.get("isFinished") else "live" if m.get("isLive") else "scheduled"
        stage = ehf_stage(m)
        matches.append(match(m["matchID"], utc_ms(date["utc"]), status, h["id"], a["id"],
                             m["homeTeam"]["score"].get("goals"), m["guestTeam"]["score"].get("goals"),
                             stage=stage))
        g = ((m.get("comp") or {}).get("group") or {}).get("name")
        if g and len(g) <= 3:
            groups[h["id"]] = groups[a["id"]] = "Grupo " + g
    by_name = {html.unescape(t["name"]): t["id"] for t in teams.values()}
    standings = []
    for tab in re.findall(r"<table.*?</table>", page, flags=re.S):
        rows = []
        for tr in re.findall(r"<tr>(.*?)</tr>", tab, flags=re.S):
            cells = [text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S)]
            rank = re.match(r"(\d+)\.", cells[0]) if cells else None
            link = re.search(r"<a[^>]*>(.*?)</a>", tr, flags=re.S)
            if len(cells) < 8 or not rank or not link:
                continue
            tid = by_name.get(text(link.group(1)))
            gf = re.match(r"(\d+)\s*:\s*(\d+)", cells[5])
            if not tid or not gf:
                continue
            pos = int(rank.group(1))
            p, w, d, l = (int(x) for x in cells[1:5])
            rows.append(row(tid, pos, p, w, d, l, int(gf.group(1)), int(gf.group(2)), int(cells[7]), groups.get(tid)))
        if rows and any(r["p"] for r in rows):
            standings += rows
    return list(teams.values()), sorted(matches, key=lambda m: (m["start"], m["id"])), standings


# ----------------------------------------------------------------------------------------------- LNH

LNH = "https://www.lnh.fr/"
LNH_MONTHS = {"janv": 1, "févr": 2, "fevr": 2, "mars": 3, "avr": 4, "mai": 5, "juin": 6, "juil": 7, "août": 8,
              "aout": 8, "sept": 9, "oct": 10, "nov": 11, "déc": 12, "dec": 12}


def lnh_form(page, prefix):
    form = re.search(r'<form[^>]*id="%s-(\d+)"(.*?)</form>' % prefix, page, flags=re.S)
    if not form:
        raise RuntimeError("no %s form" % prefix)
    fields = dict(re.findall(r'<input type="hidden" name="([^"]+)" value="([^"]*)"', form.group(2)))
    season = re.search(r'<select name="seasons_id">.*?<option value="(\d+)" selected', form.group(2), flags=re.S)
    fields["seasons_id"] = season.group(1) if season else ""
    years = re.search(r'<option value="\d+" selected=selected>(\d{4}) / (\d{4})', form.group(2))
    return fields, (int(years.group(1)), int(years.group(2))) if years else None


def lnh_post(fields, controller):
    body = dict(fields)
    body.update(contents_controller=controller, contents_action="index_ajax", cache="no")
    return fetch(LNH + "ajaxpost1", urllib.parse.urlencode(body).encode(),
                 {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "X-Requested-With": "XMLHttpRequest"})


def lnh(league_path="daikin-starligue"):
    page = fetch(LNH + league_path + "/calendrier")
    fields, years = lnh_form(page, "calendar-form")
    fields.update(days_id="all", teams_id="all", current_month="all")
    cal = lnh_post(fields, "sportsCalendars")
    y1, y2 = years or (datetime.now().year, datetime.now().year + 1)
    teams, matches = {}, []
    for item in re.split(r'(?=<div class="calendars-listing-item)', cal)[1:]:
        cls = re.match(r'<div class="calendars-listing-item([^"]*)"\s+id="(\d+)"', item)
        if not cls:
            continue
        head = re.search(r'class="competition">\s*([^<]*?)\s*</span>\s*<br>\s*([^<]+)', item)
        sides = re.findall(r'<a href="[^"]*/equipes/([^"]+)"[^>]*title="([^"]+)"[^>]*>\s*<img src="([^"]+)"', item)
        if not head or len(sides) < 2:
            continue
        rnd = re.search(r"J(\d+)", head.group(1))
        d = re.search(r"(\d{1,2})\s+([a-zéû]+)\.?\s+(\d{1,2})h(\d{2})", head.group(2).lower())
        if not d:
            continue
        month = LNH_MONTHS.get(d.group(2)[:5].rstrip(".")) or LNH_MONTHS.get(d.group(2)[:4])
        if not month:
            continue
        year = y1 if month >= 7 else y2
        start = local_ms(datetime(year, month, int(d.group(1)), int(d.group(3)), int(d.group(4))), "Europe/Paris")
        for s, name, logo in sides[:2]:
            teams[s] = team(s, html.unescape(name), None, None, logo)
        sc = re.search(r'class="scores[^"]*">\s*(\d+)\s*-\s*(\d+)', item)
        flags = cls.group(1)
        status = "final" if " finish" in flags else "scheduled" if " waiting" in flags else ("live" if sc else "scheduled")
        matches.append(match(cls.group(2), start, status, sides[0][0], sides[1][0],
                             int(sc.group(1)) if sc else None, int(sc.group(2)) if sc else None,
                             rnd=int(rnd.group(1)) if rnd else 0))
    standings = []
    try:
        tpage = fetch(LNH + league_path + "/classement")
        tfields, _ = lnh_form(tpage, "standing-form")
        standings = lnh_table(lnh_post(tfields, "sportsStandings"), teams)
    except Exception as e:
        print("lnh table failed:", e, file=sys.stderr)
    return list(teams.values()), sorted(matches, key=lambda m: (m["start"], m["id"])), standings


def lnh_table(page, teams):
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", page, flags=re.S):
        s = re.search(r'/equipes/([^"]+)"', tr)
        cells = [text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S)]
        nums = [c for c in cells if re.fullmatch(r"-?\d+", c)]
        if not s or s.group(1) not in teams or len(nums) < 8:
            continue
        # rank, points, played, won, drawn, lost, for, against (then the difference)
        pos, pts, p, w, d, l, pf, pa = (int(x) for x in nums[:8])
        out.append(row(s.group(1), pos, p, w, d, l, pf, pa, pts))
    return out


# ------------------------------------------------------------------------------------- Herreligaen

TOP = "https://tophaandbold.dk"


def hhl():
    page = fetch(TOP + "/kampprogram/herreligaen")
    teams, matches = {}, []
    now = now_ms()
    for r in re.split(r'(?=<div class="match-program__row )', page)[1:]:
        d = re.search(r'match-program__row__date">\s*(\d\d)-(\d\d)-(\d\d)\s+(\d\d):(\d\d)', r)
        sides = re.findall(r'match-program__row__team">\s*<img src="([^"]+)"[^>]*>\s*([^<]+?)\s*</div>', r)
        mid = re.search(r'href="/match/(\d+)"', r) or re.search(r"/game/(\d+)/", r)
        if not (d and len(sides) >= 2 and mid):
            continue
        dd, mm, yy, hh, mi = (int(x) for x in d.groups())
        start = local_ms(datetime(2000 + yy, mm, dd, hh, mi), "Europe/Copenhagen")
        for logo, name in sides[:2]:
            name = html.unescape(name)
            teams[slug(name)] = team(slug(name), name, None, None, TOP + logo if logo.startswith("/") else logo)
        sc = re.search(r'match-program__row__score">\s*(\d+)\s*-\s*(\d+)', r)
        tv = [re.sub(r"-(?:color|white|logo)\d*$", "", t) for t in re.findall(r'tv-channel-logos/([a-z0-9-]+)-[0-9a-f]{20,}', r)]
        if sc and now > start + 2 * 3600 * 1000:
            status = "final"
        elif sc and now >= start:
            status = "live"
        else:
            status = "scheduled"
        matches.append(match(mid.group(1), start, status, slug(html.unescape(sides[0][1])), slug(html.unescape(sides[1][1])),
                             int(sc.group(1)) if sc else None, int(sc.group(2)) if sc else None,
                             tv=[t.replace("-", " ").upper() for t in tv[:2]]))
    standings = []
    tpage = fetch(TOP + "/stillinger/herreligaen")
    body = tpage[tpage.find("<tbody"):]
    for tr in re.findall(r'<tr class="team-position__row[^"]*">(.*?)</tr>', body, flags=re.S):
        pos = re.search(r'team-position__rank">\s*(\d+)', tr)
        name = re.search(r'team-position__logo"[^>]*>\s*<span>([^<]+)</span>', tr)
        cells = [text(c) for c in re.findall(r'<td class="text-center">(.*?)</td>', tr, flags=re.S)]
        if not (pos and name and len(cells) >= 6):
            continue
        tid = slug(html.unescape(name.group(1)))
        gf = re.match(r"(\d+)-(\d+)", cells[4])
        if tid not in teams or not gf:
            continue
        p, w, d, l = (int(x) for x in cells[:4])
        standings.append(row(tid, int(pos.group(1)), p, w, d, l, int(gf.group(1)), int(gf.group(2)), int(cells[5])))
        if standings and len(standings) > 20:
            break
    return list(teams.values()), sorted(matches, key=lambda m: (m["start"], m["id"])), standings


# ------------------------------------------------------------------------------------- K&H Liga

MKSZ_API = "https://public.mksz.hu/public/api/v1/"
MKSZ_DONE = {"JEGYZOK_LEZARVA", "JEGYZOK_ELFOGADVA", "EREDMENY_RÖGZITVE", "BEFEJEZETT"}


def mksz_token():
    """The federation's site sends this public key with every request it makes; read it from the site itself."""
    page = fetch("https://www.mksz.hu/")
    js = re.search(r'src="(/js/app\.[0-9a-f]+\.js)"', page)
    if not js:
        raise RuntimeError("mksz app script not found")
    code = fetch("https://www.mksz.hu" + js.group(1))
    tok = re.search(r'baseURL:"https://public\.mksz\.hu/public/api/v1/"[^}]*?"MKSZ-AUTH":"([^"]+)"', code)
    if not tok:
        raise RuntimeError("mksz key not found")
    return tok.group(1)


def khl():
    tok = mksz_token()
    hdr = {"Accept": "application/json", "MKSZ-AUTH": tok}
    season = datetime.now().year if datetime.now().month >= 7 else datetime.now().year - 1
    prog = json.loads(fetch(MKSZ_API + "versenyek/program?evadEv.equals=%d&globalisVersenyKod.in=NBI&nem.in=F"
                            "&size=800&page=0&paged=true" % season, headers=hdr))
    prog = [p for p in prog if "férfi liga" in (p.get("alversenyNev") or "").lower()] or prog
    teams, matches, stages = {}, [], set()
    now = now_ms()
    for p in prog:
        for side in ("hazai", "vendeg"):
            tid = p.get(side + "CsapatId")
            if tid:
                teams[str(tid)] = team(tid, p.get(side + "CsapatNev") or "", p.get(side + "CsapatRovidNev"), None,
                                       p.get(side + "LogoUrl") or None)
        if not p.get("merkozesDatum") or not p.get("hazaiCsapatId") or not p.get("vendegCsapatId"):
            continue
        start = local_ms(datetime.fromisoformat(p["merkozesDatum"].split(".")[0]), "Europe/Budapest")
        st = p.get("merkozesStatusz") or ""
        hs, aw = p.get("hazaiCsapatGol"), p.get("vendegCsapatGol")
        if st == "MERK_ELMARADT":
            continue   # postponed: it comes back with its new date
        if st in MKSZ_DONE:
            status = "final"
        elif hs is not None and now >= start and now < start + 3 * 3600 * 1000:
            status = "live"
        else:
            status = "scheduled"
        stages.add(p.get("alversenyId"))
        matches.append(match(p["merkozesId"], start, status, p["hazaiCsapatId"], p["vendegCsapatId"], hs, aw,
                             rnd=p.get("fordulo") or 0))
    standings = []
    for sid in [s for s in stages if s][:1]:
        tab = json.loads(fetch(MKSZ_API + "versenyek/tabella/%s" % sid, headers=hdr))
        for i, r in enumerate(tab.get("tabella") or [], 1):
            tid = str(r.get("csapatId"))
            if tid not in teams:
                teams[tid] = team(tid, r.get("csapatNev") or "", r.get("csapatRovidNev"), None, r.get("logoPublicUrl"))
            elif not teams[tid]["logo"]:
                teams[tid]["logo"] = r.get("logoPublicUrl")
            standings.append(row(tid, i, r.get("lejatszottMerkozes") or 0, r.get("gyozelem") or 0, r.get("dontetlen") or 0,
                                 r.get("vereseg") or 0, r.get("lottGol") or 0, r.get("kapottGol") or 0, r.get("pont")))
    return list(teams.values()), sorted(matches, key=lambda m: (m["start"], m["id"])), standings


# ----------------------------------------------------------------------------------- sportschau

SS = "https://www.sportschau.de/live-und-ergebnisse/handball/"


def ss_day(page, rnd):
    out, teams = [], {}
    now = now_ms()
    for li in re.findall(r'(<li data-match_id="\d+".*?</li>)', page, flags=re.S):
        mid = re.search(r'data-match_id="(\d+)"', li).group(1)
        dt = re.search(r'data-datetime="([^"]+)"', li)
        cls = re.search(r'class="(?:even|odd) ([a-z-]+)', li)
        ids = re.findall(r"/emblem/common/\d+x\d+/(\d+)\.png\" alt=\"([^\"]+)\"", li)
        shorts = dict(re.findall(r'team-shortname team-shortname-(home|away)">([^<]+)<', li))
        micros = dict(re.findall(r'team-microname team-microname-(home|away)">([^<]+)<', li))
        res = re.findall(r'match-result match-result-(?:home|away)"><div class="match-result match-result-\d+">(\d+)<', li)
        if not dt or len(ids) < 2:
            continue
        start = utc_ms(dt.group(1))
        state = cls.group(1) if cls else ""
        for (tid, name), side in zip(ids[:2], ("home", "away")):
            teams[tid] = team(tid, html.unescape(name), html.unescape(shorts.get(side, name)),
                              micros.get(side), "https://s.hs-data.com/gfx/emblem/common/80x80/%s.png" % tid)
        if state in ("upcoming", "pre", "scheduled"):
            status = "scheduled"
        elif state in ("live", "running", "halftime", "inprogress"):
            status = "live"
        elif state:
            status = "final"
        else:
            status = "final" if now > start + 3 * 3600 * 1000 else "scheduled"
        hs = int(res[0]) if len(res) > 1 else None
        aw = int(res[1]) if len(res) > 1 else None
        period = text(re.search(r'class="match-status[^"]*">(.*?)</div>', li, flags=re.S).group(1)) if status == "live" and "match-status" in li else None
        out.append(match(mid, start, status, ids[0][0], ids[1][0], hs, aw, rnd=rnd, period=period))
    return out, teams


def ss_table(page, teams):
    out = []
    for tr in re.findall(r'<tr class="hs_team_id-(\d+)[^"]*standing[^"]*">(.*?)</tr>', page, flags=re.S):
        tid, body = tr
        def cell(name):
            c = re.search(r'class="standing-%s">([^<]*)<' % name, body)
            return c.group(1).strip() if c else ""
        if tid not in teams:
            continue
        gf = re.match(r"(\d+):(\d+)", cell("goaldiff"))
        pts = re.match(r"(\d+)", cell("points"))
        try:
            out.append(row(tid, int(cell("rank") or 0), int(cell("games_played")), int(cell("win")), int(cell("draw")),
                           int(cell("lost")), int(gf.group(1)) if gf else 0, int(gf.group(2)) if gf else 0,
                           int(pts.group(1)) if pts else None))
        except ValueError:
            continue
    return out


def sportschau(path, previous=None):
    """[path]: the competition's piece of the sportschau address ("deutschland-hbl")."""
    page = fetch(SS + path + "/spiele-und-ergebnisse")
    days = re.findall(r'<option[^>]*value="(/live-und-ergebnisse/handball/%s/se\d+/[^"]+/spieltag/md(\d+)/spiele-und-ergebnisse)"' % re.escape(path), page)
    kept = {}
    for m in (previous or {}).get("matches", []):
        kept.setdefault(m["round"], []).append(m)
    teams = {t["id"]: t for t in (previous or {}).get("teams", [])}
    matches = []
    now = now_ms()
    for url, n in dict.fromkeys(days):
        n = int(n)
        old = kept.get(n)
        recent = old and any(abs(m["start"] - now) < 3 * DAY for m in old)
        if old and not recent and all(m["status"] == "final" for m in old):
            matches += old
            continue
        try:
            got, t = ss_day(fetch("https://www.sportschau.de" + url), n)
        except Exception as e:
            print(path, "matchday", n, "failed:", e, file=sys.stderr)
            matches += old or []
            continue
        teams.update(t)
        matches += got
        time.sleep(0.4)
    if not days:   # a cup or a tournament without matchdays: the one page
        got, t = ss_day(page, 0)
        teams.update(t)
        matches = got
    standings = []
    try:
        standings = ss_table(fetch(SS + path + "/tabelle"), teams)
    except Exception as e:
        print(path, "table failed:", e, file=sys.stderr)
    return list(teams.values()), sorted(matches, key=lambda m: (m["start"], m["id"])), standings


# ----------------------------------------------------------------------------------------------- run

SEASON = "2026-27"
JOBS = {
    "ehfcl": lambda old: ehf("https://ehfcl.eurohandball.com/men/2026-27/"),
    "ehfel": lambda old: ehf("https://ehfel.eurohandball.com/men/2026-27/"),
    "lnh": lambda old: lnh(),
    "hhl": lambda old: hhl(),
    "khl": lambda old: khl(),
    "hbl": lambda old: sportschau("deutschland-hbl", old),
}


def write(name, doc):
    path = name + ".json"
    try:
        old = json.load(open(path))
    except Exception:
        old = {}
    if {k: v for k, v in old.items() if k != "updated"} == doc:
        print(name, "unchanged")
        return
    doc["updated"] = now_ms()
    json.dump(doc, open(path, "w"), ensure_ascii=False, separators=(",", ":"))
    print(name, "written", len(doc["matches"]), "matches,", len(doc["standings"]), "rows")


if __name__ == "__main__":
    only = sys.argv[1:] or list(JOBS)
    failed = 0
    for name in only:
        try:
            try:
                old = json.load(open(name + ".json"))
            except Exception:
                old = None
            teams, matches, standings = JOBS[name](old)
            if not matches and old:
                print(name, "returned nothing; keeping the previous file", file=sys.stderr)
                continue
            write(name, dict(league=name, season=SEASON, teams=sorted(teams, key=lambda t: t["name"]),
                             matches=matches, standings=standings))
        except Exception as e:
            failed += 1
            print(name, "FAILED", repr(e), file=sys.stderr)
    sys.exit(1 if only and failed == len(only) else 0)
