"""Počasí (Open-Meteo, zdarma) a předpověď výroby panelů, která se učí z historie chaty.

Model: výroba za den = a · difúzní záření + b · přímé záření (součty za den, kWh/m², vodorovná rovina).
Koeficienty se počítají pro každý den zvlášť jen z podobné roční doby (± 30 dní, všechny roky),
takže se samy naučí, že v zimě přímé slunce na panely nedopadá (b ≈ 0) a vyrábí jen difúzní světlo.
Dny, kdy byla baterie brzy plná (Float) a regulátor výrobu přiškrtil, se do učení nepočítají.
Zpětná vazba: večerní předpověď na zítřek se druhý den porovná se skutečností a medián odchylek
za poslední 2 týdny opravuje další předpovědi (počasí z předpovědi ≠ skutečné počasí, špinavé panely, sníh…).
"""
import json
import math
import urllib.parse
import urllib.request
from datetime import date as Date, datetime, timedelta

FC_URL = "https://api.open-meteo.com/v1/forecast"
AR_URL = "https://archive-api.open-meteo.com/v1/archive"

WMO = {0: "jasno", 1: "skoro jasno", 2: "polojasno", 3: "zataženo", 45: "mlha", 48: "mlha",
       51: "mrholení", 53: "mrholení", 55: "mrholení", 56: "mrznoucí mrholení", 57: "mrznoucí mrholení",
       61: "slabý déšť", 63: "déšť", 65: "silný déšť", 66: "mrznoucí déšť", 67: "mrznoucí déšť",
       71: "slabé sněžení", 73: "sněžení", 75: "silné sněžení", 77: "sněhová zrna",
       80: "přeháňky", 81: "přeháňky", 82: "silné přeháňky", 85: "sněhové přeháňky", 86: "sněhové přeháňky",
       95: "bouřky", 96: "bouřky s krupobitím", 99: "bouřky s krupobitím"}


def _get(url, params, timeout=30):
    q = urllib.parse.urlencode(params)
    with urllib.request.urlopen(f"{url}?{q}", timeout=timeout) as r:
        return json.loads(r.read().decode())


def _daily_sums(js):
    """Hodinové W/m² (průměr za hodinu) → denní součty kWh/m²: {"YYYY-MM-DD": [globální, difúzní]}."""
    h = js.get("hourly") or {}
    out = {}
    for t, g, d in zip(h.get("time", []), h.get("shortwave_radiation", []), h.get("diffuse_radiation", [])):
        if g is None or d is None:
            continue
        s = out.setdefault(t[:10], [0.0, 0.0, 0])
        s[0] += g / 1000
        s[1] += d / 1000
        s[2] += 1
    return {k: [round(v[0], 3), round(v[1], 3)] for k, v in out.items() if v[2] >= 20}


