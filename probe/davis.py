import urllib.request, urllib.parse
UA = {"User-Agent": "OwnTVFanartBot/1.0 (https://github.com/carlosglcn/owntv-sports-data)"}
u = "https://en.wikipedia.org/w/index.php?" + urllib.parse.urlencode({"title": "2026 Davis Cup Finals", "action": "raw"})
s = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read().decode()
j = s.find("==Team nominations=="); k = s.find("\n==", j + 25)
print("NOM", s[j:min(k, j + 5000)])
