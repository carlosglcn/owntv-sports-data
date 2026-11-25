import json, re, urllib.request, urllib.parse
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36", "Accept": "*/*"}
def get(u, h=None):
    with urllib.request.urlopen(urllib.request.Request(u, headers=h or UA), timeout=40) as r:
        return r.status, r.read().decode("utf-8", "replace")
def show(u, n=1500, pat=None):
    try:
        st, b = get(u)
        print("===", st, len(b), u)
        if pat:
            for m in sorted(set(re.findall(pat, b)))[:60]: print("   ", m[:200])
        else:
            print(b[:n])
    except Exception as ex:
        print("===", u, "ERR", ex)
show("https://www.daviscup.com/en/draws-results/finals/", pat=r'(?:https?:)?//[^"\'\s<>]*(?:api|json|feed)[^"\'\s<>]*')
show("https://www.daviscup.com/en/draws-results/finals/", n=0, pat=r'data-[a-z-]*(?:url|endpoint|api)[a-z-]*="[^"]*"')
show("https://www.daviscup.com/en/draws-results/finals/", n=0, pat=r'<script[^>]*src="[^"]+"')
show("https://api.sofascore.com/api/v1/search/unique-tournaments?q=davis%20cup", 1500)
show("https://api.sofascore.com/api/v1/sport/tennis/scheduled-events/2026-11-25", 0, pat=r'"uniqueTournament":\{"name":"[^"]+","slug":"[^"]+"[^}]{0,120}"id":\d+')
show("https://en.wikipedia.org/w/index.php?title=2026_Davis_Cup_Finals&action=raw", 3000)
show("https://en.wikipedia.org/w/index.php?title=2026_Davis_Cup&action=raw", 1200)
