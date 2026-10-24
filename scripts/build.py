#!/usr/bin/env python3
"""Builds acb.json and euroleague.json: teams, every match of the season, and the table.

Same shape for both leagues so the app reads them with one parser:
  {"league", "season", "updated", "teams":[{id,name,short,abbr,logo}],
   "matches":[{id,round,start,status,home,away,hs,as,period,tv}],
   "standings":[{team,pos,p,w,l,pf,pa,diff}]}
status: scheduled | live | final.  start: epoch milliseconds (UTC).
"""
import json, re, sys, time, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

UA = {"User-Agent": "Mozilla/5.0"}
LIVE_WINDOW_MS = 3 * 3600 * 1000


def get(url, retries=3):
    for i in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read().decode("utf-8")
        except Exception as e:
            if i == retries - 1:
                raise
            time.sleep(3)


def ms(iso):
    iso = iso.replace("Z", "")
    return int(datetime.fromisoformat(iso).replace(tzinfo=timezone.utc).timestamp() * 1000)


def table(teams, matches):
    row = {t["id"]: dict(team=t["id"], p=0, w=0, l=0, pf=0, pa=0) for t in teams}
    for m in matches:
        if m["status"] != "final" or m["hs"] is None or m["as"] is None:
            continue
        for me, other, f, a in ((m["home"], m["away"], m["hs"], m["as"]), (m["away"], m["home"], m["as"], m["hs"])):
            r = row.get(me)
            if r is None:
                continue
            r["p"] += 1; r["pf"] += f; r["pa"] += a
            r["w" if f > a else "l"] += 1
    out = list(row.values())
    for r in out:
        r["diff"] = r["pf"] - r["pa"]
    out.sort(key=lambda r: (-(r["w"] / r["p"] if r["p"] else 0), -r["w"], -r["diff"], -r["pf"]))
    for i, r in enumerate(out, 1):
        r["pos"] = i
    return out


def acb():
    html = get("https://www.acb.com/calendario")
    parts = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', html, flags=re.S)
    text = "".join(json.loads('"' + p + '"') for p in parts)
    dec = json.JSONDecoder()
    ti = text.index('"teams":[')
    teams_raw, _ = dec.raw_decode(text[ti + len('"teams":'):])
    ri = text.index('"rounds":[', ti)
    rounds, _ = dec.raw_decode(text[ri + len('"rounds":'):])
    teams = [dict(id=str(t["id"]), name=t["fullName"], short=t.get("shortName") or t["fullName"],
                  abbr=t.get("abbreviatedName") or "", logo=t.get("logo")) for t in teams_raw]

    def team_id(ref):
        if isinstance(ref, dict):
            return str(ref["id"])
        return str(teams_raw[int(str(ref).rsplit(":", 1)[1])]["id"])

    matches = []
    for rd in rounds:
        for m in rd.get("matches", []):
            raw = (m.get("matchStatus") or "").upper()
            if raw == "FINALIZED":
                st = "final"
            elif m.get("isOnHalfTime") or raw in ("LIVE", "IN_PROGRESS", "PLAYING", "STARTED"):
                st = "live"
            else:
                st = "scheduled"
            tv = [c["name"] for c in (m.get("broadcastChannels") or {}).get("primary", [])]
            matches.append(dict(
                id=str(m["id"]), round=rd["roundNumber"], start=ms(m["startDateTime"]), status=st,
                home=team_id(m["homeTeam"]), away=team_id(m["awayTeam"]),
                hs=m.get("homeTeamScore"), **{"as": m.get("awayTeamScore")},
                period=m.get("currentQuarter") if st == "live" else None, tv=tv))
    matches.sort(key=lambda m: m["start"])
    return dict(league="acb", season="2026-27", teams=teams, matches=matches, standings=table(teams, matches))


