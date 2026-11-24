#!/usr/bin/env python3
"""dakar.json: the Dakar Rally — each category (cars, bikes) as a stage race, in the shape of cycling.json.

  {"updated", "season", "races":[{id,name,names:{es},cat,oneday:false,start,end,
      stages:[{id,n,label,start,date,frm,to,km,status,top:[{name,team}],leader:{name,team}}],
      gc:[{pos,name,team,gap}]}]}

From the race centre of the official site (www.dakar.live.worldrallyraidchampionship.com), whose page reads the
same /api/<bind> files. The edition is the coming January's once it is published, the last one until then. A
stage already read is kept and not read again (its file is large) unless it is within a day of now.
"""
import json, os, sys, time, urllib.request
from datetime import datetime, timezone

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
API = "https://www.dakar.live.worldrallyraidchampionship.com/api/"
OUT = "dakar.json"
DAY = 24 * 3600 * 1000
TOP = 3
GC_ROWS = 30
# The categories shown, in order, with their names (the feed's own are singular and in four languages).
CATS = {"A": ("Cars", "Coches"), "M": ("Bikes", "Motos")}


def get(bind):
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(API + bind, headers=UA), timeout=90) as r:
                body = r.read().decode("utf-8", "replace")
                return json.loads(body) if body.strip() else None
        except Exception as e:
            if i == 2:
                print("dakar: failed", bind, e, file=sys.stderr)
                return None
            time.sleep(3)
        finally:
            time.sleep(0.8)


def ms(iso):
    try:
        return int(datetime.fromisoformat(iso).timestamp() * 1000)
    except Exception:
        return 0


def person(team):
    """The driver or rider (role P) — "Carlos Sainz" — and what they drive ("Ford · Raptor")."""
    comps = team.get("competitors") or []
    p = next((c for c in comps if isinstance(c, dict) and c.get("role") == "P"), comps[0] if comps and isinstance(comps[0], dict) else {})
    first = (p.get("firstName") or "").title()
    last = (p.get("lastName") or "").title()
    name = (first + " " + last).strip() or p.get("name") or "#%s" % team.get("bib")
    raw = (team.get("brand") or "").strip()
    brand = raw if len(raw) <= 4 else raw.title()   # KTM, BMW stay as they are; TOYOTA → Toyota
    return name, brand or (team.get("vehicle") or "").title()


def gap_text(rel):
    if not rel:
        return ""
    s = rel // 1000
    h, m, sec = s // 3600, s // 60 % 60, s % 60
    return "+%d:%02d:%02d" % (h, m, sec) if h else "+%d:%02d" % (m, sec)


def first(v):
    return v[0] if isinstance(v, list) and v else v


def edition():
    now = datetime.now(timezone.utc)
    year = now.year + (1 if now.month >= 9 else 0)
    for y in (year, year - 1):
        cats = get("category-%d" % y)
        if cats:
            return y, cats
    return year, []


def main():
    old = {}
    if os.path.exists(OUT):
        try:
            old = {r["id"]: r for r in json.load(open(OUT)).get("races", [])}
        except Exception:
            old = {}
    year, cats = edition()
    now = int(time.time() * 1000)
    races = []
    for cat in sorted(cats, key=lambda c: c.get("position", 9)):
        label = cat.get("label")
        if label not in CATS:
            continue
        rid = "dakar-%d-%s" % (year, label)
        kept = {s["n"]: s for s in old.get(rid, {}).get("stages", [])}
        stages_raw = sorted(get("stage-%d-%s" % (year, label)) or [], key=lambda s: s.get("stage", 0))
        stages, gc = [], old.get(rid, {}).get("gc", [])
        seen = set()
        for s in stages_raw:
            n = s.get("stage", 0)
            if n in seen or not (s.get("date") or s.get("sectors")):
                continue
            seen.add(n)
            special = sorted([x for x in s.get("sectors", []) if x.get("type") == "SPE"], key=lambda x: x.get("code", ""))
            start = ms(special[0]["startTime"]) if special else ms(s.get("date", ""))
            langs = {l.get("locale"): l.get("text") for l in s.get("stageLangs", [])}
            route = (langs.get("en") or "").split(">")
            stage = {
                "id": "%s-%d" % (rid, n), "n": n, "label": "Prologue" if n == 0 else "Stage %d" % n,
                "label_es": "Prólogo" if n == 0 else "Etapa %d" % n,
                "start": start, "date": (s.get("date") or "")[:10],
                "frm": route[0].strip().title() if route and route[0].strip() else None,
                "to": route[-1].strip().title() if len(route) > 1 else None,
                "km": sum(x.get("length", 0) for x in special) or s.get("length"),
                "marathon": bool(s.get("marathon")), "cancelled": bool(s.get("isCancelled")),
                "status": "pre", "top": [], "leader": None,
            }
            done = kept.get(n)
            fresh = abs(now - start) < DAY or start <= now < start + 2 * DAY
            if done and done.get("status") == "final" and not fresh:
                stage.update({k: done[k] for k in ("status", "top", "leader") if k in done})
                stages.append(stage)
                continue
            if start and start <= now + 3600 * 1000:
                scores = get("lastScore-%d-%s-%d" % (year, label, n)) or []
                ranked = [x for x in scores if isinstance(x, dict) and first((x.get("ce") or {}).get("position"))]
                ranked.sort(key=lambda x: first(x["ce"]["position"]))
                if ranked:
                    stage["top"] = [dict(zip(("name", "team"), person(x["team"]))) for x in ranked[:TOP]]
                    stage["status"] = "final" if now > start + 14 * 3600 * 1000 else "live"
                    key = "%02dASS" % n if n else "0PASS"
                    general = [x for x in scores if isinstance(x, dict) and first(((x.get("cg") or {}).get(key) or {}).get("position"))]
                    general.sort(key=lambda x: first(x["cg"][key]["position"]))
                    if general:
                        stage["leader"] = dict(zip(("name", "team"), person(general[0]["team"])))
                        gc = []
                        for x in general[:GC_ROWS]:
                            g = x["cg"][key]
                            name, team = person(x["team"])
                            gc.append({"pos": first(g["position"]), "name": name, "team": team,
                                       "gap": gap_text(first(g.get("relative"))) if first(g["position"]) > 1 else ""})
                elif now > start:
                    stage["status"] = "live"
            stages.append(stage)
        if not stages:
            continue
        en, es = CATS[label]
        races.append({
            "id": rid, "name": "Dakar %d · %s" % (year, en), "names": {"es": "Dakar %d · %s" % (year, es)},
            "cat": label, "oneday": False,
            "start": min(s["start"] for s in stages if s["start"]) if any(s["start"] for s in stages) else 0,
            "end": max(s["start"] for s in stages), "stages": stages, "gc": gc,
        })
    if not races and old:
        print("dakar: nothing read, the last file stays", file=sys.stderr)
        return
    json.dump({"updated": now, "season": year, "races": races}, open(OUT, "w"), ensure_ascii=False, indent=1)
    print("dakar: %d %s, %s" % (year, len(races), [(r["cat"], len(r["stages"]), sum(1 for s in r["stages"] if s["top"])) for r in races]))


if __name__ == "__main__":
    main()
