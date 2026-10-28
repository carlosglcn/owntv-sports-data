import json, urllib.request, urllib.parse, os
UA={"User-Agent":"OwnTVFanartBot/1.0 (https://github.com/carlosglcn/owntv-sports-data)"}
os.makedirs("probe/raw",exist_ok=True)
def get(u,h=None):
    hh=dict(UA); hh.update(h or {})
    r=urllib.request.urlopen(urllib.request.Request(u,headers=hh),timeout=30); return r.status,r.headers.get("content-type"),r.read()
out=[]
for tour in ("atp","wta"):
    try:
        st,ct,b=get("https://site.api.espn.com/apis/site/v2/sports/tennis/%s/rankings"%tour)
        open("probe/raw/espn_rank_%s.json"%tour,"wb").write(b); out.append("rank %s %s %d"%(tour,st,len(b)))
    except Exception as e: out.append("rank %s ERR %s"%(tour,e))
for u in ["https://www.atptour.com/-/media/alias/player-headshot/A0E2","https://a.espncdn.com/i/headshots/tennis/players/full/3782.png",
          "https://commons.wikimedia.org/wiki/Special:FilePath/Carlos%20Alcaraz%202023.jpg?width=300"]:
    try: st,ct,b=get(u); out.append("img %s %s %s %d"%(u,st,ct,len(b)))
    except Exception as e: out.append("img %s ERR %s"%(u,e))
q='''SELECT ?p ?name ?img ?atp ?wta WHERE { VALUES ?name {"Carlos Alcaraz"@en "Iga Świątek"@en "Jannik Sinner"@en "Aryna Sabalenka"@en}
 ?p rdfs:label ?name; wdt:P106 wd:Q10833314. OPTIONAL{?p wdt:P18 ?img} OPTIONAL{?p wdt:P536 ?atp} OPTIONAL{?p wdt:P597 ?wta} }'''
try:
    st,ct,b=get("https://query.wikidata.org/sparql?format=json&query="+urllib.parse.quote(q),{"Accept":"application/sparql-results+json"})
    out.append("wd %s %s"%(st,b.decode()[:1500]))
except Exception as e: out.append("wd ERR %s"%e)
open("probe/tennis.txt","w").write("\n".join(out))
