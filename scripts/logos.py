#!/usr/bin/env python3
"""Renders the ASOBAL clubs' SVG crests to small PNGs (the app reads PNGs), only the ones still missing."""
import os, re, subprocess, urllib.request

UA = {"User-Agent": "Mozilla/5.0"}
BASE = "https://www.asobal.es/"
OUT = "logos/asobal"


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


page = fetch(BASE + "liga/clasificacion/").decode("latin-1")
ids = sorted(set(re.findall(r"imagenes/jornada/club(\d+)\.svg", page)), key=int)
os.makedirs(OUT, exist_ok=True)
missing = [i for i in ids if not os.path.exists("%s/club%s.png" % (OUT, i))]
if missing:
    if subprocess.call("which rsvg-convert >/dev/null 2>&1", shell=True) != 0:
        subprocess.check_call("sudo apt-get install -y -qq librsvg2-bin >/dev/null", shell=True)
    for i in missing:
        svg = "%s/club%s.svg" % (OUT, i)
        open(svg, "wb").write(fetch(BASE + "imagenes/jornada/club%s.svg" % i))
        subprocess.check_call(["rsvg-convert", "-h", "160", "-a", "-f", "png", "-o", "%s/club%s.png" % (OUT, i), svg])
        os.remove(svg)
        print("logo", i)
