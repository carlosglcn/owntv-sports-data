import re, urllib.request
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36", "Accept": "*/*"}
def get(u, h=None):
    with urllib.request.urlopen(urllib.request.Request(u, headers=h or UA), timeout=40) as r:
        return r.read().decode("utf-8", "replace")
js = get("https://www.daviscup.com/_next/static/chunks/6610-2a3d81ef2789c43f.js")
print("len", len(js))
for m in re.finditer(r'api\.itf-production\.sports-data\.stadion\.io', js):
    print("--", js[max(0, m.start()-600):m.start()+1200])
for m in sorted(set(re.findall(r'`[^`]{0,40}/(?:v\d|public|tennis|draws|ties|events|matches)[^`]{0,160}`', js)))[:60]: print("  tpl", m)
for m in sorted(set(re.findall(r'"/[a-zA-Z]+/[a-zA-Z/{}$.]{3,100}"', js)))[:80]: print("  path", m)
