import runpy, json, sys
sys.argv = ["davis"]
runpy.run_path("probe/davis_build.py", run_name="__main__")
d = json.load(open("davis.json"))
print(json.dumps(d, ensure_ascii=False)[:6000])
