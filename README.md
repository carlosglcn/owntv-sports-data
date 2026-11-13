# owntv-sports-data

Basketball calendars, results and tables (Liga ACB, EuroLeague) for OwnTV Fanart.
`scripts/build.py` runs on GitHub every ten minutes and writes `acb.json` and `euroleague.json` (`scripts/basket.py` adds `eurocup.json`, `primerafeb.json` and `lega.json`);
the app reads them from `raw.githubusercontent.com`.
