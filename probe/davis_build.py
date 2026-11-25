#!/usr/bin/env python3
"""davis.json: the Davis Cup Finals (Final 8), in the shape of the team-league files (acb.json…) read by the app's
BasketDataSource — each tie one match between two nations, its score the rubbers won, with the rubbers themselves.

  {"updated", "season", "teams":[{id,name,short,abbr,logo,country,nation}],
   "matches":[{id,home,away,start,hs,as,status,stage,stage_es,venue,
               rubbers:[{label,label_es,p1:[..],p2:[..],s1:[..],s2:[..],winner}]}]}

From the English Wikipedia article "<year> Davis Cup Finals" (its "Davis Cup Finals box" per tie), which follows
the results within the hour; the official site's data service turns automated reads away. Start times are the
official schedule's, by day and order, as the article only gives the day.
"""
import json, re, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

UA = {"User-Agent": "OwnTVFanartBot/1.0 (https://github.com/carlosglcn/owntv-sports-data)"}
OUT = "davis.json"
ROME = ZoneInfo("Europe/Rome")
FLAG = "https://flagcdn.com/w320/%s.png"
# The official order of play (CET), by day; ties of the same day in the article's order. Unknown days: 16:00.
TIMES = {
    "2026-11-24": ["16:00"], "2026-11-25": ["16:00"], "2026-11-26": ["10:00", "17:00"],
    "2026-11-27": ["16:00"], "2026-11-28": ["12:00"], "2026-11-29": ["15:00"],
}
DEFAULT_TIME = "16:00"
STAGES = {"quarterfinals": ("Quarterfinal", "Cuartos de final"), "semifinals": ("Semifinal", "Semifinal"),
          "final": ("Final", "Final")}
RUBBERS = [("Singles 1", "Individual 1"), ("Singles 2", "Individual 2"), ("Doubles", "Dobles"),
           ("Singles 3", "Individual 3"), ("Singles 4", "Individual 4")]
# Davis Cup / IOC codes → ISO 3166-1 alpha-2 (flags and the country's name in the viewer's language).
ISO2 = {
    "ARG": "ar", "AUS": "au", "AUT": "at", "BEL": "be", "BIH": "ba", "BLR": "by", "BOL": "bo", "BRA": "br",
    "BUL": "bg", "CAN": "ca", "CHI": "cl", "CHN": "cn", "COL": "co", "CRO": "hr", "CZE": "cz", "DEN": "dk",
    "ECU": "ec", "EGY": "eg", "ESP": "es", "EST": "ee", "FIN": "fi", "FRA": "fr", "GBR": "gb", "GEO": "ge",
    "GER": "de", "GRE": "gr", "HUN": "hu", "IND": "in", "IRL": "ie", "ISR": "il", "ITA": "it", "JPN": "jp",
    "KAZ": "kz", "KOR": "kr", "LAT": "lv", "LTU": "lt", "MAR": "ma", "MEX": "mx", "MDA": "md", "NED": "nl",
    "NOR": "no", "NZL": "nz", "PAK": "pk", "PER": "pe", "POL": "pl", "POR": "pt", "ROU": "ro", "RSA": "za",
    "RUS": "ru", "SRB": "rs", "SLO": "si", "SUI": "ch", "SVK": "sk", "SWE": "se", "TPE": "tw", "TUN": "tn",
    "TUR": "tr", "UKR": "ua", "URU": "uy", "USA": "us", "UZB": "uz", "VEN": "ve",
}
NAMES = {
    "ARG": "Argentina", "AUS": "Australia", "AUT": "Austria", "BEL": "Belgium", "BRA": "Brazil", "CAN": "Canada",
    "CHI": "Chile", "CHN": "China", "COL": "Colombia", "CRO": "Croatia", "CZE": "Czechia", "DEN": "Denmark",
    "ESP": "Spain", "FIN": "Finland", "FRA": "France", "GBR": "Great Britain", "GER": "Germany", "GRE": "Greece",
    "HUN": "Hungary", "IND": "India", "ITA": "Italy", "JPN": "Japan", "KAZ": "Kazakhstan", "KOR": "South Korea",
    "NED": "Netherlands", "NOR": "Norway", "NZL": "New Zealand", "POL": "Poland", "POR": "Portugal",
    "SRB": "Serbia", "SUI": "Switzerland", "SVK": "Slovakia", "SWE": "Sweden", "USA": "United States",
}


def raw(title):
    url = "https://en.wikipedia.org/w/index.php?" + urllib.parse.urlencode({"title": title, "action": "raw"})
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def unlink(s):
    s = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", s, flags=re.S)
    s = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"\{\{(?:flagicon|davis)[^{}]*\}\}", "", s)
    return re.sub(r"'''?|&nbsp;", "", s).strip()


def fields(box):
    """The box's |key=value lines (a value may hold a whole {{TennisMatch…}})."""
    out, depth, key, buf = {}, 0, None, []
    for line in box.split("\n"):
        m = re.match(r"\|\s*([A-Za-z0-9_]+)\s*=(.*)", line) if depth == 0 else None
        if m:
            if key:
                out[key] = "\n".join(buf).strip()
            key, buf = m.group(1), [m.group(2)]
        elif key:
            buf.append(line)
        depth += line.count("{{") - line.count("}}")
        depth = max(depth, 0)
    if key:
        out[key] = "\n".join(buf).strip()
    return out


