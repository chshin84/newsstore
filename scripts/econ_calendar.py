"""무료 경제캘린더 API 테스트 — 컨센서스(forecast)/실제(actual)/이전(previous) 제공?"""
import json, time
import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
T = 45

def show(name, ok, msg):
    print(f"\n{'='*68}\n{name}\n{'='*68}\n  {('✓' if ok else '✗')} {msg}")

# 1) TradingView 공개 경제캘린더 (키 불필요)
try:
    h = {"User-Agent": UA, "Origin": "https://www.tradingview.com",
         "Referer": "https://www.tradingview.com/"}
    url = ("https://economic-calendar.tradingview.com/events"
           "?from=2026-06-10T00:00:00.000Z&to=2026-06-13T00:00:00.000Z&countries=US")
    r = requests.get(url, headers=h, timeout=T)
    data = r.json()
    evs = data.get("result", [])
    show("1) TradingView 경제캘린더 (무료/무키)", r.status_code == 200 and bool(evs),
         f"status={r.status_code} 이벤트={len(evs)}")
    for e in evs[:6]:
        print(f"      · {e.get('title','')[:42]:<42} "
              f"actual={e.get('actual')} forecast={e.get('forecast')} prev={e.get('previous')}")
except Exception as ex:
    show("1) TradingView 경제캘린더", False, f"FAIL {type(ex).__name__}: {ex}")
time.sleep(0.3)

# 2) FMP demo key
for u in ["https://financialmodelingprep.com/api/v3/economic_calendar?apikey=demo",
          "https://financialmodelingprep.com/stable/economic-calendar?apikey=demo"]:
    try:
        r = requests.get(u, headers={"User-Agent": UA}, timeout=T)
        body = r.text[:300]
        ok = r.status_code == 200 and r.text.strip().startswith("[")
        show(f"2) FMP demo: {u.split('?')[0].split('/')[-1]}", ok, f"status={r.status_code} {body[:200]}")
    except Exception as ex:
        show("2) FMP demo", False, f"FAIL {type(ex).__name__}")
    time.sleep(0.3)

# 3) TradingEconomics guest
try:
    u = "https://api.tradingeconomics.com/calendar?c=guest:guest&f=json"
    r = requests.get(u, headers={"User-Agent": UA}, timeout=T)
    show("3) TradingEconomics guest:guest", r.status_code == 200, f"status={r.status_code} {r.text[:220]}")
except Exception as ex:
    show("3) TradingEconomics guest", False, f"FAIL {type(ex).__name__}")
