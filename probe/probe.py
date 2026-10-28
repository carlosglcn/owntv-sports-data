import re, sys, json, urllib.request, urllib.parse
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36","Accept-Language":"en","Accept":"*/*"}
def get(u):
    r=urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=25); b=r.read()
    return r.status, r.headers.get("content-type"), b.decode("utf-8","replace")
for line in open("probe/urls.txt"):
    line=line.rstrip("\n")
    if not line.strip() or line.startswith("#"): continue
    mode,u,*arg=line.split(" ",2); arg=arg[0] if arg else ""
    try:
        st,ct,t=get(u)
        print("\n=== %s %s -> %s %s %d"%(mode,u,st,ct,len(t)))
        if mode=="SAVE":
            import os; os.makedirs("probe/raw",exist_ok=True); open("probe/raw/"+arg,"w").write(t); print("  saved",arg)
        elif mode=="BODY":
            print(re.sub(r"\s+"," ",t[:int(arg or 1500)]))
        elif mode=="GREP":
            seen=set()
            for m in re.finditer(arg,t,re.S):
                s=re.sub(r"\s+"," ",m.group(0))[:300]
                if s not in seen: seen.add(s); print("  ~",s)
                if len(seen)>=40: break
        elif mode=="JS":
            srcs=re.findall(r"""<script[^>]+src=["']([^"']+)["']""",t)+re.findall(r"""["'](/_nuxt/[^"']+\.js)["']""",t)
            pat=arg or r"""["'`][^"'`]*(?:api|Api)[^"'`]{2,120}["'`]"""
            seen=set()
            for s in dict.fromkeys(srcs):
                full=urllib.parse.urljoin(u,s)
                if any(x in full for x in ("google","jquery","recaptcha","gtag","cookie","minute-ly")): continue
                try: _,_,js=get(full)
                except Exception as e: print("  js ERR",full,e); continue
                for m in re.finditer(pat,js):
                    g=m.group(0)[:220]
                    if g not in seen: seen.add(g); print("  [%s] %s"%(full.rsplit('/',1)[-1][:30],g))
                    if len(seen)>=80: break
    except Exception as e:
        print("\n=== %s %s -> ERR %s"%(mode,u,e))