def euroleague():
    data = json.loads(get("https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/games"))["data"]
    teams, seen, matches = [], set(), []
    now = int(time.time() * 1000)
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
        if g.get("played"):
            st = "final"
        elif start <= now <= start + LIVE_WINDOW_MS:
            st = "live"
        else:
            st = "scheduled"
        hs, as_ = sides["local"][1], sides["road"][1]
        if st != "final" and not hs and not as_:
            hs = as_ = None
        matches.append(dict(id=g["identifier"], round=g["round"], start=start, status=st,
                            home=sides["local"][0], away=sides["road"][0], hs=hs, **{"as": as_}, period=None, tv=[]))
    matches.sort(key=lambda m: m["start"])
    standings = []
    try:
        root = ET.fromstring(get("https://api-live.euroleague.net/v1/standings?seasonCode=E2026&gameNumber=99"))
        for t in root.iter("team"):
            standings.append(dict(team=t.findtext("code"), pos=int(t.findtext("ranking")), p=int(t.findtext("totalgames")),
                                  w=int(t.findtext("wins")), l=int(t.findtext("losses")),
                                  pf=int(t.findtext("ptsfavour")), pa=int(t.findtext("ptsagainst")),
                                  diff=int(t.findtext("difference"))))
        standings.sort(key=lambda r: r["pos"])
    except Exception as e:
        print("euroleague standings failed, computing:", e, file=sys.stderr)
    if not standings:
        standings = table(teams, matches)
    return dict(league="euroleague", season="2026-27", teams=teams, matches=matches, standings=standings)


ASOBAL = "https://www.asobal.es/"
MADRID = ZoneInfo("Europe/Madrid")


def get_latin(url, retries=3):
    """ASOBAL serves ISO-8859-1."""
    for i in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read().decode("latin-1")
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(3)


def clean(t):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)).strip()


def asobal_round(html, n):
    """The matches of one round page: [{id,code home/away,club ids,start,status,score,tv,period}]."""
    out, undated = [], 0
    block = html[html.find('class="info-results"'):]
    for li in re.findall(r"<li>(.*?)</li>", block, flags=re.S):
        if "estadisticas/" in li and not re.search(r"\d\d/\d\d/\d{4} - \d\d:\d\d", li):
            undated += 1   # postponed, or its date and TV slot are not set yet
        d = re.search(r"(\d\d)/(\d\d)/(\d{4}) - (\d\d):(\d\d)", li)
        codes = re.findall(r'href="equipos/([A-Za-z0-9]+)/"', li)
        clubs = re.findall(r"imagenes/jornada/club(\d+)\.svg", li)
        mid = re.search(r"estadisticas/(\d+)/", li)
        if not (d and len(codes) >= 2 and len(clubs) >= 2 and mid):
            continue
        dd, mm, yy, hh, mi = map(int, d.groups())
        start = int(datetime(yy, mm, dd, hh, mi, tzinfo=MADRID).timestamp() * 1000)
        sc = re.search(r"<b>\s*(\d+)\s*</b>\s*-\s*<b>\s*(\d+)\s*</b>", li)
        en = re.search(r'class="enlaces">(.*?)(?:\||</span>)', li, flags=re.S)
        label = clean(en.group(1)) if en else ""
        tvm = re.search(r"fa-television[^>]*></i>(.*?)<br", li, flags=re.S)
        tv = [c.strip() for c in clean(tvm.group(1)).split("+") if c.strip()] if tvm else []
        low = label.lower()
        if "finalizado" in low:
            st = "final"
        elif "no ha comenzado" in low or not label:
            st = "scheduled"
        else:
            st = "live"
        out.append(dict(id=mid.group(1), round=n, start=start, status=st, home=codes[0], away=codes[1],
                        club_home=clubs[0], club_away=clubs[1],
                        hs=int(sc.group(1)) if sc and st != "scheduled" else None,
                        **{"as": int(sc.group(2)) if sc and st != "scheduled" else None},
                        period=label if st == "live" else None, tv=tv))
    return out, undated


