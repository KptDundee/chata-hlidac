#!/usr/bin/env python3
"""Hlídač chaty: čte Solar Guardian (EPEVER cloud) a posílá upozornění přes ntfy."""
import base64
import hashlib
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

API_BASE = "https://hncloudapi.epsolarpv.com/usrCloud"
DISPATCH = "https://hncomm.epsolarpv.com:7100/"
APP_ID = "po246089zkljagiusdgq"
DEVICE_NO = "05070616093TM23Y-00076"  # brána regulátoru XTRA-N
TZ = ZoneInfo("Europe/Prague")
DATA_FILE = "data.enc"
KEEP_DETAIL_DAYS = 14

CONFIG_FILE = "nastaveni.txt"
DASHBOARD = "https://kptdundee.github.io/chata-hlidac/"
DEFAULTS = {
    "sirka": 50.08, "delka": 14.42,
    "nabito": True,
    "panely_nevyrabi": True, "panely_min_W": 5, "panely_rezerva_min": 45, "panely_po_dobu_min": 30,
    "baterie_slabne_V": 12.2, "baterie_slabne_reset_V": 12.5,
    "baterie_kriticka_V": 12.0, "baterie_kriticka_reset_V": 12.2,
    "odpojeni_V": 11.6, "odpojeni_reset_V": 12.8,
    "regulator_offline_min": 120, "vecerni_souhrn_hodina": 20,
    "predpoved_noc": True, "nabijeni_od_vychodu_min": 90,
    "kapacita_Ah": 200, "noc_spotreba_W": 30, "menic_vlastni_W": 6,
    "zasuvka_menic": "", "zasuvky_river": "172, 190, 165", "zasuvka_generator": "115",
    "river_auto": True, "river_auto_ip": "157", "river_auto_pv_on": 150, "river_auto_pv_off": 100,
    "river_auto_v_off": 12.5, "river_auto_off_min": 20,
    "brana_hlidat": True, "brana_ticho_min": 60, "telefon_baterie_pod": 15,
    "river_vymenit": True, "river_vymenit_pod": 15, "river_nabita": True,
}

POINTS = {  # klíč: (dataPointId, itemId)
    "pv_w": (101415607, "34"),
    "bat_v": (101415576, "3"),
    "bat_a": (101415595, "22"),
    "bat_soc": (101415615, "42"),
    "bat_t": (101415605, "32"),
    "status": (101415639, "66"),
    "day_kwh": (101415577, "4"),
    "min_v": (101415632, "59"),
    "max_v": (101415625, "52"),
    "month_kwh": (101415599, "26"),
    "total_kwh": (101415619, "46"),
}
STATUS = {0: "nenabíjí", 1: "Float (nabito)", 2: "Boost (nabíjí)", 3: "Equalize"}


def post(url, body, headers):
    h = {"Content-Type": "application/json", "Accept": "*/*", "AppId": APP_ID,
         "languageType": "1", "usr-source": "usr-web"}
    h.update(headers)
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode() or "{}")


