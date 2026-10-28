#!/usr/bin/env python3
"""cycling.json: the UCI WorldTour (men) — every race of the season, every stage of the stage races.

  {"updated", "season", "races":[{id,name,cat,oneday,start,end,url,
      stages:[{id,n,label,start,date,from,to,km,profile,status,top:[{name,team}],leader:{name,team}}],
      gc:[{pos,name,team,gap}]}]}

From procyclingstats.com, read politely: a finished race is never read again, an unfinished one only around
its days, at most once an hour (the board needs no more: a stage's result is in when it is over).
"""
import html, json, re, sys, time, urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
PCS = "https://www.procyclingstats.com/"
MONTHS = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                      "September", "October", "November", "December"], 1)}
PROFILE = {"p1": "flat", "p2": "hills-flat", "p3": "hills-uphill", "p4": "mountains-flat", "p5": "mountains-uphill"}
HOUR = 3600 * 1000


def get(path):
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(PCS + path, headers=UA), timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            if i == 2:
                raise
            time.sleep(4)
        finally:
            time.sleep(1.2)   # one page at a time, with a pause


def text(t):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))).strip()


def info(page, label):
    m = re.search(r">\s*%s:?\s*</div>\s*<div[^>]*>(.*?)</div>" % re.escape(label), page, flags=re.S)
    if m:
        return text(m.group(1))
    m = re.search(r"%s:?\s*(?:</[^>]+>\s*)+(?:<[^>]+>\s*)*([^<]+)" % re.escape(label), page)
    return text(m.group(1)) if m else ""


def tz_for(page):
    # PCS gives local start times; the race's country is enough for the zone in all but a handful of cases.
    flag = re.search(r'<span class="flag ([a-z]{2})"', page[page.find("Race information") - 4000:page.find("Race information")] if "Race information" in page else page)
    return COUNTRY_TZ.get(flag.group(1) if flag else "", "Europe/Madrid")


COUNTRY_TZ = {
    "es": "Europe/Madrid", "fr": "Europe/Paris", "it": "Europe/Rome", "be": "Europe/Brussels", "nl": "Europe/Amsterdam",
    "de": "Europe/Berlin", "ch": "Europe/Zurich", "pl": "Europe/Warsaw", "gb": "Europe/London", "dk": "Europe/Copenhagen",
    "si": "Europe/Ljubljana", "au": "Australia/Adelaide", "ae": "Asia/Dubai", "ca": "America/Toronto", "cn": "Asia/Shanghai",
    "us": "America/Los_Angeles", "pt": "Europe/Lisbon", "no": "Europe/Oslo", "mc": "Europe/Monaco", "ad": "Europe/Andorra",
    "sa": "Asia/Riyadh", "tr": "Europe/Istanbul", "at": "Europe/Vienna", "lu": "Europe/Luxembourg",
}


def stage_page(page, tz):
    date = re.search(r"Date\s*(?:</[^>]+>\s*)+(?:<[^>]+>\s*)*(\d{1,2}) (\w+) (\d{4})", page)
    start_time = re.search(r"Start time:\s*(?:</[^>]+>\s*)+(?:<[^>]+>\s*)*(\d{1,2}):(\d{2})", page)
    km = re.search(r"Distance:\s*(?:</[^>]+>\s*)+(?:<[^>]+>\s*)*([\d.]+)", page)
    dep = re.search(r"Departure:\s*(?:</[^>]+>\s*)+(?:<[^>]+>\s*)*(?:<a[^>]*>)?([^<]+)", page)
    arr = re.search(r"Arrival:\s*(?:</[^>]+>\s*)+(?:<[^>]+>\s*)*(?:<a[^>]*>)?([^<]+)", page)
    prof = re.search(r'class="icon profile (p\d)', page)
    out = {}
    if date:
        d, mo, y = int(date.group(1)), MONTHS.get(date.group(2), 0), int(date.group(3))
        if mo:
            out["date"] = "%04d-%02d-%02d" % (y, mo, d)
            hh, mi = (int(start_time.group(1)), int(start_time.group(2))) if start_time else (12, 0)
            out["start"] = int(datetime(y, mo, d, hh, mi, tzinfo=ZoneInfo(tz)).timestamp() * 1000)
            out["timeKnown"] = bool(start_time)
    if km:
        out["km"] = float(km.group(1))
    if dep and dep.group(1).strip():
        out["from"] = html.unescape(dep.group(1).strip())
    if arr and arr.group(1).strip():
        out["to"] = html.unescape(arr.group(1).strip())
    if prof:
        out["profile"] = PROFILE.get(prof.group(1))
    tables = re.findall(r"<table[^>]*>(.*?)</table>", page, flags=re.S)
    out["top"] = riders(tables[0], 3) if tables else []
    # The general classification after this stage is the second results table on a stage page.
    out["gcTable"] = tables[1] if len(tables) > 1 else None
    return out


def riders(table, n):
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", table, flags=re.S)[1:]:
        rider = re.search(r'href="rider/[^"]+">([^<]+)</a>', tr)
        team = re.search(r'href="team/[^"]+">([^<]+)</a>', tr)
        # The time column: the leader's total ("32:41:44"), everyone else's gap to them ("1:18").
        times = [c.strip() for c in re.findall(r'<td class="ar"\s*>\s*([\d:]+)\s*</td>', tr)]
        if rider:
            gap = times[-1] if times else ""
            out.append(dict(name=nice(html.unescape(rider.group(1))), team=html.unescape(team.group(1)) if team else "",
                            gap=gap if not out else "+" + gap if gap else ""))
        if len(out) >= n:
            break
    return out


