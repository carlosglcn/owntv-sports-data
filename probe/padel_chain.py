import re, json, urllib.request, urllib.parse, http.cookiejar, os
os.makedirs("probe/raw", exist_ok=True)
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
out = []
def get(u, data=None, extra=None):
    h = dict(UA); h.update(extra or {})
    r = op.open(urllib.request.Request(u, data=data, headers=h), timeout=40); return r.read().decode("utf-8", "replace")
page = get("https://www.padelfip.com/events/kuwait-major-2026/")
nonce = re.search(r'var padelfip_ajax\s*=\s*\{[^}]*"nonce":"([0-9a-f]+)"', page).group(1)
pid = re.search(r'data-post-id="(\d+)"', page).group(1)
out.append("nonce %s pid %s" % (nonce, pid))
# main.js preflight for a fresh nonce
mj = re.search(r'src="([^"]*assets/js/main[^"]*\.js[^"]*)"', page)
if mj:
    js = get(mj.group(1)); open("probe/raw/fip_main.js", "w").write(js)
    out.append("main.js actions: %s" % sorted(set(re.findall(r"action['\"]?\s*:\s*['\"]([a-z_]+)", js))))
for action in ("livescore_tab_load",):
    try:
        res = get("https://www.padelfip.com/wp-admin/admin-ajax.php",
                  urllib.parse.urlencode({"action": action, "security": nonce, "post_id": pid}).encode(),
                  {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "X-Requested-With": "XMLHttpRequest",
                   "Referer": "https://www.padelfip.com/events/kuwait-major-2026/", "Origin": "https://www.padelfip.com"})
        open("probe/raw/fip_ls.json", "w").write(res)
        out.append("%s -> %d bytes %s" % (action, len(res), res[:300]))
        urls = sorted(set(re.findall(r'(https?:\\?/\\?/widget\.matchscorerlive\.com[^"\'\s<>]*)', res)))
        out.append("widgets: %s" % urls[:10])
        for k, u in enumerate(urls[:3]):
            u = u.replace("\\/", "/")
            try:
                w = get(u); open("probe/raw/msl_%d.html" % k, "w").write(w); out.append("widget %s -> %d" % (u, len(w)))
            except Exception as e: out.append("widget %s ERR %s" % (u, e))
    except Exception as e:
        out.append("%s ERR %s" % (action, e))
open("probe/padel.txt", "w").write("\n".join(out))
