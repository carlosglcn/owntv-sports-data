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
    only = sys.argv[1:] or ["acb", "euroleague"]
    failed = 0
    for n, fn in (("acb", acb), ("euroleague", euroleague)):
        if n in only:
            try:
                write(n, fn())
            except Exception as e:
                failed += 1
                print(n, "FAILED", repr(e), file=sys.stderr)
    sys.exit(1 if failed == 2 else 0)