def update_weather(data, cfg, now, log=print, budget_days=900):
    """Doplní skutečné počasí k dnům s výrobou (archiv) a stáhne předpověď na 7 dní."""
    wx = data.setdefault("wx", {})          # skutečné počasí: date → [G, D]
    lat, lon = cfg["sirka"], cfg["delka"]
    today = now.date()
    # 1) archiv (ERA5, zpoždění ~5 dní) – doplnit dny, které mají výrobu a nemají počasí
    need = sorted(k for k, d in data.get("days", {}).items()
                  if k not in wx and d.get("solar_kwh") is not None and k < (today - timedelta(days=6)).isoformat())
    if need:
        start = need[0]
        end = min(Date.fromisoformat(start) + timedelta(days=budget_days), today - timedelta(days=6)).isoformat()
        try:
            js = _get(AR_URL, {"latitude": lat, "longitude": lon, "start_date": start, "end_date": end,
                               "hourly": "shortwave_radiation,diffuse_radiation", "timezone": "Europe/Prague"}, 60)
            got = _daily_sums(js)
            wx.update(got)
            for k in need:                      # dny bez dat v archivu označit, ať se nestahují pořád dokola
                if start <= k <= end and k not in wx:
                    wx[k] = None
            log(f"Počasí – archiv {start}…{end}: {len(got)} dní")
        except Exception as e:
            log(f"Počasí – archiv selhal: {e}")
    # 2) předpověď + posledních 5 dní (analýza modelu jako „skutečnost“, než dorazí archiv)
    try:
        js = _get(FC_URL, {"latitude": lat, "longitude": lon, "past_days": 5, "forecast_days": 8,
                           "hourly": "shortwave_radiation,diffuse_radiation",
                           "daily": "weather_code,temperature_2m_max,temperature_2m_min",
                           "timezone": "Europe/Prague"})
        sums = _daily_sums(js)
        d = js.get("daily") or {}
        fc = {}
        for i, k in enumerate(d.get("time", [])):
            if k < today.isoformat():
                if k in sums and not wx.get(k):
                    wx[k] = sums[k]
                continue
            if k in sums:
                code = (d.get("weather_code") or [None] * 99)[i]
                fc[k] = {"g": sums[k][0], "d": sums[k][1], "code": code, "txt": WMO.get(code, ""),
                         "tmax": (d.get("temperature_2m_max") or [None] * 99)[i],
                         "tmin": (d.get("temperature_2m_min") or [None] * 99)[i]}
        if fc:
            data["wxf"] = fc
            data["wxf_t"] = int(now.timestamp())
    except Exception as e:
        log(f"Počasí – předpověď selhala: {e}")
        if data.get("wxf_t") and now.timestamp() - data["wxf_t"] > 2 * 86400:
            data["wxf"] = {}


def _doy_dist(a, b):
    x = abs(a.timetuple().tm_yday - b.timetuple().tm_yday)
    return min(x, 365 - x)


def training_rows(data, cfg, sun_times, target, today):
    """Dny použitelné k učení pro datum `target`: známé počasí, výroba, baterie nebyla brzy plná."""
    rows = []
    wx = data.get("wx", {})
    for k, day in data.get("days", {}).items():
        if k >= today.isoformat():
            continue
        w = wx.get(k)
        kwh = day.get("solar_kwh")
        if not w or kwh is None or w[0] < 0.02:
            continue
        dd = Date.fromisoformat(k)
        dist = _doy_dist(dd, target)
        if dist > 30:
            continue
        fl = day.get("fl")
        if fl is None:
            continue                            # nevíme, jestli byla plná → raději ne
        if fl:
            _, set_ = sun_times(cfg["sirka"], cfg["delka"], dd)
            if set_ and fl < set_.timestamp() - 5400:
                continue                        # plná dřív než 1,5 h před západem → výroba přiškrcená
        age = (target - dd).days / 365.0
        wgt = math.exp(-dist / 15) * (0.6 ** max(age, 0))
        rows.append((w[1], max(w[0] - w[1], 0.0), kwh, wgt))
    return rows


def fit(rows):
    """Vážené nejmenší čtverce kwh ≈ a·D + b·B (a, b ≥ 0). Vrací (a, b, n) nebo None."""
    if len(rows) < 6:
        return None
    sdd = sum(w * d * d for d, b, y, w in rows)
    sbb = sum(w * b * b for d, b, y, w in rows)
    sdb = sum(w * d * b for d, b, y, w in rows)
    sdy = sum(w * d * y for d, b, y, w in rows)
    sby = sum(w * b * y for d, b, y, w in rows)
    det = sdd * sbb - sdb * sdb
    a = b = None
    if det > 1e-9:
        a = (sdy * sbb - sby * sdb) / det
        b = (sby * sdd - sdy * sdb) / det
    if a is None or b < 0:                      # přímé slunce nepomáhá (zima, stín) → jen difúzní
        a, b = (sdy / sdd if sdd else 0.0), 0.0
    elif a < 0:                                 # jen přímé
        a, b = 0.0, (sby / sbb if sbb else 0.0)
    return max(a, 0.0), max(b, 0.0), len(rows)


