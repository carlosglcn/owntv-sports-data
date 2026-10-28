#!/usr/bin/env python3
"""snooker.json: the World Snooker Tour — the matches of the events on now and coming up, their results, and the
world ranking — in the shape of the other files (see handball.py), plus

  "ranking":[{pos,team,points}]   (team = a player id in "teams")

Players are "teams" with "athlete": true. From snooker.org's public pages, read gently: an event is read again
only while it is on (or about to be), at most every ten minutes, and the ranking once a day.
"""
import html, json, re, sys, time, urllib.request
from datetime import datetime, timezone

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
BASE = "https://www.snooker.org/res/index.asp?"
DAY = 86400 * 1000
MONTHS = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
ROUNDS = {"final": "Final", "semi-finals": "Semifinales", "quarter-finals": "Cuartos de final", "last 16": "Octavos",
          "last 32": "Dieciseisavos", "last 64": "Ronda de 64", "last 128": "Ronda de 128"}


def get(q):
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(BASE + q, headers=UA), timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            if i == 2:
                raise
            time.sleep(3)
        finally:
            time.sleep(1)


def text(t):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))).replace("\u2011", "-").strip()


def now_ms():
    return int(time.time() * 1000)


def event_list(page):
    """(id, name, start, end) of the events a page lists ("International Championship (31 Oct - 7 Nov 2026)")."""
    out = {}
    for eid, label in re.findall(r'href="/res/index\.asp\?event=(\d+)"[^>]*>([^<]+)</a>', page):
        t = text(label)
        m = re.match(r"(.*?)\s*\((\d{1,2})(?:\s*(\w{3}))?\s*-\s*(\d{1,2})\s*(\w{3})\s*(\d{4})\)", t)
        if not m:
            continue
        name, d1, m1, d2, m2, y = m.groups()
        y = int(y)
        mo2 = MONTHS.get(m2, 1)
        mo1 = MONTHS.get(m1, mo2) if m1 else mo2
        y1 = y - 1 if mo1 > mo2 else y
        start = int(datetime(y1, mo1, int(d1), tzinfo=timezone.utc).timestamp() * 1000)
        end = int(datetime(y, mo2, int(d2), 23, 59, tzinfo=timezone.utc).timestamp() * 1000)
        out[eid] = (eid, name.strip(), start, end)
    return list(out.values())


