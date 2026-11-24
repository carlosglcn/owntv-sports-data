#!/usr/bin/env python3
"""wrc.json: the World Rally Championship season, in the shape of cycling.json — each rally one race with one
"stage" (the rally itself, Thursday to Sunday), its winner once run; the drivers' championship as the gc.

  {"updated", "season", "races":[{id,name,round,oneday:true,start,end,
      stages:[{id,n,label,start,end,date,frm,to,km,status,top:[{name,team}]}],
      surface, hq}], "gc":[{pos,name,team,gap}]}

From the season's English Wikipedia article (Calendar, Season summary, Drivers' standings). No live stage
times: the official site and the results sites turn automated reads away; Wikipedia follows within the day.
"""
import json, os, re, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

UA = {"User-Agent": "OwnTVFanartBot/1.0 (https://github.com/carlosglcn/owntv-sports-data)"}
OUT = "wrc.json"
MONTHS = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                      "September", "October", "November", "December"], 1)}
# A rally day's first stage is in the morning; Thursday's shakedown / opening stage counts as its start.
START_HOUR_UTC = 8
GC_ROWS = 15
SURFACE_ES = {"gravel": "Tierra", "tarmac": "Asfalto", "snow": "Nieve", "mixed": "Mixto"}


def raw(title):
    url = "https://en.wikipedia.org/w/index.php?" + urllib.parse.urlencode({"title": title, "action": "raw"})
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def clean(cell):
    """A wikitext cell's text: links to their label, templates and refs out."""
    c = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", cell, flags=re.S)
    c = re.sub(r"\{\{efn[^{}]*\}\}", "", c)
    c = re.sub(r"\{\{flagicon\|[^}]*\}\}", "", c)
    c = re.sub(r"\{\{(?:nowrap|small|sortname)\|([^{}|]*)(?:\|[^{}]*)?\}\}", r"\1", c)
    c = re.sub(r"\{\{[^{}]*\}\}", "", c)
    c = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", c)
    c = re.sub(r"'''?|&nbsp;", " ", c)
    c = re.sub(r"<[^>]+>", "", c)
    if "|" in c and not c.strip().startswith("["):
        c = c.split("|")[-1]   # cell attributes: align=center|value
    return re.sub(r"\s+", " ", c).strip()


def table_after(text, heading):
    i = text.find(heading)
    if i < 0:
        return []
    j = text.find("{|", i)
    k = text.find("\n|}", j)
    if j < 0 or k < 0:
        return []
    rows = []
    for block in re.split(r"\n\|-[^\n]*", text[j:k]):
        cells = []
        for line in block.split("\n"):
            if line.startswith("{|") or not line or line[0] not in "!|":
                if cells and line and line[0] not in "!|":
                    cells[-1] += " " + line
                continue
            for part in re.split(r"\|\||!!", line[1:]):
                cells.append(part)
        if cells:
            rows.append(cells)
    return rows


def date_ms(day_month, year, hour=START_HOUR_UTC):
    m = re.match(r"(\d{1,2})\s+([A-Za-z]+)", day_month)
    if not m or m.group(2) not in MONTHS:
        return 0
    return int(datetime(year, MONTHS[m.group(2)], int(m.group(1)), hour, tzinfo=timezone.utc).timestamp() * 1000)


def main():
    now = datetime.now(timezone.utc)
    year = now.year
    # Between seasons (December), the coming one once its article has a calendar.
    text = None
    for y in ([year + 1, year] if now.month == 12 else [year]):
        try:
            t = raw("%d World Rally Championship" % y)
            if "==Calendar==" in t:
                text, year = t, y
                break
        except Exception as e:
            print("wrc: article %d failed: %s" % (y, e), file=sys.stderr)
    if not text:
        sys.exit(0)
    winners = {}
    for cells in table_after(text, "===Season summary==="):
        if len(cells) >= 5 and clean(cells[0]).isdigit():
            winners[int(clean(cells[0]))] = {"name": clean(cells[2]), "co": clean(cells[3]), "team": clean(cells[4])}
    races = []
    for cells in table_after(text, "==Calendar=="):
        if len(cells) < 8 or not clean(cells[0]).isdigit():
            continue
        rnd = int(clean(cells[0]))
        start, end = date_ms(clean(cells[1]), year), date_ms(clean(cells[2]), year, 18)
        name = clean(cells[3])
        hq = clean(cells[4]).split(",")[0]
        km = re.search(r"([\d.]+)", clean(cells[7]))
        w = winners.get(rnd)
        status = "final" if w and w["name"] else ("live" if start <= now.timestamp() * 1000 <= end else "pre")
        rid = "wrc-%d-%d" % (year, rnd)
        races.append({
            "id": rid, "name": name, "round": rnd, "oneday": True, "start": start, "end": end,
            "surface": clean(cells[5]), "hq": hq,
            "stages": [{
                "id": rid, "n": rnd, "label": "Round %d" % rnd, "label_es": "Ronda %d" % rnd, "start": start, "end": end,
                "surface": clean(cells[5]), "surface_es": SURFACE_ES.get(clean(cells[5]).lower(), clean(cells[5])),
                "date": datetime.fromtimestamp(start / 1000, timezone.utc).strftime("%Y-%m-%d") if start else "",
                "frm": hq, "to": None, "km": float(km.group(1)) if km else None, "ss": clean(cells[6]),
                "status": status, "top": [{"name": w["name"], "team": w["team"]}] if w and w["name"] else [],
            }],
        })
    gc = []
    for cells in table_after(text, "===FIA World Rally Championship for Drivers==="):
        pos = clean(cells[0]) if cells else ""
        if not pos.isdigit() or len(cells) < 3:
            continue
        pts = next((clean(c) for c in reversed(cells) if re.fullmatch(r"\d+", clean(c))), "")
        gc.append({"pos": int(pos), "name": clean(cells[1]), "team": "", "gap": (pts + " pts") if pts else ""})
        if len(gc) >= GC_ROWS:
            break
    if not races:
        print("wrc: no calendar read", file=sys.stderr)
        sys.exit(0)
    json.dump({"updated": int(time.time() * 1000), "season": year, "races": races, "gc": gc},
              open(OUT, "w"), ensure_ascii=False, indent=1)
    print("wrc: %d, %d rallies, %d won, %d in standings" % (year, len(races), sum(1 for r in races if r["stages"][0]["top"]), len(gc)))


if __name__ == "__main__":
    main()