def model_for(data, cfg, sun_times, target, today, cache):
    k = target.isoformat()
    if k not in cache:
        cache[k] = fit(training_rows(data, cfg, sun_times, target, today))
    return cache[k]


def bias(data, today):
    """Zpětná vazba: medián (skutečnost / předpověď) za posledních 14 vyhodnocených nepřiškrcených dnů."""
    log = data.get("fclog", {})
    r = [v["a"] / v["raw"] for k, v in sorted(log.items())
         if k < today.isoformat() and v.get("a") is not None and not v.get("cap") and v.get("raw", 0) > 0.05][-14:]
    if len(r) < 3:
        return 1.0, len(r)
    r.sort()
    return min(max(r[len(r) // 2], 0.6), 1.6), len(r)


def evaluate(data, cfg, sun_times, today):
    """Doplní ke včerejším (a starším) předpovědím skutečnost."""
    for k, v in data.get("fclog", {}).items():
        if k >= today.isoformat() or v.get("a") is not None:
            continue
        day = data.get("days", {}).get(k)
        if not day or day.get("solar_kwh") is None:
            continue
        v["a"] = day["solar_kwh"]
        fl = day.get("fl")
        if fl:
            _, set_ = sun_times(cfg["sirka"], cfg["delka"], Date.fromisoformat(k))
            v["cap"] = bool(set_ and fl < set_.timestamp() - 5400)
        else:
            v["cap"] = False
    # starší než 120 dní pryč
    cut = (today - timedelta(days=120)).isoformat()
    for k in [k for k in data.get("fclog", {}) if k < cut]:
        data["fclog"].pop(k)


def predict_days(data, cfg, sun_times, now):
    """Předpověď výroby (kWh) na dnes + 7 dní. Vrací list dictů."""
    fc = data.get("wxf") or {}
    today = now.date()
    cache = {}
    bf, bn = bias(data, today)
    out = []
    for k in sorted(fc):
        w = fc[k]
        dd = Date.fromisoformat(k)
        m = model_for(data, cfg, sun_times, dd, today, cache)
        if not m:
            continue
        a, b, n = m
        raw = a * w["d"] + b * max(w["g"] - w["d"], 0)
        out.append({"d": k, "raw": round(raw, 3), "kwh": round(raw * bf, 2), "txt": w.get("txt", ""),
                    "code": w.get("code"), "tmax": w.get("tmax"), "tmin": w.get("tmin"),
                    "a": round(a, 3), "b": round(b, 3), "n": n})
    return out, bf, bn


def remember_forecast(data, preds, now):
    """Večerní předpověď na zítřek si uložit (z ní se pak učí oprava)."""
    if now.hour < 18:
        return
    tomorrow = (now.date() + timedelta(days=1)).isoformat()
    p = next((x for x in preds if x["d"] == tomorrow), None)
    log = data.setdefault("fclog", {})
    if p and tomorrow not in log:
        log[tomorrow] = {"raw": p["raw"], "p": p["kwh"], "made": int(now.timestamp())}


def accuracy(data, today, n=14):
    """Přesnost za posledních n vyhodnocených dnů: list + medián absolutní chyby v %."""
    rows = [(k, v) for k, v in sorted(data.get("fclog", {}).items())
            if k < today.isoformat() and v.get("a") is not None and not v.get("cap")][-n:]
    errs = sorted(abs(v["a"] - v["p"]) / max(v["a"], 0.1) for k, v in rows)
    med = errs[len(errs) // 2] if errs else None
    return [{"d": k, "p": v["p"], "a": v["a"]} for k, v in rows], (round(med * 100) if med is not None else None)


def typical_kwh(data, cfg, sun_times, target, today):
    """Typická výroba pro tuto roční dobu (medián skutečné výroby ± 15 dní, všechny roky)."""
    v = sorted(d["solar_kwh"] for k, d in data.get("days", {}).items()
               if d.get("solar_kwh") is not None and k < today.isoformat()
               and _doy_dist(Date.fromisoformat(k), target) <= 15)
    return v[len(v) // 2] if len(v) >= 5 else None
