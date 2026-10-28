import re, sys, urllib.request, ssl
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36","Accept-Language":"en"}
urls=[l.strip() for l in open("probe/urls.txt") if l.strip() and not l.startswith("#")]
API=re.compile(r"""https?://[^"'\s<>\\)]*(?:api|json|feed|graphql|sportdata|widget)[^"'\s<>\\)]*""",re.I)
REL=re.compile(r"""["'](/[^"'\s<>]*(?:api|json|sportdata)[^"'\s<>]*)["']""",re.I)
for u in urls:
    try:
        r=urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=25)
        b=r.read(); t=b.decode("utf-8","replace")
        print("\n=== %s -> %s %s %d bytes"%(u,r.status,r.headers.get("content-type"),len(b)))
        print("HEAD:",re.sub(r"\s+"," ",t[:400]))
        found=sorted(set(API.findall(t)))[:40]+sorted(set(REL.findall(t)))[:30]
        for f in found: print("  ~",f[:200])
        if "__NEXT_DATA__" in t: print("  NEXT_DATA present")
    except Exception as e:
        print("\n=== %s -> ERR %s"%(u,e))