def event_matches(eid, name, start, end, page, players):
    out, labels, best = [], {}, {}
    year = datetime.fromtimestamp(end / 1000, timezone.utc).year
    # Each round's heading: <a name="r8"></a><span class="round">Round 2</span><div class="roundinfo">(Last 64; Best of 11; …
    for h in re.finditer(r'<a name="r(\d+)"></a>\s*<span class="round">([^<]+)</span>\s*<div class="roundinfo">(.{0,300})', page, flags=re.S):
        n, rname, info = int(h.group(1)), h.group(2).strip(), text(h.group(3))
        last = re.match(r"\((Last \d+)", info)
        key = (last.group(1) if last else rname).lower().replace("semifinals", "semi-finals").replace("quarterfinals", "quarter-finals")
        labels[n] = ROUNDS.get(key) or ("Ronda previa" if last else rname)
        bo = re.search(r"Best of (\d+)", info)
        if bo:
            best[n] = int(bo.group(1))
    for row in re.findall(r'<tr class="gradeA[^"]*oneonone[^"]*"[^>]*>.*?</tr>', page, flags=re.S):
        rn = re.search(r"\bround(\d+)\b", row)
        rnd = int(rn.group(1)) if rn else 0
        rt = re.search(r'<td class="round"[^>]*>\s*<a[^>]*title="([^"]+)"', row)
        if rt:
            parts = [p.strip() for p in rt.group(1).split(";")]
            labels[rnd] = ROUNDS.get(parts[1].lower(), parts[1]) if len(parts) > 1 else parts[0]
        who = re.findall(r'<td class="nationality">(?:<img[^>]*alt="([^"]*)")?[^<]*</td>\s*<td class="player ">\s*<a href="/res/index\.asp\?player=(\d+)"[^>]*title="([^"]+)"', row)
        if len(who) < 2:
            continue   # a slot not drawn yet
        for country, pid, pname in who[:2]:
            players[pid] = dict(id=pid, name=html.unescape(pname), short=html.unescape(pname), abbr="", logo=None,
                                athlete=True, country=country or None)
        s1 = re.search(r'class="score\s+first-score"[^>]*>\s*(\d+)\s*<', row)
        s2 = re.search(r'class="last-score"[^>]*>\s*(\d+)\s*<', row)
        when = re.search(r'class="scheduled"[^>]*>(\d{4}-\d\d-\d\d \d\d:\d\d):\d\dZ<', row)
        mod = re.search(r'title="Last modified: \w{3} (\d{1,2})(?:&nbsp;|\s)(\w{3})(?:&nbsp;|\s)(\d\d):(\d\d)"', row)
        live = "live" in row.split(">", 1)[0] or 'class="live' in row
        if when:
            st = int(datetime.strptime(when.group(1), "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp() * 1000)
        elif mod:
            d, mo, hh, mi = int(mod.group(1)), MONTHS.get(mod.group(2), 1), int(mod.group(3)), int(mod.group(4))
            y = year if mo <= datetime.fromtimestamp(end / 1000, timezone.utc).month or mo >= 7 else year
            st = int(datetime(y, mo, d, hh, mi, tzinfo=timezone.utc).timestamp() * 1000) - 2 * 3600 * 1000
        else:
            continue
        status = "scheduled"
        if s1 and s2:
            bo = re.search(r'title="Best of (\d+) frames"', row)
            frames = int(bo.group(1)) if bo else best.get(rnd)
            need = frames // 2 + 1 if frames else None
            done = need is not None and max(int(s1.group(1)), int(s2.group(1))) >= need
            status = "final" if done or (not live and now_ms() > st + 5 * 3600 * 1000) else "live"
        mid = re.search(r'match-centre/([0-9a-f-]{36})', row)
        out.append(dict(id=mid.group(1) if mid else "%s-%s-%s-%s" % (eid, rnd, who[0][1], who[1][1]), round=0, start=st,
                        status=status, home=who[0][1], away=who[1][1],
                        hs=int(s1.group(1)) if s1 and status != "scheduled" else None,
                        **{"as": int(s2.group(1)) if s2 and status != "scheduled" else None},
                        period=None, tv=[], stage=name + (" · " + labels[rnd] if rnd in labels else ""), event=eid))
    return out


def ranking(players):
    page = get("template=31")
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", page, flags=re.S):
        pos = re.search(r'class="position"\s*>(\d+)\.', tr)
        p = re.search(r'player=(\d+)"[^>]*>([^<]+)</a>', tr)
        nat = re.search(r'class="nationality">([^<]*)<', tr)
        pts = re.search(r'class="sum javascript_on"\s*>(\d+)<', tr)
        if not (pos and p):
            continue
        pid = p.group(1)
        players.setdefault(pid, dict(id=pid, name=html.unescape(p.group(2)), short=html.unescape(p.group(2)), abbr="",
                                     logo=None, athlete=True, country=(nat.group(1).strip() if nat else None) or None))
        out.append(dict(pos=int(pos.group(1)), team=pid, points=int(pts.group(1)) if pts else 0))
        if len(out) >= 128:
            break
    return out


def main():
    try:
        old = json.load(open("snooker.json"))
    except Exception:
        old = {}
    now = now_ms()
    if old.get("updated", 0) > now - 9 * 60 * 1000 and "--force" not in sys.argv:
        print("snooker fresh")
        return
    players = {t["id"]: t for t in old.get("teams", [])}
    events = {e["id"]: e for e in old.get("events", [])}
    for q in ("template=24", "template=22"):
        try:
            for eid, name, start, end in event_list(get(q)):
                events[eid] = dict(id=eid, name=name, start=start, end=end)
        except Exception as e:
            print("snooker list", q, "failed:", e, file=sys.stderr)
    kept = {}
    for m in old.get("matches", []):
        kept.setdefault(m.get("event"), []).append(m)
    matches = []
    for eid, e in sorted(events.items(), key=lambda kv: kv[1]["start"]):
        if e["end"] < now - 120 * DAY:
            continue
        active = e["start"] - 2 * DAY <= now <= e["end"] + DAY
        if kept.get(eid) and not active:
            matches += kept[eid]
            continue
        if e["start"] > now + 40 * DAY:
            continue
        try:
            got = event_matches(eid, e["name"], e["start"], e["end"], get("event=" + eid), players)
            matches += got or kept.get(eid, [])
        except Exception as ex:
            print("snooker event", eid, "failed:", ex, file=sys.stderr)
            matches += kept.get(eid, [])
    rank = old.get("ranking", [])
    if not rank or old.get("rankedAt", 0) < now - DAY:
        try:
            rank = ranking(players)
            ranked_at = now
        except Exception as ex:
            print("snooker ranking failed:", ex, file=sys.stderr)
            ranked_at = old.get("rankedAt", 0)
    else:
        ranked_at = old.get("rankedAt", 0)
    used = {m["home"] for m in matches} | {m["away"] for m in matches} | {r["team"] for r in rank}
    doc = dict(league="snooker", season="2026-27", events=sorted(events.values(), key=lambda e: e["start"]),
               teams=sorted((p for k, p in players.items() if k in used), key=lambda p: p["name"]),
               matches=sorted(matches, key=lambda m: (m["start"], m["id"])), standings=[], ranking=rank, rankedAt=ranked_at)
    if {k: v for k, v in old.items() if k != "updated"} == doc:
        print("snooker unchanged")
        return
    doc["updated"] = now
    json.dump(doc, open("snooker.json", "w"), ensure_ascii=False, separators=(",", ":"))
    print("snooker written:", len(doc["matches"]), "matches,", len(rank), "ranked")


if __name__ == "__main__":
    main()