def asobal_table(html):
    rows, names = [], {}
    body = html[html.find("<tbody"):]
    for tr in re.findall(r"<tr>(.*?)</tr>", body, flags=re.S):
        pos = re.search(r"<h4>\s*(\d+)", tr)
        code = re.search(r'href="equipos/([A-Za-z0-9]+)/"', tr)
        club = re.search(r"imagenes/jornada/club(\d+)\.svg", tr)
        name = re.search(r"<span>([^<]+)</span>", tr)
        cells = [clean(c) for c in re.findall(r"<td>(.*?)</td>", tr, flags=re.S)]
        if not (pos and code and club and name and len(cells) >= 8):
            continue
        v = [int(c.replace("+", "")) for c in cells[:8]]
        names[code.group(1)] = (name.group(1).strip(), club.group(1))
        rows.append(dict(team=code.group(1), pos=int(pos.group(1)), pts=v[0], p=v[1], w=v[2], d=v[3], l=v[4],
                         pf=v[5], pa=v[6], diff=v[7]))
    return rows, names


def asobal(previous=None):
    now = int(time.time() * 1000)
    standings, names = asobal_table(get_latin(ASOBAL + "liga/clasificacion/"))
    kept = {}
    for m in (previous or {}).get("matches", []):
        kept.setdefault(m["round"], []).append(m)
    matches, clubs = [], {}
    open_rounds = set((previous or {}).get("open", []))
    still_open = set()
    for n in range(1, 31):
        old = kept.get(n)
        recent = old and any(abs(m["start"] - now) < 3 * 86400 * 1000 for m in old)
        if old and not recent and n not in open_rounds and all(m["status"] == "final" for m in old):
            matches += old
            continue
        try:
            rnd, undated = asobal_round(get_latin(ASOBAL + "liga/calendario/%d/" % n), n)
            if undated:
                still_open.add(n)
        except Exception as e:
            print("asobal round", n, "failed:", e, file=sys.stderr)
            matches += old or []
            continue
        time.sleep(0.3)
        for m in rnd:
            clubs[m["home"]] = m.pop("club_home"); clubs[m["away"]] = m.pop("club_away")
        matches += rnd
    for t in (previous or {}).get("teams", []):
        clubs.setdefault(t["id"], (t.get("logo") or "").rsplit("club", 1)[-1].replace(".svg", ""))
    codes = {m["home"] for m in matches} | {m["away"] for m in matches}
    teams = []
    for code in sorted(codes):
        name, club = names.get(code, (code, clubs.get(code, "")))
        club = clubs.get(code) or club
        teams.append(dict(id=code, name=name, short=name, abbr=code,
                          logo=ASOBAL + "imagenes/jornada/club%s.svg" % club if club else None))
    matches.sort(key=lambda m: (m["start"], m["id"]))
    return dict(league="asobal", season="2026-27", teams=teams, matches=matches, standings=standings, open=sorted(still_open))


def write(name, doc):
    path = name + ".json"
    try:
        old = json.load(open(path))
    except Exception:
        old = {}
    if {k: v for k, v in old.items() if k != "updated"} == doc:
        print(name, "unchanged"); return
    doc["updated"] = int(time.time() * 1000)
    json.dump(doc, open(path, "w"), ensure_ascii=False, separators=(",", ":"))
    print(name, "written", len(doc["matches"]), "matches")


if __name__ == "__main__":
    only = sys.argv[1:] or ["acb", "euroleague", "asobal"]
    failed = 0
    jobs = [n for n in ("acb", "euroleague", "asobal") if n in only]
    for n in jobs:
        try:
            if n == "asobal":
                try:
                    old = json.load(open("asobal.json"))
                except Exception:
                    old = None
                write(n, asobal(old))
            else:
                write(n, {"acb": acb, "euroleague": euroleague}[n]())
        except Exception as e:
            failed += 1
            print(n, "FAILED", repr(e), file=sys.stderr)
    sys.exit(1 if jobs and failed == len(jobs) else 0)