def nice(name):
    """"POGAČAR Tadej" → "Tadej Pogačar"."""
    parts = name.split()
    surname = [p for p in parts if p.isupper() and len(p) > 1]
    given = [p for p in parts if p not in surname]
    if not surname or not given:
        return name
    return " ".join(given + [s.capitalize() if "-" not in s else "-".join(x.capitalize() for x in s.split("-")) for s in surname])


def season_races(year):
    page = get("races.php?year=%d&circuit=1&filter=Filter" % year)
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", page, flags=re.S):
        link = re.search(r'href="race/([a-z0-9-]+)-(\d{4})-(gc|result)"', tr)
        name = re.search(r'href="race/[^"]+">([^<]+)</a>', tr)
        cat = re.search(r">([12]\.UWT)<", tr)
        if not (link and name):
            continue
        out.append(dict(id=link.group(1) + "-" + link.group(2), slug=link.group(1), year=int(link.group(2)),
                        name=html.unescape(name.group(1)).strip(), cat=cat.group(1) if cat else "",
                        oneday=link.group(3) == "result"))
    return out


def build_race(r, old):
    now = int(time.time() * 1000)
    base = "race/%s/%d" % (r["slug"], r["year"])
    stages = {s["id"]: s for s in (old or {}).get("stages", [])}
    done = old and old.get("stages") and all(s.get("status") == "final" for s in old["stages"])
    if done and old.get("end", 0) < now - 2 * 86400 * 1000:
        return old   # over: never read again
    if old and old.get("start", 0) > now + 3 * 86400 * 1000 and old.get("stages"):
        return old   # still days away and already read once
    first = get(base + ("/result" if r["oneday"] else "/stage-1"))
    tz = tz_for(first)
    if r["oneday"]:
        pages = [("result", 0, "", first)]
    else:
        opts = re.findall(r'<option value="race/%s-%d-stage-(\d+)[^"]*"[^>]*>([^<]+)</option>' % (re.escape(r["slug"]), r["year"]), first)
        seen, pages = set(), []
        for n, label in opts:
            if n in seen:
                continue
            seen.add(n)
            pages.append(("stage-" + n, int(n), html.unescape(label), None))
        if not pages:
            pages = [("stage-1", 1, "", first)]
    out, gc = [], (old or {}).get("gc", [])
    for key, n, label, page in pages:
        sid = r["id"] + "-" + key
        prev = stages.get(sid)
        if prev and prev.get("status") == "final" and prev.get("start", 0) < now - 86400 * 1000:
            out.append(prev)
            continue
        try:
            page = page or (first if key == "stage-1" else get(base + "/" + key))
        except Exception as e:
            print(r["id"], key, "failed:", e, file=sys.stderr)
            if prev:
                out.append(prev)
            continue
        s = stage_page(page, tz)
        start = s.get("start")
        if not start:
            continue
        status = "final" if s["top"] else ("live" if now >= start else "scheduled")
        if status == "live" and now > start + 7 * HOUR:
            status = "final"
        kind = re.search(r"\((ITT|TTT)\)", label)
        st = dict(id=sid, n=n, label=("Etapa %d" % n if n else ""), tt=kind.group(1) if kind else None,
                  start=start, date=s.get("date"), timeKnown=s.get("timeKnown", False),
                  frm=s.get("from"), to=s.get("to"), km=s.get("km"), profile=s.get("profile"),
                  status=status, top=[dict(name=x["name"], team=x["team"]) for x in s["top"]])
        if not r["oneday"] and s.get("gcTable") and status == "final":
            g = riders(s["gcTable"], 10)
            if g:
                st["leader"] = dict(name=g[0]["name"], team=g[0]["team"])
                gc = [dict(pos=i + 1, name=x["name"], team=x["team"], gap=x["gap"]) for i, x in enumerate(g)]
        out.append(st)
    out.sort(key=lambda s: (s["start"], s["n"]))
    if not out:
        return old
    return dict(id=r["id"], name=r["name"], cat=r["cat"], oneday=r["oneday"], start=out[0]["start"],
                end=out[-1]["start"] + 6 * HOUR, stages=out, gc=gc if not r["oneday"] else [])


def main():
    try:
        old = json.load(open("cycling.json"))
    except Exception:
        old = {}
    now = int(time.time() * 1000)
    racing_today = any(s.get("status") != "final" and abs(s.get("start", 0) - now) < 8 * HOUR
                       for r in old.get("races", []) for s in r.get("stages", []))
    if old.get("updated", 0) > now - (20 if racing_today else 55) * 60 * 1000 and "--force" not in sys.argv:
        print("cycling fresh")
        return
    year = datetime.now(timezone.utc).year
    olds = {r["id"]: r for r in old.get("races", [])}
    races = []
    calendars = season_races(year)
    if datetime.now(timezone.utc).month >= 11:
        try:
            calendars += season_races(year + 1)   # next season's calendar, once it is out
        except Exception:
            pass
    for r in calendars:
        try:
            built = build_race(r, olds.get(r["id"]))
        except Exception as e:
            print(r["id"], "failed:", e, file=sys.stderr)
            built = olds.get(r["id"])
        if built:
            races.append(built)
    races.sort(key=lambda r: r["start"])
    doc = dict(season=year, races=races)
    if {k: v for k, v in old.items() if k != "updated"} == doc:
        print("cycling unchanged")
        return
    doc["updated"] = now
    json.dump(doc, open("cycling.json", "w"), ensure_ascii=False, separators=(",", ":"))
    print("cycling written:", len(races), "races,", sum(len(r["stages"]) for r in races), "stages")


if __name__ == "__main__":
    main()