def games(token):
    m = re.match(r"\s*(\d+)", token)
    return int(m.group(1)) if m else None


def rubber(text, n):
    """One {{TennisMatch3|T1P1=…|6|7|…|T2P1=…|3|6|…}}: the players and sets of each side, and who won."""
    inner = unlink(re.sub(r"^\{\{\s*TennisMatch\d\s*\|?|\}\}\s*$", "", text.strip()))
    sides = {1: {"p": [], "s": []}, 2: {"p": [], "s": []}}
    cur = None
    for tok in inner.split("|"):
        m = re.match(r"\s*T([12])P\d\s*=(.*)", tok)
        if m:
            cur = int(m.group(1))
            name = m.group(2).strip()
            if name:
                sides[cur]["p"].append(name)
            continue
        if cur is None or "=" in tok:
            continue
        g = games(tok)
        if g is not None:
            sides[cur]["s"].append(g)
    if not sides[1]["p"] or not sides[2]["p"]:
        return None
    sets = list(zip(sides[1]["s"], sides[2]["s"]))
    won1 = sum(1 for a, b in sets if a > b and (a >= 6 or b >= 6 or a == 1))
    won2 = sum(1 for a, b in sets if b > a and (a >= 6 or b >= 6 or b == 1))
    winner = 1 if won1 >= 2 else 2 if won2 >= 2 else None
    label, label_es = RUBBERS[min(n, len(RUBBERS) - 1)]
    return {"label": label, "label_es": label_es, "p1": sides[1]["p"], "p2": sides[2]["p"],
            "s1": sides[1]["s"], "s2": sides[2]["s"], "winner": winner}


def start_ms(date_text, order):
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", date_text)
    if not m:
        return 0
    day = datetime.strptime(" ".join(m.groups()), "%d %B %Y")
    key = day.strftime("%Y-%m-%d")
    slots = TIMES.get(key, [])
    hh, mm = map(int, (slots[order] if order < len(slots) else DEFAULT_TIME).split(":"))
    return int(day.replace(hour=hh, minute=mm, tzinfo=ROME).timestamp() * 1000), key


def main():
    now = datetime.now(timezone.utc)
    year = now.year if now.month >= 6 else now.year - 1
    try:
        text = raw("%d Davis Cup Finals" % year)
    except Exception as e:
        print("davis: article failed: %s" % e, file=sys.stderr)
        sys.exit(0)
    teams, matches, per_day = {}, [], {}
    stage = ("Tie", "Eliminatoria")
    for m in re.finditer(r"^===\s*([^=\n]+?)\s*===\s*$|\{\{Davis Cup Finals box(.*?)\n\}\}", text, re.M | re.S):
        if m.group(1):
            stage = STAGES.get(m.group(1).strip().lower(), stage)
            continue
        f = fields(m.group(2))
        t1, t2 = unlink(f.get("team1", "")).upper(), unlink(f.get("team2", "")).upper()
        if t1 not in ISO2 or t2 not in ISO2:
            continue
        day_text = f.get("date", "")
        dkey = re.sub(r"<ref.*", "", day_text, flags=re.S)
        order = per_day.get(dkey, 0)
        per_day[dkey] = order + 1
        got = start_ms(dkey, order)
        if not got:
            continue
        start, _ = got
        for code in (t1, t2):
            teams[code] = {"id": code, "name": NAMES.get(code, code), "short": NAMES.get(code, code), "abbr": code,
                           "logo": FLAG % ISO2[code], "country": ISO2[code].upper(), "nation": ISO2[code].upper()}
        rubbers = [r for r in (rubber(f[k], i) for i, k in enumerate(sorted(k for k in f if re.fullmatch(r"R\d", k)))) if r]
        s1 = sum(1 for r in rubbers if r["winner"] == 1)
        s2 = sum(1 for r in rubbers if r["winner"] == 2)
        need = 2 if len(rubbers) <= 3 else 3
        playing = any((r["s1"] or r["s2"]) and not r["winner"] for r in rubbers)
        now_ms = now.timestamp() * 1000
        if max(s1, s2) >= need:
            status = "final"
        elif playing or (s1 + s2 > 0) or start <= now_ms:
            status = "live" if now_ms < start + 12 * 3600 * 1000 else "final"
        else:
            status = "scheduled"
        matches.append({
            "id": "davis-%d-%s-%s" % (year, t1, t2), "home": t1, "away": t2, "start": start,
            "hs": s1 if status != "scheduled" else None, "as": s2 if status != "scheduled" else None,
            "status": status, "stage": stage[0], "stage_es": stage[1],
            "venue": unlink(f.get("venue", "")), "rubbers": rubbers,
        })
    if not matches:
        print("davis: no ties read", file=sys.stderr)
        sys.exit(0)
    json.dump({"updated": int(time.time() * 1000), "season": year, "teams": list(teams.values()), "matches": matches},
              open(OUT, "w"), ensure_ascii=False, indent=1)
    print("davis: %d, %d ties: %s" % (year, len(matches), [(x["home"], x["away"], x["hs"], x["as"], x["status"]) for x in matches]))


if __name__ == "__main__":
    main()
