import urllib.request, urllib.parse, re
UA = {"User-Agent": "OwnTVFanartBot/1.0 (https://github.com/carlosglcn/owntv-sports-data)"}
u = "https://en.wikipedia.org/w/index.php?" + urllib.parse.urlencode({"title": "2026 Davis Cup Finals", "action": "raw"})
s = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read().decode()
i = s.find("Great Britain vs Germany"); i = i if i >= 0 else s.find("team1=GBR")
print("GBR", s[max(0, i-300):i+2500])
j = s.find("omination"); print("NOM", s[max(0, j-200):j+3500])