def find_token(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k.lower() == "token" and isinstance(v, str) and v:
                return v
        for v in o.values():
            t = find_token(v)
            if t:
                return t
    return None


def login(account, password):
    body = {"account": account, "password": hashlib.md5(password.encode()).hexdigest(), "isPhone": 0}
    for path in ("/user/login", "/Login/loginByPassword"):
        d = post(API_BASE + path, body, {})
        if d.get("status") == 0 and find_token(d.get("data")):
            return find_token(d.get("data"))
    raise SystemExit(f"Přihlášení selhalo: status={d.get('status')} info={d.get('info')}")


def dev_server(token):
    d = post(DISPATCH + "device/getDevServerAddr", {"type": 3, "deviceNos": [DEVICE_NO]}, {"token": token})
    srv = (d.get("data", d) or {}).get("devServer") or []
    if not srv:
        raise SystemExit(f"Dispatch selhal: {str(d)[:200]}")
    url = srv[0]["url"]
    return (url if url.startswith("http") else "https://" + url).rstrip("/")


HIST_URLS = ("https://hncloudapi.epsolarpv.com:7002",)   # odtud čte historii web Solar Guardian


def history(token, dp_id, start, end, base=None):
    """Historie jednoho údaje (po ~10 min) za období [start, end) jako [(ms, float), ...]."""
    out, offset, page = [], 0, 1000
    urls = ([base] if base else []) + list(HIST_URLS)
    fmt_dt = lambda t: t.strftime("%Y-%m-%d %H:%M:%S")
    while True:
        body = {"devDatapoints": [{"deviceNo": DEVICE_NO, "dataPointId": dp_id}],
                "start": int(start.timestamp() * 1000), "end": int(end.timestamp() * 1000) - 1,
                "startDt": fmt_dt(start), "endDt": fmt_dt(end - timedelta(seconds=1)),
                "limit": page, "row": page, "offset": offset, "timeSort": "asc"}
        d, err = None, None
        for u in urls:
            try:
                d = post(u + "/history/getDatapointHistory0", body, {"token": token})
                if d.get("status") == 0:
                    break
            except Exception as e:
                err = e
                d = None
        if not d or d.get("status") != 0:
            raise RuntimeError(f"historie {dp_id}: {err or str(d)[:150]}")
        items = d.get("data") or []
        if isinstance(items, dict):
            items = items.get("list") or items.get("rows") or []
        for it in items:
            try:
                out.append((int(it["time"]), float(it["value"])))
            except (KeyError, TypeError, ValueError):
                pass
        if len(items) < page or offset > 20000:
            return out
        offset += page


def night_window(date, cfg):
    """Noc končící ráno dne `date`: od západu (předchozí den) + 2 h (odezní povrchový náboj) do východu slunce."""
    _, set_prev = sun_times(cfg["sirka"], cfg["delka"], date - timedelta(days=1))
    rise, _ = sun_times(cfg["sirka"], cfg["delka"], date)
    if not rise or not set_prev:
        return None, None
    return set_prev + timedelta(hours=2), rise


def night_voltages(series, date, cfg):
    """series = [(unix_s, V)] → (V na začátku noci, V na konci noci) jako medián 30 min."""
    ts, te = night_window(date, cfg)
    if not ts:
        return None
    a, b = ts.timestamp(), te.timestamp()
    first = sorted(v for t, v in series if a <= t < a + 1800 and v > 5)
    last = sorted(v for t, v in series if b - 1800 <= t < b and v > 5)
    if not first or not last:
        return None
    return {"vs": round(first[len(first) // 2], 3), "ve": round(last[len(last) // 2], 3),
            "ts": int(a), "te": int(b)}


def import_history(token, data, st, now, cfg, budget_s=90):
    """Postupně (po měsících, odzadu) doplní denní výrobu, min/max napětí a noční napětí ze Solar Guardianu."""
    if not st.get("hist_v3"):              # nová verze importu (noc od západu + 2 h) → projít znovu
        st.update({"hist_v3": True, "hist_done": False, "hist_back": 0, "hist_empty": 0, "hist_err": 0})
        for d in data["days"].values():
            d.pop("nv", None)
            d.pop("h", None)
    if st.get("hist_done"):
        return
    t0 = time.time()
    first = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    back = st.get("hist_back", 0)          # kolik měsíců zpět už je hotovo
    empty = st.get("hist_empty", 0)
    while time.time() - t0 < budget_s:
        y, m = first.year, first.month - back
        while m <= 0:
            y, m = y - 1, m + 12
        start = first.replace(year=y, month=m)
        end = (start + timedelta(days=32)).replace(day=1)
        got = 0
        try:
            daily, vser = {}, []
            for key in ("day_kwh", "bat_v"):
                for ms, val in history(token, POINTS[key][0], start, end):
                    if key == "bat_v":
                        vser.append((ms / 1000, val))
                    dk = datetime.fromtimestamp(ms / 1000, TZ).strftime("%Y-%m-%d")
                    dd = daily.setdefault(dk, {})
                    if key == "day_kwh":
                        dd["solar_kwh"] = max(dd.get("solar_kwh", 0), val)
                    elif key == "bat_v" and val > 5:
                        dd["min_v"] = min(dd.get("min_v", 99), val)
                        dd["max_v"] = max(dd.get("max_v", 0), val)
                    got += 1
            for dk, dd in daily.items():
                day = data["days"].setdefault(dk, {})
                if "solar_kwh" in dd:
                    day["solar_kwh"] = round(max(day.get("solar_kwh", 0), dd["solar_kwh"]), 2)
                if "min_v" in dd:
                    day["min_v"] = round(min(day.get("min_v", 99), dd["min_v"]), 2)
                if "max_v" in dd:
                    day["max_v"] = round(max(day.get("max_v", 0), dd["max_v"]), 2)
            for dk in daily:
                nv = night_voltages(vser, datetime.strptime(dk, "%Y-%m-%d").date(), cfg)
                if nv:
                    data["days"][dk]["nv"] = nv
        except Exception as e:
            print("Import historie:", e)
            st["hist_err"] = st.get("hist_err", 0) + 1
            if st["hist_err"] >= 5:
                st["hist_done"] = True
            return
        print(f"Import historie {start:%Y-%m}: {got} hodnot")
        back += 1
        empty = empty + 1 if got == 0 else 0
        st["hist_back"], st["hist_empty"] = back, empty
        if empty >= 3 or back >= 60:       # 3 prázdné měsíce za sebou = dál už nic není
            st["hist_done"] = True
            print("Import historie hotový.")
            return


def read_values(token):
    hdr = {"token": token}
    d = post(DISPATCH + "device/getDevServerAddr", {"type": 3, "deviceNos": [DEVICE_NO]}, hdr)
    srv = (d.get("data", d) or {}).get("devServer") or []
    if not srv:
        raise SystemExit(f"Dispatch selhal: {str(d)[:200]}")
    url = srv[0]["url"]
    if not url.startswith("http"):
        url = "https://" + url
    pts = [{"deviceNo": DEVICE_NO, "slaveIndex": "1", "itemId": it, "dataPointId": dp} for dp, it in POINTS.values()]
    d = post(url.rstrip("/") + "/history/lastDatapoint", {"devDatapoints": pts}, hdr)
    if d.get("status") != 0:
        raise SystemExit(f"Čtení dat selhalo: {str(d)[:200]}")
    by_id = {i["dataPointId"]: i for i in d["data"]["list"]}
    out, newest = {}, 0
    for k, (dp, _) in POINTS.items():
        i = by_id.get(dp) or {}
        try:
            out[k] = float(i.get("value"))
        except (TypeError, ValueError):
            out[k] = None
        newest = max(newest, int(i.get("time") or 0))
    out["age_min"] = (time.time() * 1000 - newest) / 60000 if newest else None
    return out


EVENTS = []   # události tohoto běhu → data["log"] (deník do večerního souhrnu a na web)


def log(kind, text):
    """kind: 'ev' = událost / upozornění, 'auto' = automatika, 'err' = chyba."""
    EVENTS.append({"t": int(time.time()), "k": kind, "x": str(text)[:160]})


def flush_log(data):
    lg = data.setdefault("log", [])
    for e in EVENTS:
        if e["k"] == "err":          # opakovaná stejná chyba → jeden řádek s počtem
            key = e["x"][:40]
            prev = next((x for x in reversed(lg[-30:]) if x["k"] == "err" and x["x"][:40] == key), None)
            if prev and e["t"] - prev.get("t2", prev["t"]) < 45 * 60:
                prev["t2"], prev["n"], prev["x"] = e["t"], prev.get("n", 1) + 1, e["x"]
                continue
        lg.append(e)
    EVENTS.clear()
    cut = time.time() - 14 * 86400
    data["log"] = [x for x in lg if x.get("t2", x["t"]) >= cut][-600:]


def ntfy(topic, title, msg, prio=3, tags="", note=None):
    body = {"topic": topic, "title": title, "message": msg, "priority": prio}
    if tags:
        body["tags"] = tags.split(",")
    body["click"] = DASHBOARD  # ťuknutím se otevře přehled
    req = urllib.request.Request("https://ntfy.sh/", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    for attempt in range(3):
        try:
            urllib.request.urlopen(req, timeout=30).read()
            print("NTFY:", title, "|", msg)
            if "bar_chart" not in tags and "test" not in title:
                log("auto" if title.startswith("🔌") else "ev", note or title)
            return
        except Exception as e:  # výpadek ntfy nesmí shodit hlídače
            print("NTFY chyba:", e)
            time.sleep(5)
    log("err", f"Notifikace nedoručena: {title}")


def _key(passphrase, salt):
    return hashlib.pbkdf2_hmac("sha256", passphrase.encode(), salt, 200_000, 32)


def load_data(passphrase):
    if not os.path.exists(DATA_FILE):
        return {"state": {}, "points": [], "days": {}}
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    e = json.load(open(DATA_FILE))
    salt, iv, ct = (base64.b64decode(e[k]) for k in ("salt", "iv", "ct"))
    try:
        return json.loads(AESGCM(_key(passphrase, salt)).decrypt(iv, ct, None))
    except Exception:  # heslo DATA_KEY se změnilo -> začít novou historii
        print("Historii nejde odšifrovat (změněné DATA_KEY?) – začínám novou.")
        return {"state": {}, "points": [], "days": {}}


def save_data(passphrase, data):
    flush_log(data)
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    salt, iv = os.urandom(16), os.urandom(12)
    ct = AESGCM(_key(passphrase, salt)).encrypt(iv, json.dumps(data, separators=(",", ":")).encode(), None)
    b = lambda x: base64.b64encode(x).decode()
    json.dump({"v": 1, "salt": b(salt), "iv": b(iv), "ct": b(ct)}, open(DATA_FILE, "w"))


def record(data, v, now):
    """Uloží bod historie a denní souhrn."""
    ts = int(now.timestamp())
    p = {"t": ts}
    for k in ("bat_v", "bat_a", "bat_soc", "pv_w", "bat_t", "status"):
        if v.get(k) is not None:
            p[k] = round(v[k], 2)
    data["points"].append(p)
    cutoff = ts - KEEP_DETAIL_DAYS * 86400
    data["points"] = [x for x in data["points"] if x["t"] >= cutoff]
    day = data["days"].setdefault(now.strftime("%Y-%m-%d"), {})
    # Regulátor denní počítadla v noci nuluje (po setmění) → držet maximum / minimum za kalendářní den
    if v.get("day_kwh") is not None:
        day["solar_kwh"] = round(max(day.get("solar_kwh", 0), v["day_kwh"]), 2)
    lows = [x for x in (v.get("min_v"), v.get("bat_v")) if x]
    highs = [x for x in (v.get("max_v"), v.get("bat_v")) if x]
    if lows:
        day["min_v"] = round(min(lows + ([day["min_v"]] if "min_v" in day else [])), 2)
    if highs:
        day["max_v"] = round(max(highs + ([day["max_v"]] if "max_v" in day else [])), 2)
    # ať upozornění i souhrn pracují s denními hodnotami, ne s vynulovaným počítadlem
    v["day_kwh"], v["min_v"], v["max_v"] = day.get("solar_kwh"), day.get("min_v"), day.get("max_v")
    if v.get("bat_soc") is not None:
        day["soc_min"] = min(day.get("soc_min", 999), v["bat_soc"])
    data["updated"] = ts


def load_config(path=CONFIG_FILE):
    """Načte nastaveni.txt (klíč = hodnota); chybné řádky ignoruje."""
    cfg = dict(DEFAULTS)
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except OSError:
        return cfg
    for ln in lines:
        ln = ln.split("#", 1)[0].strip()
        if "=" not in ln:
            continue
        k, val = (x.strip() for x in ln.split("=", 1))
        if k not in DEFAULTS:
            continue
        low = val.lower()
        if isinstance(DEFAULTS[k], bool):
            cfg[k] = low in ("zapnuto", "ano", "on", "true", "1")
        elif isinstance(DEFAULTS[k], str):
            cfg[k] = val
        elif low in ("vypnuto", "ne", "off"):
            cfg[k] = None
        else:
            try:
                cfg[k] = float(val.replace(",", "."))
            except ValueError:
                print("Nastavení: neplatná hodnota", k, "=", val)
    return cfg


def sun_times(lat, lon, day):
    """Východ a západ slunce (NOAA) v místním čase; (None, None) při polárním dni/noci."""
    import math
    rad = math.radians
    n = day.timetuple().tm_yday
    out = []
    for rising in (True, False):
        t = n + ((6 if rising else 18) - lon / 15) / 24
        M = 0.9856 * t - 3.289
        L = (M + 1.916 * math.sin(rad(M)) + 0.020 * math.sin(rad(2 * M)) + 282.634) % 360
        RA = math.degrees(math.atan(0.91764 * math.tan(rad(L)))) % 360
        RA = (RA + (L // 90) * 90 - (RA // 90) * 90) / 15
        sd = 0.39782 * math.sin(rad(L))
        cd = math.cos(math.asin(sd))
        ch = (math.cos(rad(90.833)) - sd * math.sin(rad(lat))) / (cd * math.cos(rad(lat)))
        if abs(ch) > 1:
            return None, None
        H = (360 - math.degrees(math.acos(ch)) if rising else math.degrees(math.acos(ch))) / 15
        UT = (H + RA - 0.06571 * t - 6.622 - lon / 15) % 24
        base = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        out.append((base + timedelta(hours=UT)).astimezone(TZ))
    return out[0], out[1]


# Klidové napětí AGM 12 V -> stav nabití % (přibližně)
AGM_SOC = [(11.80, 0), (11.95, 10), (12.05, 20), (12.15, 30), (12.25, 40), (12.35, 50),
           (12.45, 60), (12.55, 70), (12.65, 80), (12.75, 90), (12.85, 100)]


def soc_from_v(v):
    if v <= AGM_SOC[0][0]:
        return 0.0
    for (v1, s1), (v2, s2) in zip(AGM_SOC, AGM_SOC[1:]):
        if v <= v2:
            return s1 + (s2 - s1) * (v - v1) / (v2 - v1)
    return 100.0


def battery_health(data, now, cfg):
    """Ukazatel zdraví baterie za noci: pokles napětí (mV) na 10 Ah odebraných z baterie.

    Noční napětí: z živých bodů (nebo z importu Solar Guardianu), odběr: ze zásuvky za měničem
    (živé body po 10 min, nebo hodinová historie ze zásuvky). Čím vyšší číslo, tím menší kapacita.
    """
    idle = cfg["menic_vlastni_W"] or 0
    hourly = data.get("plug_hourly", {})
    pts = data.get("points", [])
    for dk, day in data["days"].items():
        if "h" in day:
            continue
        date = datetime.strptime(dk, "%Y-%m-%d").date()
        ts, te = night_window(date, cfg)
        if not ts or te > now:
            continue
        a, b = ts.timestamp(), te.timestamp()
        nv = day.get("nv")
        if not nv:
            nv = night_voltages([(p["t"], p["bat_v"]) for p in pts if p.get("bat_v")], date, cfg)
        if not nv:
            continue
        # odběr ve W za měničem během noci
        ah, covered, src = 0.0, 0.0, None
        live = [p for p in pts if a <= p["t"] < b and p.get("mw", p.get("ac_w")) is not None]
        if len(live) * 600 >= 0.8 * (b - a):
            for p in live:
                ah += (p.get("mw", p.get("ac_w")) / 0.88 + idle) * (600 / 3600) / 12.3
            covered, src = len(live) * 600, "live"
        else:
            for t0 in range(int(a // 3600) * 3600, int(b), 3600):
                hk = datetime.fromtimestamp(t0, TZ)
                wh = (hourly.get(hk.strftime("%Y-%m-%d")) or [None] * 24)[hk.hour] if hk.strftime("%Y-%m-%d") in hourly else None
                if wh is None:
                    continue
                part = (min(t0 + 3600, b) - max(t0, a)) / 3600
                if part <= 0:
                    continue
                ah += (wh * part / 0.88 + idle * part) / 12.3
                covered += part * 3600
            src = "tapo"
        if covered < 0.8 * (b - a) or ah < 5:
            continue
        drop = (nv["vs"] - nv["ve"]) * 1000
        mv10 = drop / ah * 10
        day["h"] = {"mv10": round(mv10, 1), "ah": round(ah, 1), "vs": nv["vs"], "ve": nv["ve"], "src": src,
                    "cap": round(min(260, cfg["kapacita_Ah"] * 52 / mv10)) if mv10 > 5 else None}


def health_baseline(data):
    vals = [d["h"]["mv10"] for k, d in sorted(data["days"].items()) if "h" in d]
    if len(vals) < 7:
        return None, vals
    first = sorted(vals[:14])
    return first[len(first) // 2], vals


def forecast(data, now, cfg):
    """Vydrží baterie do rána? Výpočet z kapacity a očekávané noční spotřeby.

    Stav nabití se bere z napětí (vyhlazeně za posledních 30 min bez slunce),
    spotřeba z nastavení (průměr na výstupu měniče + vlastní spotřeba měniče).
    """
    rise, set_ = sun_times(cfg["sirka"], cfg["delka"], now.date())
    if not rise:
        return None
    if now >= rise and now < set_:          # přes den se nepočítá
        return None
    if now >= set_:
        rise, _ = sun_times(cfg["sirka"], cfg["delka"], (now + timedelta(days=1)).date())
    t_now = now.timestamp()
    pts = [p for p in data.get("points", []) if p["t"] >= t_now - 1800 and p.get("bat_v") is not None]
    if not pts:
        return None
    v = sum(p["bat_v"] for p in pts) / len(pts) + 0.05   # +0,05 V za pokles pod malou zátěží
    cap = cfg["kapacita_Ah"] or 200
    ac = cfg["noc_spotreba_W"] or 0
    measured = [p.get("mw", p.get("ac_w")) for p in data.get("points", [])
                if p.get("mw", p.get("ac_w")) is not None and p["t"] >= t_now - 3 * 3600 and (p.get("pv_w") or 0) < 5]
    if len(measured) >= 6:                       # aspoň hodina změřeného nočního odběru
        ac = sum(measured) / len(measured)
    draw = ac / 0.88 + (cfg["menic_vlastni_W"] or 0)   # W z baterie
    a = draw / 12.2                                                             # A z baterie
    until = rise + timedelta(minutes=cfg["nabijeni_od_vychodu_min"] or 0)
    hours = (until.timestamp() - t_now) / 3600
    soc_now = soc_from_v(v)
    soc_until = soc_now - a * hours / cap * 100
    f = {"until": int(until.timestamp()), "soc_now": round(soc_now), "soc_until": round(soc_until),
         "draw_w": round(draw), "ah_night": round(a * hours), "n": len(pts),
         "measured": len(measured) >= 6}
    for key, lim in (("t_crit", cfg["baterie_kriticka_V"]), ("t_off", cfg["odpojeni_V"])):
        if lim is None:
            continue
        ah_left = (soc_now - soc_from_v(lim)) / 100 * cap
        if ah_left <= 0:
            f[key] = int(t_now)
        elif a > 0 and ah_left / a < hours:
            f[key] = int(t_now + ah_left / a * 3600)
    # skutečný noční trend napětí (jen pro kontrolu, z doby po západu)
    night = [p for p in data.get("points", []) if p["t"] >= max(t_now - 3 * 3600, set_.timestamp() if now >= set_ else 0)
             and p.get("bat_v") is not None and (p.get("pv_w") or 0) < 5]
    if len(night) >= 6 and night[-1]["t"] - night[0]["t"] >= 3600:
        xs = [(p["t"] - t_now) / 3600 for p in night]
        ys = [p["bat_v"] for p in night]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        sxx = sum((x - mx) ** 2 for x in xs)
        if sxx:
            f["slope"] = round(sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx, 4)
    return f


def forecast_text(f):
    if not f:
        return None
    hm = lambda t: datetime.fromtimestamp(t, TZ).strftime("%H:%M")
    tail = f" (noc ~{f['ah_night']} Ah při ~{f['draw_w']} W)"
    if f.get("t_off"):
        return f"Do rána nevydrží: pod alarm ~{hm(f.get('t_crit', f['t_off']))}, měnič se vypne ~{hm(f['t_off'])}" + tail
    if f.get("t_crit"):
        return f"Do rána těsně: pod alarm kolem {hm(f['t_crit'])}" + tail
    return f"Do rána vydrží: teď ~{f['soc_now']} %, v {hm(f['until'])} ~{max(f['soc_until'], 0)} %" + tail


def fmt(x, d=0):
    return "?" if x is None else f"{x:.{d}f}".replace(".", ",")


def main():
    acc, pw, topic = os.environ["SG_ACCOUNT"], os.environ["SG_PASSWORD"], os.environ["NTFY_TOPIC"]
    key = os.environ["DATA_KEY"].strip()
    data = load_data(key)
    st = data.setdefault("state", {})
    now = datetime.now(TZ)
    cfg = load_config()
    rise, set_ = sun_times(cfg["sirka"], cfg["delka"], now.date())
    data["cfg"] = cfg
    data["sun"] = [int(rise.timestamp()), int(set_.timestamp())] if rise else None
    data["checked"] = int(now.timestamp())
    try:
        data["ver"] = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "VERSION")).read().strip()
    except OSError:
        data["ver"] = None
    rivers = read_ecoflow(data, st, now, topic, cfg)
    inv = read_inverter(data, topic, now, cfg)
    read_plug_history(data, topic)
    check_gateway(inv, st, now, topic, cfg)
    if inv and now.timestamp() - inv["t"] < 1200:   # alarm / vypnutí hlášené samotným měničem
        al = inv.get("al") if inv.get("al") not in ("0", "NONE", "No alarm") else None
        if al and st.get("inv_al") != al:
            ntfy(topic, "⚠️ Měnič hlásí alarm", f"Victron: {al} (stav {inv.get('st', '?')}), baterie {fmt(inv.get('v'), 2)} V.", 4, "warning")
        st["inv_al"] = al
    try:
        token = login(acc, pw)
        v = read_values(token)
    except (Exception, SystemExit) as e:  # výpadek cloudu: nespadnout, po ~2 h upozornit
        print("Chyba čtení cloudu:", e)
        log("err", f"Solar Guardian nejde přečíst: {str(e)[:100]}")
        note_run(data, now, sg=False, inv=inv)
        try:
            daily_summary(data, None, st, now, topic, cfg, rise, set_)
        except Exception as e2:
            print("Souhrn:", e2)
        st["err_n"] = st.get("err_n", 0) + 1
        if st["err_n"] == 12:
            ntfy(topic, "📡 Hlídač nemůže číst Solar Guardian", f"Už ~2 hodiny selhává čtení cloudu: {str(e)[:150]}", 4, "warning")
        save_data(key, data)
        return
    st["err_n"] = 0
    st["sg_ok"] = True
    data["last"] = {k: (round(x, 2) if isinstance(x, float) else x) for k, x in v.items()}
    if v.get("age_min") is not None and v["age_min"] <= cfg["regulator_offline_min"]:
        record(data, v, now)
        if inv and now.timestamp() - inv["t"] < 1200:
            pt = data["points"][-1]
            if inv.get("w") is not None:
                pt["ac_w"] = inv["w"]
            if inv.get("mw") is not None:
                pt["mw"] = inv["mw"]
            if (inv.get("gen") or {}).get("w") is not None:
                pt["gw"] = inv["gen"]["w"]
            if inv.get("v") is not None:            # napětí měřené měničem
                pt["iv"] = inv["v"]
            if inv.get("lw") is not None:           # odběr ve stejném okamžiku jako to napětí
                pt["lw"] = inv["lw"]
            plugs = {p["ip"]: p["w"] for p in inv.get("tp", []) if p.get("w") is not None and p.get("ip")}
            if plugs:
                pt["tp"] = plugs
            day = data["days"].setdefault(now.strftime("%Y-%m-%d"), {})
            names = data.setdefault("plug_names", {})
            for p in inv.get("tp", []):
                if p.get("ip") and p.get("n"):
                    names[p["ip"]] = p["n"]
                if p.get("ip") and p.get("wh") is not None:
                    dt = day.setdefault("tp", {})
                    dt[p["ip"]] = max(dt.get(p["ip"], 0), p["wh"])
        if rivers:
            data["points"][-1]["rv"] = [{"s": r.get("soc"), "i": r.get("in_w"), "o": r.get("out_w")} for r in rivers]
    try:
        import_history(token, data, st, now, cfg)
    except Exception as e:
        print("Import historie selhal:", e)
        log("err", f"Import historie Solar Guardian: {str(e)[:100]}")
    try:
        battery_health(data, now, cfg)
        base, vals = health_baseline(data)
        data["health_base"] = base
        if base and len(vals) >= 30:
            recent = sorted(vals[-14:])
            med = recent[len(recent) // 2]
            month = now.strftime("%Y-%m")
            if med > base * 1.2 and st.get("health_warned") != month:
                ntfy(topic, "🔋 Baterie možná ztrácí kapacitu",
                     f"V noci teď napětí klesá o {fmt(med, 0)} mV na 10 Ah, na začátku sledování {fmt(base, 0)} mV (+{fmt((med / base - 1) * 100, 0)} %).", 3, "battery")
                st["health_warned"] = month
    except Exception as e:
        print("Zdraví baterie:", e)
        log("err", f"Výpočet zdraví baterie: {str(e)[:100]}")
    data["forecast"] = forecast(data, now, cfg)
    st["_forecast"] = data["forecast"]
    st["_rivers"] = [{"name": r["name"], "soc": r.get("soc")} for r in (rivers or [])]
    note_run(data, now, sg=True, inv=inv)
    try:
        for name, fn in (("Kontrola upozornění", lambda: check(v, st, now, topic, cfg, rise, set_)),
                         ("Automatika River", lambda: river_auto(v, st, now, topic, cfg, rise, set_, data, inv)),
                         ("Večerní souhrn", lambda: daily_summary(data, v, st, now, topic, cfg, rise, set_))):
            try:
                fn()
            except Exception as e:          # chyba jedné části nesmí shodit ostatní
                print(name, "selhalo:", e)
                log("err", f"{name}: {type(e).__name__} {str(e)[:100]}")
    finally:
        save_data(key, data)


def send_cmd(topic, ip, on, reason):
    """Povel pro Flip (brána na chatě): zapnout / vypnout zásuvku Tapo."""
    body = json.dumps({"ip": str(ip), "on": bool(on), "id": int(time.time()), "why": reason})
    req = urllib.request.Request(f"https://ntfy.sh/{topic}-cmd", data=body.encode(),
                                 headers={"Title": "cmd", "Priority": "1"}, method="POST")
    try:
        urllib.request.urlopen(req, timeout=20).read()
        return True
    except Exception as e:
        log("err", f"Povel pro zásuvku .{ip} neodešel: {str(e)[:80]}")
        return False


def dur(sec):
    m = int(sec // 60)
    return f"{m // 60} h {m % 60:02d} min" if m >= 60 else f"{m} min"


def river_auto(v, st, now, topic, cfg, rise, set_, data, inv=None):
    """Automatické nabíjení River přebytkem ze slunce přes zásuvku za měničem."""
    ip = str(cfg.get("river_auto_ip") or "").strip()
    if not cfg.get("river_auto") or not ip:
        if st.get("ra_on"):              # automatika vypnutá v nastavení → zásuvku vypnout
            send_cmd(topic, ip or "157", False, "automatika vypnuta")
            st["ra_on"] = False
        data["river_auto"] = None
        return
    bv, pv = v.get("bat_v"), v.get("pv_w")
    status = int(v["status"]) if v.get("status") is not None else None
    stale = v.get("age_min") is None or v["age_min"] > cfg["regulator_offline_min"]
    on = bool(st.get("ra_on"))
    reason = None
    day = rise and set_ and rise <= now <= set_ - timedelta(minutes=30)
    if stale or bv is None or pv is None:
        if on:
            on, reason = False, "regulátor neposílá data"
    elif not on:
        if day and status == 1 and pv >= (cfg["river_auto_pv_on"] or 0) and bv >= (cfg["river_auto_v_off"] or 0) + 0.3:
            on, reason = True, f"baterie plná, panely {fmt(pv)} W"
    else:
        lowpv = pv < (cfg["river_auto_pv_off"] or 0)
        st["ra_low"] = (st.get("ra_low", 0) + 10) if lowpv else 0
        if bv < (cfg["river_auto_v_off"] or 0):
            on, reason = False, f"napětí klesla na {fmt(bv, 2)} V"
        elif st["ra_low"] >= (cfg["river_auto_off_min"] or 0):
            on, reason = False, f"panely jen {fmt(pv)} W"
        elif not day:
            on, reason = False, "blíží se západ slunce"
    if on:                          # počítat dobu nabíjení za den
        day_ = data["days"].setdefault(now.strftime("%Y-%m-%d"), {})
        day_["ra_min"] = day_.get("ra_min", 0) + 10
    if reason:
        send_cmd(topic, ip, on, reason)
        ran = f" (běželo {dur(now.timestamp() - st['ra_since'])})" if not on and st.get("ra_since") else ""
        ntfy(topic, "🔌 Nabíjení River zapnuto" if on else "🔌 Nabíjení River vypnuto",
             f"Zásuvka .{ip}: {reason}{ran}. Baterie {fmt(bv, 2)} V, panely {fmt(pv)} W.", 3, "electric_plug",
             note=f"🔌 River {'ZAP' if on else 'VYP'} – {reason}{ran} · {fmt(bv, 2)} V, {fmt(pv)} W")
        st["ra_chk"] = False
        st["ra_on"], st["ra_since"], st["ra_low"] = on, int(now.timestamp()), 0
    elif on and now.timestamp() - st.get("ra_sent", 0) > 3600:
        send_cmd(topic, ip, True, "trvá")       # jednou za hodinu připomenout (kdyby se povel ztratil)
        st["ra_sent"] = int(now.timestamp())
    if reason:
        st["ra_sent"] = int(now.timestamp())
    # ověřit, že zásuvka povel opravdu provedla (brána hlásí stav P100 "on")
    if inv and not reason and st.get("ra_since") and now.timestamp() - st["ra_since"] > 25 * 60 and now.timestamp() - inv["t"] < 1200:
        p = next((x for x in inv.get("tp", []) if x.get("ip") == ip), None)
        real = None if not p else (None if p.get("off") else (bool(p["on"]) if p.get("on") is not None else None))
        if real is not None and real != on and not st.get("ra_chk"):
            log("err", f"Zásuvka .{ip} je {'vypnutá' if on else 'zapnutá'}, ale automatika chce {'ZAP' if on else 'VYP'} – brána povel neprovedla?")
            st["ra_chk"] = True
        elif p and p.get("off") and on and not st.get("ra_chk"):
            log("err", f"Zásuvka .{ip} je nedostupná (bez napájení?) – River se nenabíjí")
            st["ra_chk"] = True
    data["river_auto"] = {"on": on, "since": st.get("ra_since"), "ip": ip, "why": reason or st.get("ra_why")}
    if reason:
        st["ra_why"] = reason
        data["river_auto"]["why"] = reason


def note_run(data, now, sg, inv):
    """Záznam o běhu hlídače: [čas, regulátor OK, brána čerstvá, napětí z Victronu]."""
    fresh = bool(inv) and now.timestamp() - inv["t"] < 1800
    runs = data.setdefault("runs", [])
    runs.append([int(now.timestamp()), int(sg), int(fresh), int(bool(fresh and inv.get("v")))])
    cut = now.timestamp() - 3 * 86400
    data["runs"] = [r for r in runs if r[0] >= cut]


def daily_summary(data, v, st, now, topic, cfg, rise, set_):
    """Večerní souhrn: čísla za den + deník (automatika, upozornění, chyby) + jak spolehlivě vše běželo."""
    h = cfg["vecerni_souhrn_hodina"]
    today = now.strftime("%Y-%m-%d")
    if h is None or now.hour < h or st.get("summary_day") == today:
        return
    flush_log(data)
    since = st.get("summary_ts") or int(now.timestamp()) - 86400
    since = max(since, int(now.timestamp()) - 36 * 3600)
    hm = lambda t: datetime.fromtimestamp(t, TZ).strftime("%H:%M")
    day = data["days"].get(today, {})
    v = v or data.get("last") or {}
    L = []
    # --- čísla ---
    full = next((e for e in data.get("log", []) if e["t"] >= since and e["x"].startswith("🔋 Baterie nabitá")), None)
    L.append(f"☀️ Výroba {fmt(day.get('solar_kwh'), 2)} kWh" + (f" · 100 % v {hm(full['t'])}" if full else " · 100 % nedosaženo"))
    pts = [p for p in data["points"] if p["t"] >= since and p.get("bat_v")]
    if pts:
        lo = min(pts, key=lambda p: p["bat_v"])
        hi = max(pts, key=lambda p: p["bat_v"])
        L.append(f"🔋 Teď {fmt(v.get('bat_v'), 2)} V ({fmt(v.get('bat_soc'))} %) · min {fmt(lo['bat_v'], 2)} V v {hm(lo['t'])} · max {fmt(hi['bat_v'], 2)} V")
    elif v.get("bat_v") is not None:
        L.append(f"🔋 Teď {fmt(v.get('bat_v'), 2)} V ({fmt(v.get('bat_soc'))} %)")
    inv = data.get("inverter") or {}
    names = data.get("plug_names", {})
    tp = day.get("tp", {})
    mip = inv.get("mip")
    if mip and tp.get(mip) is not None:
        extra = [f"{names.get(ip, '.' + ip)} {fmt(tp[ip] / 1000, 2)}" for ip in sorted(tp, key=lambda i: -tp[i])
                 if ip != mip and ip not in ips(cfg.get("zasuvky_river")) and ip != str(cfg.get("zasuvka_generator")) and tp[ip] > 20][:3]
        L.append(f"⚡ Ze solární baterie (měnič) {fmt(tp[mip] / 1000, 2)} kWh" + (f" · z toho {', '.join(extra)}" if extra else ""))
    rv = [tp[i] for i in ips(cfg.get("zasuvky_river")) if tp.get(i)]
    if rv and sum(rv) > 20:
        L.append(f"🔌 Z River {fmt(sum(rv) / 1000, 2)} kWh")
    g = tp.get(str(cfg.get("zasuvka_generator") or ""))
    if g and g > 20:
        L.append(f"⛽ Generátor dodal {fmt(g / 1000, 2)} kWh")
    if day.get("ra_min"):
        L.append(f"🔌 Nabíjení River ze slunce celkem {dur(day['ra_min'] * 60)}")
    for r in st.get("_rivers") or []:
        L.append(f"🔋 {r['name']}: {fmt(r.get('soc'))} %")
    ft = forecast_text(st.get("_forecast"))
    if ft:
        L.append(f"🌙 {ft}")
    # --- deník ---
    ev = [e for e in data.get("log", []) if e.get("t2", e["t"]) >= since]
    errs = [e for e in ev if e["k"] == "err"]
    rest = [e for e in ev if e["k"] != "err"]
    L.append("")
    if rest:
        L.append("Deník:")
        for e in rest[-20:]:
            L.append(f"{hm(e['t'])} {e['x']}")
        if len(rest) > 20:
            L.insert(len(L) - 20, f"(+ {len(rest) - 20} starších)")
    else:
        L.append("Deník: klid, nic se nedělo.")
    if errs:
        L.append("")
        L.append("⚠️ Chyby:")
        for e in errs[-10:]:
            n = e.get("n", 1)
            when = f"{hm(e['t'])}–{hm(e['t2'])}, {n}×" if n > 1 else hm(e["t"])
            L.append(f"{when}: {e['x']}")
    # --- spolehlivost ---
    runs = [r for r in data.get("runs", []) if r[0] >= since]
    if runs:
        exp = max(1, round((now.timestamp() - since) / 600))
        gap = max([b[0] - a[0] for a, b in zip(runs, runs[1:])] + [0]) / 60
        sg = sum(r[1] for r in runs) * 100 // len(runs)
        gw = sum(r[2] for r in runs) * 100 // len(runs)
        vi = sum(r[3] for r in runs) * 100 // len(runs)
        L.append("")
        L.append(f"Provoz: hlídač {len(runs)}/{exp} běhů" + (f" (nejdelší pauza {gap:.0f} min)" if gap > 30 else "")
                 + f" · regulátor {sg} % · brána {gw} % · Victron {vi} %")
    if rise:
        L.append(f"Slunce zítra cca {rise.strftime('%H:%M')}–{set_.strftime('%H:%M')}")
    ne = len(errs)
    title = "📊 Chata – souhrn dne" + (f" · ⚠️ {ne} {'chyba' if ne == 1 else 'chyby' if ne < 5 else 'chyb'}" if errs else " · bez chyb")
    msg = "\n".join(L)
    if len(msg.encode()) > 3900:
        msg = msg.encode()[:3900].decode(errors="ignore") + "…"
    ntfy(topic, title, msg, 3 if errs else 2, "bar_chart")
    st["summary_day"] = today
    st["summary_ts"] = int(now.timestamp())


def ips(txt):
    import re
    return [x for x in re.split(r"[,;\s]+", str(txt or "")) if x]


def read_inverter(data, topic, now, cfg=None):
    """Poslední zpráva z ESP32 u měniče (posílá do ntfy tématu <NTFY_TOPIC>-menic každých 10 min).

    Formát zprávy: JSON {"w": průměr VA, "max": max VA, "v": napětí baterie, "st": stav, "al": alarm}.
    """
    url = f"https://ntfy.sh/{topic}-menic/json?poll=1&since=12h"
    try:
        lines = urllib.request.urlopen(url, timeout=20).read().decode().strip().splitlines()
    except Exception as e:
        print("Měnič (ntfy):", e)
        return None
    last = None
    for ln in lines:
        try:
            m = json.loads(ln)
            if m.get("event") == "message":
                last = m
        except ValueError:
            pass
    if not last:
        return None
    try:
        body = json.loads(last.get("message") or "{}")
    except ValueError:
        return None
    inv = {"t": int(last.get("time") or now.timestamp())}
    try:
        if float(body.get("lw", -1)) >= 0:
            inv["lw"] = round(float(body["lw"]), 1)
    except (TypeError, ValueError):
        pass
    if isinstance(body.get("age"), (int, float)):
        inv["age"] = int(body["age"])
    for k in ("w", "max", "v"):
        try:
            x = float(body[k])
            if x >= 0 and (k != "v" or x > 5):   # -1 / 0 = měnič zatím nic nevyslal
                inv[k] = round(x, 2)
        except (KeyError, TypeError, ValueError):
            pass
    ph = body.get("ph")
    if isinstance(ph, dict) and ph.get("b") is not None and ph["b"] >= 0:
        inv["ph"] = {"b": ph.get("b"), "c": ph.get("c"), "t": ph.get("t")}
    tp = body.get("tp")
    if isinstance(tp, list):
        inv["tp"] = [{k: p.get(k) for k in ("n", "w", "wh", "on", "err", "ip", "off", "nm") if p.get(k) is not None}
                     for p in tp if isinstance(p, dict)][:12]
    if body.get("av"):
        inv["av"] = str(body["av"])[:12]       # verze aplikace na Flipu
    for k in ("st", "al"):
        if body.get(k) not in (None, ""):
            inv[k] = str(body[k])[:40]
    # Spotřeba ze zásuvek Tapo (skutečné W): za měničem (solární baterie) + na River (zimní provoz).
    # Victron měří VA (u malých zátěží víc) – necháme ho pro informaci.
    cfg = cfg or DEFAULTS
    by_ip = {p.get("ip"): p for p in inv.get("tp", []) if p.get("ip")}
    menic = by_ip.get(str(cfg.get("zasuvka_menic") or "").strip())
    if not menic:                        # záloha: podle názvu
        import re
        menic = next((p for p in inv.get("tp", []) if re.search(r"m[eě]ni[cč]|inverter|220|230", str(p.get("n", "")), re.I)), None)
    rivers = [by_ip[i] for i in ips(cfg.get("zasuvky_river")) if i in by_ip]
    gen = by_ip.get(str(cfg.get("zasuvka_generator") or "").strip())
    if menic and menic.get("w") is not None:
        if "w" in inv:
            inv["va"] = inv["w"]
        inv["mw"] = menic["w"]           # odběr ze solární baterie (přes měnič)
        inv["mip"] = menic.get("ip")
        inv["w"], inv["src"] = menic["w"], "tapo"
    rw = [p["w"] for p in rivers if p.get("w") is not None]
    if rw:
        inv["rw"] = round(sum(rw), 1)    # odběr z River (zimní provoz)
        inv["w"] = round((inv.get("mw") or 0) + inv["rw"], 1)
        inv["src"] = "tapo"
    if gen and (gen.get("w") is not None or gen.get("wh") is not None):
        inv["gen"] = {"w": gen.get("w"), "wh": gen.get("wh"), "off": gen.get("off")}
    if "w" not in inv and not inv.get("tp") and "ph" not in inv:
        return None
    data["inverter"] = inv
    print(f"Měnič: {fmt(inv.get('w'))} W (max {fmt(inv.get('max'))}), {fmt(inv.get('v'), 2)} V, {inv.get('st', '')}")
    return inv


def read_plug_history(data, topic):
    """Hodinová spotřeba zásuvky za měničem, kterou jednou denně pošle Flip: {"d": {"YYYY-MM-DD": [24× Wh]}}."""
    try:
        lines = urllib.request.urlopen(f"https://ntfy.sh/{topic}-menic-hist/json?poll=1&since=12h", timeout=20).read().decode().splitlines()
    except Exception as e:
        print("Historie zásuvky (ntfy):", e)
        return
    hourly = data.setdefault("plug_hourly", {})
    n = 0
    for ln in lines:
        try:
            m = json.loads(ln)
            if m.get("event") != "message":
                continue
            body = json.loads(m.get("message") or "{}")
        except ValueError:
            continue
        for dk, arr in (body.get("d") or {}).items():
            if isinstance(arr, list) and len(arr) == 24:
                hourly[dk] = [None if x is None or x < 0 else x for x in arr]
                n += 1
    for dk in sorted(hourly)[:-400]:
        hourly.pop(dk)
    if n:
        print(f"Historie zásuvky: {n} dní")


def check_gateway(inv, st, now, topic, cfg):
    """Brána na chatě (telefon / ESP32): mlčí? má telefon vybitou baterii?"""
    if inv:
        st["gw_seen"] = True
    fresh = bool(inv) and now.timestamp() - inv["t"] < 1800
    if st.get("gw_fresh") is not None and fresh != st["gw_fresh"]:
        if not cfg["brana_hlidat"]:
            log("ev", "Brána (Flip) zase posílá data" if fresh else "Brána (Flip) přestala posílat data")
    st["gw_fresh"] = fresh
    if not cfg["brana_hlidat"] or not st.get("gw_seen"):
        return
    age = (now.timestamp() - inv["t"]) / 60 if inv else 99999
    lim = cfg["brana_ticho_min"] or 60
    if age > lim and not st.get("gw_silent"):
        ntfy(topic, "📵 Brána na chatě neposílá data",
             f"Telefon u měniče se neozval {'přes 12 h' if age > 700 else f'{age:.0f} min'}. Vybitý, vypnutá Wi-Fi, nebo ho Android uspal?", 4, "warning")
        st["gw_silent"] = True
    if age <= lim:
        if st.get("gw_silent"):
            ntfy(topic, "📱 Brána na chatě zase posílá", "Data z telefonu u měniče znovu chodí.", 2, "white_check_mark")
        st["gw_silent"] = False
    ph = (inv or {}).get("ph")
    low = cfg["telefon_baterie_pod"]
    if ph and low is not None and age <= lim:
        b = ph.get("b")
        if b is not None and b <= low and not ph.get("c") and not st.get("ph_low"):
            ntfy(topic, f"🪫 Telefon na chatě má {b:.0f} %", "Brána brzy přestane posílat data – dobij ho (nebo zkontroluj nabíječku / zásuvku).", 4, "battery,warning")
            st["ph_low"] = True
        if b is not None and (b > low + 10 or ph.get("c")):
            st["ph_low"] = False


def read_ecoflow(data, st, now, topic, cfg):
    """Načte River 2 Pro z EcoFlow API (jen když jsou nastavené klíče) a pohlídá je."""
    ak = os.environ.get("ECOFLOW_ACCESS_KEY", "").strip()
    sk = os.environ.get("ECOFLOW_SECRET_KEY", "").strip()
    if not (ak and sk):
        return None
    try:
        import ecoflow
        host, rivers = ecoflow.read_rivers(ak, sk, st.get("eco_host"))
    except Exception as e:
        print("Chyba EcoFlow:", e)
        log("err", f"EcoFlow nejde přečíst: {str(e)[:100]}")
        st["eco_err"] = st.get("eco_err", 0) + 1
        if st["eco_err"] == 12:
            ntfy(topic, "📡 Hlídač nemůže číst EcoFlow", f"Už ~2 hodiny selhává čtení EcoFlow: {str(e)[:150]}", 3, "warning")
        return None
    st["eco_err"] = 0
    st["eco_host"] = host
    data["rivers"] = rivers
    data["rivers_t"] = int(now.timestamp())
    for r in rivers:
        print(f"EcoFlow {r['name']}: {fmt(r.get('soc'))} %, vstup {fmt(r.get('in_w'))} W, výstup {fmt(r.get('out_w'))} W"
              + ("" if r["online"] else " (offline)"))
        check_river(r, st, topic, cfg)
    return rivers


def check_river(r, st, topic, cfg):
    soc, k = r.get("soc"), "rv_" + str(r["sn"])[-6:]
    if soc is None or not r["online"]:
        return
    name = r["name"]
    io = f"{name}: {fmt(soc)} %, nabíjení {fmt(r.get('in_w'))} W, odběr {fmt(r.get('out_w'))} W"
    # Skoro vybitá -> vyměnit
    lim = cfg["river_vymenit_pod"]
    if cfg["river_vymenit"] and lim is not None:
        if soc <= lim and not st.get(k + "_low"):
            mins = r.get("dsg_min")
            rest = f" Zbývá asi {fmt(mins / 60, 1)} h." if mins and mins < 6000 else ""
            ntfy(topic, f"🔄 Vyměň River ({fmt(soc)} %)", f"{io}.{rest}\nPřepoj spotřebiče na druhou River a tuhle nabij.", 4, "battery,warning")
            st[k + "_low"] = True
        if soc > lim + 10:
            st[k + "_low"] = False
    # Nabitá při nabíjení (generátor) -> vypnout generátor
    charging = (r.get("in_w") or 0) > 20
    if cfg["river_nabita"]:
        if soc >= 100 and (charging or st.get(k + "_chg")) and not st.get(k + "_full"):
            ntfy(topic, f"⛽ {name} nabitá na 100 %", f"Můžeš vypnout generátor (nebo přepojit nabíjení na druhou River).\n{io}", 4, "fuelpump,white_check_mark")
            st[k + "_full"] = True
        if soc < 95:
            st[k + "_full"] = False
    st[k + "_chg"] = charging


def check(v, st, now, topic, cfg, rise, set_):
    bv, status = v["bat_v"], int(v["status"]) if v["status"] is not None else None
    pv = v["pv_w"]
    line = (f"Baterie {fmt(bv, 2)} V, {fmt(v['bat_soc'])} %, panely {fmt(pv)} W, "
            f"{STATUS.get(status, status)}, dnes {fmt(v['day_kwh'], 2)} kWh")
    print(now.isoformat(), line, f"(stáří dat {v['age_min']:.0f} min)" if v["age_min"] is not None else "")
    hm = lambda d: d.strftime("%H:%M")

    if os.environ.get("TEST") == "1":
        ntfy(topic, "🔔 Hlídač chaty – test", line, 3, "white_check_mark")

    # Regulátor offline
    stale = v["age_min"] is None or v["age_min"] > cfg["regulator_offline_min"]
    if stale and not st.get("stale"):
        ntfy(topic, "📡 Regulátor neposílá data", f"Poslední data z cloudu před {v['age_min'] or 0:.0f} min. Zkontroluj Wi‑Fi modul / internet.", 4, "warning")
    st["stale"] = stale
    if stale or bv is None:
        return

    # Baterie na 100 % (fáze Float, 2 kontroly po sobě)
    st["float_n"] = min(st.get("float_n", 0) + 1, 2) if status == 1 else 0
    if cfg["nabito"] and st["float_n"] >= 2 and not st.get("full_sent"):
        ntfy(topic, "🔋 Baterie nabitá na 100 %", f"Regulátor přešel do Float. Můžeš zapojit náročnější spotřebič (nabíjení apod.).\n{line}", 4, "battery,sunny")
        st["full_sent"] = True
    if status != 1 and bv < 13.2:  # další „nabito“ až po vybití pod Boost Recovery 13,2 V
        st["full_sent"] = False

    # Panely nevyrábí za denního světla
    if cfg["panely_nevyrabi"] and rise and pv is not None:
        m = timedelta(minutes=cfg["panely_rezerva_min"] or 0)
        daylight = rise + m <= now <= set_ - m
        full = status == 1 or bv >= 13.5  # plná baterie => regulátor sám omezí výkon
        if daylight and pv < (cfg["panely_min_W"] or 0) and not full:
            st.setdefault("pv_low_since", int(now.timestamp()))
            low_min = (now.timestamp() - st["pv_low_since"]) / 60
            if low_min >= (cfg["panely_po_dobu_min"] or 0) - 1 and not st.get("pv_sent"):
                ntfy(topic, "🌥 Panely nevyrábí",
                     f"Už {low_min:.0f} min jen {fmt(pv)} W, i když je den (slunce dnes {hm(rise)}–{hm(set_)}). "
                     f"Sníh, zastínění, nebo vypadlý kabel?\n{line}", 4, "warning")
                st["pv_sent"] = True
        else:
            st.pop("pv_low_since", None)
            if st.get("pv_sent") and pv >= max(20, (cfg["panely_min_W"] or 0) * 4):
                ntfy(topic, "☀️ Panely zase vyrábí", line, 2, "sunny")
                st["pv_sent"] = False
        if now > set_:
            st["pv_sent"] = False

    # Nízké napětí (2 kontroly po sobě, s hysterezí); posílá se jen nejhorší úroveň
    levels = (
        ("off", "odpojeni", "🔌 Měnič se vypíná – 230 V nejde",
         "Napětí pod {lim} V – měnič Victron (a výstup LOAD regulátoru) se vypíná kvůli ochraně baterie.", 5),
        ("crit", "baterie_kriticka", "🛑 Odpoj spotřebiče",
         "Napětí pod {lim} V – alarm regulátoru. Nevybíjej dál, přepni na EcoFlow.", 5),
        ("warn", "baterie_slabne", "⚠️ Solární baterie slábne",
         "Napětí pod {lim} V (~50 %). Šetři spotřebu.", 4),
    )
    worse = False
    for key, name, title, text, prio in levels:
        lim, reset = cfg[name + "_V"], cfg[name + "_reset_V"]
        if lim is None:
            continue
        st[key + "_n"] = min(st.get(key + "_n", 0) + 1, 2) if bv < lim else 0
        if st[key + "_n"] >= 2 and not st.get(key + "_sent"):
            if not worse:
                ntfy(topic, title, text.format(lim=fmt(lim, 2), reset=fmt(reset or lim, 2)) + "\n" + line, prio, "warning")
            st[key + "_sent"] = True
        if bv > (reset if reset is not None else lim):
            st[key + "_sent"] = False
        worse = worse or bool(st.get(key + "_sent"))

    # Předpověď do rána (jednou za noc)
    if cfg["predpoved_noc"] and set_:
        from_t = set_ + timedelta(hours=1)
        night = now >= from_t or (rise and now < rise)
        if not night:
            st["night_warned"] = False
        f = st.get("_forecast")
        if night and f and f.get("t_crit") and not st.get("night_warned"):
            ntfy(topic, "🌙 Baterie do rána nejspíš nevydrží",
                 f"{forecast_text(f)}.\nZvaž odpojení něčeho teď, nebo ráno počítej s EcoFlow.\n{line}", 4, "crescent_moon,warning")
            st["night_warned"] = True



if __name__ == "__main__":
    main()
