import urllib.request, urllib.parse, re
UA = {"User-Agent": "OwnTVFanartBot/1.0 (https://github.com/carlosglcn/owntv-sports-data)"}
def raw(t):
    u = "https://en.wikipedia.org/w/index.php?" + urllib.parse.urlencode({"title": t, "action": "raw"})
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60) as r: return r.read().decode()
for t in ["2026 Davis Cup Finals", "2025 Davis Cup Finals"]:
    s = raw(t)
    print("#####", t, len(s))
    for m in re.finditer(r"^=+[^=\n]+=+\s*$", s, re.M): print("H", m.group(0))
    i = s.find("Quarterfinals")
    j = s.find("==", s.find("\n", s.find("==Quarterfinals") if "==Quarterfinals" in s else i))
    k = s.find("{{Davis Cup")
    print("TIE", s[k:k+3500] if k >= 0 else "no davis cup template")
    m = re.search(r"\{\{[^{}|]*[Tt]ie[^{}|]*\|", s); print("tpl", m.group(0) if m else None)
