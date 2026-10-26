#!/usr/bin/env python3
"""Hlídač chaty: čte Solar Guardian (EPEVER cloud) a posílá upozornění přes ntfy."""
import base64
import hashlib
import json
import os
import sys
import time
import urllib.request

import chladnuti
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
    "regulator_offline_min": 30, "vecerni_souhrn_hodina": 20,
    "predpoved_noc": True, "nabijeni_od_vychodu_min": 90,
    "kapacita_Ah": 200, "noc_spotreba_W": 30, "menic_vlastni_W": 6, "desulfator_W": 0.25, "hash_upozornit": "50, 30", "lednice_hlidat": True, "lednice_ticho_h": 3, "lednice_bezi_h": 2,
    "mraz_hlidat": True, "mraz_C": 0, "mraz_hash": 40, "plne_nabiti_dni": 14,
    "teplomer_baterie": "", "teplomer_lednice": "", "lednice_max_C": 8,
    "teplomery": "", "teplomery_ticho_min": 60, "teplomery_baterie": "10, 5",
    "vlhkost_hlidat": "", "vlhkost_min": 35,
    "river_sn": "",
    "gen_rizeni": True, "gen_palivo": "benzin", "gen_max_benzin_W": 1800, "gen_max_lpg_W": 1600, "gen_rezerva_W": 100,
    "gen_po_behu_W": 200, "gen_mala_po_behu_W": 100, "gen_povel": "",
    "zasuvky_stale": "1, 4, 5, 9", "zasuvky_stale_min": 8,
    "zasuvka_flip": "9", "flip_nabijeni_rizeni": True, "flip_min_pct": 30, "zasuvka_router": "5", "router_nabijeni_rizeni": True, "chladnuti_teplomer": "Pokoj", "chladnuti_rano": "7:00", "chladnuti_noc_od": "0:00", "chladnuti_noc_do": "7:00", "chladnuti_cil_C": 21, "chladnuti_min_vecery": 5, "venku_sirka": 50.095, "venku_delka": 14.517, "flip_teplota_max_C": 40, "kabely_ubytek_V": 0.35, "kabely_odpor_mOhm": 20, "oprava_spoju": "2026-10-14 18:00", "nutne_river_v": "22:00", "den_do": "22:00",
    "den_kontrola": "po 7:00, út 5:30, st 7:00, čt 5:30, pá 7:00, so 8:00, ne 8:00",
    "zasuvka_menic": "", "zasuvky_river": "2, 3, 6", "river_noci_od": "2026-10-15", "zasuvka_generator": "7",
    "river_auto": True, "river_auto_ip": "8", "river_auto_pv_on": 150, "river_auto_pv_off": 100,
    "river_auto_v_off": 12.5, "river_auto_off_min": 20, "river_auto_v_drzet": 13.0, "river_auto_boost": True, "boost_V": 14.4, "float_V": 13.7, "odber_hlidat": True, "odber_z_baterie_A": 2.0, "odber_navic_W": 40, "lednice_max_W": 80, "river_auto_notifikace": False,
    "brana_hlidat": True, "brana_ticho_min": 60, "telefon_baterie_pod": 15, "telefon_upozornit": "50,30,20,10,0",
    "river_vymenit": True, "river_vymenit_pod": 15, "river_Wh": 768, "river_rezerva_pct": 5, "river_nabita": True,
    "zasuvka_lednice": "4", "ostatni_hlidat": True,
    "pocasi": True, "rezim": "auto", "zima_pripojit_od_V": 12.7, "zima_pripojit_do_V": 12.4,
    "sezona_upozornit": True,
    "panely_pocet": 2, "panel_Wp": 410, "pojistka_A": 30, "pojistka_rezerva": 1.0, "panely_doporucit": True,
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


NH_DAYS = 90          # rozbor nocí: kolik nocí zpět z historie Solar Guardianu


def night_history(token, data, st, now, cfg, budget_s=60):
    """Rozbor nocí z historie Solar Guardianu (napětí, proud, režim, panely, teplota) + hodinová spotřeba
    zásuvky za měničem z Tapo (plug_hourly). data["nh"][večer YYYY-MM-DD] = jedna noc (večer → ráno).
    Postupně po 10 dnech odzadu, nejvýš budget_s za běh; každý den doplní uplynulou noc."""
    nh = data.setdefault("nh", {})
    lat, lon = cfg["sirka"], cfg["delka"]
    idle = cfg.get("menic_vlastni_W") or 6
    today = now.date()
    # noc k je hotová, až je 2 h po východu dne k+1
    want = []
    for back in range(NH_DAYS, 0, -1):
        k = today - timedelta(days=back)
        r1, _ = sun_times(lat, lon, k + timedelta(days=1))
        if r1 and now >= r1 + timedelta(hours=2) and k.isoformat() not in nh:
            want.append(k)
    t0 = time.time()
    while want and time.time() - t0 < budget_s:
        chunk = [want.pop(0)]
        while want and want[0] == chunk[-1] + timedelta(days=1) and len(chunk) < 10:
            chunk.append(want.pop(0))
        start = datetime(chunk[0].year, chunk[0].month, chunk[0].day, tzinfo=TZ)
        end = datetime(chunk[-1].year, chunk[-1].month, chunk[-1].day, tzinfo=TZ) + timedelta(days=2)
        ser = {}
        try:
            for key in ("bat_v", "bat_a", "status", "pv_w", "bat_t"):
                ser[key] = [(ms / 1000, val) for ms, val in history(token, POINTS[key][0], start, end)]
        except Exception as e:
            print("Rozbor nocí (historie):", e)
            return
        for k in chunk:
            nh[k.isoformat()] = night_row(k, ser, data, lat, lon, idle)
        print(f"Rozbor nocí: {chunk[0]} – {chunk[-1]}")
    for kk in sorted(nh)[:-NH_DAYS - 10]:
        nh.pop(kk)


def night_row(k, ser, data, lat, lon, idle):
    rise, set_ = sun_times(lat, lon, k)
    r1, _ = sun_times(lat, lon, k + timedelta(days=1))
    if not (rise and set_ and r1):
        return {"x": 1}
    R, S, R1 = rise.timestamp(), set_.timestamp(), r1.timestamp()
    sel = lambda key, a, b: [(t, v) for t, v in ser.get(key, []) if a <= t < b]
    V = [(t, v) for t, v in sel("bat_v", S, R1 + 5400) if v > 5]
    if len(V) < 6:
        return {"x": 1}
    row = {"hrs": round((R1 - S) / 3600, 2)}
    v0 = sorted(v for t, v in V if S + 2700 <= t <= S + 4500)
    row["v0"] = round(v0[len(v0) // 2], 2) if v0 else None
    row["vmin"] = round(min(v for t, v in V), 2)
    ve = [v for t, v in V if R1 - 3600 <= t <= R1 + 900]
    row["ve"] = round(min(ve), 2) if ve else None
    # přes den: Ah z regulátoru, režimy
    A = sel("bat_a", R, S)
    ai = 0.0
    for (t1, a1), (t2, _) in zip(A, A[1:]):
        if a1 > 0:
            ai += a1 * min(t2 - t1, 1800) / 3600
    row["ai"] = round(ai, 1) if len(A) > 10 else None
    St = sel("status", R - 3600, S + 3600)
    row["fl"] = next((int(t) for t, v in St if int(v) == 1), 0) if St else None
    bm = 0
    for (t1, v1), (t2, _) in zip(St, St[1:]):
        if int(v1) == 2:
            bm += min(t2 - t1, 1800)
    row["bm"] = round(bm / 60) if St else None
    vmax = [v for t, v in sel("bat_v", R, S) if v > 5]
    row["vmax"] = round(max(vmax), 2) if vmax else None
    T = [v for t, v in sel("bat_t", S, R1) if -40 < v < 80]
    row["tn"] = round(min(T), 1) if T else None
    row["prod"] = (data.get("days", {}).get(k.isoformat()) or {}).get("solar_kwh")
    # spotřeba za měničem z hodinové historie Tapo (Wh) – noc a den
    ph = data.get("plug_hourly") or {}

    def wh(a, b):
        tot, cov, t = 0.0, 0.0, a
        while t < b:
            dt_ = datetime.fromtimestamp(t, TZ)
            hs = dt_.replace(minute=0, second=0, microsecond=0)
            he = hs + timedelta(hours=1)
            seg = min(b, he.timestamp()) - t
            arr = ph.get(hs.strftime("%Y-%m-%d"))
            if arr and arr[hs.hour] is not None:
                tot += arr[hs.hour] * seg / 3600
                cov += seg
            t += seg
        return tot if cov >= (b - a) * 0.8 else None
    nw, dw = wh(S, R1), wh(R, S)
    row["nwh"] = round(nw) if nw is not None else None
    row["dwh"] = round(dw) if dw is not None else None
    if nw is not None:
        row["nah"] = round((nw / 0.88 + idle * (R1 - S) / 3600) / 12.3, 1)        # z baterie přes noc
    if dw is not None and row["ai"] is not None:
        row["dnet"] = round(row["ai"] - (dw / 0.88 + idle * (S - R) / 3600) / 12.8, 1)   # čistě do baterie přes den
    return row


def day_yield(vals, rise, base0=None):
    """Výroba dne z počítadla regulátoru. Regulátor ho nenuluje o půlnoci (ráno ještě ukazuje včerejšek),
    takže: výroba = hodnota − základ; základ = poslední hodnota před východem slunce (nebo konec předchozího dne);
    když počítadlo spadne pod základ (vynulování), základ = 0. Před východem výroba 0.
    vals = [(t, kWh)] seřazené; vrací (kWh, poslední hodnota)."""
    base, prod, last = base0, 0.0, base0
    for t, r in vals:
        if rise is not None and t < rise:
            base = r
        else:
            if base is None:
                base = 0.0
            elif r < base - 0.01:
                base = 0.0
            prod = max(prod, r - base)
        last = r
    return round(prod, 2), last


def import_history(token, data, st, now, cfg, budget_s=90):
    """Postupně (po měsících, odzadu) doplní denní výrobu, min/max napětí a noční napětí ze Solar Guardianu."""
    if not st.get("hist_v8"):              # 3.87: výroba dne až od vynulování počítadla (ne včerejšek po půlnoci) → projít znovu
        st.update({"hist_v6": False, "hist_v8": True})
    if not st.get("hist_v7"):              # 3.47: min/max dne jen ze vzorků (bez okamžitých propadů regulátoru) → projít znovu
        st.update({"hist_v6": False, "hist_v7": True, "minmax_over": True})
    if not st.get("hist_v6"):              # nová verze importu (+ plná, nejnižší napětí, špička proudu) → projít znovu
        st.update({"hist_v3": True, "hist_v4": True, "hist_v5": True, "hist_v6": True, "hist_done": False, "hist_back": 0, "hist_empty": 0, "hist_err": 0})
        for d in data["days"].values():
            d.pop("nv", None)
            d.pop("h", None)
            if d.get("c") is False:
                d.pop("c")
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
            daily, vser, full = {}, [], {}
            for key in ("day_kwh", "bat_v", "bat_a", "status"):
                for ms, val in history(token, POINTS[key][0], start, end):
                    if key != "day_kwh":
                        full.setdefault(int(ms / 1000) // 60 * 60, {})[{"bat_v": "v", "bat_a": "a", "status": "s"}[key]] = val
                    if key in ("bat_a", "status"):
                        continue
                    if key == "bat_v":
                        vser.append((ms / 1000, val))
                    dk = datetime.fromtimestamp(ms / 1000, TZ).strftime("%Y-%m-%d")
                    dd = daily.setdefault(dk, {})
                    if key == "day_kwh":
                        dd.setdefault("dk", []).append((ms / 1000, val))
                    elif key == "bat_v" and val > 5:
                        if val < dd.get("min_v", 99):
                            dd["min_t"] = int(ms / 1000)
                        dd["min_v"] = min(dd.get("min_v", 99), val)
                        dd["max_v"] = max(dd.get("max_v", 0), val)
                    got += 1
            last_r = None
            for dk in sorted(daily):
                dd = daily[dk]
                if dd.get("dk"):
                    dt_ = datetime.strptime(dk, "%Y-%m-%d").date()
                    rs_ = sun_times(cfg["sirka"], cfg["delka"], dt_)[0]
                    dd["solar_kwh"], last_r = day_yield(sorted(dd["dk"]), rs_.timestamp() if rs_ else None, last_r)
            for dk, dd in daily.items():
                day = data["days"].setdefault(dk, {})
                if "solar_kwh" in dd and dk != now.strftime("%Y-%m-%d"):     # dnešek počítá record() průběžně
                    day["solar_kwh"] = dd["solar_kwh"]
                over = st.get("minmax_over") and dk != now.strftime("%Y-%m-%d")
                if "min_v" in dd:
                    if over or dd["min_v"] < day.get("min_v", 99):
                        day["min_t"] = dd.get("min_t")
                    day["min_v"] = round(dd["min_v"] if over else min(day.get("min_v", 99), dd["min_v"]), 2)
                if "max_v" in dd:
                    day["max_v"] = round(dd["max_v"] if over else max(day.get("max_v", 0), dd["max_v"]), 2)
            cser = [dict(t=t, **x) for t, x in sorted(full.items())]
            for x in cser:
                if x.get("s") is not None:
                    x["s"] = int(x["s"])
            lf = load_lookup(data, cfg)
            for dk in daily:
                date = datetime.strptime(dk, "%Y-%m-%d").date()
                nv = night_voltages(vser, date, cfg)
                if nv:
                    data["days"][dk]["nv"] = nv
                if "c" not in data["days"][dk] and date < now.date():
                    data["days"][dk]["c"] = charge_metric(cser, date, cfg, lf) or False
                if date < now.date():
                    a0 = datetime(date.year, date.month, date.day, tzinfo=TZ).timestamp()
                    dser = [x for x in cser if a0 <= x["t"] < a0 + 86400]
                    if any(x.get("s") is not None for x in dser):
                        data["days"][dk]["fl"] = next((x["t"] for x in dser if x.get("s") == 1), 0)
                    aa = [x["a"] for x in dser if x.get("a") is not None and x.get("s") != 1]
                    if aa:
                        data["days"][dk]["pa"] = round(max(aa), 1)
                    vv = [x["v"] for x in dser if x.get("v") and x["v"] > 5]
                    if vv:
                        data["days"][dk]["mp"] = round(min(vv), 2)
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
            st["minmax_over"] = False
            print("Import historie hotový.")
            return


def backfill_points(token, data, now, hours=3):
    """Doplní body historie mezi běhy hlídače (cron běží nepravidelně, v noci i po 30–40 min) z historie
    Solar Guardianu (~10 min) – graf napětí pak ukáže i skutečné minimum dne."""
    ts = int(now.timestamp())
    start = datetime.fromtimestamp(ts - hours * 3600, TZ).replace(second=0, microsecond=0)
    end = now + timedelta(minutes=1)
    ser = {}
    for key in ("bat_v", "bat_a", "pv_w", "status", "bat_soc"):
        for ms, val in history(token, POINTS[key][0], start, end):
            if val is None or key == "bat_soc" and not 0 <= val <= 100:
                continue
            ser.setdefault(int(ms / 1000) // 60 * 60, {})[key] = round(int(val) if key == "status" else val, 2)
    have = sorted(p["t"] for p in data["points"])
    import bisect
    added = 0
    for t, x in sorted(ser.items()):
        if "bat_v" not in x or x["bat_v"] <= 5 or t > ts - 120:
            continue
        i = bisect.bisect_left(have, t)
        if any(abs(have[j] - t) < 300 for j in (i - 1, i) if 0 <= j < len(have)):
            continue
        data["points"].append({"t": t, **x, "bf": 1})
        bisect.insort(have, t)
        added += 1
        day = data["days"].setdefault(datetime.fromtimestamp(t, TZ).strftime("%Y-%m-%d"), {})
        if x["bat_v"] < day.get("min_v", 99):
            day["min_t"] = t
        day["min_v"] = round(min(day.get("min_v", 99), x["bat_v"]), 2)
        day["max_v"] = round(max(day.get("max_v", 0), x["bat_v"]), 2)
        if x.get("bat_soc") is not None:
            day["soc_min"] = min(day.get("soc_min", 999), x["bat_soc"])
            day["soc_max"] = max(day.get("soc_max", -1), x["bat_soc"])
    data["points"].sort(key=lambda p: p["t"])
    if hours > 3:     # první plné doplnění: dnešní min/max přepočítat jen z bodů (dřív v něm byl i okamžitý propad regulátoru)
        dk = now.strftime("%Y-%m-%d")
        today = [p for p in data["points"] if p.get("bat_v") and p["bat_v"] > 5
                 and datetime.fromtimestamp(p["t"], TZ).strftime("%Y-%m-%d") == dk]
        if today:
            lo = min(today, key=lambda p: p["bat_v"])
            day = data["days"].setdefault(dk, {})
            day.update({"min_v": round(lo["bat_v"], 2), "min_t": lo["t"], "max_v": round(max(p["bat_v"] for p in today), 2)})
    if added:
        print(f"Doplněno {added} bodů z historie Solar Guardianu")


def migrate_plug_ids(data, st, cfg):
    """Jednorázově: do 14. 10. 2026 se zásuvky ukládaly pod koncovkou IP adresy, od té doby pod číslem ze jména „(N) …“.
    Zásuvky, které měří pořád totéž – 220 V za měničem, lednice, Wi‑Fi – se ve staré historii přejmenují na nová čísla
    (podle starého jména v aplikaci Tapo). Ostatní staré záznamy zůstanou, web je nezobrazuje."""
    if st.get("tp_mig1"):
        return
    import re as _re
    names = data.get("plug_names") or {}
    new = {k: v for k, v in names.items() if _re.match(r"\s*\(\d{1,3}\)", str(v or ""))}
    old = {k: v for k, v in names.items() if k not in new}
    pats = [("menic", r"m[eě]ni[cč]|inverter|220|230"), ("lednice", r"lednic|fridge|chlad"), ("wifi", r"wi.?fi|router|internet|m7000")]
    want = {"menic": str(cfg.get("zasuvka_menic") or "1"), "lednice": str(cfg.get("zasuvka_lednice") or "4")}
    wf = next((k for k, v in new.items() if _re.search(pats[2][1], v, _re.I)), None)
    if wf:
        want["wifi"] = wf
    mp = {}
    for k, v in old.items():
        for cat, rx in pats:
            if cat in want and _re.search(rx, str(v), _re.I) and k != want[cat]:
                mp[k] = want[cat]
                break
    for day in data.get("days", {}).values():
        dt = day.get("tp")
        if not dt:
            continue
        for o, n in mp.items():
            if o in dt:
                dt[n] = round(dt.get(n, 0) + dt.pop(o), 1)
    for p in data.get("points", []):
        tp = p.get("tp")
        if tp:
            for o, n in mp.items():
                if o in tp:
                    tp[n] = tp.pop(o) if n not in tp else tp[n]
                    tp.pop(o, None)
    data["tp_mig"] = {o: [n, old[o]] for o, n in mp.items()}
    st["tp_mig1"] = True
    print("Přejmenování staré historie zásuvek:", data["tp_mig"])


def backfill_flip(data, now, cfg):
    """Flip posílá každých 10 min, ale hlídač (cron GitHubu) běží nepravidelně – často jen po 30–45 min. Ze zpráv
    v ntfy (drží 12 h) doplní odběr a zásuvky i do mezer mezi běhy: k bodu regulátoru ze stejné chvíle (±5 min),
    jinak jako samostatný bod jen s údaji z Flipu."""
    msgs = data.pop("_inv_msgs", None) or []
    if len(msgs) < 2:
        return
    import bisect
    ts = now.timestamp()
    cut = ts - KEEP_DETAIL_DAYS * 86400
    pts = data["points"]
    times = [p["t"] for p in pts]
    added = filled = 0
    for m in msgs[:-1]:                        # poslední zprávu zpracuje běžný běh
        inv = inv_from_msg(m, now, cfg)
        if not inv or inv["t"] < cut or ts - inv["t"] < 120:
            continue
        t = inv["t"]
        plugs = {p["ip"]: p["w"] for p in inv.get("tp", []) if p.get("w") is not None and p.get("ip")}
        i = bisect.bisect_left(times, t)
        near = [j for j in (i - 1, i) if 0 <= j < len(pts) and abs(pts[j]["t"] - t) <= 300]
        if near:
            pt = min((pts[j] for j in near), key=lambda q: abs(q["t"] - t))
            if "tp" in pt or "mw" in pt:
                continue                       # už má data z Flipu
            filled += 1
        else:
            pt = {"t": t, "bf": 2}
            pts.insert(i, pt)
            times.insert(i, t)
            added += 1
        if inv.get("w") is not None:
            pt["ac_w"] = inv["w"]
        if inv.get("mw") is not None:
            pt["mw"] = inv["mw"]
        if (inv.get("gen") or {}).get("w") is not None:
            pt["gw"] = inv["gen"]["w"]
        if plugs:
            pt["tp"] = plugs
        rcp = next((p for p in inv.get("tp", []) if str(p.get("ip")) == str(cfg.get("river_auto_ip") or "")), None)
        if rcp and rcp.get("on") == 1 and not rcp.get("off"):
            pt["rc"] = 1                       # nabíjení River ze soláru (zásuvka 8, neměří) zapnuté
        # napětí Victronu jen k bodu regulátoru ze stejné chvíle
        if inv.get("v") is not None:
            vt = t - (inv.get("age") or 0)
            k = bisect.bisect_left(times, vt)
            cand = [pts[j] for j in (k - 1, k) if 0 <= j < len(pts) and pts[j].get("bat_v") and abs(pts[j]["t"] - vt) <= 150]
            if cand:
                b = min(cand, key=lambda q: abs(q["t"] - vt))
                if b.get("ivs") is None:
                    b["iv"], b["ivs"] = inv["v"], int(vt - b["t"])
                    if inv.get("lw") is not None:
                        b["lw"] = inv["lw"]
    if added or filled:
        print(f"Flip: doplněno {filled} bodů, přidáno {added} bodů z ntfy")


def sync_inverter_voltage(data, inv, v, now, tol=150):
    """Napětí Victronu přiřadí k bodu regulátoru, který je časově nejblíž (nejvýš tol s). Jinak by se porovnávaly
    dvě různé chvíle (Flip posílá po 10 min, regulátor má vlastní takt) a rozdíl napětí by vycházel i záporný."""
    vt = inv["t"] - (inv.get("age") or 0)                       # kdy Victron měřil
    ts = now.timestamp()
    reg_t = ts - (v.get("age_min") or 0) * 60                   # kdy měřil regulátor (poslední bod)
    best, bd = None, None
    for p in data["points"][-12:]:
        if not p.get("bat_v"):
            continue
        te = reg_t if p is data["points"][-1] else p["t"]
        dd = abs(te - vt)
        if bd is None or dd < bd:
            best, bd = p, dd
    if best is None or bd > tol:
        return
    best["iv"] = inv["v"]
    best["ivs"] = int(vt - (reg_t if best is data["points"][-1] else best["t"]))    # posun v s (synchronizováno)
    if inv.get("lw") is not None:
        best["lw"] = inv["lw"]


def fix_ts(cfg):
    """Kdy se naposledy opravovaly spoje / pojistka (nastavení oprava_spoju): starší měření kabelů, přechody do Float
    a testy kapacity neplatí (špatný spoj zkresloval napětí, regulátor mohl přejít do Float dřív, než byla baterie plná)."""
    try:
        return datetime.strptime(str(cfg.get("oprava_spoju") or "").strip()[:16], "%Y-%m-%d %H:%M").replace(tzinfo=TZ).timestamp()
    except ValueError:
        try:
            return datetime.strptime(str(cfg.get("oprava_spoju") or "").strip()[:10], "%Y-%m-%d").replace(tzinfo=TZ).timestamp()
        except ValueError:
            return 0


def wiring_check(data, st, now, topic, cfg):
    """Úbytek napětí na kabelech a spojích (regulátor − Victron, jen časově souhlasná měření, minus stálý rozdíl
    kalibrace přístrojů změřený v klidu). Upozorní na výrazný úbytek hned a na zvýšený odpor spojů jednou denně."""
    ts = now.timestamp()
    idle = (cfg.get("menic_vlastni_W") or 6) + (cfg.get("desulfator_W") or 0)
    rows = []
    for p in data.get("points", []):
        if p["t"] < max(ts - 3 * 86400, fix_ts(cfg)) or p.get("ivs") is None or not p.get("bat_v") or not p.get("iv"):
            continue
        lw = p.get("lw", p.get("mw"))
        if lw is None:
            continue
        ir, ii = max(p.get("bat_a") or 0, 0), (lw / 0.88 + idle) / p["iv"]
        rows.append((p["t"], p["bat_v"] - p["iv"], ir, ii))
    if not rows:
        return
    med = lambda a: sorted(a)[len(a) // 2]
    quiet = [r[1] for r in rows if r[2] < 0.5 and r[3] < 3]
    off = med(quiet) if len(quiet) >= 3 else 0.0
    data["wire_off"] = round(off, 3)
    lim_v = cfg.get("kabely_ubytek_V") or 0.35
    lim_r = cfg.get("kabely_odpor_mOhm") or 20
    t, dv, ir, ii = rows[-1]
    drop = dv - off
    # 4.46: po poplachu vždy další zpráva z dalšího spárovaného měření – potvrdí (trvá, už N. měření) nebo vyvrátí
    if "wire_acute" not in st and ts - st.get("wire_acute_t", 0) < 6 * 3600:    # poplach z doby před 4.46 (21. 10. 12:01)
        st["wire_acute"] = {"active": True, "t": int(st["wire_acute_t"]), "last_t": st["wire_acute_t"], "n": 1}
    wa = st.get("wire_acute")
    if wa and wa.get("active") and t > wa["last_t"] and ts - t < 1800:
        wa["last_t"] = t
        if drop >= lim_v:
            wa["n"] += 1
            if wa["n"] <= 4 or wa["n"] % 6 == 0:            # 2., 3., 4. měření, pak zhruba jednou za hodinu
                ntfy(topic, f"🔥 Úbytek na kabelech trvá – {wa['n']}. měření po sobě",
                     f"Teď o {fmt(drop, 2)} V při ~{fmt(ir + ii, 0)} A (od {datetime.fromtimestamp(wa['t'], TZ).strftime('%H:%M')}).\n"
                     "Potvrzeno – zkontroluj pojistku, pouzdro a spoje (nejsou horké / natavené?).", 4, "fire,warning")
        else:
            ntfy(topic, "✓ Úbytek na kabelech zase v normě",
                 f"Další měření: {fmt(drop, 2)} V při ~{fmt(ir + ii, 0)} A (hranice {fmt(lim_v, 2)} V)."
                 + (" Poplach se nepotvrdil – nejspíš měření regulátoru a měniče z trochu jiné chvíle." if wa["n"] == 1
                    else f" Vysoký úbytek trval {wa['n']} měření."), 3, "white_check_mark")
            wa["active"], wa["end_t"] = False, int(ts)
        wa["drop"], wa["a"] = round(drop, 2), round(ir + ii)
    elif ts - t < 1800 and drop >= lim_v and ts - st.get("wire_acute_t", 0) > 6 * 3600:
        ntfy(topic, "🔥 Velký úbytek napětí na kabelech",
             f"Regulátor ukazuje o {fmt(drop, 2)} V víc než měnič (při ~{fmt(ir + ii, 0)} A).\n"
             f"Na cestě regulátor → baterie → měnič je velký odpor – zkontroluj pojistku, pouzdro a spoje (nejsou horké / natavené?).\n"
             "Z dalšího měření přijde potvrzení, nebo zpráva, že je to v normě.", 4, "fire,warning")
        st["wire_acute_t"] = ts
        st["wire_acute"] = wa = {"active": True, "t": int(ts), "last_t": t, "n": 1, "drop": round(drop, 2), "a": round(ir + ii)}
    if wa:
        data["wire_state"] = {k: wa.get(k) for k in ("active", "t", "n", "drop", "a", "end_t")}
    load = [(r[1] - off) / (r[2] + r[3]) for r in rows if r[0] >= ts - 86400 and r[2] + r[3] >= 8]
    if len(load) >= 4:
        mo = med(load) * 1000
        data["wire_mo"] = round(mo, 1)
        day = now.strftime("%Y-%m-%d")
        if mo >= lim_r and st.get("wire_warn_d") != day:
            ntfy(topic, "🔧 Zvýšený odpor kabelů a spojů",
                 f"Za posledních 24 h vychází odpor cesty regulátor → baterie → měnič ~{fmt(mo, 0)} mΩ (v pořádku je do ~10 mΩ).\n"
                 f"Při proudu 20 A je to úbytek ~{fmt(mo * 20 / 1000, 2)} V. Zkontroluj pojistku a spoje.", 3, "wrench")
            st["wire_warn_d"] = day


def night_modes(data, now, cfg, days_back=120):
    """Pro každý den: jak byla zatížená solární baterie v ~6 h před nejnižším napětím dne (obvykle noc → ráno).
    days[k]["mn"] = "s" (chatu napájela solární baterie přes měnič) | "r" (chata na River / měnič bez odběru,
    baterie v klidu) – minima obou druhů nejsou porovnatelná. Bez dat se nic nezapíše."""
    rids = ips(cfg.get("zasuvky_river"))
    od = str(cfg.get("river_noci_od") or "2026-10-15")      # dřív v noci River nejel (zásuvky sloužily jinak)
    ph = data.get("plug_hourly") or {}
    pts = data.get("points") or []
    for k in sorted(data.get("days", {}))[-days_back:]:
        day = data["days"][k]
        if k < od:
            day["mn"] = "s"
            continue
        t = day.get("min_t") or datetime.strptime(k + " 06:00", "%Y-%m-%d %H:%M").replace(tzinfo=TZ).timestamp()
        a = t - 6 * 3600
        # 1) body hlídače (posledních 14 dní): odběr za měničem vs. zásuvky River
        sol = riv = 0
        for p in pts:
            if a <= p["t"] <= t and ("mw" in p or "tp" in p):
                if (p.get("mw") or 0) > 5:
                    sol += 1
                elif any(((p.get("tp") or {}).get(i) or 0) > 3 for i in rids) or "mw" not in p:
                    riv += 1
        mode = None
        if sol + riv >= 3:
            mode = "s" if sol >= riv else "r"
        else:
            # 2) hodinová spotřeba zásuvky za měničem (Tapo si ji pamatuje): ~0 Wh = chata nebrala ze solární baterie
            vals, h = [], a
            while h < t:
                dt_ = datetime.fromtimestamp(h, TZ)
                arr = ph.get(dt_.strftime("%Y-%m-%d"))
                if arr and arr[dt_.hour] is not None:
                    vals.append(arr[dt_.hour])
                h += 3600
            if len(vals) >= 3:
                mode = "s" if sum(vals) / len(vals) > 5 else "r"
        if mode:
            day["mn"] = mode


def import_soc_history(token, data, st, now, budget_s=40):
    """Jednorázově (po měsících, odzadu) doplní nejnižší a nejvyšší nabití dne (%) podle regulátoru ze Solar Guardianu."""
    if st.get("soc_hist_done"):
        return
    t0 = time.time()
    first = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    back, empty = st.get("soc_hist_back", 0), st.get("soc_hist_empty", 0)
    while time.time() - t0 < budget_s:
        y, m = first.year, first.month - back
        while m <= 0:
            y, m = y - 1, m + 12
        start = first.replace(year=y, month=m)
        end = (start + timedelta(days=32)).replace(day=1)
        try:
            daily = {}
            for ms, val in history(token, POINTS["bat_soc"][0], start, end):
                if val is None or not (0 <= val <= 100):
                    continue
                dk = datetime.fromtimestamp(ms / 1000, TZ).strftime("%Y-%m-%d")
                lo, hi = daily.get(dk, (999, -1))
                daily[dk] = (min(lo, val), max(hi, val))
        except Exception as e:
            print("Import historie nabití:", e)
            st["soc_hist_err"] = st.get("soc_hist_err", 0) + 1
            if st["soc_hist_err"] >= 5:
                st["soc_hist_done"] = True
            return
        for dk, (lo, hi) in daily.items():
            day = data["days"].setdefault(dk, {})
            day["soc_min"] = min(day.get("soc_min", 999), lo)
            day["soc_max"] = max(day.get("soc_max", -1), hi)
        print(f"Import historie nabití {start:%Y-%m}: {len(daily)} dní")
        back += 1
        empty = empty + 1 if not daily else 0
        st["soc_hist_back"], st["soc_hist_empty"] = back, empty
        if empty >= 3 or back >= 60:
            st["soc_hist_done"] = True
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
        if k == "bat_soc" and out[k] is not None and not 0 <= out[k] <= 100:
            print("Regulátor: nesmyslné nabití", out[k], "% – nepoužito")     # 17. 10. 2026 poslal 1446 %
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


# Priority (4.02) – v aplikaci ntfy má každá vlastní zvuk (Android: Kategorie oznámení):
#   5 Nejvyšší = TEĎ jednej (přepni na River, měnič se vypíná, odpoj spotřebiče, pojistka, Flip skoro vybitý)
#   4 Vysoká   = důležité, vyřeš brzy (nevydrží do rána, alarm měniče, data nechodí, odběr navíc, vyměň River…)
#   3 Výchozí  = doporučení / informace s radou (kabely, kapacita, sezóna, panely, pod 50 #…)
#   2 Malá     = jen pro informaci (nabito / Float, zase posílá, nabíjení River zapnuto, souhrn dne bez chyb)
#   1 Nejnižší = data pro hodinky a probouzení Flipu (jiná témata)
def ntfy(topic, title, msg, prio=3, tags="", note=None, actions=None, delay=None, view=True):
    body = {"topic": topic, "title": title, "message": msg, "priority": prio}
    if tags:
        body["tags"] = tags.split(",")
    # ťuknutí otevře zprávu v aplikaci ntfy; přehled je tlačítko pod notifikací (ntfy dovolí nejvýš 3 tlačítka)
    body["actions"] = (actions or []) + ([{"action": "view", "label": "Přehled", "url": DASHBOARD, "clear": False}] if view else [])
    if delay:
        body["delay"] = delay                      # ntfy doručí později (např. "5m")
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
    data.pop("_inv_msgs", None)
    flush_log(data)
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    salt, iv = os.urandom(16), os.urandom(12)
    ct = AESGCM(_key(passphrase, salt)).encrypt(iv, json.dumps(data, separators=(",", ":")).encode(), None)
    b = lambda x: base64.b64encode(x).decode()
    json.dump({"v": 1, "salt": b(salt), "iv": b(iv), "ct": b(ct)}, open(DATA_FILE, "w"))


def clean_soc(data):
    """Nabití % od regulátoru mimo 0–100 (17. 10. 2026 přišlo 1446 %) z uložených bodů a dnů vyhodit."""
    bad = lambda x: x is not None and not 0 <= x <= 100
    for p in data.get("points", []):
        if bad(p.get("bat_soc")):
            p.pop("bat_soc")
    for k, d in data.get("days", {}).items():
        if bad(d.get("soc_max")) or bad(d.get("soc_min")) and d.get("soc_min") != 999:
            vals = [p["bat_soc"] for p in data.get("points", []) if p.get("bat_soc") is not None
                    and datetime.fromtimestamp(p["t"], TZ).strftime("%Y-%m-%d") == k]
            if vals:
                d["soc_min"], d["soc_max"] = min(vals), max(vals)
            else:
                d.pop("soc_min", None)
                d.pop("soc_max", None)


def record(data, v, now, cfg=None):
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
    # Výroba: počítadlo regulátoru se nenuluje o půlnoci (ráno ukazuje ještě včerejšek) → viz day_yield:
    # před východem 0, pak hodnota − základ (poslední hodnota před východem; po vynulování 0). dkr = poslední hodnota, dkb = základ
    if v.get("day_kwh") is not None:
        raw = v["day_kwh"]
        rise = sun_times(cfg["sirka"], cfg["delka"], now.date())[0] if cfg else None
        if rise is not None and now < rise:
            day["solar_kwh"] = 0.0
            day.pop("dkb", None)
        else:
            if "dkb" not in day:
                prev = data["days"].get((now.date() - timedelta(days=1)).isoformat()) or {}
                day["dkb"] = day.get("dkr", prev.get("dkr", 0.0))
                day["solar_kwh"] = 0.0
            if raw < day["dkb"] - 0.01:
                day["dkb"] = 0.0
            day["solar_kwh"] = round(max(day.get("solar_kwh", 0), raw - day["dkb"]), 2)
        day["dkr"] = raw
    # min / max dne jen z naměřených bodů (po ~10 min) – stejná data jako graf napětí.
    # Vlastní min/max regulátoru chytá i okamžité propady (rozběh lednice…) a nuluje se až po setmění → jen pro informaci
    if v.get("min_v"):
        day["min_vr"] = round(min(v["min_v"], day.get("min_vr", 99)), 2)
    lows = [x for x in (v.get("bat_v"),) if x]
    if lows and lows[0] < day.get("min_v", 99):
        day["min_t"] = ts
    highs = [x for x in (v.get("bat_v"),) if x]
    if lows:
        day["min_v"] = round(min(lows + ([day["min_v"]] if "min_v" in day else [])), 2)
    if highs:
        day["max_v"] = round(max(highs + ([day["max_v"]] if "max_v" in day else [])), 2)
    # ať upozornění i souhrn pracují s denními hodnotami, ne s vynulovaným počítadlem
    v["day_kwh"], v["min_v"], v["max_v"] = day.get("solar_kwh"), day.get("min_v"), day.get("max_v")
    if v.get("bat_soc") is not None:
        day["soc_min"] = min(day.get("soc_min", 999), v["bat_soc"])
        day["soc_max"] = max(day.get("soc_max", -1), v["bat_soc"])
    # kdy poprvé přešla do Float (0 = dnes ještě ne) – pro učení předpovědi (plná baterie = přiškrcená výroba)
    if v.get("status") is not None and int(v["status"]) == 1 and not day.get("fl"):
        day["fl"] = ts
    day.setdefault("fl", 0)
    if v.get("bat_a") is not None and (v.get("status") is None or int(v["status"]) != 1):
        day["pa"] = round(max(day.get("pa", 0), v["bat_a"]), 1)
    if v.get("bat_v") and v["bat_v"] > 5:
        day["mp"] = round(min(day.get("mp", 99), v["bat_v"]), 2)
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


# Kalibrace na Petrovu baterii: „plná“ = klidové napětí večer po dni, kdy byla ve Float (stará baterie má nižší než 12,85 V)
VCAL = {"full": 12.85, "empty": 11.80}


def _map_in(v):                                 # skutečné napětí → napětí v obecné tabulce
    f, e = VCAL["full"], VCAL["empty"]
    return 11.80 + (v - e) * (12.85 - 11.80) / max(f - e, 0.2)


def soc_from_v(v):
    v = _map_in(v)
    if v <= AGM_SOC[0][0]:
        return 0.0
    for (v1, s1), (v2, s2) in zip(AGM_SOC, AGM_SOC[1:]):
        if v <= v2:
            return s1 + (s2 - s1) * (v - v1) / (v2 - v1)
    return 100.0


def v_from_soc(soc):
    """Opačný převod: stav nabití % → klidové napětí tvé baterie."""
    soc = max(0.0, min(100.0, soc))
    g = AGM_SOC[-1][0]
    for (v1, s1), (v2, s2) in zip(AGM_SOC, AGM_SOC[1:]):
        if soc <= s2:
            g = v1 + (v2 - v1) * (soc - s1) / (s2 - s1)
            break
    f, e = VCAL["full"], VCAL["empty"]
    return e + (g - 11.80) * (f - e) / (12.85 - 11.80)


def calibrate(data):
    """Klidové napětí „plné“ baterie: začátek noci (západ + 2 h) po dni, kdy byla ve Float."""
    days = data.get("days", {})
    vals = []
    for k in sorted(days)[-90:]:
        nv = days[k].get("nv")
        prev = (datetime.strptime(k, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        if nv and (days.get(prev) or {}).get("fl"):
            vals.append(nv["vs"] + 0.04)          # +0,04 V za pokles pod malým nočním odběrem
    vals = vals[-30:]
    if len(vals) >= 5:
        vals.sort()
        VCAL["full"] = max(12.30, min(12.95, vals[len(vals) // 2]))
    data["vcal"] = {"full": round(VCAL["full"], 2), "empty": VCAL["empty"], "n": len(vals)}


def battery_health(data, now, cfg):
    """Ukazatel zdraví baterie za noci: pokles napětí (mV) na 10 Ah odebraných z baterie.

    Noční napětí: z živých bodů (nebo z importu Solar Guardianu), odběr: ze zásuvky za měničem
    (živé body po 10 min, nebo hodinová historie ze zásuvky). Čím vyšší číslo, tím menší kapacita.
    """
    idle = cfg["menic_vlastni_W"] or 0
    hourly = data.get("plug_hourly", {})
    pts = data.get("points", [])
    st = data.setdefault("state", {})
    if not st.get("h_v2"):                     # nová pravidla (noci pod 12,1 V se nepočítají) → přepočítat
        for d in data["days"].values():
            d.pop("h", None)
        st["h_v2"] = True
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
            if nv:
                day["nv"] = nv
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
        if nv["ve"] < 12.10:                   # hluboko vybitá: napětí pod zátěží už neodpovídá stavu nabití
            continue
        drop = (nv["vs"] - nv["ve"]) * 1000
        mv10 = drop / ah * 10
        day["h"] = {"mv10": round(mv10, 1), "ah": round(ah, 1), "vs": nv["vs"], "ve": nv["ve"], "src": src,
                    "cap": round(min(260, 10400 / mv10)) if mv10 > 5 else None}   # ~52 mV/10 Ah = 200 Ah (nezávisle na nastavení)


def charge_metric(ser, date, cfg, load_w):
    """Kapacita z nabíjení: kolik Ah se vešlo od rána (stav z napětí) do přechodu do Float.

    ser = [{"t", "v", "a", "s"}] seřazené (napětí, proud z regulátoru, stav), load_w(t) = W za měničem nebo None.
    Vrací dict nebo None, když den nevyhovuje (málo vybitá, nedošlo do Float, chybí data).
    """
    rise, set_ = sun_times(cfg["sirka"], cfg["delka"], date)
    if not rise:
        return None
    r, z = rise.timestamp(), set_.timestamp()
    idle = cfg["menic_vlastni_W"] or 0
    pre = sorted(p["v"] for p in ser if r - 2400 <= p["t"] <= r and p.get("v") and p["v"] > 5)
    if not pre:
        return None
    lw = load_w(r - 1200)
    lw = lw if lw is not None else (cfg["noc_spotreba_W"] or 0)
    v0 = pre[len(pre) // 2] + (lw / 0.88 + idle) / 12.2 * 0.015     # pokles napětí odběrem (~15 mΩ)
    soc0 = soc_from_v(v0)
    if soc0 > 85:
        return None
    day_pts = [p for p in ser if r <= p["t"] <= z and p.get("s") is not None]
    tf = None
    for p, q in zip(day_pts, day_pts[1:]):
        if p.get("s") == 1 and q.get("s") == 1:
            tf = p["t"]
            break
    if not tf or tf - r < 3600:
        return None
    ah, cov, src = 0.0, 0.0, "live"
    win = [p for p in ser if r - 600 <= p["t"] <= tf and p.get("a") is not None]
    for p, q in zip(win, win[1:]):
        dt = min(q["t"] - p["t"], 1200)
        w = load_w(p["t"])
        if w is None:
            w, src = (cfg["noc_spotreba_W"] or 0), "odhad"
        ah += (p["a"] - (w / 0.88 + idle) / max(p.get("v") or 12.8, 11)) * dt / 3600
        cov += dt
    if cov < 0.8 * (tf - r) or ah < 8:
        return None
    cap = ah / 1.08 / ((100 - soc0) / 100)
    if not 40 <= cap <= 320:
        return None
    return {"ah": round(ah, 1), "soc": round(soc0), "cap": round(cap), "tf": int(tf), "src": src}


def load_lookup(data, cfg):
    """Funkce t → W za měničem: živé body (po 10 min), jinak hodinová historie zásuvky."""
    pts = {p["t"] // 600: p.get("mw", p.get("ac_w")) for p in data.get("points", []) if p.get("mw", p.get("ac_w")) is not None}
    hourly = data.get("plug_hourly", {})

    def f(t):
        for k in (t // 600, t // 600 - 1, t // 600 + 1):
            if k in pts:
                return pts[k]
        d = datetime.fromtimestamp(t, TZ)
        arr = hourly.get(d.strftime("%Y-%m-%d"))
        return arr[d.hour] if arr and arr[d.hour] is not None else None
    return f


def charge_capacity(data, now, cfg):
    """Doplní day["c"] z živých bodů (posledních 14 dní)."""
    lf = load_lookup(data, cfg)
    ser = [{"t": p["t"], "v": p.get("bat_v"), "a": p.get("bat_a"), "s": p.get("status")} for p in data.get("points", [])]
    today = now.strftime("%Y-%m-%d")
    for dk, day in data["days"].items():
        if "c" in day or dk == today and now.hour < 21:
            continue
        date = datetime.strptime(dk, "%Y-%m-%d").date()
        if (now.date() - date).days > 13:
            continue
        r = charge_metric(ser, date, cfg, lf)
        day["c"] = r or False             # False = spočítáno, den nevyhovuje


def eff_cap(data, cfg):
    """Skutečná kapacita pro výpočty (předpověď do rána, výhled, odhad nabití): medián posledních 14 spolehlivých nocí."""
    nom = cfg["kapacita_Ah"] or 200
    fts = fix_ts(cfg)
    qc = sorted(d["qc"]["cap"] for k, d in sorted(data.get("days", {}).items())[-45:]
                if (d.get("qc") or {}).get("ok") and (d["qc"].get("te") or d["qc"].get("t") or 0) >= fts)
    if len(qc) >= 2:                       # testy kapacity z Ah (plné nabití → noc → ráno) mají přednost
        m = qc[len(qc) // 2] if len(qc) % 2 else (qc[len(qc) // 2 - 1] + qc[len(qc) // 2]) / 2
        return max(40, min(300, m))
    # noční odhad z poklesu napětí (d["h"]) se nepoužívá – kolísal mezi ~20 a ~125 Ah (3.90); do 2 testů štítek
    return nom


def health_baseline(data):
    vals = [d["h"]["mv10"] for k, d in sorted(data["days"].items()) if "h" in d]
    if len(vals) < 7:
        return None, vals
    first = sorted(vals[:14])
    return first[len(first) // 2], vals


def night_corr(data):
    """Medián chyby (skutečnost − předpověď) za posledních 10 vyhodnocených nocí; oprava max ±0,4 V."""
    errs = [v["a"] - v["raw"] for k, v in sorted((data.get("nlog") or {}).items())
            if v.get("a") is not None and v.get("raw") is not None and not v.get("riv")][-10:]   # 4.75: bez nocí na River
    if len(errs) < 3:
        return 0.0, len(errs)
    errs.sort()
    return round(max(-0.4, min(0.4, errs[len(errs) // 2])), 2), len(errs)


def night_log(data, now, cfg, set_):
    """Deník nocí: večerní předpověď (1 h po západu) a ranní skutečnost – z toho se předpověď učí."""
    nl = data.setdefault("nlog", {})
    if not data.get("nlog_bf"):                  # jednorázově zpětně: předpovědi za posledních ~12 nocí z uložených bodů
        data["nlog_bf"] = 1
        for i in range(12, 0, -1):
            dd = now.date() - timedelta(days=i)
            r_, s_ = sun_times(cfg["sirka"], cfg["delka"], dd)
            if not s_:
                continue
            fake = s_ + timedelta(hours=1)
            fb = forecast(data, fake, cfg)
            if fb:
                nl.setdefault(dd.isoformat(), {"p": fb["v_until"], "raw": fb.get("v_raw", fb["v_until"]), "corr": fb.get("corr", 0),
                                               "until": fb["until"], "t": int(fake.timestamp()), "v0": fb.get("v_now"),
                                               "w": fb.get("draw_w"), "cap": fb.get("cap"), "bf": 1})
    f = data.get("forecast")
    t = now.timestamp()
    if f and set_ and t >= set_.timestamp() + 3600:
        key = now.strftime("%Y-%m-%d")
        if key not in nl:
            nl[key] = {"p": f["v_until"], "raw": f.get("v_raw", f["v_until"]), "corr": f.get("corr", 0), "until": f["until"],
                       "t": int(t), "v0": f.get("v_now"), "w": f.get("draw_w"), "cap": f.get("cap")}
    pts = data.get("points", [])
    # 4.75: noc, kdy chata (aspoň zčásti) jela z River, není měřítko – solární baterie neměla odběr, předpověď
    # s odběrem počítala. Takové noci se označí a z učení (oprava předpovědi) vynechají.
    for k, e in nl.items():
        if "riv" in e or t < e["until"]:
            continue
        night = [p for p in pts if e["t"] <= p["t"] <= e["until"] and p.get("tp") is not None]
        if len(night) >= 6:
            e["riv"] = sum(1 for p in night if (p.get("mw") or 0) > 3) < 0.8 * len(night)
    for k, e in nl.items():
        if e.get("a") is not None or e.get("skip") or t < e["until"] + 900:
            continue
        # skutečnost = ranní minimum (hodinu před koncem noci až 15 min po něm – než začne nabíjet)
        near = [p["bat_v"] for p in pts if e["until"] - 3600 <= p["t"] <= e["until"] + 900 and p.get("bat_v")]
        night = [p["bat_v"] for p in pts if e["t"] <= p["t"] <= e["until"] + 600 and p.get("bat_v")]
        if near:
            e["a"] = round(min(near), 2)
            e["min"] = round(min(night), 2) if night else None
            if not e.get("bf"):
                log("ev", f"Noc z {datetime.strptime(k, '%Y-%m-%d').strftime('%-d. %-m.')}: předpověď {fmt(e['p'], 2)} V, ráno potom skutečně {fmt(e['a'], 2)} V"
                    + (" (chata jela z River – do učení se nepočítá)" if e.get("riv") else ""))
        elif t > e["until"] + 6 * 3600:
            e["a"] = None
            e["skip"] = True
    for k in sorted(nl)[:-40]:
        nl.pop(k)


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
    cap = eff_cap(data, cfg) * cold_factor(data, cfg)[0]                 # 4.48: v chladu menší kapacita
    ac = cfg["noc_spotreba_W"] or 0
    measured = [p.get("mw", p.get("ac_w")) for p in data.get("points", [])
                if p.get("mw", p.get("ac_w")) is not None and p["t"] >= t_now - 3 * 3600 and (p.get("pv_w") or 0) < 5]
    if len(measured) >= 6:                       # aspoň hodina změřeného nočního odběru
        ac = sum(measured) / len(measured)
    # 4.50: odběr za poslední hodinu (≥ 3 měření) – po vypnutí PC se předpověď spraví do hodiny, ne až za 3 h
    recent = [p.get("mw", p.get("ac_w")) for p in data.get("points", [])
              if p.get("mw", p.get("ac_w")) is not None and p["t"] >= t_now - 3600 and (p.get("pv_w") or 0) < 5]
    if len(recent) >= 3:
        ac = sum(recent) / len(recent)
    # běžný noční odběr (medián nocí 21–5 h za posledních 7 dní, bez dnešního večera)
    base = sorted(p["mw"] for p in data.get("points", []) if p.get("mw") is not None and p["mw"] > 3
                  and t_now - 7 * 86400 <= p["t"] < t_now - 6 * 3600 and (p.get("pv_w") or 0) < 5
                  and (datetime.fromtimestamp(p["t"], TZ).hour >= 21 or datetime.fromtimestamp(p["t"], TZ).hour < 5))
    base_w = base[len(base) // 2] if len(base) >= 12 else None
    draw = ac / 0.88 + (cfg["menic_vlastni_W"] or 0)   # W z baterie
    a = draw / 12.2                                                             # A z baterie
    # 4.50: pod větším odběrem napětí klesne víc (vnitřní odpor + kabely, ~10 mΩ) → stav z napětí by vyšel horší
    if recent and len(recent) >= 3:
        i_now = (sum(recent) / len(recent) / 0.88 + (cfg["menic_vlastni_W"] or 0)) / 12.2
        v += max(0.0, i_now * 0.010 - 0.05)                # +0,05 V už je výš; navíc jen při proudu nad ~5 A
    until = rise + timedelta(minutes=cfg["nabijeni_od_vychodu_min"] or 0)
    hours = (until.timestamp() - t_now) / 3600
    soc_now = soc_from_v(v)
    soc_until = soc_now - a * hours / cap * 100
    f = {"until": int(until.timestamp()), "soc_now": round(soc_now), "soc_until": round(soc_until),
         "v_now": round(v - 0.05, 2), "v_until": round(v_from_soc(max(soc_until, 0)) - a * 0.015, 2),
         "draw_w": round(draw), "ah_night": round(a * hours), "n": len(pts), "cap": round(cap),
         "measured": len(measured) >= 6}
    # učení: o kolik se předpověď v minulých nocích pletla (medián) → oprava ranního napětí
    corr, ncorr = night_corr(data)
    f["v_raw"], f["corr"], f["corr_n"] = f["v_until"], corr, ncorr
    f["v_until"] = round(f["v_until"] + corr, 2)
    for key, lim in (("t_crit", cfg["baterie_kriticka_V"]), ("t_off", cfg["odpojeni_V"])):
        if lim is None:
            continue
        ah_left = (soc_now - soc_from_v(lim)) / 100 * cap
        if ah_left <= 0:
            f[key] = int(t_now)
        elif a > 0 and ah_left / a < hours:
            f[key] = int(t_now + ah_left / a * 3600)
        elif f["v_until"] < lim:                  # podle opravy z minulých nocí ráno pod hranicí
            f[key] = f["until"]
        # 4.50: odběr je teď zvýšený (PC…) – vydržela by, kdyby se do určité doby vrátil na běžný noční?
        if key == "t_crit" and f.get("t_crit") and base_w and ac > base_w * 1.3 + 15:
            ab = (base_w / 0.88 + (cfg["menic_vlastni_W"] or 0)) / 12.2
            ah_left = (soc_now - soc_from_v(lim)) / 100 * cap
            if ah_left > ab * hours * 1.1 and a > ab:                       # s rezervou 10 %
                cut = t_now + (ah_left - ab * hours * 1.1) / (a - ab) * 3600
                f.update(base_w=round(base_w), now_w=round(ac), ok_base=True, cut_by=int(min(cut, until.timestamp())))
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


REL_DAY = {-2: "předevčírem", -1: "včera", 0: "dnes", 1: "zítra", 2: "pozítří"}
REL_GEN = {-2: "předvčerejšího", -1: "včerejšího", 0: "dnešního", 1: "zítřejšího", 2: "pozítřejšího"}


def rel_day(t, now=None):
    """Ráno / noc / večer vždy s dnes / zítra / včera (t = unix s nebo date)."""
    d = t if hasattr(t, "isoformat") and not isinstance(t, (int, float)) else datetime.fromtimestamp(t, TZ).date()
    n = (d - (now or datetime.now(TZ)).date()).days
    return REL_DAY.get(n) or d.strftime("%-d. %-m.")


def do_rana(t, now=None):
    """„do zítřejšího rána“ / „do dnešního rána“."""
    d = datetime.fromtimestamp(t, TZ).date()
    n = (d - (now or datetime.now(TZ)).date()).days
    return f"do {REL_GEN[n]} rána" if n in REL_GEN else f"do rána {d.strftime('%-d. %-m.')}"


def forecast_text(f):
    if not f:
        return None
    hm = lambda t: f"{rel_day(t)} ~" + datetime.fromtimestamp(t, TZ).strftime("%H:%M")
    dr = do_rana(f["until"])
    tail = f" ({dr} ~{f['ah_night']} Ah při ~{f['draw_w']} W)"
    if f.get("t_off"):
        return f"{dr[0].upper() + dr[1:]} nevydrží: pod alarm {hm(f.get('t_crit', f['t_off']))}, měnič se vypne {hm(f['t_off'])}" + tail
    if f.get("t_crit"):
        return f"{dr[0].upper() + dr[1:]} těsně: pod alarm {hm(f['t_crit'])}" + tail
    return (f"{dr[0].upper() + dr[1:]} vydrží: teď ~{fmt(f.get('v_now'), 2)} V, "
            f"{rel_day(f['until'])} v {datetime.fromtimestamp(f['until'], TZ).strftime('%H:%M')} ~{fmt(f.get('v_until'), 2)} V") + tail


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
        calibrate(data)
    except Exception as e:
        print("Kalibrace napětí:", e)
    try:
        data["ver"] = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "VERSION")).read().strip()
    except OSError:
        data["ver"] = None
    rivers = read_ecoflow(data, st, now, topic, cfg)
    if os.environ.get("WAKE") == "1":
        # Flip 1.4+ posílá data přes GitHub (sám spustí další běh) → nečekat na ntfy, jen ho probudit
        wake_flip(topic, 0 if now.timestamp() - (st.get("flip_gh") or 0) < 3600 else 110)
    inv = read_inverter(data, topic, now, cfg)
    read_plug_history(data, topic)
    try:
        read_tp_history(data, topic, cfg)
    except Exception as e:
        print("Historie zásuvek:", e)
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
        try:
            backfill_points(token, data, now, 6 if st.get("bf14") else KEEP_DETAIL_DAYS * 24)   # poprvé celých 14 dní
            st["bf14"] = True
        except Exception as e:
            print("Doplnění bodů:", e)
        record(data, v, now, cfg)
        clean_soc(data)
        if inv and now.timestamp() - inv["t"] < 1200:
            pt = data["points"][-1]
            if inv.get("w") is not None:
                pt["ac_w"] = inv["w"]
            if inv.get("mw") is not None:
                pt["mw"] = inv["mw"]
            if (inv.get("gen") or {}).get("w") is not None:
                pt["gw"] = inv["gen"]["w"]
            if inv.get("v") is not None:            # napětí měřené měničem → jen k bodu regulátoru ze STEJNÉ chvíle
                sync_inverter_voltage(data, inv, v, now)
            plugs = {p["ip"]: p["w"] for p in inv.get("tp", []) if p.get("w") is not None and p.get("ip")}
            if plugs:
                pt["tp"] = plugs
            ph_ = inv.get("ph") or {}
            if ph_.get("b") is not None:       # 4.53: baterie Flipu do historie (graf v dlaždici Flip)
                pt["pb"] = ph_["b"]
                pt["pc"] = 1 if ph_.get("c") else 0
                if ph_.get("t") is not None:
                    pt["pt"] = ph_["t"]
            if inv.get("fc"):
                pt["fc"] = inv["fc"].get("on")
            if (inv.get("rt") or {}).get("b") is not None:
                pt["rb"] = inv["rt"]["b"]      # baterie routeru (graf, později řízení nabíjení)
                if inv["rt"].get("c") is not None:
                    pt["rbc"] = 1 if inv["rt"]["c"] else 0      # 5.42: router se nabíjí (hlásí router)
            if isinstance(inv.get("rc"), dict) and not inv["rc"].get("miss") and inv["rc"].get("on") is not None:
                pt["rcon"] = 1 if inv["rc"]["on"] else 0        # 5.42: zásuvka routeru zapnutá (Flip 1.9)
            ths = {x["n"]: x["t"] for x in inv.get("th", []) if x.get("t") is not None and now.timestamp() - x["tm"] < 1800}
            if ths:
                pt["th"] = ths                 # 1.5: teploty z teploměrů Xiaomi
            rcp = next((p for p in inv.get("tp", []) if str(p.get("ip")) == str(cfg.get("river_auto_ip") or "")), None)
            if rcp and rcp.get("on") == 1 and not rcp.get("off"):
                pt["rc"] = 1                   # nabíjení River ze soláru (zásuvka 8, neměří) zapnuté
            ow = other_load(data, st, cfg, now, topic, inv, st.get("ra_on"))
            if ow is not None:
                pt["ow"] = ow
            day = data["days"].setdefault(now.strftime("%Y-%m-%d"), {})
            names = data.setdefault("plug_names", {})
            # denní energie zásuvek z PŘÍRŮSTKŮ počítadla: Tapo nuluje „dnes“ podle svých hodin (ne přesně
            # o půlnoci našeho dne), takže maximum by do nového dne přeneslo kus včerejška
            raw = st.setdefault("tp_raw", {})
            first_v2 = not st.get("tp_v2")
            # podíl zdrojů teď: solár (zásuvka 220 V za měničem) vs. River (zásuvky na výstupu River) → rozdělení spotřeby
            byid = {str(p.get("ip")): p for p in inv.get("tp", [])}
            mip_ = str(cfg.get("zasuvka_menic") or inv.get("mip") or "")
            S_ = (byid.get(mip_) or {}).get("w") or 0
            R_ = sum((byid.get(i) or {}).get("w") or 0 for i in ips(cfg.get("zasuvky_river")))
            if now.strftime("%Y-%m-%d") < str(cfg.get("river_noci_od") or "2026-10-15"):
                fs = 1.0
            elif S_ > 3:         # měnič dodává → hlavní okruh chaty (i všechny měřené zásuvky) jede ze soláru;
                fs = 1.0         # River zároveň napájí jen něco konkrétního neměřeného (TV, telefon) → „ostatní z River“
            elif R_ > 3:
                fs = 0.0         # měnič nic nedává, River ano → chata přepojená na River
            else:
                fs = 1.0 if S_ > 0 or (byid.get(mip_) and not byid[mip_].get("off")) else 0.0
            for p in inv.get("tp", []):
                if p.get("ip") and p.get("n"):
                    names[p["ip"]] = p["n"]
                if p.get("ip") and p.get("wh") is not None:
                    ip, wh = p["ip"], float(p["wh"])
                    dt = day.setdefault("tp", {})
                    if first_v2:                          # přechod na nový výpočet: dnešek nejvýš to, co ukazuje počítadlo
                        dt[ip] = round(min(dt.get(ip, wh), wh), 1)
                    else:
                        prev = raw.get(ip)
                        inc = 0.0 if prev is None else (wh - prev if wh >= prev else wh)   # pokles = počítadlo se vynulovalo
                        if 0 <= inc < 3000:
                            dt[ip] = round(dt.get(ip, 0) + inc, 1)
                            sp = day.setdefault("tps", {}).setdefault(ip, {"s": 0, "r": 0})
                            sp["s"] = round(sp["s"] + inc * fs, 1)
                            sp["r"] = round(sp["r"] + inc * (1 - fs), 1)
                    raw[ip] = wh
            st["tp_v2"] = True
        if rivers:
            data["points"][-1]["rv"] = [{"s": r.get("soc"), "i": r.get("in_w"), "o": r.get("out_w"), "k": str(r.get("sn", ""))[-6:]}
                                        for r in rivers]       # 4.99: „k“ = konec SN (pořadí River se může změnit)
    try:
        backfill_flip(data, now, cfg)
    except Exception as e:
        print("Doplnění z Flipu:", e)
    data.pop("_inv_msgs", None)
    try:
        import_history(token, data, st, now, cfg)
    except Exception as e:
        print("Import historie selhal:", e)
        log("err", f"Import historie Solar Guardian: {str(e)[:100]}")
    try:
        wiring_check(data, st, now, topic, cfg)
    except Exception as e:
        print("Kabely:", e)
    try:
        migrate_plug_ids(data, st, cfg)
    except Exception as e:
        print("Přejmenování zásuvek:", e)
    try:
        night_modes(data, now, cfg)
    except Exception as e:
        print("Druh nocí:", e)
    try:
        import_soc_history(token, data, st, now)
    except Exception as e:
        print("Import historie nabití selhal:", e)
    try:
        night_history(token, data, st, now, cfg)
    except Exception as e:
        print("Rozbor nocí selhal:", e)
    try:
        charge_capacity(data, now, cfg)
    except Exception as e:
        print("Kapacita z nabíjení:", e)
        log("err", f"Kapacita z nabíjení: {str(e)[:100]}")
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
    try:
        night_log(data, now, cfg, set_)
    except Exception as e:
        print("Deník nocí:", e)
    st["_rivers"] = [{"name": r["name"], "soc": r.get("soc")} for r in (rivers or [])]
    note_run(data, now, sg=True, inv=inv)
    mode = "leto"
    try:
        mode = detect_mode(data, st, cfg, now, inv)
        track_soc(data, st, v, now, cfg, inv, mode)
        fuse_check(v, st, now, topic, cfg)
        overload_check(v, st, now, topic, cfg, data, rise, set_)
    except Exception as e:
        print("Režim / SOC:", e)
        log("err", f"Odhad nabití: {type(e).__name__} {str(e)[:90]}")
    try:
        for name, fn in (("Počasí a výhled", lambda: weather_and_outlook(data, st, cfg, now, topic, mode)),
                         ("Ostatní odběr", lambda: other_load_check(data, st, cfg, now, topic)),
                         ("Kontrola upozornění", lambda: check(v, st, now, topic, cfg, rise, set_, data)),
                         ("Automatika River", lambda: river_auto(v, st, now, topic, cfg, rise, set_, data, inv)),
                         ("River napájí chatu", lambda: river_supply(data, st, now, topic, cfg, rise, set_)),
                         ("Připomínka EcoFlow", lambda: ecoflow_reminder(data, st, now, topic)),
                         ("Nabití #", lambda: hash_soc(data, st, now, cfg)),
                         ("Test kapacity", lambda: capacity_check(data, st, now, cfg)),
                         ("Upozornění #", lambda: hash_alert(data, st, now, topic, cfg)),
                         ("Lednice", lambda: fridge_check(data, st, now, topic, cfg)),
                         ("Lednice po dnech", lambda: fridge_days(data, now, cfg)),
                         ("Spotřeba proti obvyklé", lambda: cons_compare(data, st, now, topic, cfg)),
                         ("River po dnech", lambda: river_days(data, now, cfg)),
                         ("Mráz", lambda: frost_check(data, st, now, topic, cfg)),
                         ("Teploměry", lambda: thermo_check(data, st, now, topic, cfg)),
                         ("Data internetu", lambda: net_usage(data, st, now, cfg)),
                         ("Chladnutí pokoje", lambda: chladnuti.update(data, st, now, cfg)),
                         ("Plné nabití", lambda: full_charge_check(data, st, now, topic, cfg)),
                         ("Flip – výdrž", lambda: flip_check(data, st, now, topic, cfg)),
                         ("Flip – nabíjení", lambda: flip_charge_cmd(data, st, now, topic, cfg)),
                         ("Učení výhledu", lambda: night_learn(data, st, now, cfg)),
                         ("Výhled dne", lambda: day_outlook(data, st, now, topic, cfg, rise, set_)),
                         ("Běh generátoru", lambda: gen_sessions(data, st, now, topic, cfg)),
                         ("Nabíjení z generátoru", lambda: gen_charge_ctl(data, st, now, topic, cfg)),
                         ("Palivo a cena", lambda: fuel_stats(data, st, now, cfg)),
                         ("Zásuvky vidět", lambda: plug_watch(data, st, now, topic, cfg)),
                         ("Večerní souhrn", lambda: daily_summary(data, v, st, now, topic, cfg, rise, set_)),
                         ("Hodinky", lambda: watch_publish(data, v, st, now, topic, cfg))):
            try:
                fn()
            except Exception as e:          # chyba jedné části nesmí shodit ostatní
                print(name, "selhalo:", e)
                log("err", f"{name}: {type(e).__name__} {str(e)[:100]}")
    finally:
        save_data(key, data)
        if data.get("gen_cont"):                    # 4.87: nabíjení z generátoru běží → další běh hned (smyčka po 30 s)
            try:
                tok = os.environ.get("GH_TOKEN", "")
                rep = os.environ.get("GITHUB_REPOSITORY", "KptDundee/chata-hlidac")
                # 4.98: když už čeká jiný běh (typicky s daty z Flipu), nespouštět – čekající běh by nahradil a data
                # z Flipu by se ztratila (proto „Flip se neozval 1 h“); ten čekající běh smyčku stejně převezme
                waiting = 0
                if tok:
                    for stt in ("pending", "queued", "waiting"):
                        try:
                            jr = json.loads(urllib.request.urlopen(urllib.request.Request(
                                f"https://api.github.com/repos/{rep}/actions/workflows/hlidac.yml/runs?status={stt}&per_page=5",
                                headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"}), timeout=15).read())
                            waiting += int(jr.get("total_count") or 0)
                        except Exception as e:
                            print("Čekající běhy – nejde zjistit:", e)
                if tok and not waiting:
                    urllib.request.urlopen(urllib.request.Request(
                        f"https://api.github.com/repos/{rep}/actions/workflows/hlidac.yml/dispatches",
                        data=json.dumps({"ref": "main"}).encode(), method="POST",
                        headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"}), timeout=20).read()
            except Exception as e:
                print("Další běh (generátor) nejde spustit:", e)


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
    # 4.86: zásuvka vypnutá vypínačem (zima – nic k nabíjení) → automatika čeká a nic neposílá; jakmile se zásuvka
    # zase objeví (vypínač zapnutý), automatika běží sama dál – nic se nemusí přepínat v nastavení
    inv_ = data.get("inverter") or {}
    if inv_ and now.timestamp() - inv_.get("t", 0) < 1800:
        pp = next((p for p in inv_.get("tp") or [] if str(p.get("ip")) == ip), None)
        seen = pp is not None and not pp.get("off") and not pp.get("gone") and pp.get("err") is None
        if not seen:
            st["ra_gone_n"] = st.get("ra_gone_n", 0) + 1
            if st["ra_gone_n"] >= 3:
                st["ra_paused"], st["ra_on"] = True, False
        else:
            st["ra_gone_n"] = 0
            if st.get("ra_paused"):
                st["ra_paused"] = False
                log("ev", f"Zásuvka ({ip}) zase zapnutá – nabíjení River ze soláru znovu automaticky")
                ntfy(topic, "☀️ Nabíjení River ze soláru zase běží",
                     f"Zásuvka ({ip}) je zase zapnutá – hlídač bude River nabíjet přebytkem ze slunce sám, jako dřív.", 2, "sunny")
        if st.get("ra_paused"):
            data["river_auto"] = {"on": False, "paused": True, "reason": f"zásuvka ({ip}) vypnutá vypínačem – zapne se sama, až bude vidět"}
            return
    bv, pv = v.get("bat_v"), v.get("pv_w")
    status = int(v["status"]) if v.get("status") is not None else None
    stale = v.get("age_min") is None or v["age_min"] > cfg["regulator_offline_min"]
    on = bool(st.get("ra_on"))
    reason = None
    day = rise and set_ and rise <= now <= set_ - timedelta(minutes=30)
    # zapínat jen do 2 h před západem (ať to nevypne hned kvůli slábnoucímu slunci) a ne hned po vypnutí
    early = rise and set_ and rise + timedelta(minutes=60) <= now <= set_ - timedelta(minutes=120)
    # pauza po vypnutí: 20 min, po každém neúspěšném pokusu (baterie se vybíjela) dvojnásobek, max 120 min
    pause = min(120, 20 * 2 ** st.get("ra_fail", 0)) * 60
    cooldown = now.timestamp() - st.get("ra_off_ts", 0) < pause - 30
    # nabíjecí napětí Boostu s teplotní kompenzací (−18 mV/°C pro 12V baterii, vztaženo k 25 °C)
    bt = v.get("bat_t")
    boost_v = (cfg.get("boost_V") or 14.4) + (max(-0.3, min(0.3, (25 - bt) * 0.018)) if bt is not None else 0)
    if stale or bv is None or pv is None:
        if on:
            on, reason = False, "regulátor neposílá data"
    elif not on:
        # Ve Float regulátor škrtí panely na aktuální potřebu → výkon panelů tu nic neříká;
        # skutečný přebytek se ukáže až po zapnutí (a když nestačí, vypne se níž kvůli „panely jen … W“).
        st["ra_fl"] = st.get("ra_fl", 0) + 1 if status == 1 else 0
        # Boost – fáze stálého napětí: dokud regulátor drží nabíjecí napětí, baterie dostává plnou dávku
        # a River jede jen z toho, co by jinak propadlo.
        st["ra_bh"] = st.get("ra_bh", 0) + 1 if (cfg.get("river_auto_boost") and status == 2 and bv >= boost_v - 0.08) else 0
        if early and not cooldown and st["ra_fl"] >= 1 and bv >= (cfg["river_auto_v_off"] or 0) + 0.3:
            on, reason = True, f"baterie plná (Float), panely {fmt(pv)} W (přiškrcené)"
        elif early and not cooldown and st["ra_bh"] >= 1:
            on, reason = True, f"regulátor drží nabíjecí napětí {fmt(bv, 2)} V (Boost), panely {fmt(pv)} W"
    else:
        # Priorita je solární baterie: jakmile napětí spadne z Float (~13,6 V) pod hranici, baterie
        # se vybíjí → vypnout hned. Výkon panelů se posuzuje až z měření pořízeného po přepnutí zásuvky
        # (Flip povel provede do 10 min) – jedno slabé měření stačí.
        reading_ts = now.timestamp() - (v.get("age_min") or 0) * 60
        fresh_after = reading_ts > st.get("ra_since", 0) + 600
        hold = cfg.get("river_auto_v_drzet") or 13.0
        float_v = cfg.get("float_V") or 13.7
        # čistý proud do baterie = proud z regulátoru − odběr měniče (River je za měničem)
        net = None
        if inv and now.timestamp() - inv.get("t", 0) < 1200 and inv.get("mw") is not None and v.get("bat_a") is not None:
            net = v["bat_a"] - (inv["mw"] / 0.88 + (cfg["menic_vlastni_W"] or 0)) / bv
        if status == 2 and not cfg.get("river_auto_boost"):
            # nabíjení River jen ve Float: v Boostu baterie ještě není plná → přednost má ona, i za cenu přebytku
            on, reason = False, "regulátor je v Boostu – baterie ještě není plně nabitá (River jen ve Float)"
        elif net is not None and net < -(cfg.get("odber_z_baterie_A") or 2.0):
            on, reason = False, f"baterie se vybíjí ({fmt(net, 1)} A) – panely na River nestačí"
        elif status == 1 and bv < float_v - 0.4:
            on, reason = False, f"napětí ve Float kleslo na {fmt(bv, 2)} V – baterie se vybíjí"
        elif status == 2 and bv < boost_v - 0.15:
            # V Boostu musí regulátor DRŽET nabíjecí napětí – jen pak baterie bere, kolik potřebuje, a River jede
            # z přebytku, který by regulátor jinak škrtil. Jakmile napětí klesne, panely nestačí na obojí → River pryč,
            # baterie (ještě ne plně nabitá, i když regulátor ukazuje 100 %) má přednost. (Konec Boostu = stav Float.)
            on, reason = False, f"regulátor už nedrží nabíjecí napětí ({fmt(bv, 2)} V) – baterie má přednost"
        elif bv < hold:
            on, reason = False, f"baterie se vybíjí ({fmt(bv, 2)} V)"
        elif bv < (cfg["river_auto_v_off"] or 0):
            on, reason = False, f"napětí kleslo na {fmt(bv, 2)} V"
        elif fresh_after and pv < (cfg["river_auto_pv_off"] or 0):
            on, reason = False, f"panely jen {fmt(pv)} W"
        elif not day:
            on, reason = False, "blíží se západ slunce"
    if on:                          # počítat dobu nabíjení za den
        day_ = data["days"].setdefault(now.strftime("%Y-%m-%d"), {})
        day_["ra_min"] = day_.get("ra_min", 0) + 10
    if reason:
        send_cmd(topic, ip, on, reason)
        ran = f" (běželo {dur(now.timestamp() - st['ra_since'])})" if not on and st.get("ra_since") else ""
        note = f"🔌 River {'ZAP' if on else 'VYP'} – {reason}{ran} · {fmt(bv, 2)} V, {fmt(pv)} W"
        if cfg.get("river_auto_notifikace"):
            ntfy(topic, "🔌 Nabíjení River zapnuto" if on else "🔌 Nabíjení River vypnuto",
                 f"Zásuvka .{ip}: {reason}{ran}. Baterie {fmt(bv, 2)} V, panely {fmt(pv)} W.", 2, "electric_plug", note=note)
        else:
            log("auto", note)                   # potichu – jen do Deníku a večerního souhrnu
        st["ra_chk"] = False
        st["ra_since_prev"] = st.get("ra_since", now.timestamp())
        st["ra_on"], st["ra_since"], st["ra_low"] = on, int(now.timestamp()), 0
        if not on:
            st["ra_off_ts"] = int(now.timestamp())
            ran_s = now.timestamp() - st.get("ra_since_prev", now.timestamp())
            if "vybíjí" in reason or "neudrží" in reason or "panely jen" in reason:
                st["ra_fail"] = min(st.get("ra_fail", 0) + 1, 3) if ran_s < 40 * 60 else 0
            else:
                st["ra_fail"] = 0
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
    data["river_auto"] = {"on": on, "since": st.get("ra_since"), "ip": ip, "why": reason or st.get("ra_why"),
                          "off_ts": st.get("ra_off_ts"), "wait": int(st.get("ra_off_ts", 0) + pause) if not on else None}
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
    L.append(f"☀️ Výroba {fmt(day.get('solar_kwh'), 2)} kWh" + (f" · nabitá (Float) v {hm(full['t'])}" if full else " · do Float nedošla"))
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
    cc = data.get("cons_cmp") or {}                    # 5.22: spotřeba chaty proti obvyklé
    if cc.get("now_wh") is not None:
        pc = lambda a, b: f" ({'+' if a >= b else '−'}{fmt(abs(a / b - 1) * 100, 0)} %)" if b else ""
        L.append(f"🏠 Chata dnes {fmt(cc['now_wh'] / 1000, 2)} kWh" + (f", obvykle do teď {fmt(cc['typ_wh'] / 1000, 2)}{pc(cc['now_wh'], cc['typ_wh'])}" if cc.get("typ_wh") else "")
                 + (f" · minulá noc {fmt(cc['night_wh'] / 1000, 2)} kWh, obvykle {fmt(cc['night_typ_wh'] / 1000, 2)}{pc(cc['night_wh'], cc['night_typ_wh'])}"
                    if cc.get("night_wh") is not None and cc.get("night_typ_wh") else ""))
    if day.get("on") is not None:
        L.append(f"💡 Světla, kamery, wifi dnes mezi 0 a 5 h ~{fmt(day['on'])} W")
    wxo = data.get("wxo") or {}
    ol = wxo.get("ol") or {}
    od = ol.get("days") or []
    if len(od) > 1:
        t = od[1]
        line = f"🌤 Zítra {t['txt'] or ''} ~{fmt(t['kwh'], 1)} kWh"
        if ol.get("mode") == "zima":
            okd = next((x for x in od[1:] if x.get("ok")), None)
            line += f" · solární baterie zítra ráno ~{fmt(t.get('mvm'), 2)} V"
            line += (f"\n☀️ Připojit chatu na solární baterii jde nejdřív: {datetime.strptime(okd['d'], '%Y-%m-%d').strftime('%-d. %-m.')}"
                     if okd else "\n❄️ Příštích 7 dní nebude solární baterie dost nabitá k připojení")
        else:
            if od[0].get("mv") is not None:
                line += f" · zítra ráno ~{fmt(od[0]['mv'], 2)} V"
            if t.get("mv") is not None:
                line += f" · pozítří ráno ~{fmt(t['mv'], 2)} V"
        L.append(line)
    if wxo.get("acc_med") is not None:
        L.append(f"🎯 Předpověď výroby: odchylka obvykle ±{wxo['acc_med']} % (posledních {len(wxo.get('acc') or [])} dní)")
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


def watch_publish(data, v, st, now, topic, cfg):
    """Krátké shrnutí pro hodinky (Wear OS dlaždice + komplikace) do ntfy <topic>-hodinky."""
    bv = v.get("bat_v")
    if bv is None:
        return
    lvl = 0
    if cfg["baterie_kriticka_V"] and bv < cfg["baterie_kriticka_V"]:
        lvl = 2
    elif cfg["baterie_slabne_V"] and bv < cfg["baterie_slabne_V"]:
        lvl = 1
    inv = data.get("inverter") or {}
    fresh = inv and now.timestamp() - inv.get("t", 0) < 1800
    stc = int(v["status"]) if v.get("status") is not None else -1
    # Boost pod ~14,1 V = nabíjí plným proudem; nad = dobíjí (napětí drží, proud klesá – „100 %“ podle regulátoru, ale ještě ne plná)
    st_txt = {1: "nabito", 2: "dobíjí" if bv >= 14.1 else "nabíjí", 3: "vyrovnává", 0: "nenabíjí"}.get(stc, "")
    f = data.get("forecast")
    fc = ""
    if f and f.get("until"):
        if f.get("t_off"):
            fc, lvl = f"🌙 {do_rana(f['until'], now)} NEVYDRŽÍ", max(lvl, 2)
        elif f.get("t_crit"):
            fc, lvl = f"🌙 {do_rana(f['until'], now)} těsně", max(lvl, 1)
        else:
            fc = f"🌙 {rel_day(f['until'], now)} ráno ~{fmt(f.get('v_until'), 1)} V ✓"
    else:
        preds = ((data.get("wxo") or {}).get("preds") or [])
        t = next((p for p in preds if p["d"] == (now.date() + timedelta(days=1)).isoformat()), None)
        if t:
            fc = f"zítra {t.get('txt') or ''} ~{fmt(t['kwh'], 1)} kWh".replace("  ", " ")
    rs = data.get("river_sup")
    if rs and rs.get("plug"):          # bez EcoFlow: jen ze zásuvky na výstupu River (% a výdrž neznáme)
        t0 = datetime.fromtimestamp(rs["t0"], TZ)
        od = t0.strftime("%H:%M") if t0.date() == now.date() else f"{rel_day(rs['t0'], now)} {t0.strftime('%H:%M')}"
        fc = f"🔋 {rs['name']} · {rs['now']} W\nod {od} · {fmt(rs['wh'] / 1000, 2)} kWh"
    elif rs:
        hh =f"{rs['h']:.0f} h" if rs["h"] >= 1.5 else f"{rs['h'] * 60:.0f} min"
        fc = f"🔋 River {rs['soc']} % · ~{hh}\ndo {rel_day(rs['until'], now)} {datetime.fromtimestamp(rs['until'], TZ).strftime('%H:%M')}"
        if rs["soc"] <= (cfg["river_vymenit_pod"] or 15):
            lvl = max(lvl, 1)
    rv_ok = None                            # River vydrží do rána (jen s EcoFlow – známe % a výdrž)
    if rs and rs.get("until"):
        r_, s_ = sun_times(cfg["sirka"], cfg["delka"], now.date())
        mor = r_ if r_ and now < r_ else sun_times(cfg["sirka"], cfg["delka"], now.date() + timedelta(days=1))[0]
        rv_ok = bool(mor and rs["until"] >= mor.timestamp())
    hq = data.get("hq") or {}               # nabití # (z Ah): hodinky 1.7+ ho ukazují jako samostatný výrazný řádek
    body = {"t": int(now.timestamp()), "v": round(bv, 2), "soc": None if hq.get("pct") is not None else v.get("bat_soc"),
            "pv": round(v["pv_w"]) if v.get("pv_w") is not None else None,
            "w": (round((inv.get("mw") or 0) + (inv.get("rw") or 0)) if fresh and (inv.get("mw") is not None or inv.get("rw") is not None) else None),   # celá chata: solár + River
            "st": st_txt, "fc": fc, "lvl": lvl, "day": v.get("day_kwh"), "hq": hq.get("pct"),
            "ra": bool((data.get("river_auto") or {}).get("on")), "vmin": cfg["odpojeni_V"] or 11.6,
            "lat": cfg["sirka"], "lon": cfg["delka"],
            "rv": ({"s": rs.get("soc"), "h": rs.get("h"), "w": rs["w"], "u": rs.get("until"), "n": rs["name"],
                    "now": rs.get("now"), "t0": rs.get("t0"), "wh": rs.get("wh"), "ok": rv_ok} if rs else None)}           # poloha chaty – hodinky z ní počítají východ / západ slunce
    try:
        req = urllib.request.Request(f"https://ntfy.sh/{topic}-hodinky", data=json.dumps(body).encode(),
                                     headers={"Title": "chata", "Priority": "1"}, method="POST")
        urllib.request.urlopen(req, timeout=15).read()
    except Exception as e:
        print("Hodinky (ntfy):", e)


def overload_check(v, st, now, topic, cfg, data, rise, set_):
    """Přes den: odběr za měničem je větší, než panely dají → čistý proud do baterie je záporný."""
    if not cfg.get("odber_hlidat") or not rise or not (rise + timedelta(minutes=30) <= now <= set_):
        return
    inv = data.get("inverter") or {}
    bv, ba = v.get("bat_v"), v.get("bat_a")
    if not inv or now.timestamp() - inv.get("t", 0) > 1200 or inv.get("mw") is None or not bv or ba is None:
        return
    load_a = (inv["mw"] / 0.88 + (cfg["menic_vlastni_W"] or 0)) / bv
    net = ba - load_a
    data["net_a"] = round(net, 1)
    # běžný odběr teď = lednice (měřená) + obvyklé světla/kamery/wifi (noční medián) → „navíc“ je to ostatní
    fr = next((p for p in inv.get("tp", []) if p.get("ip") == str(cfg.get("zasuvka_lednice") or "").strip()), None)
    ons = sorted(d["on"] for k, d in sorted(data.get("days", {}).items())[-8:] if d.get("on") is not None)
    # 3.22: když zásuvka lednice nepošle hodnotu, počítat s lednicí naplno (běžící kompresor) – ne s 0 W.
    # Dřív se chybějící lednice brala jako 0 W a kompresor (~55 W) se hlásil jako odběr navíc.
    fr_ok = fr and fr.get("w") is not None and not fr.get("err") and not fr.get("off")
    fr_w = fr["w"] if fr_ok else (cfg.get("lednice_max_W") or 80)
    base = ons[len(ons) // 2] if ons else 10
    normal = fr_w + base
    extra = inv["mw"] - normal
    data["extra_w"] = round(extra)
    lim = cfg.get("odber_z_baterie_A") or 2.0
    navic_min = cfg.get("odber_navic_W") or 40
    # nabíjení River ze soláru (zásuvka 8 za měničem, NEMĚŘÍ) – když je zapnutá nebo ji automatika právě vypnula
    # (Flip povel provede až při dalším měření), je „navíc“ nejspíš ona → automatika to řeší sama, nepoplašit
    rip = str(cfg.get("river_auto_ip") or "").strip()
    rp = next((p for p in inv.get("tp", []) if str(p.get("ip")) == rip), None)
    river_on = bool(st.get("ra_on")) or bool(rp and rp.get("on") == 1 and not rp.get("off"))
    just_off = now.timestamp() - st.get("ra_off_ts", 0) < 20 * 60
    # potvrzení průměrem za ~10 min (z počítadel zásuvek): krátká špička v jednom měření sama nestačí;
    # velký odběr (≥ 300 W) se hlásí hned
    avg = inv.get("avg") or {}
    m_avg = avg.get(str(cfg.get("zasuvka_menic") or inv.get("mip") or ""))
    f_avg = avg.get(str(cfg.get("zasuvka_lednice") or "").strip())
    extra_avg = (m_avg - (f_avg if f_avg is not None else fr_w) - base) if m_avg is not None else None
    data["extra_avg_w"] = round(extra_avg) if extra_avg is not None else None
    sustained = extra_avg is None or extra_avg >= navic_min
    hit = net < -lim and extra >= navic_min and (extra >= 300 or sustained) \
        and not ((river_on or just_off) and cfg.get("river_auto"))
    if net < -lim and extra >= navic_min and not hit and extra_avg is not None:
        log("ev", f"Krátká špička za měničem {fmt(inv['mw'])} W (průměr za {inv.get('avg_dt', 0) // 60} min jen {fmt(m_avg)} W) – bez upozornění")
    fr_txt = f"lednice {fmt(fr_w)} W" if fr_ok else f"lednice neměřená – počítám ~{fmt(fr_w)} W"
    mip = str(cfg.get("zasuvka_menic") or inv.get("mip") or "")
    skip = {mip, rip, str(cfg.get("zasuvka_lednice") or "")} | set(ips(cfg.get("zasuvky_river")))
    import re as _re
    others = [f"{_re.sub(r'^\s*(\([^)]*\)\s*)+', '', str(p.get('n') or p.get('ip')))} {fmt(p['w'])} W"
              for p in inv.get("tp", []) if str(p.get("ip")) not in skip and (p.get("w") or 0) >= 3]
    mp_ = next((p for p in inv.get("tp", []) if str(p.get("ip")) == mip), {})
    src = (f"\nZásuvka 220 V: „{mp_.get('n')}“ (IP .{mp_.get('a') or mp_.get('ip')}"
           + (f", zařízení …{mp_['d']}" if mp_.get("d") else "") + f") hlásila {fmt(mp_.get('w'))} W.") if mp_ else ""
    hint = src
    if river_on and not cfg.get("river_auto"):
        hint += "\nZásuvka nabíjení River je zapnutá (neměří) – nejspíš je to ona."
    elif rp and rp.get("on") == 1:
        hint += "\nZásuvka nabíjení River je zapnutá (neměří)."
    if hit:
        log("ev", f"Odběr navíc: měnič {fmt(inv['mw'])} W = {fr_txt} + běžně {fmt(base)} W + navíc {fmt(extra)} W (baterie {fmt(net, 1)} A)")
    if hit and now.timestamp() - st.get("ovl_ts", 0) > 3600:
        ntfy(topic, f"⚡ Odběr navíc ~{fmt(extra)} W – bere se z baterie",
             f"Za měničem teď {fmt(inv['mw'])} W = {fr_txt} + světla/kamery/wifi běžně ~{fmt(base)} W + navíc ~{fmt(extra)} W "
             f"(nabíjení zařízení?). Panely dají {fmt(v.get('pv_w'))} W, baterie se vybíjí ~{fmt(-net, 1)} A ({fmt(bv, 2)} V).\n"
             f"Měřené zásuvky teď: {', '.join(others) if others else 'nic dalšího nebere'} (měřeno {datetime.fromtimestamp(inv['t'], TZ).strftime('%H:%M')})."
             + (f"\nPrůměr za posledních {inv.get('avg_dt', 0) // 60} min: za měničem {fmt(m_avg)} W, navíc ~{fmt(extra_avg)} W." if extra_avg is not None else "")
             + hint, 4, "zap,warning")
        st["ovl_ts"] = int(now.timestamp())


def fuse_check(v, st, now, topic, cfg):
    """Nabíjecí proud blízko pojistky mezi regulátorem a baterií."""
    a = v.get("bat_a")
    fuse = cfg.get("pojistka_A") or 30
    lim = fuse * 1.1                       # okamžité varování nad 110 % (pojistka snese 100 % trvale, pálí až ~135 %)
    if a is None:
        return
    day = now.strftime("%Y-%m-%d")
    if a >= lim and st.get("fuse_day") != day:
        ntfy(topic, f"⚡ Nabíjecí proud {fmt(a, 1)} A – blízko pojistky {fmt(fuse)} A",
             f"Panely teď dávají {fmt(v.get('pv_w'))} W. Pokud jsou zapojené dva panely, odpoj jeden, ať se nespálí pojistka.", 5, "warning,zap")
        st["fuse_day"] = day


def track_soc(data, st, v, now, cfg, inv, mode):
    """Vlastní odhad stavu nabití: počítání Ah (nabíjení − odběr), v noci zpřesnění podle napětí, Float = 100 %."""
    cap = eff_cap(data, cfg)
    bv, ba, status = v.get("bat_v"), v.get("bat_a"), v.get("status")
    if not bv:
        return
    s, t0 = st.get("soc"), st.get("soc_t")
    ts = now.timestamp()
    fresh = inv and ts - inv["t"] < 1800
    load_w = inv.get("mw") if fresh and inv.get("mw") is not None else (0 if mode == "zima" else cfg["noc_spotreba_W"] or 0)
    idle = 0 if mode == "zima" else (cfg["menic_vlastni_W"] or 0)
    load_a = (load_w / 0.88 + idle) / bv if load_w or idle else 0.0
    rise, set_ = sun_times(cfg["sirka"], cfg["delka"], now.date())
    night = rise and (now < rise - timedelta(minutes=10) or now > set_ + timedelta(hours=2))
    if status is not None and int(status) == 1:
        st["soc_fl"] = st.get("soc_fl", 0) + 1
    else:
        st["soc_fl"] = 0
    if st["soc_fl"] >= 2:
        s = 100.0
    elif s is None or t0 is None or ts - t0 > 6 * 3600:
        s = soc_from_v(bv + load_a * 0.015) if (v.get("pv_w") or 0) < 5 else (v.get("bat_soc") or 50)
    else:
        dt = min(ts - t0, 1800)
        s += ((ba or 0) * 0.92 - load_a) * dt / 3600 / cap * 100
        if night and load_a < 6:                # v klidu napětí ≈ stav nabití → pomalu dorovnat
            s += (soc_from_v(bv + load_a * 0.015) - s) * 0.15
    s = max(0.0, min(100.0, s))
    st["soc"], st["soc_t"] = s, ts
    data["soc_est"] = round(s)


def detect_mode(data, st, cfg, now, inv):
    """Letní provoz = chata jede z měniče (solární baterie); zimní = měnič vypnutý, chatu napájí River."""
    want = str(cfg.get("rezim") or "auto").strip().lower()
    if want in ("leto", "léto", "zima"):
        mode = "zima" if want == "zima" else "leto"
        data["mode"] = {"m": mode, "auto": False}
        st["mode"] = mode
        return mode
    guess = None
    if inv and now.timestamp() - inv["t"] < 3600:
        st_off = str(inv.get("st", "")).upper() in ("OFF",)
        mplug = next((p for p in inv.get("tp", []) if p.get("ip") == inv.get("mip")), None)
        menic_dead = st_off or (mplug is not None and (mplug.get("off") or (mplug.get("w") is not None and mplug["w"] < 1)))
        river_w = inv.get("rw") or 0
        if menic_dead and river_w > 3:
            guess = "zima"
        elif (inv.get("mw") or 0) > 3:
            guess = "leto"
    mode = st.get("mode") or "leto"
    if guess and guess != mode:                 # přepnout až po 3 bězích za sebou (30 min)
        st["mode_n"] = st.get("mode_n", 0) + 1
        if st["mode_n"] >= 3:
            log("ev", "Přechod na zimní provoz (chatu napájí River)" if guess == "zima" else "Přechod na letní provoz (chata jede ze solární baterie)")
            mode, st["mode_n"], st["mode_since"] = guess, 0, int(now.timestamp())
    else:
        st["mode_n"] = 0
    st["mode"] = mode
    data["mode"] = {"m": mode, "auto": True, "since": st.get("mode_since")}
    return mode


def cabin_consumption(data, cfg, mode, now):
    """Spotřeba chaty za den (Wh na výstupu, AC) – medián posledních 7 celých dní.

    Léto: lednice + ostatní (světla, kamery, wifi) – BEZ nabíjení River přebytkem (to není spotřeba chaty).
    Když chybí, zásuvka měniče za dny, kdy se River nenabíjela. Zima: zásuvky na River.
    """
    inv = data.get("inverter") or {}
    mip = inv.get("mip") or str(cfg.get("zasuvka_menic") or "").strip()
    fip = str(cfg.get("zasuvka_lednice") or "").strip()
    rivers = ips(cfg.get("zasuvky_river"))
    vals = []
    for k in sorted(data["days"])[-9:-1]:
        day = data["days"][k]
        tp = day.get("tp") or {}
        if mode == "zima":
            x = sum(tp.get(i, 0) for i in rivers)
        elif fip and tp.get(fip) and day.get("on") is not None:
            x = tp[fip] + day["on"] * 24
        elif mip and not day.get("ra_min"):
            x = tp.get(mip)
        else:
            x = None
        if x and x > 50:
            vals.append(x)
    if len(vals) >= 2:
        vals.sort()
        return vals[len(vals) // 2]
    return (cfg["noc_spotreba_W"] or 30) * 24


def outlook(data, st, cfg, now, mode, preds):
    """Simulace stavu solární baterie na 7 dní podle předpovědi výroby a spotřeby chaty.

    Léto: chata jede ze solární baterie celý den i noc.
    Zima: solární baterie se jen nabíjí; den „k připojení“ = ráno ≥ zima_pripojit_od_V a po dni
    s chatou na solární baterii zůstane ≥ zima_pripojit_do_V.
    """
    cap = eff_cap(data, cfg)
    idle = cfg["menic_vlastni_W"] or 0
    ac_day = cabin_consumption(data, cfg, mode, now)               # Wh AC za 24 h
    dc_day = ac_day / 0.88 + idle * 24                             # Wh z baterie za 24 h (při zapojení)
    soc = data.get("soc_est")
    if soc is None or not preds:
        return None
    today = now.date().isoformat()
    produced = (data["days"].get(today) or {}).get("solar_kwh") or 0
    rows = []
    for p in preds[:7]:
        dd = Date_from(p["d"])
        rise, set_ = sun_times(cfg["sirka"], cfg["delka"], dd)
        light_h = (set_ - rise).total_seconds() / 3600 if rise else 10
        kwh = p["kwh"]
        if p["d"] == today:
            kwh = max(0.0, kwh - produced) if now < set_ else 0.0
            frac_day = max(0.0, min(1.0, (set_ - now).total_seconds() / 3600 / light_h)) if rise and now < set_ else 0.0
        else:
            frac_day = 1.0
        gain = kwh * 1000 * 0.9 / 12.8 / cap * 100                     # % z výroby
        day_use = dc_day * light_h / 24 / 12.4 / cap * 100 * frac_day  # % spotřeba přes den
        night_use = dc_day * (24 - light_h) / 24 / 12.4 / cap * 100     # % spotřeba v noci
        morning = soc
        r = {"d": p["d"], "kwh": p["kwh"], "txt": p["txt"], "m": round(morning)}
        if mode == "zima":
            od = soc_from_v(cfg["zima_pripojit_od_V"] or 12.7)
            do = soc_from_v(cfg["zima_pripojit_do_V"] or 12.4)
            full_day_use = dc_day * light_h / 24 / 12.4 / cap * 100
            r["after"] = round(max(0, min(100, morning + gain - full_day_use)))
            r["ok"] = bool(p["d"] != today and morning >= od and r["after"] >= do)
            r["mvm"] = round(v_from_soc(morning), 2)                   # solární baterie ráno (v klidu)
            r["av"] = round(v_from_soc(r["after"]) - 0.04, 2)          # po dni s chatou
            soc = min(100.0, soc + gain)                               # bez připojení se jen nabíjí
            r["e"] = round(soc)
            r["ev"] = round(v_from_soc(soc), 2)                 # klidové napětí solární baterie večer
        else:
            e = morning + gain - day_use
            r["waste"] = round(max(0.0, e - 100) / 100 * cap * 12.8 / 1000, 2)
            e = max(0.0, min(100.0, e))
            r["e"] = round(e)
            soc = max(0.0, e - night_use)
            r["nm"] = round(soc)                                       # ráno dalšího dne
            r["mv"] = round(v_from_soc(soc) - 0.04, 2)                 # napětí ráno (pod malým odběrem)
        rows.append(r)
    return {"mode": mode, "days": rows, "ac_day": round(ac_day), "dc_day": round(dc_day)}


def Date_from(k):
    return datetime.strptime(k, "%Y-%m-%d").date()


def weather_and_outlook(data, st, cfg, now, topic, mode):
    if not cfg.get("pocasi"):
        data["wxo"] = None
        return
    import pocasi
    import panely
    n_now = int(cfg.get("panely_pocet") or 1)
    nh = data.setdefault("np_hist", [])
    if not nh:                                  # 2 panely zapojené zhruba od začátku září 2026 (podle Petra)
        nh.append(["2026-09-01", 2] if n_now == 2 else [now.date().isoformat(), n_now])
    if nh[-1][1] != n_now:                      # změna v nastavení = přepojení panelů
        nh.append([now.date().isoformat(), n_now])
        log("ev", f"Zapojené panely: {n_now}")
    lab, _ = panely.label_panels(data, cfg, now.date())
    pocasi.update_weather(data, cfg, now, log=lambda m: (print(m), "selhal" in m and log("err", m)))
    pocasi.evaluate(data, cfg, sun_times, now.date())
    preds, bf, bn = pocasi.predict_days(data, cfg, sun_times, now, lab, n_now)
    pocasi.remember_forecast(data, preds, now)
    acc, med = pocasi.accuracy(data, now.date())
    ol = outlook(data, st, cfg, now, mode, preds)
    typ = pocasi.typical_kwh(data, cfg, sun_times, now.date(), now.date())
    need = ol["dc_day"] / 1000 / 0.9 if ol else None
    pp = panely.plan(data, st, cfg, now, [(p["d"], p["k1"]) for p in preds], need, mode)
    data["wxo"] = {"preds": preds, "bias": round(bf, 2), "bias_n": bn, "acc": acc, "acc_med": med,
                   "ol": ol, "typ": typ, "t": int(now.timestamp()), "pan": pp}
    if cfg.get("panely_doporucit") and pp.get("rec") and now.hour >= 18 and \
            (st.get("pan_rec") != pp["rec"] or now.timestamp() - st.get("pan_sent", 0) > 7 * 86400):
        title = {"add": "🔆 Zapoj druhý panel", "wait": "⏳ Jeden panel nestačí – druhý ještě ne",
                 "remove": "⚠️ Odpoj druhý panel"}[pp["rec"]]
        ntfy(topic, title, pp["msg"] + "\nPo přepojení přepni počet panelů v Nastavení.", 4 if pp["rec"] == "remove" else 3, "sunny")
        st["pan_rec"], st["pan_sent"] = pp["rec"], int(now.timestamp())
    if not ol:
        return
    days = ol["days"]
    # zima: zítra je den k připojení solární baterie
    if mode == "zima" and len(days) > 1 and now.hour >= 18:
        t = days[1]
        tomorrow = t["d"]
        if t.get("ok") and st.get("connect_sent") != tomorrow:
            ntfy(topic, "☀️ Zítra můžeš chatu připojit na solární baterii",
                 f"Zítra ráno ~{fmt(t.get('mvm'), 2)} V, zítra {t['txt'] or ''} ~{fmt(t['kwh'], 1)} kWh, zítra večer s chatou zbyde ~{fmt(t.get('av'), 2)} V.\n"
                 f"Zítra večer zase přepoj na River.", 3, "sunny,battery")
            st["connect_sent"] = tomorrow
    # přechody sezón (nejvýš jednou za 14 dní)
    if cfg.get("sezona_upozornit") and len(days) >= 5 and now.hour >= 18 and now.timestamp() - st.get("season_sent", 0) > 14 * 86400:
        avg = sum(d["kwh"] for d in days[1:6]) / 5
        need = ol["dc_day"] / 1000 / 0.9
        mon = now.month
        if mode == "leto" and mon in (9, 10, 11, 12, 1) and avg < need * 0.9 and min(d["nm"] for d in days[1:6]) < 40:
            ntfy(topic, "🍂 Blíží se zimní provoz",
                 f"Příštích 5 dní vyrobí panely ~{fmt(avg, 2)} kWh/den. {need_txt(ol, need)}\n"
                 f"Baterie by v některém z příštích rán klesla až na ~{fmt(min(d['mv'] for d in days[1:6]), 2)} V. Zvaž přechod na River.", 3, "fallen_leaf")
            st["season_sent"] = int(now.timestamp())
        elif mode == "zima" and mon in (2, 3, 4, 5) and avg > need * 1.3:
            ntfy(topic, "🌱 Můžeš přejít na letní provoz",
                 f"Příštích 5 dní vyrobí panely ~{fmt(avg, 2)} kWh/den. {need_txt(ol, need)}", 3, "seedling")
            st["season_sent"] = int(now.timestamp())


def need_txt(ol, need):
    """Srozumitelně: kolik chata opravdu spotřebuje a kolik k tomu musí panely vyrobit navíc kvůli ztrátám."""
    ac = (ol.get("ac_day") or 0) / 1000
    dc = (ol.get("dc_day") or 0) / 1000
    return (f"Panely musí vyrobit ~{fmt(need, 2)} kWh/den = chata {fmt(ac, 2)} (lednice, světla, kamery, wifi)"
            f" + měnič {fmt(dc - ac, 2)} (účinnost a jeho vlastní spotřeba) + nabíjení baterie {fmt(need - dc, 2)}.")


def other_load(data, st, cfg, now, topic, inv, ra_on):
    """Ostatní odběr za měničem (světla, kamery, wifi) = zásuvka měniče − lednice (bez doby nabíjení River)."""
    if not inv or now.timestamp() - inv["t"] > 1200 or inv.get("mw") is None or ra_on:
        return None
    if (inv.get("mw") or 0) <= 3:
        return None                              # 5.43: měnič nedodává (chata na River) – ostatní odběr za měničem nejde spočítat
    fr = next((p for p in inv.get("tp", []) if p.get("ip") == str(cfg.get("zasuvka_lednice") or "").strip()), None)
    if not fr or fr.get("w") is None:
        return None
    ow = round(max(0.0, inv["mw"] - fr["w"]), 1)
    return ow


def other_load_check(data, st, cfg, now, topic):
    """Noční medián ostatního odběru (0–5 h) po dnech; upozornit na výraznou změnu."""
    pts = data.get("points", [])
    today = now.strftime("%Y-%m-%d")
    if not st.get("on_fix1"):                    # 5.43: noci na River dávaly 0 W – přepočítat dny, pro které máme body
        cut = (now - timedelta(days=14)).strftime("%Y-%m-%d")
        for k, d_ in data["days"].items():
            if k >= cut:
                d_.pop("on", None)
        st["on_fix1"] = 1
    for k in sorted(data["days"])[-8:]:
        day = data["days"][k]
        if "on" in day:
            continue
        a0 = datetime.strptime(k, "%Y-%m-%d").replace(tzinfo=TZ).timestamp()
        if k == today and now.hour < 5:
            continue
        vals = sorted(p["ow"] for p in pts if a0 <= p["t"] < a0 + 5 * 3600 and p.get("ow") is not None
                      and (p.get("mw") or 0) > 3)        # 5.43: jen body, kdy měnič dodával (ne chata na River)
        if len(vals) >= 12:
            day["on"] = vals[len(vals) // 2]
    if not cfg.get("ostatni_hlidat"):
        return
    k = today
    cur = (data["days"].get(k) or {}).get("on")
    hist = sorted(d["on"] for kk, d in data["days"].items() if kk < k and d.get("on") is not None)[-14:]
    if cur is None or len(hist) < 5 or st.get("on_sent") == k:
        return
    med = sorted(hist)[len(hist) // 2]
    if abs(cur - med) > max(5, med * 0.5):
        what = "víc" if cur > med else "míň"
        ntfy(topic, f"💡 Dnes v noci (0–5 h) šlo {what} proudu na světla/kamery/wifi",
             f"Ostatní odběr za měničem dnes mezi 0 a 5 h ~{fmt(cur)} W, obvykle ~{fmt(med)} W."
             + (" Nezůstalo něco zapnuté?" if cur > med else " Nevypadla kamera nebo wifi?"), 3, "bulb")
        st["on_sent"] = k


def cabin_on_river(data, cfg, now, st=None):
    """5.43: chata teď jede z River (měnič nedodává, některá zásuvka River ano, nebo EcoFlow hlásí River napájí chatu).
    S pamětí 30 min (st["onriv_t"]), ať krátký výkyv odběru nespustí upozornění určená pro chatu na soláru."""
    inv = data.get("inverter") or {}
    ts = now.timestamp()
    fresh = inv and ts - inv.get("t", 0) < 1800
    rids = ips(cfg.get("zasuvky_river"))
    on = bool(fresh and (inv.get("mw") or 0) <= 3 and any(
        str(p.get("ip")) in rids and (p.get("w") or 0) > 3 for p in inv.get("tp", [])))
    on = on or bool((data.get("river_sup") or {}).get("w"))
    if st is not None:
        if on:
            st["onriv_t"] = int(ts)
        elif fresh and (inv.get("mw") or 0) > 3:
            st.pop("onriv_t", None)                   # měnič dodává = chata na soláru – hned
        on = on or ts - st.get("onriv_t", 0) < 1800
    return on


def net_usage(data, st, now, cfg):
    """5.44: kolik dat přenesl router M7000 (mobilní internet chaty) a kolik z toho Flip (celý telefon přes Wi‑Fi,
    z toho aplikace Brána). Router: čítač wan.totalStatistics (bajty), Flip: TrafficStats od zapnutí telefonu.
    Přírůstky po dnech → days[k]["net"] = {rt, ph, app} (bajty); při restartu / vynulování čítače se bere nová hodnota.
    data["net"] = {dnes…, info: klíče, které router posílá}."""
    inv = data.get("inverter") or {}
    ts = now.timestamp()
    if not inv or ts - inv.get("t", 0) > 1800 or inv.get("t") == st.get("net_t"):
        return
    st["net_t"] = inv.get("t")
    c = st.setdefault("netc", {})
    day = data["days"].setdefault(now.strftime("%Y-%m-%d"), {}).setdefault("net", {})
    pd = {}                                         # 5.52: přírůstky do posledního bodu (graf po hodinách)

    def add(name, cur, reset=False):
        if cur is None:
            return
        last = c.get(name)
        if last is None:
            d = 0                                   # první hodnota – jen zapamatovat
        elif reset or cur < last:
            d = cur                                 # restart / vynulování čítače
        else:
            d = cur - last
        c[name] = cur
        if d > 0:
            day[name] = round(day.get(name, 0) + d)
            pd[name] = d

    net = (inv.get("rt") or {}).get("net") or {}
    tot = next((net[k] for k in net if k.lower() == "totalstatistics"), None)
    if tot is None:
        tot = next((net[k] for k in net if "total" in k.lower() and isinstance(net[k], (int, float))), None)
    add("rt", tot)
    nb = inv.get("nb") or {}
    reboot = nb.get("up") is not None and c.get("up") is not None and nb["up"] < c["up"]
    if nb.get("up") is not None:
        c["up"] = nb["up"]
    if nb.get("ph") is not None:
        add("ph", nb["ph"] - (nb.get("mob") or 0), reboot)      # jen Wi‑Fi (bez mobilních dat Flipu)
    add("app", nb.get("app"), reboot)
    pts = data.get("points") or []
    if pts and ts - pts[-1]["t"] < 900:
        if pd.get("rt"):
            pts[-1]["nr"] = round(pd["rt"])
        if pd.get("ph"):
            pts[-1]["np"] = round(pd["ph"])
    data["net"] = {"day": dict(day), "dev": net.get("dev"),
                   "rt_day": next((net[k] for k in net if k.lower() == "dailystatistics"), None),
                   "info": {"wk": net.get("_wk"), "k": net.get("_k"),
                            "vals": {k: v for k, v in net.items() if not k.startswith("_")}} if net else None}


def ips(txt):
    import re
    return [x for x in re.split(r"[,;\s]+", str(txt or "")) if x]


def inv_from_msg(last, now, cfg=None):
    """Jedna zpráva Flipu (ntfy) → slovník měniče a zásuvek (bez zápisu do data)."""
    try:
        body = json.loads(last.get("message") or "{}")
    except ValueError:
        return None
    t_msg = int(last.get("time") or now.timestamp())
    try:                                   # Flip 1.3.4+: čas měření (zpráva mohla odejít později z fronty)
        t_meas = int(body.get("ts") or 0)
    except (TypeError, ValueError):
        t_meas = 0
    inv = {"t": t_meas if 0 < t_meas <= t_msg + 60 and t_msg - t_meas < 2 * 86400 else t_msg}
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
    if isinstance(body.get("fc"), dict):                 # 1.6: řízení nabíjení Flipu (stav zásuvky a proč)
        inv["fc"] = body["fc"]
    if isinstance(body.get("rc"), dict):                 # 1.9: řízení nabíjení routeru (stav zásuvky a proč)
        inv["rc"] = body["rc"]
    else:
        inv.pop("rc", None)
    if isinstance(body.get("rt"), dict):                 # 1.7: baterie routeru M7000 (jen čtení)
        inv["rt"] = {k: body["rt"].get(k) for k in ("b", "c", "err", "net") if body["rt"].get(k) is not None}
    if isinstance(body.get("nb"), dict):                 # 1.9.3: data přenesená Flipem (aplikace Brána / celý telefon)
        inv["nb"] = {k: body["nb"].get(k) for k in ("up", "app", "ph", "mob") if body["nb"].get(k) is not None}
    else:
        inv.pop("nb", None)
    th = body.get("th")                                   # 1.5: teploměry Xiaomi [{n, t, h, b, age}]
    if isinstance(th, list):
        import re as _re                                  # 5.10: jméno bez čárek / středníků na krajích („, ,Lednice“)
        inv["th"] = [{"n": _re.sub(r"^[\s,;:.]+|[\s,;:.]+$", "", str(x.get("n")))[:30], "t": x.get("t"), "h": x.get("h"), "b": x.get("b"),
                      "tm": int(inv.get("t") or 0) - int(x.get("age") or 0), "sn": x.get("sn"), "ok": x.get("ok")}
                     for x in th if isinstance(x, dict) and x.get("n")]   # 1.7.7: sn/ok = zachyceno/přečteno
    tp = body.get("tp")
    if isinstance(tp, list):
        inv["tp"] = [{k: p.get(k) for k in ("n", "w", "wh", "on", "err", "ip", "off", "nm", "a", "since", "gone", "d", "lt") if p.get(k) is not None}
                     for p in tp if isinstance(p, dict)][:16]
        # zásuvka se pozná podle čísla v první závorce jména („(3) (R) River…“), ne podle IP – i se starším Flipem
        import re as _re
        for p in inv["tp"]:
            m = _re.match(r"\s*\((\d{1,3})\)", str(p.get("n") or ""))
            if m and str(p.get("ip")) != str(int(m.group(1))):
                p["a"] = p.get("a") or p.get("ip")
                p["ip"] = str(int(m.group(1)))
    if body.get("wifi") is not None:
        inv["wifi"] = int(body["wifi"])
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
    if menic:
        inv["mip"] = menic.get("ip")     # i když je vypnutá (zimní provoz: měnič vypnutý)
    if menic and menic.get("w") is not None:
        if "w" in inv:
            inv["va"] = inv["w"]
        inv["mw"] = menic["w"]           # odběr ze solární baterie (přes měnič)
        inv["w"], inv["src"] = menic["w"], "tapo"
    rw = [p["w"] for p in rivers if p.get("w") is not None]
    if rw:
        inv["rw"] = round(sum(rw), 1)    # odběr z River (zimní provoz)
        inv["w"] = round((inv.get("mw") or 0) + inv["rw"], 1)
        inv["src"] = "tapo"
    if gen and (gen.get("w") is not None or gen.get("wh") is not None):
        inv["gen"] = {"w": gen.get("w"), "wh": gen.get("wh"), "off": gen.get("off"), "since": gen.get("since"), "gone": gen.get("gone")}
    if "w" not in inv and not inv.get("tp") and "ph" not in inv:
        return None
    return inv


def wake_flip(topic, wait_s=110):
    """Nouzové „změř hned“ (tlačítko ⚡ Načíst na webu): pošle zprávu na <topic>-wake, Flip (1.3.5+) drží
    spojení a hned změří a odešle. Počká, až nová data z Flipu dorazí (nejvýš wait_s)."""
    t0 = int(time.time())
    try:
        urllib.request.urlopen(urllib.request.Request(f"https://ntfy.sh/{topic}-wake", data=b"mer", method="POST",
                                                      headers={"Priority": "1"}), timeout=15).read()
    except Exception as e:
        print("Probuzení Flipu:", e)
        return
    while time.time() - t0 < wait_s:
        time.sleep(10)
        try:
            lines = urllib.request.urlopen(f"https://ntfy.sh/{topic}-menic/json?poll=1&since={t0}", timeout=15).read().decode().splitlines()
            if any('"event":"message"' in ln for ln in lines):
                print(f"Flip odpověděl za {int(time.time() - t0)} s")
                return
        except Exception:
            pass
    if wait_s:
        print("Flip na probuzení neodpověděl (starší verze, spí nebo bez internetu)")


def read_inverter(data, topic, now, cfg=None):
    """Poslední zpráva z ESP32 u měniče (posílá do ntfy tématu <NTFY_TOPIC>-menic každých 10 min).

    Formát zprávy: JSON {"w": průměr VA, "max": max VA, "v": napětí baterie, "st": stav, "al": alarm}.
    """
    url = f"https://ntfy.sh/{topic}-menic/json?poll=1&since=12h"
    lines = []
    try:
        lines = urllib.request.urlopen(url, timeout=20).read().decode().strip().splitlines()
    except Exception as e:
        print("Měnič (ntfy):", e)
    msgs = []
    for ln in lines:
        try:
            m = json.loads(ln)
            if m.get("event") == "message":
                msgs.append(m)
        except ValueError:
            pass
    # Flip 1.4+: data přímo ve spuštění z GitHubu (parametr „flip“ = pole zpráv); ntfy jen záloha.
    # Poslední dvě zprávy si hlídač pamatuje (běhy bez dat z Flipu – plán, cron-job.org – pak mají z čeho brát).
    st = data.setdefault("state", {})
    gh = []
    raw = os.environ.get("FLIP_DATA", "").strip()
    if raw:
        try:
            for s_ in json.loads(raw):
                b_ = json.loads(s_)
                gh.append({"event": "message", "time": int(b_.get("ts") or time.time()), "message": s_})
            st["flip_gh"] = int(now.timestamp())
            print(f"Flip přes GitHub: {len(gh)} zpráv")
        except (ValueError, TypeError) as e:
            print("Data z Flipu (GitHub):", e)
    seen = {}
    for m in msgs + (st.get("flip_last") or []) + gh:
        seen.setdefault(m.get("message"), m)            # stejná zpráva z více cest jen jednou
    msgs = [m for m in seen.values() if now.timestamp() - int(m.get("time") or 0) < 12 * 3600]
    if not msgs:
        return None

    def _mt(m):
        try:
            return int(json.loads(m.get("message") or "{}").get("ts") or m.get("time") or 0)
        except (ValueError, AttributeError, TypeError):
            return int(m.get("time") or 0)
    msgs.sort(key=_mt)                     # podle času měření (zprávy z fronty Flipu chodí opožděně)
    st["flip_last"] = [{"event": "message", "time": m.get("time"), "message": m.get("message")} for m in msgs[-2:]]
    last = msgs[-1]
    inv = inv_from_msg(last, now, cfg)
    if inv is None:
        return None
    data["_inv_msgs"] = msgs               # všechny zprávy za 12 h – doplnění mezer mezi běhy hlídače
    # kdy naposledy přišla data z Victronu (Bluetooth) – web ukáže, když dlouho nechodí
    for m in reversed(msgs):
        try:
            b_ = json.loads(m.get("message") or "{}")
            if float(b_.get("v") or 0) > 5:
                data["vic_t"] = int(b_.get("ts") or m.get("time")) - int(b_.get("age") or 0)
                break
        except (ValueError, TypeError):
            pass
    # průměrný příkon každé zásuvky za posledních ~10 min z jejího počítadla energie (dvě poslední zprávy):
    # okamžitá hodnota může být krátká špička, průměr ukáže, co opravdu odtéká z baterie
    if len(msgs) >= 2:
        try:
            prev = inv_from_msg(msgs[-2], now, cfg)
            dt = inv["t"] - prev["t"] if prev else 0
            if prev and 300 <= dt <= 1800:
                pw = {p.get("ip"): p.get("wh") for p in prev.get("tp", []) if p.get("wh") is not None}
                avg = {}
                for p in inv.get("tp", []):
                    a, b = pw.get(p.get("ip")), p.get("wh")
                    if a is not None and b is not None and b >= a:
                        avg[p["ip"]] = round((b - a) * 3600 / dt, 1)
                if avg:
                    inv["avg"], inv["avg_dt"] = avg, int(dt)
        except Exception as e:
            print("Průměr zásuvek:", e)
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


def read_tp_history(data, topic, cfg):
    """Hodinová energie, kterou si pamatují samy zásuvky (Flip ji posílá do <topic>-tp-hist).
    Opraví denní součty zásuvek a zpětně doplní / opraví běhy generátoru, které Flip nezachytil."""
    try:
        lines = urllib.request.urlopen(f"https://ntfy.sh/{topic}-tp-hist/json?poll=1&since=24h", timeout=20).read().decode().splitlines()
    except Exception as e:
        print("Historie zásuvek (ntfy):", e)
        return
    th = data.setdefault("tp_hist", {})
    changed = set()
    for ln in lines:
        try:
            m = json.loads(ln)
            if m.get("event") != "message":
                continue
            body = json.loads(m.get("message") or "{}")
        except ValueError:
            continue
        pid = str(body.get("id") or "")
        for dk, arr in (body.get("h") or {}).items():
            if pid and isinstance(arr, list) and 23 <= len(arr) <= 25:          # 5.19: den změny času má 23 / 25 h
                th.setdefault(pid, {})[dk] = [None if x is None or x < 0 else x for x in arr]
                changed.add((pid, dk))
    for pid in th:
        for dk in sorted(th[pid])[:-14]:
            th[pid].pop(dk)
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    for pid, dk in changed:
        arr = th[pid][dk]
        tot = sum(x for x in arr if x)
        day = data["days"].setdefault(dk, {})
        tp = day.setdefault("tp", {})
        cur = tp.get(pid)
        new = max(cur or 0, tot) if dk == today else tot          # minulé dny: zásuvka má pravdu
        if cur is None or abs(new - cur) > 5:
            tp[pid] = round(new, 1)
            if cur is not None and dk != today:
                log("ev", f"Zásuvka ({pid}) {dk}: opraveno {fmt(cur / 1000, 2)} → {fmt(new / 1000, 2)} kWh podle historie zásuvky")
    gip = str(cfg.get("zasuvka_generator") or "").strip()
    if gip and gip in th:
        gen_from_history(data, th[gip])


def gen_from_history(data, hist):
    """Běhy generátoru z hodinové historie jeho zásuvky: doplní chybějící, opraví energii u zaznamenaných."""
    log_ = data.setdefault("gen_log", [])
    now = datetime.now(TZ)
    for dk in sorted(hist):
        arr = hist[dk]
        base = datetime.strptime(dk, "%Y-%m-%d").replace(tzinfo=TZ)
        blocks, cur = [], None
        for hh, wh in enumerate(arr):
            if wh and wh > 3:
                if cur and cur[1] == hh:
                    cur[1], cur[2] = hh + 1, cur[2] + wh
                else:
                    cur = [hh, hh + 1, wh]
                    blocks.append(cur)
            else:
                cur = None
        for h0, h1, wh in blocks:
            # 5.19: hodiny od půlnoci skutečně uplynulé (ne „na ciferníku“) – v den změny času se jinak posune o hodinu
            t0 = base.timestamp() + h0 * 3600
            t1 = base.timestamp() + h1 * 3600
            if t1 > now.timestamp() - 600:
                continue                                         # hodina ještě běží – vyhodnotit později
            ov = [r for r in log_ if r["t0"] < t1 + 600 and r["t1"] > t0 - 600]
            if ov:
                r = ov[0]
                r["wh_h"] = round(wh, 1)
                if not r.get("wh") or abs(r["wh"] - wh) > max(20, wh * 0.1):
                    r["wh_old"], r["wh"], r["kor"] = r.get("wh"), round(wh, 1), True
            else:
                log_.append({"t0": int(t0), "t1": int(t1), "wh": round(wh, 1), "rv": {}, "src": "hist", "kor": True})
                log("ev", f"Generátor: doplněn běh {dk} {datetime.fromtimestamp(t0, TZ).strftime('%H:%M')}–{datetime.fromtimestamp(t1, TZ).strftime('%H:%M')} ({fmt(wh / 1000, 2)} kWh) z historie zásuvky")
    log_.sort(key=lambda r: r["t0"])
    del log_[:-60]


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
        pl = st.get("ph_last") or {}
        bt = f" Naposledy měl baterii {pl['b']:.0f} %{' (nabíjel se)' if pl.get('c') else ' a nenabíjel se'}." if pl.get("b") is not None else ""
        ntfy(topic, "📵 Brána na chatě neposílá data",
             f"Flip se neozval {'přes 12 h' if age > 700 else f'{age:.0f} min'}.{bt} Vybitý, vypnutá Wi-Fi, nebo ho Android uspal?", 4, "warning")
        st["gw_silent"] = True
    if age <= lim:
        if st.get("gw_silent"):
            ntfy(topic, "📱 Brána na chatě zase posílá", "Data z telefonu u měniče znovu chodí.", 2, "white_check_mark")
        st["gw_silent"] = False
    # 5.67: Flip posílá jen záložní cestou (ntfy), ne přes GitHub → hlídač běží jen podle plánu GitHubu (v noci po
    # 30–45 min) a v datech jsou díry. Typicky prošlý / odmítnutý GitHub token ve Flipu.
    gh_age = (now.timestamp() - (st.get("flip_gh") or 0)) / 60
    if inv and age <= lim and st.get("flip_gh") and gh_age > 90 and not st.get("gw_nogh"):
        ntfy(topic, "🐢 Flip neposílá data přes GitHub",
             f"Data z Flipu chodí jen záložní cestou (naposledy přes GitHub před {gh_age / 60:.1f} h), hlídač proto běží jen "
             "každých 30–45 min a v grafech jsou díry.\nV aplikaci Brána se podívej do záznamu na „GitHub odpověděl …“ – "
             "nejspíš prošlý GitHub token (vytvoř nový s Actions: Read and write a vlož ho do Brány).", 4, "turtle,warning")
        st["gw_nogh"] = True
    elif gh_age <= 30:
        st["gw_nogh"] = False
    # Flip mimo Wi‑Fi (na mobilních datech) → nevidí zásuvky
    if inv and age <= lim and inv.get("wifi") is not None:
        if inv["wifi"] == 0 and not st.get("gw_nowifi"):
            ntfy(topic, "📶 Flip není na Wi‑Fi chaty",
                 "Posílá přes mobilní data, takže nevidí zásuvky Tapo (spotřeba, River, generátor, automatika).\n"
                 "Připoj ho na Flipu zpět k Wi‑Fi; v nastavení Wi‑Fi vypni „přepínání na mobilní data“.", 4, "warning")
            st["gw_nowifi"] = True
        elif inv["wifi"] == 1:
            st["gw_nowifi"] = False
    ph = (inv or {}).get("ph")
    if ph and ph.get("b") is not None:
        st["ph_last"] = {"b": ph["b"], "c": bool(ph.get("c")), "t": inv["t"]}
    # upozornění po stupních (výchozí 50, 30, 20, 10, 0 %) – každý stupeň jednou, znovu až po nabití
    lv = sorted({int(float(x)) for x in str(cfg.get("telefon_upozornit") or "50,30,20,10,0").replace(";", ",").split(",")
                 if x.strip().replace(".", "", 1).isdigit()}, reverse=True)
    if ph and lv and age <= lim and ph.get("b") is not None:
        b, chg = ph["b"], bool(ph.get("c"))
        sent = set(st.get("ph_sent") or [])
        crossed = [L for L in lv if b <= max(L, 2)]           # všechny stupně, pod které už spadl
        if crossed and not chg and not set(crossed) <= sent:
            L = min(crossed)
            prio = 5 if L <= 10 else 4 if L <= 20 else 3
            ntfy(topic, f"🪫 Flip na chatě má {b:.0f} %" + (" – vypíná se!" if L == 0 else ""),
                 "Flip se nenabíjí. Bez něj nechodí data z Victronu ani zásuvek, nefunguje automatika River."
                 "\nZkontroluj nabíječku / zásuvku u Flipu.", prio, "battery,warning")
            sent.update(crossed)
        sent = {x for x in sent if not (b > x + 5 or chg)}  # po nabití se stupně znovu odemknou
        st["ph_sent"] = sorted(sent)

GEN_KEYS = {"fuel": ("pd.oilVal",), "w": ("pd.acPower", "pd.totalPower", "pd.outputWatts"), "max_w": ("pd.oilMaxOutPower",),
            "type": ("pd.type",), "motor": ("pd.motorState",), "mode": ("pd.sysMode",), "eco": ("pd.ecoMode",),
            "err": ("pd.errCode",), "hours": ("pd.motorUseTime",), "remain": ("pd.remainTime",), "temp": ("pd.temp",)}


def read_ecoflow_app(rivers, data, st, now, force=False):
    """4.76: zařízení, která vývojářské rozhraní nepouští (1006), přečíst přes přihlášení aplikace EcoFlow
    (ECOFLOW_EMAIL / ECOFLOW_PASSWORD). Doplní stejná pole jako vývojářské rozhraní (soc, in_w, …), generátoru
    r["gd"] = {fuel %, w, max_w, type, motor, …}. Stav do data["eco_app"]."""
    em = os.environ.get("ECOFLOW_EMAIL", "").strip()
    pw = os.environ.get("ECOFLOW_PASSWORD", "")
    # 4.83: přes aplikaci všechna zařízení – vývojářské rozhraní u červené vracelo starou hodnotu (inv.inputWatts 150 W,
    # když už nenabíjela; jen 20 údajů), aplikace posílá živá data (175 údajů). Vývojářské rozhraní zůstává jako záloha.
    bad = list(rivers)
    if not (em and pw) or not bad:
        return
    import ecoflow_app
    ts = int(now.timestamp())
    sess = st.get("efp")
    out = {"t": ts}
    try:
        if not sess or ts - sess.get("t", 0) > 7 * 86400:
            if ts - (st.get("efp_fail") or 0) < 3600:      # přihlášení selhalo – zkusit až za hodinu (ať účet nezablokuje)
                data["eco_app"] = data.get("eco_app") or {"t": ts, "err": "přihlášení selhalo, další pokus za hodinu"}
                return
            sess = ecoflow_app.login(em, pw)
            st["efp"] = sess
            log("ev", "EcoFlow (aplikace): přihlášeno")
        res = ecoflow_app.read(sess, [r["sn"] for r in bad])
        if res.get("_auth"):                                # token / MQTT údaje přestaly platit → jednou znovu
            sess = ecoflow_app.login(em, pw)
            st["efp"] = sess
            res = ecoflow_app.read(sess, [r["sn"] for r in bad])
        st["efp_fail"] = 0
        out["ok"] = True
    except Exception as e:
        msg = str(e).replace(em, "…")[:180]
        print("EcoFlow aplikace:", msg)
        if "přihlášení" in msg:
            st["efp_fail"], st["efp"] = ts, None
        data["eco_app"] = {"t": ts, "err": msg}
        return
    for r in bad:
        a = res.get(r["sn"]) or {}
        q = a.get("q") or {}
        r["ak"] = {"n": a.get("n"), "on": a.get("online"), "nq": len(q), "bin": a.get("bin")}
        if a.get("online") == 1:
            r["online"] = True
        elif a.get("online") == 0:
            r["online"] = False
        if not q:
            continue
        r["src"], r["qerr"], r["nq"] = "app", None, len(q)
        for k in ("soc", "in_w", "out_w", "ac_in_w", "ac_out_w", "dsg_min", "chg_min", "temp"):
            r.pop(k, None)                              # hodnoty z vývojářského rozhraní nahradí živé z aplikace
        for key, names in KEYS_EF().items():
            for n in names:
                if q.get(n) is not None:
                    try:
                        r[key] = float(q[n])
                    except (TypeError, ValueError):
                        pass
                    break
        r["socs"] = {k: q[k] for k in KEYS_EF()["soc"] if q.get(k) is not None}
        if q.get("mppt.cfgChgWatts") is not None:           # 4.88: nastavený nabíjecí výkon (skutečný, z River)
            try:
                r["cfg_w"] = int(q["mppt.cfgChgWatts"])
            except (TypeError, ValueError):
                pass
        import ecoflow as _ef
        r["pw"] = _ef.power_keys(q)
        if not r.get("online"):
            for k in ("in_w", "out_w", "ac_in_w", "ac_out_w"):
                if r.get(k):
                    r[k] = 0.0
        if r.get("gen"):
            gd = {}
            for key, names in GEN_KEYS.items():
                v = next((q[n] for n in names if q.get(n) is not None), None)
                if v is not None:
                    gd[key] = v
            r["gd"] = gd
            # všechny číselné údaje generátoru (zatím neznáme význam všech – na web k dohledání benzín/plyn)
            r["q"] = dict(list({k: v for k, v in sorted(q.items()) if isinstance(v, (int, float)) and not isinstance(v, bool)}.items())[:80])
    out["devs"] = {str(r["sn"])[-4:]: r.get("ak") for r in bad}
    data["eco_app"] = out


def KEYS_EF():
    import ecoflow
    return ecoflow.KEYS


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
        data["eco_err"] = {"t": int(now.timestamp()), "msg": str(e)[:200]}     # 4.59: na web (diagnostika)
        st["eco_err"] = st.get("eco_err", 0) + 1
        if st["eco_err"] == 12:
            ntfy(topic, "📡 Hlídač nemůže číst EcoFlow", f"Už ~2 hodiny selhává čtení EcoFlow: {str(e)[:150]}", 3, "warning")
        return None
    st["eco_err"] = 0
    st["eco_host"] = host
    # 4.66: zkušební nastavení nabíjecího výkonu (workflow vstup efset „konec SN:W“, např. 1167:300)
    efs = os.environ.get("EF_SET", "").strip()
    if efs and ":" in efs:
        tail, w = (x.strip() for x in efs.split(":", 1))
        tgt = next((r for r in rivers if str(r.get("sn", "")).upper().endswith(tail.upper())), None)
        try:
            res = ecoflow.set_ac_charge(host, ak, sk, tgt["sn"], int(w)) if tgt else {"code": "?", "message": "SN nenalezeno"}
        except Exception as e:
            res = {"code": "chyba", "message": str(e)[:150]}
        print("EcoFlow nastavení", efs, res)
        data["eco_set"] = {"t": int(now.timestamp()), "cmd": efs, "code": str(res.get("code")), "msg": str(res.get("message"))[:150]}
    read_ecoflow_app(rivers, data, st, now)        # 4.76: generátor a malá River přes přihlášení aplikace
    # 4.67: zařízení s 1006 (generátor, malá River) – zkusit jiné cesty (vybrané údaje přes HTTP, poslech MQTT).
    bad = [r for r in rivers if r.get("qerr")]
    lastp = (st.get("eco_probe") or {}).get("t", 0)
    gen_on = any(r.get("gen") and r.get("online") for r in bad)
    # 4.70: jen když je generátor online, nejvýš 1× za den (ruční spuštění = i každé odeslání Flipu, to by zdržovalo)
    if bad and gen_on and now.timestamp() - lastp > 86400:
        try:
            ecoflow.probe(host, ak, sk, rivers)
            st["eco_probe"] = {"t": int(now.timestamp()),
                               "devs": {str(r.get("sn", ""))[-4:]: dict(r["probe"], on=r.get("online"))
                                        for r in rivers if r.get("probe")}}
            print("EcoFlow zkouška", json.dumps(st["eco_probe"], ensure_ascii=False)[:3000])
        except Exception as e:
            print("EcoFlow zkouška selhala", e)
            st["eco_probe"] = {"t": int(now.timestamp()), "err": str(e)[:150]}
    data["eco_probe"] = st.get("eco_probe")
    data["eco_err"] = None
    data["eco_seen"] = {"t": int(now.timestamp()), "host": host.replace("https://", ""),
                        "devs": [{"n": r.get("name"), "sn": str(r.get("sn", ""))[-4:], "on": r.get("online"),
                                  "soc": r.get("soc"), "gen": bool(r.get("gen")), "model": r.get("model"), "wh": r.get("wh"),
                                  "qk": r.get("qk"), "nq": r.get("nq"), "socs": r.get("socs"), "qerr": r.get("qerr"),
                                  "chgk": r.get("chgk"), "src": r.get("src"), "gd": r.get("gd"), "ak": r.get("ak"), "pw": r.get("pw")} for r in rivers]}
    gens = [r for r in rivers if r.get("gen")]
    rivers = [r for r in rivers if not r.get("gen")]
    data["ef_gens"] = gens
    data["rivers"] = rivers
    # energie každé River za den (Wh): nabito (vstup) a dodáno (výstup) – lichoběžník mezi dvěma čteními (max 1 h mezera)
    tnow = now.timestamp()
    day = data["days"].setdefault(now.strftime("%Y-%m-%d"), {})
    rvd = day.setdefault("rv", {})
    prev, pt = st.get("rv_e_prev") or {}, st.get("rv_e_t")
    nxt = {}
    for r in rivers:
        k = str(r.get("sn", ""))[-6:]
        iw, ow = r.get("in_w") or 0, r.get("out_w") or 0
        e = rvd.setdefault(k, {"n": r.get("name"), "i": 0.0, "o": 0.0})
        if r.get("soc") is not None:
            e.setdefault("s0", r["soc"])
            e["s"] = r["soc"]
        if r.get("online") and pt and 0 < tnow - pt <= 3600 and k in prev:
            dt = (tnow - pt) / 3600
            e["i"] = round(e["i"] + (prev[k][0] + iw) / 2 * dt, 1)
            e["o"] = round(e["o"] + (prev[k][1] + ow) / 2 * dt, 1)
        if r.get("online"):
            nxt[k] = [iw, ow]
    st["rv_e_prev"], st["rv_e_t"] = nxt, tnow
    data["rivers_t"] = int(now.timestamp())
    for r in rivers:
        print(f"EcoFlow {r['name']}: {fmt(r.get('soc'))} %, vstup {fmt(r.get('in_w'))} W, výstup {fmt(r.get('out_w'))} W"
              + ("" if r["online"] else " (offline)"))
        check_river(r, st, topic, cfg)
    return rivers


def hash_soc(data, st, now, cfg):
    """Nabití „#“ počítáním ampérhodin (ne z napětí). Pokaždé se přepočítá z bodů (14 dní):
    qr = souvislý součet Ah do (×0,9) / z baterie. Plné nabití = přechod regulátoru do Float.
    Každý bod se vztahuje k nejbližšímu plnému nabití: po něm = od posledního plného (max. 3 dny),
    před ním = kolik chybělo do následujícího plného (max. 3 dny), jinak nejlepší stav za 2 dny.
    Body: q / hq = Ah od plné (≤ 0). data["hq"] = shrnutí pro web."""
    pts = [p for p in data.get("points", []) if p.get("bat_v") and p.get("bat_a") is not None]
    if len(pts) < 2:
        return
    idle = (cfg.get("menic_vlastni_W") or 6) + (cfg.get("desulfator_W") or 0)
    rids = ips(cfg.get("zasuvky_river"))
    mip = str(cfg.get("zasuvka_menic") or (data.get("inverter") or {}).get("mip") or "1")
    eff = 0.9                                   # nabíjecí účinnost AGM
    fts = fix_ts(cfg)
    qr, fl_since, fulls, mw_last, mw_t = 0.0, 0, [], None, 0
    pts[0]["qr"] = 0.0
    for a, b in zip(pts, pts[1:]):
        if a.get("mw") is not None:
            mw_last, mw_t = a["mw"], a["t"]
        dt = b["t"] - a["t"]
        if 0 < dt <= 2400:
            if mw_last is not None and a["t"] - mw_t <= 1800:
                load = mw_last / 0.88 + idle
            elif a.get("tp") and (a["tp"].get(mip) or 0) <= 3 and any((a["tp"].get(i) or 0) > 3 for i in rids):
                load = cfg.get("desulfator_W") or 0
            else:
                load = idle + 30                # bez dat o odběru: běžná chata
            i_net = a["bat_a"] - load / a["bat_v"]
            a["_in"] = i_net
            qr += i_net * dt / 3600 * (eff if i_net > 0 else 1.0)
        b["qr"] = round(qr, 2)
        # plná = regulátor přešel do Float (jeho vlastní kritérium konce nabíjení) – i když ve Float vydrží jen chvíli
        if b.get("status") == 1:
            if not fl_since:
                fl_since = b["t"]
                if b["t"] >= fts:               # Float před opravou spojů nebyl spolehlivě „plná“
                    fulls.append((fl_since, b["t"]))
        else:
            fl_since = 0
    # 5.62: kotva z klidového napětí – když dlouho nebylo plné nabití (v zimě běžné), „nejlepší stav za 2 dny“ jako
    # 100 # dával nesmysl (43 # při 11,75 V). Klid = aspoň 60 min bez slunce a s proudem baterie do ±0,8 A (typicky
    # chata na River nebo noc bez odběru) → nabití z klidového napětí (soc_from_v) = Ah od plné v tu chvíli.
    cap0 = eff_cap(data, cfg)
    rests = []                                   # (t, qr, Ah od plné)
    run0 = None
    for a, b in zip(pts, pts[1:]):
        quiet = a.get("_in") is not None and abs(a["_in"]) < 0.8 and (a.get("pv_w") or 0) < 5 and 0 < b["t"] - a["t"] <= 2400
        if quiet:
            run0 = run0 or a["t"]
            # 5.63: aspoň 2 h klidu – po nabíjení drží baterie ještě hodiny vyšší („povrchové“) napětí a nabití by
            # vycházelo moc vysoko
            if b["t"] - run0 >= 2 * 3600 and (b.get("pv_w") or 0) < 5:
                # 5.64: skutečný klid (≥ 2 h bez proudu) = klidové napětí → obecná tabulka AGM (ocv_soc). Naučený převod
                # (soc_from_v, „plná“ = napětí na začátku noci pod odběrem) dával moc vysoko: 12,40 V = 77 % místo ~55 %
                soc_r = ocv_soc(b["bat_v"] + (0.02 if abs(a["_in"]) > 0.3 else 0.0))
                item = (b["t"], b["qr"], -(100 - soc_r) / 100 * cap0, b["bat_v"], round(soc_r), round((b["t"] - run0) / 3600, 1))
                if not rests or b["t"] - rests[-1][0] >= 1800:
                    rests.append(item)
                else:
                    rests[-1] = item                 # konec klidu = nejpřesnější
        else:
            run0 = None
    for p in pts:
        p.pop("_in", None)
    rtimes = [r[0] for r in rests]
    # kotva pro každý bod
    import bisect
    ftimes = [f[1] for f in fulls]
    qr_at = {p["t"]: p["qr"] for p in pts}
    out, run_max, cur_f = [], None, None
    for idx, p in enumerate(pts):
        t = p["t"]
        k = bisect.bisect_right(ftimes, t)
        prev_f = ftimes[k - 1] if k else None
        next_f = ftimes[k] if k < len(ftimes) else None
        if prev_f and t - prev_f <= 3 * 86400:
            if cur_f != prev_f:
                cur_f, run_max = prev_f, qr_at[prev_f]
            run_max = max(run_max, p["qr"])       # po plném nabití už „víc než plná“ být nemůže
            h = p["qr"] - run_max
        elif next_f and next_f - t <= 3 * 86400:
            h = min(0.0, p["qr"] - qr_at[next_f])
        else:
            j = bisect.bisect_right(rtimes, t)
            ra = rests[j - 1] if j and t - rtimes[j - 1] <= 4 * 86400 else (rests[j] if j < len(rests) and rtimes[j] - t <= 86400 else None)
            if ra:                               # 5.62: od klidového napětí
                h = ra[2] + (p["qr"] - ra[1])
                p["_rk"] = ra
            else:
                win = [x["qr"] for x in pts[max(0, idx - 300):idx + 1] if x["t"] >= t - 2 * 86400]
                h = min(0.0, p["qr"] - max(win))
        p["q"] = p["hq"] = round(min(0.0, h), 2)
    full_t = ftimes[-1] if ftimes else 0
    st["hq_full_t"] = full_t
    cap = eff_cap(data, cfg)
    # nejnižší / nejvyšší # každého dne (přepočet z bodů; body se drží 14 dní)
    mins, maxs = {}, {}
    for p in pts:
        k_ = datetime.fromtimestamp(p["t"], TZ).strftime("%Y-%m-%d")
        v_ = round(max(0, 100 + p["hq"] / cap * 100))
        mins[k_] = min(mins.get(k_, 999), v_)
        maxs[k_] = max(maxs.get(k_, -1), v_)
    for k_, v_ in mins.items():
        data["days"].setdefault(k_, {})["hq_min"] = v_
        data["days"][k_]["hq_max"] = maxs[k_]
    last = pts[-1]
    ts = now.timestamp()
    rka = last.get("_rk")
    rk = rka[0] if rka else None
    kind = "full" if full_t and ts - full_t <= 3 * 86400 else "rest" if rk else "best"
    for p in pts:
        p.pop("_rk", None)
    nqc = sum(1 for d in data.get("days", {}).values() if (d.get("qc") or {}).get("ok"))
    capsrc = "testy z Ah" if cap != (cfg["kapacita_Ah"] or 200) else "štítek – zatím bez 2 testů"
    data["hq"] = {"capsrc": capsrc, "nqc": nqc, "ah": round(last["hq"], 1), "cap": round(cap), "kind": kind,
                  "ref_t": int(full_t if kind == "full" else rk if kind == "rest" else last["t"]), "pct": round(max(0, 100 + last["hq"] / cap * 100)),
                  "full_t": int(full_t) if full_t else None, "fl_since": int(fl_since) if fl_since else None,
                  "rest": {"v": rka[3], "soc": rka[4], "h": rka[5], "ah": round(last["qr"] - rka[1], 1)} if kind == "rest" else None,
                  "vfull": round(VCAL["full"], 2), "vempty": VCAL["empty"]}
    for k_ in ("hq_t", "hq_q", "hq_fl"):
        st.pop(k_, None)


# klidové napětí AGM 12 V → nabití (přibližně, 25 °C)
AGM_OCV = [(11.95, 10), (12.05, 20), (12.15, 30), (12.25, 40), (12.35, 50), (12.45, 60), (12.55, 70), (12.65, 80), (12.75, 90), (12.85, 100)]


def ocv_soc(v):
    if v <= AGM_OCV[0][0]:
        return AGM_OCV[0][1]
    for (v0, s0), (v1, s1) in zip(AGM_OCV, AGM_OCV[1:]):
        if v <= v1:
            return s0 + (s1 - s0) * (v - v0) / (v1 - v0)
    return 100


WD = ["po", "út", "st", "čt", "pá", "so", "ne"]


def river_days(data, now, cfg):
    """5.07: kolik hodin která River napájela chatu (zásuvka na jejím výstupu > 3 W a měnič nic nedává) a kolik
    hodin napájela jen spotřebič – po dnech, z uložených bodů (váha = čas do dalšího bodu, ≤ 15 min).
    days[k]["rh"] = {číslo zásuvky: hodiny chaty}, days[k]["rhs"] = {…: hodiny spotřebiče}. Přepisuje se jen víc daty."""
    rids = ips(cfg.get("zasuvky_river"))
    mip = str(cfg.get("zasuvka_menic") or (data.get("inverter") or {}).get("mip") or "1")
    pts = [p for p in data.get("points", []) if p.get("tp")]
    agg = {}
    for p, q in zip(pts, pts[1:] + [{"t": now.timestamp()}]):
        dt = q["t"] - p["t"]
        if dt <= 0 or dt > 900:
            continue
        k = datetime.fromtimestamp(p["t"], TZ).strftime("%Y-%m-%d")
        a = agg.setdefault(k, {"c": {}, "s": {}, "tot": 0.0})
        a["tot"] += dt
        sol = (p.get("mw") if p.get("mw") is not None else (p["tp"].get(mip) or 0)) > 3
        for rid in rids:
            if (p["tp"].get(rid) or 0) > 3:
                b = a["s" if sol else "c"]
                b[rid] = b.get(rid, 0.0) + dt
    days = data.setdefault("days", {})
    for k, a in agg.items():
        if k not in days and k != now.strftime("%Y-%m-%d"):
            continue
        d = days.setdefault(k, {})
        if a["tot"] / 3600 + 0.05 < (d.get("rhh") or 0):
            continue
        d["rh"] = {i: round(v / 3600, 2) for i, v in a["c"].items()}
        d["rhs"] = {i: round(v / 3600, 2) for i, v in a["s"].items()}
        d["rhh"] = round(a["tot"] / 3600, 1)


def cons_compare(data, st, now, topic, cfg):
    """5.22: spotřeba chaty proti obvyklé. Odběr chaty = zásuvka měniče (220 V ze solární baterie) + zásuvky na výstupu
    River (W, jak je měří zásuvky), integrováno mezi body (mezery nad 30 min se nepočítají).
    • dnes do teď vs medián posledních 7 dní do stejné denní doby (medián = velké výkyvy se neprojeví)
    • noc (18–6 h) vs medián předchozích 7 nocí
    • upozornění 1× za den, když je dnes do teď o 50 % a aspoň o 0,15 kWh víc než obvykle (po 10:00)
    data["cons_cmp"] = {now_wh, typ_wh, day_typ_wh, night_wh, night_typ_wh, n}"""
    import statistics as _stt
    rids = ips(cfg.get("zasuvky_river"))
    mip = str(cfg.get("zasuvka_menic") or (data.get("inverter") or {}).get("mip") or "1")
    pts = [p for p in data.get("points", []) if p.get("tp")]
    if len(pts) < 10:
        return
    def w_of(p):
        tp = p["tp"]
        a = tp.get(mip) if tp.get(mip) is not None else p.get("mw")
        return (a or 0) + sum(tp.get(i) or 0 for i in rids)
    def energy(t0, t1):
        """Wh mezi t0 a t1 + pokryté hodiny."""
        wh = cov = 0.0
        for a, b in zip(pts, pts[1:]):
            if b["t"] <= t0 or a["t"] >= t1:
                continue
            dt = b["t"] - a["t"]
            if dt <= 0 or dt > 1800:
                continue
            lo, hi = max(a["t"], t0), min(b["t"], t1)
            if hi > lo:
                wh += w_of(a) * (hi - lo) / 3600
                cov += (hi - lo) / 3600
        return wh, cov
    ts = now.timestamp()
    mid = now.replace(hour=0, minute=0, second=0, microsecond=0)
    sec = (now - mid).total_seconds()
    now_wh, cov = energy(mid.timestamp(), ts)
    typ, typ_day = [], []
    for i in range(1, 8):
        m_i = mid - timedelta(days=i)
        e, c = energy(m_i.timestamp(), m_i.timestamp() + sec)
        if sec < 3600 or c >= 0.8 * sec / 3600:
            typ.append(e)
        e2, c2 = energy(m_i.timestamp(), (m_i + timedelta(days=1)).timestamp())
        if c2 >= 20:
            typ_day.append(e2)
    n0 = now.replace(hour=6, minute=0, second=0, microsecond=0)
    if now < n0:
        n0 -= timedelta(days=1)
    night_wh, ncov = energy((n0 - timedelta(hours=12)).timestamp(), n0.timestamp())
    nights = []
    for i in range(1, 8):
        e, c = energy((n0 - timedelta(days=i, hours=12)).timestamp(), (n0 - timedelta(days=i)).timestamp())
        if c >= 10:
            nights.append(e)
    med = lambda x: _stt.median(x) if len(x) >= 3 else None
    cc = {"t": int(ts), "now_wh": round(now_wh), "cov": round(cov, 1), "typ_wh": round(med(typ)) if med(typ) is not None else None,
          "day_typ_wh": round(med(typ_day)) if med(typ_day) is not None else None,
          "night_wh": round(night_wh) if ncov >= 10 else None, "night_typ_wh": round(med(nights)) if med(nights) is not None else None,
          "n": len(typ_day)}
    data["cons_cmp"] = cc
    # velká odchylka → jedno upozornění za den
    day = now.strftime("%Y-%m-%d")
    t_ = cc["typ_wh"]
    if t_ and now.hour >= 10 and cov >= 0.8 * sec / 3600 and now_wh > t_ * 1.5 and now_wh - t_ > 150 \
            and st.get("cons_warn") != day:
        ntfy(topic, "🏠 Chata dnes bere víc než obvykle",
             f"Dnes do teď {fmt(now_wh / 1000, 2)} kWh, obvykle touhle dobou {fmt(t_ / 1000, 2)} kWh (+{fmt((now_wh / t_ - 1) * 100, 0)} %). "
             "Nezůstalo něco zapnuté?", 3, "house,warning")
        st["cons_warn"] = day


FUEL_FILE = "palivo.txt"


def fuel_stats(data, st, now, cfg):
    """5.26: lahve PB a tankování benzínu (palivo.txt, zapisuje web: „čas | lpg/benzin | cena Kč | plna/castecna | litry“).
    Energie generátoru podle paliva (st.fuel_e – roste během nabíjení). Každý záznam = od té chvíle se pálí tohle palivo
    → kWh na lahev / tankování = počítadlo u dalšího záznamu stejného paliva − počítadlo při tomto záznamu.
    Cena za kWh = součet cen / součet kWh jen z plných a už spotřebovaných (průměr); částečně plné = odhad z průměru.
    data["fuel"] = {lpg|benzin: {cur, avg_kwh, czk_kwh, n, hist}}, ceny nabíjení do data["fuel_runs"]."""
    try:
        lines = open(FUEL_FILE, encoding="utf-8").read().splitlines()
    except OSError:
        lines = []
    ent = []
    for ln in lines:
        ln = ln.split("#", 1)[0].strip()
        bits = [b.strip() for b in ln.split("|")]
        if len(bits) < 3:
            continue
        try:
            t = int(datetime.strptime(bits[0], "%Y-%m-%d %H:%M").replace(tzinfo=TZ).timestamp())
            f = "lpg" if bits[1].lower().startswith(("lpg", "plyn", "pb")) else "benzin"
            price = float(bits[2].lower().replace("kč", "").replace(",", ".").strip() or 0)
        except ValueError:
            continue
        full = not (len(bits) > 3 and bits[3].lower().startswith(("cast", "část", "ne")))
        lit = None
        if len(bits) > 4:
            try:
                lit = float(bits[4].lower().replace("l", "").replace(",", ".").strip())
            except ValueError:
                pass
        ent.append({"t": t, "f": f, "price": price, "full": full, "l": lit})
    ent.sort(key=lambda e: e["t"])
    fe = st.setdefault("fuel_e", {})
    snap = st.setdefault("fuel_snap", {})
    if not st.get("fuel_e_t0"):
        # jednorázově: plyn se pálí od 23. 10. ~21:00 (Petr: všechno nabíjení z plynu je z nové lahve) – energie z doby
        # před počítadlem: hodinová historie zásuvky generátoru 23. 10. od 21 h + dnešní součet z EcoFlow
        gip = str(cfg.get("zasuvka_generator") or "7")
        h23 = ((data.get("tp_hist") or {}).get(gip) or {}).get("2026-10-23") or []
        seed = sum(x for x in h23[21:] if x) + (((data.get("days") or {}).get(now.strftime("%Y-%m-%d")) or {}).get("gq") or 0)
        fe["lpg"] = round(fe.get("lpg", 0.0) + seed, 1)
        st["fuel_e_t0"] = int(now.timestamp())
        log("ev", f"Palivo: počítadlo plynu založeno s {fmt(seed / 1000, 2)} kWh (od 23. 10. 21 h)")
    for e in ent:                                           # počítadlo energie v okamžiku záznamu (při prvním běhu po něm)
        k = f"{e['f']}:{e['t']}"
        if k not in snap:
            snap[k] = 0.0 if e["t"] < st["fuel_e_t0"] else fe.get(e["f"], 0.0)   # záznam z doby před počítadlem → od začátku
    out = {}
    for f in ("lpg", "benzin"):
        es = [e for e in ent if e["f"] == f]
        hist = []
        for i, e in enumerate(es):
            a = snap.get(f"{f}:{e['t']}", 0.0)
            closed = i + 1 < len(es)
            b = snap.get(f"{f}:{es[i + 1]['t']}", fe.get(f, 0.0)) if closed else fe.get(f, 0.0)
            hist.append({"t": e["t"], "price": e["price"], "full": e["full"], "l": e["l"], "wh": round(max(0.0, b - a)), "closed": closed})
        ok = [x for x in hist if x["closed"] and x["full"] and x["wh"] > 100]
        czk_kwh = sum(x["price"] for x in ok) / (sum(x["wh"] for x in ok) / 1000) if ok else None
        avg_kwh = sum(x["wh"] for x in ok) / len(ok) / 1000 if ok else None
        cur = hist[-1] if hist else None
        if cur and not cur["closed"]:
            cur = dict(cur)
            cur["left_pct"] = round(max(0.0, 100 - cur["wh"] / 1000 / avg_kwh * 100)) if avg_kwh and cur["full"] else None
        # cena za kWh pro odhad: průměr; bez průměru z aktuální plné lahve zatím nejde
        out[f] = {"cur": cur if cur and not cur["closed"] else None, "avg_kwh": round(avg_kwh, 2) if avg_kwh else None,
                  "czk_kwh": round(czk_kwh, 1) if czk_kwh else None, "n": len(ok), "hist": hist[-8:], "e": round(fe.get(f, 0.0))}
    data["fuel"] = out
    for r in data.get("fuel_runs") or []:                   # cena každého nabíjení (odhad z průměru)
        c = (out.get(r.get("fuel")) or {}).get("czk_kwh")
        r["czk"] = round(r["wh"] / 1000 * c) if c else None


def fridge_days(data, now, cfg):
    """4.73: kolik % dne běžel kompresor lednice – z uložených bodů (zásuvka lednice), každý bod váží čas do
    dalšího (nejvýš 15 min, při mezeře v datech se nepočítá). days[k]["fd"] = % času, "fh" = pokryté hodiny,
    "fn" = rozběhů, "fw" = průměrný příkon za běhu (W). Přepisuje se jen lepším pokrytím (body se po 14 dnech mažou)."""
    fid = str(cfg.get("zasuvka_lednice") or "4")
    pts = [(p["t"], p["tp"][fid]) for p in data.get("points", []) if (p.get("tp") or {}).get(fid) is not None]
    agg = {}
    for (t, w), (t2, _) in zip(pts, pts[1:] + [(now.timestamp(), None)]):
        dt = t2 - t
        if dt <= 0 or dt > 900:
            continue
        k = datetime.fromtimestamp(t, TZ).strftime("%Y-%m-%d")
        a = agg.setdefault(k, {"tot": 0.0, "on": 0.0, "wh": 0.0, "n": 0, "prev": None})
        a["tot"] += dt
        if w > 20:
            a["on"] += dt
            a["wh"] += w * dt
            if a["prev"] is not None and a["prev"] <= 20:
                a["n"] += 1
        a["prev"] = w
    days = data.setdefault("days", {})
    for k, a in agg.items():
        h = a["tot"] / 3600
        if h < 1 or k not in days and k != now.strftime("%Y-%m-%d"):
            continue
        d = days.setdefault(k, {})
        if h + 0.05 < (d.get("fh") or 0):
            continue
        d["fd"], d["fh"], d["fn"] = round(a["on"] / a["tot"] * 100, 1), round(h, 1), a["n"]
        d["fw"] = round(a["wh"] / a["on"]) if a["on"] else None


def fridge_check(data, st, now, topic, cfg):
    """4.48: hlídání lednice (zásuvka zasuvka_lednice, Flip po ~10 min). Kompresor normálně cykluje běží / stojí.
    • stojí déle než max(lednice_ticho_h, 1,5× nejdelší stání za 7 dní) → porucha / bez proudu → jídlo se kazí
      (přizpůsobí se zimě: ve studené chatě stojí kompresor déle)
    • běží déle než max(lednice_bezi_h, 1,5× nejdelší běh za 7 dní) → otevřené dveře / námraza / porucha
    • zásuvka lednice nedostupná ≥ 1 h, když Flip posílá (ostatní zásuvky jdou) → lednice bez proudu
    Každý stav jednou, při návratu do normálu zpráva „zase v pořádku“."""
    if not cfg.get("lednice_hlidat", True):
        return
    # 1.5: teploměr v lednici – teplota nad lednice_max_C déle než 30 min
    nm = str(cfg.get("teplomer_lednice") or "").strip()
    if nm:
        fz = st.setdefault("fridge_t", {})
        tp_ = [(p["t"], p["th"][nm]) for p in data.get("points", []) if p["t"] >= now.timestamp() - 3600 and nm in (p.get("th") or {})]
        lim_c = cfg.get("lednice_max_C") or 8
        if tp_ and now.timestamp() - tp_[-1][0] < 1800:
            hot = [x for x in tp_ if x[0] >= now.timestamp() - 1800]
            if len(hot) >= 2 and all(v > lim_c for _, v in hot) and not fz.get("hot"):
                ntfy(topic, f"🧊 Lednice má {fmt(hot[-1][1], 1)} °C", f"Teplota v lednici je přes {fmt(lim_c, 0)} °C už půl hodiny. "
                     "Otevřené dveře, porucha, nebo lednice bez proudu?", 4, "warning")
                fz["hot"] = True
            elif fz.get("hot") and tp_[-1][1] <= lim_c - 1:
                ntfy(topic, f"✓ Lednice zase chladí ({fmt(tp_[-1][1], 1)} °C)", "Teplota v lednici je zpátky v normě.", 2, "white_check_mark")
                fz["hot"] = False
    fid = str(cfg.get("zasuvka_lednice") or "").strip()
    if not fid:
        return
    ts = now.timestamp()
    on_w = 20                                                   # kompresor běží (~55–80 W), v klidu ~0–2 W
    pts = [p for p in data.get("points", []) if p["t"] >= ts - 7 * 86400 and p.get("tp")]
    smp = [(p["t"], p["tp"][fid]) for p in pts if p["tp"].get(fid) is not None]
    # epizody stání / běhu (mezera v datech > 40 min epizodu ukončí – nevíme, co se dělo)
    eps, cur = [], None
    for t, w in smp:
        on = w > on_w
        if cur and (on != cur[0] or t - cur[2] > 2400):
            eps.append(cur); cur = None
        cur = [on, cur[1], t] if cur else [on, t, t]
    if cur:
        eps.append(cur)
    hist = [e for e in eps[:-1]]                                # hotové epizody (bez právě probíhající)
    max_off = max((e[2] - e[1] for e in hist if not e[0]), default=0)
    max_on = max((e[2] - e[1] for e in hist if e[0]), default=0)
    lim_off = max((cfg.get("lednice_ticho_h") or 3) * 3600, 1.5 * max_off)
    lim_on = max((cfg.get("lednice_bezi_h") or 2) * 3600, 1.5 * max_on)
    fs = st.setdefault("fridge", {})
    state, info = "ok", {}
    inv = data.get("inverter") or {}
    flip_ok = inv and ts - inv.get("t", 0) < 1800
    if flip_ok:
        fp = next((p for p in inv.get("tp", []) if str(p.get("ip")) == fid), None)
        others = [p for p in inv.get("tp", []) if str(p.get("ip")) != fid and p.get("w") is not None]
        if (fp is None or fp.get("off") or fp.get("err") or fp.get("w") is None) and others:
            fs.setdefault("na_t", int(ts))
            if ts - fs["na_t"] >= 3600:
                state, info = "na", {"od": fs["na_t"]}
        else:
            fs.pop("na_t", None)
    if state == "ok" and cur and ts - cur[2] < 1800 and len(smp) >= 6:
        dur = cur[2] - cur[1]
        if not cur[0] and dur >= lim_off:
            state, info = "off", {"od": cur[1], "h": round(dur / 3600, 1), "lim": round(lim_off / 3600, 1)}
        elif cur[0] and dur >= lim_on:
            state, info = "on", {"od": cur[1], "h": round(dur / 3600, 1), "lim": round(lim_on / 3600, 1)}
    prev = fs.get("state", "ok")
    if state != prev:
        hm = lambda t: f"{rel_day(t, now)} {datetime.fromtimestamp(t, TZ).strftime('%H:%M')}"
        if state == "off":
            ntfy(topic, "🧊 Lednice nechladí?", f"Kompresor lednice neběžel od {hm(info['od'])} (už {fmt(info['h'], 1)} h, "
                 f"obvykle nejdéle ~{fmt(max_off / 3600, 1)} h). Porucha, vypnutá lednice, nebo je v chatě hodně zima?", 4, "snowflake,warning")
        elif state == "on":
            ntfy(topic, "🧊 Lednice běží bez přestávky", f"Kompresor běží od {hm(info['od'])} (už {fmt(info['h'], 1)} h, "
                 f"obvykle nejdéle ~{fmt(max_on / 3600, 1)} h). Otevřené dveře, námraza, nebo porucha?", 4, "warning")
        elif state == "na":
            ntfy(topic, "🧊 Lednice bez proudu?", f"Zásuvka lednice nejde přečíst od {hm(info['od'])}, ostatní zásuvky jdou. "
                 "Vypadlá / vypnutá zásuvka?", 4, "warning")
        elif prev in ("off", "on", "na"):
            ntfy(topic, "✓ Lednice zase normálně běží", "Kompresor zase cykluje (běží / stojí).", 2, "white_check_mark")
        fs["state"] = state
    data["fridge"] = {"state": state, **info, "max_off_h": round(max_off / 3600, 1), "max_on_h": round(max_on / 3600, 1),
                      "now_on": bool(cur and cur[0]) if cur else None, "since": cur[1] if cur else None}


def flip_charge_cmd(data, st, now, topic, cfg):
    """4.53: povolení nabíjení Flipu (zásuvka zasuvka_flip) – posílá se do ntfy <téma>-fc, Flip ho čte a zásuvku
    přepne sám (bezpečnost podle teploty a spodní hranici řeší Flip místně, i bez internetu).
    5.58: do 80 % jen když je slunce navíc (regulátor škrtí panely: Float / držení nabíjecího napětí), jinak jen pod
    spodní hranicí (flip_min_pct) a jen do slunce. Router stejně (Flip ho řídí 40 / 80 %, „rfree“ do 90 %).
    Posílá se při změně a nejméně jednou za hodinu. Taky upozornění, když je baterie Flipu horká."""
    ts = now.timestamp()
    pid = str(cfg.get("zasuvka_flip") or "").strip()
    if not cfg.get("flip_nabijeni_rizeni", True):
        pid = ""                                          # řízení vypnuté → Flip nic nepřepíná
    inv = data.get("inverter") or {}
    fresh = inv and ts - inv.get("t", 0) < 1800
    rids = ips(cfg.get("zasuvky_river"))
    on_solar = fresh and (inv.get("mw") or 0) > 3
    on_river = fresh and not on_solar and any(str(p.get("ip")) in rids and (p.get("w") or 0) > 3 for p in inv.get("tp", []))
    last = (data.get("points") or [{}])[-1]
    pv = last.get("pv_w") or 0
    # 5.58: „proud zadarmo“ = jen když regulátor panely ŠKRTÍ – solární baterie je plná (Float), nebo ji regulátor drží
    # na nabíjecím napětí (Boost / absorpce) a bere jen tolik, kolik potřebuje. Jen tehdy je slunce navíc; jinak
    # (Bulk – baterie bere všechno) by každý watt pro Flip / router chyběl solární baterii (ta má přednost).
    # Stejná podmínka jako automatické nabíjení River. Navíc čistý výkon do baterie nesmí být záporný.
    status = last.get("status")
    bv = last.get("bat_v") or 0
    bt = last.get("bat_t")
    boost_v = (cfg.get("boost_V") or 14.4) + (max(-0.3, min(0.3, (25 - bt) * 0.018)) if bt is not None else 0)
    float_v = cfg.get("float_V") or 13.7
    load = inv.get("mw") or 0
    net_w = pv * 0.95 - (load / 0.88 + (cfg.get("menic_vlastni_W") or 6))      # W do solární baterie (záporné = vybíjí)
    reg_fresh = ts - last.get("t", 0) < 1800
    throttled = reg_fresh and ((status == 1 and bv >= float_v - 0.3) or (status == 2 and bv >= boost_v - 0.1))
    free_sun = bool(on_solar and throttled and pv >= 20 and net_w >= -5)
    # 5.59: odpoledne (3 h až 1 h před západem) nabít Flip i router do plna přímo z panelů, když panely pokryjí chatu
    # i nabíječku – energie uložená v telefonu / routeru přeskočí ztrátu nabití a vybití solární baterie (~15–20 %),
    # v noci ji stejně spotřebují. Když panely nestíhají, šlo by to ze solární baterie → nic se neušetří → ne.
    _, set_d = sun_times(cfg["sirka"], cfg["delka"], now.date())
    eve = bool(set_d and set_d - timedelta(hours=3) <= now <= set_d - timedelta(hours=1))
    fc_on = (inv.get("fc") or {}).get("on") == 1
    rc_on = (inv.get("rc") or {}).get("on") == 1
    FLIP_W, ROUTER_W = 15, 8                           # odhad příkonu nabíječek i se ztrátou měniče
    eve_flip = bool(on_solar and reg_fresh and eve and net_w - (0 if fc_on else FLIP_W) >= (-10 if fc_on else 0))
    if on_solar:
        allow = free_sun or eve_flip
        why = ("solární baterie plná (Float) – slunce navíc" if status == 1 else "regulátor drží nabíjecí napětí – slunce navíc") if free_sun \
            else f"odpoledne z panelů do plna (panely {pv:.0f} W pokryjí chatu {load:.0f} W i nabíjení)" if eve_flip \
            else f"chata na soláru – slunce navíc není (panely {pv:.0f} W, chata {load:.0f} W, {STATUS.get(status, '?')})"
    elif on_river:
        allow, why = False, "chata na River – jen při poklesu pod spodní hranici"
    else:
        allow, why = False, "zdroj neznámý – jen při poklesu pod spodní hranici"
    # 5.34: zásuvka routeru M7000 – Flip 1.9 ji řídí sám podle baterie routeru (40 / 80 %), povolení „allow“ =
    # proud zadarmo (River / přebytek) → nabíjet. Prázdné = neřídit (zásuvka zůstane, jak je).
    rip = str(cfg.get("zasuvka_router") or "").strip() if cfg.get("router_nabijeni_rizeni", True) else ""
    fs = st.setdefault("flip_chg", {})
    # 5.41: noční dobití Flipu (na soláru bez přebytku): při poklesu pod 20 % dobít jen na „ftgt“ – tolik, aby
    # vydržel do doby, kdy panely obvykle začnou mít přebytek (východ + 3 h), s rezervou 5 %. Rychlost vybíjení
    # = typická z posledních 24 h (flip_check), jinak 2 %/h.
    ff = data.get("flip_fc") or {}
    if ff.get("rate"):
        st["flip_rate"] = ff["rate"]
    rate = st.get("flip_rate") or 2.0
    ftgt, f_until = None, None
    if not (on_solar and allow):
        r0, _ = sun_times(cfg["sirka"], cfg["delka"], now.date())
        light = r0 + timedelta(hours=3) if r0 else None
        if light and now >= light:
            r1, _ = sun_times(cfg["sirka"], cfg["delka"], now.date() + timedelta(days=1))
            light = r1 + timedelta(hours=3) if r1 else None
        if light:
            hrs = (light - now).total_seconds() / 3600
            fmin = int(cfg.get("flip_min_pct") or 30)
            ftgt = int(max(fmin + 5, min(80, round(fmin + rate * hrs + 5))))
            f_until = int(light.timestamp())
    # 5.40: router nabíjet „zadarmo“ jen z přebytku slunce – proud z River zadarmo není (River musí vydržet noc)
    # 5.58: router stejně jako Flip – když regulátor škrtí panely; 5.59: odpoledne z panelů, když stačí i na Flip
    rfree = free_sun or bool(on_solar and reg_fresh and eve and net_w - (0 if rc_on else ROUTER_W)
                             - (FLIP_W if eve_flip and not fc_on else 0) >= (-10 if rc_on else 0))
    if fs.get("allow") != allow or fs.get("ip") != pid or fs.get("rip") != rip or fs.get("rfree") != rfree \
            or fs.get("fmin") != int(cfg.get("flip_min_pct") or 30) or abs((fs.get("ftgt") or 0) - (ftgt or 0)) >= 5 \
            or ts - fs.get("t", 0) >= 3600:
        body = json.dumps({"allow": allow, "ip": pid, "rip": rip, "rfree": rfree, "ftgt": ftgt or 0,
                           "fmin": int(cfg.get("flip_min_pct") or 30), "why": why, "id": int(ts)})
        try:
            urllib.request.urlopen(urllib.request.Request(f"https://ntfy.sh/{topic}-fc", data=body.encode(),
                                                          headers={"Title": "fc", "Priority": "1"}, method="POST"), timeout=20).read()
            fs.update(allow=allow, ip=pid, rip=rip, rfree=rfree, ftgt=ftgt, fmin=int(cfg.get("flip_min_pct") or 30), t=int(ts), why=why)
        except Exception as e:
            print("Povolení nabíjení Flipu:", e)
    data["flip_chg"] = {"allow": allow, "why": why, "ip": pid, "fc": inv.get("fc"), "ftgt": fs.get("ftgt"), "f_until": f_until, "rate": rate}
    # 5.60: pro web – kdy Flip při téhle rychlosti klesne na spodní hranici a na kolik se pak dobije (ftgt se počítá
    # „kdyby klesl teď“; Flipu se posílá průběžně, takže v okamžiku poklesu platí ten správný)
    pb = (inv.get("ph") or {}).get("b")
    fmin_ = int(cfg.get("flip_min_pct") or 30)
    if pb is not None and f_until and rate and not (inv.get("ph") or {}).get("c") and pb > fmin_:
        t_hit = ts + (pb - fmin_) / rate * 3600
        if t_hit < f_until:
            data["flip_chg"].update(t_hit=int(t_hit), tgt_hit=int(max(fmin_ + 5, min(80, round(fmin_ + rate * (f_until - t_hit) / 3600 + 5)))))
        else:
            data["flip_chg"].update(t_hit=None, ok_until=True)
    data["router_chg"] = {"ip": rip, "rc": inv.get("rc"), "rfree": rfree, "pv": round(pv), "load": round(inv.get("mw") or 0)}
    data["sun_free"] = {"free": free_sun, "eve": eve, "eve_flip": eve_flip, "set": int(set_d.timestamp()) if set_d else None, "status": status, "bv": bv, "boost_v": round(boost_v, 2), "float_v": float_v,
                        "net_w": round(net_w), "pv": round(pv), "load": round(load)}
    # 5.34: baterie routeru pod 25 % – vybitý router = chata bez Wi‑Fi a Flip už nic nezapne
    rb = (inv.get("rt") or {}).get("b")
    if fresh and rb is not None:
        if rb < 25 and not fs.get("rlow"):
            ntfy(topic, f"📶 Router na chatě má jen {rb:.0f} %",
                 f"Baterie routeru M7000 {rb:.0f} % ({'nabíjí se' if (inv.get('rt') or {}).get('c') else 'nenabíjí se'}). "
                 f"Až se vybije, chata je bez Wi‑Fi a bez dat. Zkontroluj zásuvku ({rip or '?'}) v aplikaci Tapo.", 4, "warning")
            fs["rlow"] = True
        elif fs.get("rlow") and rb >= 35:
            fs["rlow"] = False
    # horká baterie Flipu
    ph = inv.get("ph") or {}
    lim = cfg.get("flip_teplota_max_C") or 40
    if fresh and ph.get("t") is not None:
        if ph["t"] >= lim and not fs.get("hot"):
            ntfy(topic, f"🔥 Flip je horký – {fmt(ph['t'], 1)} °C",
                 f"Baterie Flipu má {fmt(ph['t'], 1)} °C ({'nabíjí se' if ph.get('c') else 'nenabíjí se'}). Nad 42 °C Flip nabíjení sám vypne. "
                 "Nemá na slunci / u topení?", 4, "fire,warning")
            fs["hot"] = True
        elif fs.get("hot") and ph["t"] <= lim - 4:
            fs["hot"] = False


def flip_check(data, st, now, topic, cfg):
    """4.51: jak rychle se Flip (brána na chatě) vybíjí a kdy dojde – s předstihem, ne až při 20 %.
    Historie baterie Flipu ve state.ph_hist (24 h). Z posledního úseku bez nabíjení (≥ 45 min, pokles ≥ 2 %) rychlost %/h.
    • nenabíjí se a pod 15 % klesne do 12 h → jednou za vybíjení „Flip vydrží jen do ~HH:MM“ (Vysoká)
    • v ranní čas z rozvrhu (den_kontrola) a dojde do 48 h → „Než odjedeš: Flip se nenabíjí…“ (Vysoká)"""
    inv = data.get("inverter") or {}
    ph = inv.get("ph") or {}
    ts = now.timestamp()
    h = st.setdefault("ph_hist", [])
    if ph.get("b") is not None and inv.get("t") and (not h or inv["t"] > h[-1][0]):
        h.append([int(inv["t"]), float(ph["b"]), 1 if ph.get("c") else 0])
    h[:] = [x for x in h if x[0] >= ts - 86400]
    data.pop("flip_fc", None)
    if not h or ts - h[-1][0] > 3600:
        return
    seg = []
    for x in reversed(h):                                  # poslední úsek bez nabíjení
        if x[2]:
            break
        seg.append(x)
    seg.reverse()
    fp = st.setdefault("flip_fc", {})
    if h[-1][2]:                                           # nabíjí se → vše znovu
        fp.clear()
        return
    if len(seg) < 3 or seg[-1][0] - seg[0][0] < 2700 or seg[0][1] - seg[-1][1] < 2:
        return
    rate_now = (seg[0][1] - seg[-1][1]) / ((seg[-1][0] - seg[0][0]) / 3600)      # %/h teď (poslední úsek)
    # 5.16: odhad podle typického vybíjení za 24 h (všechny úseky bez nabíjení), ne jen podle posledního úseku –
    # krátké intenzivní používání (např. vzdálená plocha) jinak dalo „vydrží jen do 21:40“ při 48 %
    drop = dur = 0.0
    for a, b_ in zip(h, h[1:]):
        if not a[2] and not b_[2] and 0 < b_[0] - a[0] <= 3600 and b_[1] <= a[1]:
            drop += a[1] - b_[1]
            dur += b_[0] - a[0]
    rate = drop / (dur / 3600) if dur >= 3 * 3600 and drop > 0 else rate_now
    b = seg[-1][1]
    t_empty = seg[-1][0] + b / rate * 3600
    t15 = seg[-1][0] + max(0.0, b - 15) / rate * 3600
    data["flip_fc"] = {"b": b, "rate": round(rate, 1), "rate_now": round(rate_now, 1), "t_empty": int(t_empty), "t15": int(t15)}
    hm = lambda t: f"{rel_day(t, now)} ~{datetime.fromtimestamp(t, TZ).strftime('%H:%M')}"
    # 5.02: když nabíjení Flipu řídí hlídač zásuvkou (9) a zásuvka je vidět, Flip se nenabíjí schválně (drží 40–80 %)
    # a dobije se sám → neupozorňovat. Jen když řízení nejde (zásuvka nevidět / vypnuté), nebo Flip i tak klesl pod 18 %.
    fid = str(cfg.get("zasuvka_flip") or "9")
    pp = next((p for p in inv.get("tp") or [] if str(p.get("ip")) == fid), None)
    ctl_ok = bool(cfg.get("flip_nabijeni_rizeni")) and pp is not None and not pp.get("off") and pp.get("err") is None
    data["flip_fc"]["ctl"] = ctl_ok
    if ctl_ok and b >= 18:
        return
    if t15 - ts < 12 * 3600 and not fp.get("early"):
        ntfy(topic, f"📱 Flip se nenabíjí – vydrží jen do {hm(t_empty)}",
             f"Má {b:.0f} %, ubývá ~{rate:.1f} % za hodinu → pod 15 % {hm(t15)}, vybitý {hm(t_empty)}.\n"
             "Bez Flipu nechodí data z Victronu ani zásuvek. Zkontroluj nabíječku / zásuvku u Flipu.", 4, "battery,warning")
        fp["early"], fp["early_t"] = True, int(ts)
    # ranní kontrola před odjezdem (stejný rozvrh jako výhled dne)
    tk = None
    for part in str(cfg.get("den_kontrola") or "").split(","):
        bits = part.strip().split()
        if len(bits) == 2 and bits[0].lower()[:2] == WD[now.weekday()] and ":" in bits[1]:
            tk = bits[1]
    if tk and t_empty - ts < 48 * 3600 and fp.get("morning") != now.strftime("%Y-%m-%d") and ts - fp.get("early_t", 0) > 6 * 3600:
        try:
            hh, mm = (int(x) for x in tk.split(":")[:2])
            t_k = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if t_k <= now <= t_k + timedelta(hours=2):        # 5.02: jen ráno v čase kontroly, ne kdykoli během dne
                ntfy(topic, f"📱 Než odjedeš: Flip se nenabíjí – vybije se {hm(t_empty)}",
                     f"Má {b:.0f} %, ubývá ~{rate:.1f} % za hodinu. Dej ho nabíjet, jinak přestanou chodit data.", 4, "battery,warning")
                fp["morning"] = now.strftime("%Y-%m-%d")
        except ValueError:
            pass


def full_charge_check(data, st, now, topic, cfg):
    """4.49: AGM nemá dlouho stát nedobitá (sulfatace). Když regulátor plne_nabiti_dni dní nepřešel do Float
    (= plně nabito), jedna klidná zpráva (Výchozí), pak nejvýš jednou za týden. Jen pro jistotu – v zimě normální."""
    lim = cfg.get("plne_nabiti_dni") or 14
    fl = [d_.get("fl") for d_ in data.get("days", {}).values() if d_.get("fl")]
    last = max(fl) if fl else None
    data["last_full"] = last
    if not last or not lim:
        return
    days_ = (now.timestamp() - last) / 86400
    fc = st.setdefault("fullchg", {})
    if days_ < lim:
        fc.clear()
        return
    if now.timestamp() - fc.get("t", 0) >= 7 * 86400 and 9 <= now.hour < 20:
        ntfy(topic, f"🔋 Solární baterie {int(days_)} dní bez plného nabití",
             f"Naposledy plně nabitá (Float) {rel_day(last, now)} {datetime.fromtimestamp(last, TZ).strftime('%-d. %-m.')}. "
             "AGM baterii dlouhé stání nedobité škodí (sulfatace). Až bude slunečno, nech ji nabít – chata klidně na River. "
             "Jen připomínka, další nejdřív za týden.", 3, "battery")
        fc["t"] = now.timestamp()


def cold_factor(data, cfg):
    """4.48: AGM má v chladu menší kapacitu – zhruba −0,6 % na °C pod 15 °C (při ~15 °C se kapacita měřila, v říjnu).
    Teplota z regulátoru (bat_t), medián poslední hodiny. 0 °C → ×0,91, −10 °C → ×0,85 (nejvýš ×0,6)."""
    pts = data.get("points", [])
    if not pts:
        return 1.0, None
    t1 = pts[-1]["t"]
    nm = str(cfg.get("teplomer_baterie") or "").strip()      # 1.5: teploměr u baterie (Xiaomi) má přednost před regulátorem
    T = sorted(p["th"][nm] for p in pts if nm and p["t"] >= t1 - 3600 and nm in (p.get("th") or {}))
    if not T:
        T = sorted(p["bat_t"] for p in pts if p["t"] >= t1 - 3600 and p.get("bat_t") is not None and -40 < p["bat_t"] < 80)
    if not T:
        return 1.0, None
    tm = T[len(T) // 2]
    return (max(0.6, 1 - 0.006 * (15 - tm)) if tm < 15 else 1.0), tm


def thermo_check(data, st, now, topic, cfg):
    """5.13: hlídání teploměrů Xiaomi. Seznam „teplomery“ (jména jako ve Flipu): když některý nepošle hodnotu
    teplomery_ticho_min minut (a Flip jinak posílá) → upozornění s důvodem (Flip ho neslyší / slyší, ale nejde
    přečíst); po návratu zpráva. Baterie teploměru: upozornění při teplomery_baterie (10 %, 5 %), znovu až po výměně.
    data["th_watch"] = [{n, last, why, b}]"""
    import re as _re, unicodedata as _ud
    key = lambda x: _ud.normalize("NFD", _re.sub(r"^[\s,;:.]+|[\s,;:.]+$", "", str(x or ""))).encode("ascii", "ignore").decode().lower()
    want = [w.strip() for w in str(cfg.get("teplomery") or "").split(",") if w.strip()]
    inv = data.get("inverter") or {}
    ts = int(now.timestamp())
    if not inv or ts - inv.get("t", 0) > 1800:
        return                                         # Flip mlčí – to hlídá jiná kontrola
    tw = st.setdefault("th_watch", {})
    # 5.38: baterie teploměru se mění pomalu a Xiaomi ji vysílá jen občas → pamatovat poslední známou (bt = kdy změřena)
    tb = st.setdefault("th_bat", {})
    for x in inv.get("th") or []:
        kb = key(x.get("n"))
        if x.get("b") is not None:
            tb[kb] = [x["b"], int(x.get("tm") or ts)]
            x["bt"] = tb[kb][1]
        elif kb in tb:
            x["b"], x["bt"] = tb[kb][0], tb[kb][1]
    th = {key(x.get("n")): x for x in inv.get("th") or []}
    lim_min = cfg.get("teplomery_ticho_min") or 60
    levels = sorted((int(float(x)) for x in str(cfg.get("teplomery_baterie") or "").replace(";", ",").split(",") if x.strip()), reverse=True)
    out = []
    names = want or [x.get("n") for x in inv.get("th") or []]
    for n in names:
        k = key(n)
        x = th.get(k) or {}
        e = tw.setdefault(k, {"first": ts})
        has = x.get("t") is not None or x.get("h") is not None
        if has:
            e["last"] = max(e.get("last") or 0, int(x.get("tm") or ts))
        last = e.get("last") or e["first"]
        why = None
        if not has:
            why = "Flip ho neslyší – mimo dosah Bluetooth nebo vybitý" if x.get("sn") == 0 else \
                  f"Flip ho slyší, ale nejde přečíst – zkontroluj klíč a MAC" if x.get("sn") and not x.get("ok") else \
                  "Flip ho nemá v nastavení" if want and not x else "Flip od něj nemá hodnotu"
        quiet = ts - last >= lim_min * 60
        if quiet and not e.get("warned"):
            ntfy(topic, f"🌡️ Teploměr {n} nehlásí", f"Poslední hodnota {rel_day(last, now)} {datetime.fromtimestamp(last, TZ).strftime('%H:%M')}. {why or ''}".strip(),
                 3, "thermometer,warning")
            log("ev", f"Teploměr {n} nehlásí – {why}")
            e["warned"] = True
        if has and e.get("warned"):
            ntfy(topic, f"🌡️ Teploměr {n} zase hlásí", f"{fmt(x.get('t'), 1)} °C", 2, "thermometer")
            e["warned"] = False
        b = x.get("b")
        if b is not None:
            if b >= 30:
                e["bw"] = []                            # nová baterie → upozornit znovu
            for lv in levels:
                if b <= lv and lv not in (e.get("bw") or []):
                    ntfy(topic, f"🪫 Teploměr {n}: baterie {b} %", "Vyměň baterii (CR2032)." if lv <= 5 else "Baterie teploměru dochází – připrav novou (CR2032).",
                         3 if lv <= 5 else 2, "battery")
                    e.setdefault("bw", []).extend([l2 for l2 in levels if l2 >= lv])
                    break
            e["b"] = b
        out.append({"n": n, "last": last if e.get("last") else None, "why": why if quiet or not has else None, "b": e.get("b"), "quiet": quiet})
    data["th_watch"] = out
    # 5.54: teploměr, který Flip zrovna neslyší (časté), ukázat s poslední známou hodnotou (šedě, „old“) – ne prázdný.
    # Body grafů a hlídání (lednice, mráz) berou jen čerstvé hodnoty (tm), takže se tím nic nezkreslí.
    tl = st.setdefault("th_last", {})
    for x in inv.get("th") or []:
        kx = key(x.get("n"))
        if x.get("t") is not None or x.get("h") is not None:
            tl[kx] = {"t": x.get("t"), "h": x.get("h"), "tm": int(x.get("tm") or ts)}
        elif kx in tl and ts - tl[kx]["tm"] < 7 * 86400:
            x.update(t=tl[kx]["t"], h=tl[kx]["h"], tm=tl[kx]["tm"], old=1)
    # 5.20: suchý vzduch v obytných místnostech (topení v kamnech na dřevo) – pod vlhkost_min dvě měření po sobě
    rooms = {key(w) for w in str(cfg.get("vlhkost_hlidat") or "").split(",") if w.strip()}
    hmin = cfg.get("vlhkost_min") or 35
    hs = st.setdefault("dry", {})
    for k, x in th.items():
        if k not in rooms or x.get("h") is None or ts - int(x.get("tm") or 0) > 1800:
            continue
        e = hs.setdefault(k, {})
        if x["h"] < hmin:
            e["n"] = e.get("n", 0) + (1 if e.get("t") != x.get("tm") else 0)
            e["t"] = x.get("tm")
            if e["n"] >= 2 and ts - e.get("warned", 0) > 12 * 3600:
                ntfy(topic, f"💧 Suchý vzduch – {x['n']} {fmt(x['h'], 0)} %",
                     f"V místnosti {x['n']} je jen {fmt(x['h'], 0)} % vlhkosti (dobré je 40–60 %). Dej na kamna hrnec s vodou, ať se odpařuje.",
                     3, "droplet")
                e["warned"] = ts
        elif x["h"] >= hmin + 5:
            e.clear()


def frost_check(data, st, now, topic, cfg):
    """4.48: mráz a solární baterie. Vybitá AGM v mrazu může zamrznout (elektrolyt) a prasknout, plná vydrží mnohem víc.
    • teplota ≤ mraz_C a nabití # < mraz_hash → upozornění (Vysoká), znovu až po oteplení / nabití
    • první mráz u baterie v sezóně → informace (Výchozí)"""
    if not cfg.get("mraz_hlidat", True):
        return
    f, T = cold_factor(data, cfg)
    data["cold"] = {"T": T, "f": round(f, 2)} if T is not None else None
    if T is None:
        return
    lim_t = cfg.get("mraz_C") if cfg.get("mraz_C") is not None else 0
    lim_h = cfg.get("mraz_hash") or 40
    pct = (data.get("hq") or {}).get("pct")
    fz = st.setdefault("frost", {})
    season = now.strftime("%Y") if now.month >= 7 else str(now.year - 1)
    if T <= lim_t and fz.get("first") != season:
        ntfy(topic, "❄️ Mráz u solární baterie", f"Teplota u baterie {fmt(T, 1)} °C. Nabitá AGM mráz vydrží, "
             f"vybitá může zamrznout – drž ji nabitou (upozorním, když bude pod {lim_h} # a pod {fmt(lim_t, 0)} °C). "
             f"Kapacita je v chladu menší (teď ~×{fmt(f, 2)}), výhledy s tím počítají.", 3, "snowflake")
        fz["first"] = season
    risk = T <= lim_t and pct is not None and pct < lim_h
    if risk and not fz.get("risk"):
        ntfy(topic, "❄️⚠️ Vybitá baterie v mrazu", f"Baterie {pct} # při {fmt(T, 1)} °C. Vybitá AGM může v mrazu zamrznout a prasknout. "
             "Nevybíjej ji dál (chata na River) a dobij ji, jak to půjde.", 4, "snowflake,warning")
        fz["risk"] = True
    elif fz.get("risk") and (T > lim_t + 2 or (pct is not None and pct >= lim_h + 10)):
        fz["risk"] = False


def night_learn(data, st, now, cfg):
    """4.42: učení výhledu do rána. Při západu slunce si zapíše, kolik Ah chata do rána spotřebuje (noční odběr ×
    dosavadní oprava), ráno při východu porovná se skutečností z # (body „hq“ = Ah od plné). Oprava = medián poměru
    skutečnost / předpověď z posledních až 7 nocí (0,6–1,6). Poměr, ne rozdíl – sedí i při delší noci (podzim)."""
    ts = now.timestamp()
    pend = st.get("dfl_pend")
    if pend and ts >= pend["t1"]:
        st["dfl_pend"] = None
        pts = [p for p in data.get("points", []) if pend["t0"] - 900 <= p["t"] <= pend["t1"] + 900]
        a_ = min((p for p in pts if p.get("hq") is not None), key=lambda p: abs(p["t"] - pend["t0"]), default=None)
        b_ = min((p for p in pts if p.get("hq") is not None), key=lambda p: abs(p["t"] - pend["t1"]), default=None)
        night = [p for p in pts if pend["t0"] <= p["t"] <= pend["t1"]]
        solar = night and sum(1 for p in night if (p.get("mw") or 0) > 3) >= 0.8 * len(night)   # celou noc na soláru
        if a_ and b_ and solar and abs(a_["t"] - pend["t0"]) < 1200 and abs(b_["t"] - pend["t1"]) < 1200 and pend["pred"] > 3:
            act = round(a_["hq"] - b_["hq"], 1)
            if act > 1:
                lg = st.setdefault("dfl_log", [])
                lg.append({"d": datetime.fromtimestamp(pend["t0"], TZ).strftime("%Y-%m-%d"), "pred": pend["pred"], "predc": pend.get("predc"),
                           "act": act, "r": round(act / pend["pred"], 2)})
                del lg[:-10]
    # jen noci z posledních 45 dní – po zimě na River (bez nocí na soláru) se stará oprava nepoužije
    cut = (now - timedelta(days=45)).strftime("%Y-%m-%d")
    lg = [x for x in (st.get("dfl_log") or []) if x["d"] >= cut]
    rs = sorted(x["r"] for x in lg[-7:])
    med = (rs[len(rs) // 2] + rs[(len(rs) - 1) // 2]) / 2 if rs else 1.0
    f = max(0.6, min(1.6, med)) if len(rs) >= 2 else 1.0                # aspoň 2 noci, jinak bez opravy
    data["dfl"] = {"f": round(f, 2), "n": len(rs), "log": lg[-7:]}
    return f


def day_outlook(data, st, now, topic, cfg, rise, set_):
    """Výhled dne (přání 18. 10. 2026): když chata jede ze solární baterie – vydrží do den_do (22:00)?
    Teď v baterii (# nad alarmem 12,0 V) + zbývající výroba podle předpovědi − odběr (průměr 3 h), po 10 min.
    data["day_fc"] = {ok, t_empty, t} pro web. Upozornění (Vysoká): v čas z rozvrhu den_kontrola (po dnech)
    a kdykoli během dne, když se výhled zhorší (ráno vydrželo, teď ne). Noc řeší jiná upozornění."""
    ts = now.timestamp()
    try:
        hh, mm = (int(x) for x in str(cfg.get("den_do") or "22:00").split(":")[:2])
    except ValueError:
        hh, mm = 22, 0
    end = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    inv = data.get("inverter") or {}
    fresh = inv and ts - inv.get("t", 0) < 1800
    rids = ips(cfg.get("zasuvky_river"))
    on_solar = fresh and (inv.get("mw") or 0) > 3
    on_river = fresh and not on_solar and any(str(p.get("ip")) in rids and (p.get("w") or 0) > 3 for p in inv.get("tp", []))
    hq = data.get("hq") or {}
    if not (on_solar or on_river) or now >= end or hq.get("pct") is None or (rise and now < rise - timedelta(hours=3)):
        data.pop("day_fc", None)
        return
    cf, _ = cold_factor(data, cfg)                                        # 4.48: v chladu menší kapacita
    cap = (hq.get("cap") or eff_cap(data, cfg)) * cf
    alarm = ocv_soc((cfg.get("baterie_kriticka_V") or 12.0) + 0.05)      # 12,0 V pod malou zátěží ≈ klid ~12,05 V
    ah = (hq["pct"] - alarm) / 100 * cap                                   # Ah nad alarmem
    room = (100 - hq["pct"]) / 100 * cap                                   # kolik se ještě vejde
    idle = (cfg.get("menic_vlastni_W") or 6) + (cfg.get("desulfator_W") or 0)
    if on_solar:
        mws = [p["mw"] for p in data.get("points", []) if p.get("mw") is not None and p["t"] >= ts - 3 * 3600]
        now_w = inv.get("mw") or 0
    else:                                   # chata na River: stejný odběr by šel přes měnič ze solární baterie
        mws = [sum((p["tp"].get(i) or 0) for i in rids) for p in data.get("points", []) if p.get("tp") and p["t"] >= ts - 3 * 3600]
        now_w = inv.get("rw") or 0
    load_a = ((sum(mws) / len(mws) if mws else now_w) / 0.88 + idle) / 12.4 * 1.15   # s rezervou: odběr +15 %
    today = now.strftime("%Y-%m-%d")
    pred = next((p for p in ((data.get("wxo") or {}).get("preds") or []) if p.get("d") == today), None)
    made = (data["days"].get(today) or {}).get("solar_kwh") or 0
    import math
    # podíl dne (podle tvaru výroby – sinus mezi východem a západem), který už proběhl
    def frac(t):
        if not rise or not set_:
            return 1.0
        x = min(1.0, max(0.0, (t - rise.timestamp()) / (set_.timestamp() - rise.timestamp())))
        return (1 - math.cos(math.pi * x)) / 2
    f_done = frac(ts)
    fc_kwh = pred["kwh"] if pred else 0
    # zbývající výroba: podle předpovědi, opravené tím, jak dnes skutečně vyrábí (dnes víc než předpověď → víc)
    ratio = made / (fc_kwh * f_done) if fc_kwh > 0 and f_done > 0.15 else 1.0
    ratio = max(0.3, min(3.0, ratio))
    # 4.39: ve Floatu regulátor výrobu přiškrtí (baterie plná) – nízká dnešní výroba pak není počasím → nesnižovat
    d0 = now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    if any(p.get("status") == 1 and p["t"] >= d0 for p in data.get("points", [])):
        ratio = max(ratio, 1.0)
    rem_kwh = fc_kwh * ratio * (1 - f_done) * 0.8                          # s rezervou −20 %
    rise2 = sun_times(cfg["sirka"], cfg["delka"], now.date() + timedelta(days=1))[0]
    # do rána = jako noční předpověď: do zítřejšího východu + nabijeni_od_vychodu_min (dřív +1 h)
    end2 = rise2.timestamp() + (cfg.get("nabijeni_od_vychodu_min") or 0) * 60 if rise2 else end.timestamp()
    # 4.40: po západu počítat s NOČNÍM odběrem (medián nocí za poslední 3 dny, chata na soláru) – denní průměr za 3 h
    # bývá vyšší (lednice v teple, nabíjení) a s +15 % výhled do rána zbytečně shazoval. Noc bez rezervy +15 %,
    # stejně jako noční předpověď (ta se navíc učí z minulých nocí).
    # 4.43: noci na River se počítají taky – zásuvky River měří stejný odběr chaty (230 V) jako zásuvka za měničem.
    # Bez toho by v zimě (noci jen na River) nebylo z čeho brát. Okno 7 nocí.
    def _nw(p):
        if (p.get("mw") or 0) > 3:
            return p["mw"]
        rw_ = sum((p.get("tp") or {}).get(i) or 0 for i in rids)
        return rw_ if rw_ > 3 else None
    nmw = sorted(w_ for p in data.get("points", []) if p["t"] >= ts - 7 * 86400 and (p.get("pv_w") or 0) < 5
                 and (datetime.fromtimestamp(p["t"], TZ).hour >= 21 or datetime.fromtimestamp(p["t"], TZ).hour < 5)
                 and (w_ := _nw(p)) is not None)
    load_n = ((nmw[len(nmw) // 2] if len(nmw) >= 12 else (cfg.get("noc_spotreba_W") or (sum(mws) / len(mws) if mws else now_w)))
              / 0.88 + idle) / 12.4
    set_ts = set_.timestamp() if set_ else end.timestamp()
    nf_ = (data.get("dfl") or {}).get("f") or 1.0
    load_n *= nf_                                                       # oprava podle minulých nocí (night_learn)
    if on_solar and set_ and ts >= set_ts and not st.get("dfl_pend") and st.get("dfl_day") != now.strftime("%Y-%m-%d") and rise2:
        st["dfl_day"] = now.strftime("%Y-%m-%d")                         # při západu: zapsat předpověď do rána
        st["dfl_pend"] = {"t0": int(ts), "t1": int(rise2.timestamp()), "pred": round(load_n / nf_ * (rise2.timestamp() - ts) / 3600, 1),
                           "predc": round(load_n * (rise2.timestamp() - ts) / 3600, 1)}   # pred = bez opravy (z něj se učí)
    steps, t = [], ts
    while t < end2:
        steps.append(t)
        t += 600
    w = [max(0.0, frac(t + 600) - frac(t)) for t in steps]
    wsum = sum(w) or 1
    t_empty, t_empty_n, lvl = None, None, ah
    for t, wi in zip(steps, w):
        prod_a_h = rem_kwh * 1000 * wi / wsum / 13.0 * 0.9                 # Ah do baterie v tomhle kroku
        lvl = min(lvl + prod_a_h, ah + room) - (load_a if t < set_ts else load_n) * 600 / 3600
        if lvl <= 0:
            t_empty_n = t
            if t < end.timestamp():
                t_empty = t
            break
    res = {"ok": t_empty is None, "t_empty": int(t_empty) if t_empty else None, "t": int(ts), "end": int(end.timestamp()),
           "load_w": round(load_a * 12.4), "rem_kwh": round(rem_kwh, 2), "pct": hq["pct"], "ratio": round(ratio, 2),
           "ah": round(ah, 1), "alarm": round(alarm), "cap": round(cap),
           "prod_ah": round(rem_kwh * 1000 / 13.0 * 0.9, 1), "cons_ah": round(load_a * (end.timestamp() - ts) / 3600, 1),
           "hrs": round((end.timestamp() - ts) / 3600, 1), "src": "solar" if on_solar else "river",
           "night_ok": t_empty_n is None, "t_empty_n": int(t_empty_n) if t_empty_n else None,
           "load_n_w": round(load_n * 12.4), "night_ah": round(load_n * max(0.0, end2 - max(ts, set_ts)) / 3600, 1),
           "lvl_end": round(lvl, 1) if t_empty_n is None else None, "nf": nf_, "cf": round(cf, 2)}
    data["day_fc"] = res
    day = now.strftime("%Y-%m-%d")
    # čas kontroly podle rozvrhu (dnešní den v týdnu)
    sched = {}
    for part in str(cfg.get("den_kontrola") or "").split(","):
        bits = part.strip().split()
        if len(bits) == 2 and bits[0].lower()[:2] in WD and ":" in bits[1]:
            sched[bits[0].lower()[:2]] = bits[1]
    tk = sched.get(WD[now.weekday()])
    due = False
    after = False                           # už je po dnešním čase kontroly (pro nabídku soláru během dne)
    if tk:
        try:
            h2, m2 = (int(x) for x in tk.split(":")[:2])
            tchk = now.replace(hour=h2, minute=m2, second=0, microsecond=0)
            due = now >= tchk and st.get("do_chk") != day
            after = now >= tchk
        except ValueError:
            pass
    if due:
        st["do_chk"] = day
    if on_river:                            # chata jede z River: v čas z rozvrhu nabídnout solár, když vydrží do večera
        # 4.30: nejen v čas z rozvrhu – i během dne, jakmile to poprvé vyjde (baterie se nabíjí, do večera ubývá hodin);
        # jednou za den, jen do konce výhledu (den_do)
        if (due or after) and res["ok"] and st.get("do_conn") != day and now.timestamp() < res["end"]:
            ntfy(topic, "☀️ Dnes můžeš chatu přepnout na solární baterii",
                 f"Solární baterie ({hq['pct']} #) s dnešní výrobou podle předpovědi (~{fmt(rem_kwh, 1)} kWh, s rezervou) "
                 f"vydrží chatu (~{res['load_w']} W) do {hh}:{mm:02d}.\nVečer zase přepoj na River.", 3, "sunny,battery")
            st["do_conn"] = day
        return
    worse = st.get("do_ok_day") == day and not res["ok"]                  # dnes už vycházelo, teď ne
    if res["ok"]:
        st["do_ok_day"] = day
        return
    if (due or worse) and st.get("do_sent") != day:
        te = datetime.fromtimestamp(res["t_empty"], TZ).strftime("%H:%M")
        ntfy(topic, f"⚠️ Dnes ~{te} solární baterie dojde – přepni chatu na River",
             f"Chata jede ze solární baterie ({hq['pct']} #, odběr ~{res['load_w']} W). Dnes ještě vyrobí ~{fmt(rem_kwh, 1)} kWh "
             f"(předpověď opravená podle dnešní výroby) – nestačí: pod 12,0 V dnes ~{te}, dřív než {hh}:{mm:02d}.\n"
             "Než odjedeš, přepni chatu na River. Počítáno s rezervou (výroba −20 %, odběr +15 %) – raději zbytečně přepnout, "
             "než aby přes den došla energie.", 4, "warning,sunny")
        st["do_sent"] = day


def hash_alert(data, st, now, topic, cfg):
    """Upozornění, když nabití # klesne pod hranice (výchozí 50 a 30) – každá jednou, znovu až po nabití nad 60 #."""
    hq = data.get("hq")
    if not hq or hq.get("pct") is None:
        return
    pct = hq["pct"]
    lims = sorted({int(float(x)) for x in str(cfg.get("hash_upozornit") or "50, 30").replace(";", ",").split(",") if x.strip()}, reverse=True)
    sent = st.setdefault("hash_sent", [])
    if pct >= 60 and sent:
        st["hash_sent"] = []
        return
    if cabin_on_river(data, cfg, now, st):
        return                                   # 5.43: chata jede z River – solární baterii nevybíjí, rada nedává smysl
    for lim in lims:
        if pct < lim and lim not in sent:
            ntfy(topic, f"🔋 Solární baterie pod {lim} #",
                 f"Nabití podle ampérhodin {pct} # (−{fmt(-hq['ah'], 0)} Ah od plného nabití, kapacita {hq['cap']} Ah). "
                 + ("Pod 50 # baterie rychle stárne – omez odběr nebo přepni chatu na River." if lim >= 50 else
                    "Hrozí poškození baterie – přepni chatu na River / odpoj spotřebiče."), 4 if lim < 50 else 3, "battery")
            sent.append(lim)
            break


def capacity_check(data, st, now, cfg):
    """Testy kapacity pro každé ráno po opravě spojů, pro které máme body (14 dní) – přepočítá se při každém běhu
    (dny bez dat se nemění). Jen s odběrem měniče (zásuvka 220 V za měničem) aspoň v 80 % bodů.
    1) od plného nabití: předchozí přechod do Float (≤ 30 h před východem) → ráno; kapacita = Ah ÷ (100 % − nabití ráno).
    2) dvoubodový (když 1 nejde – v zimě baterie často plná nebude): večer 2–3 h po západu a ráno před sluncem
       nabití z klidového napětí, mezi tím spočítané Ah; kapacita = Ah ÷ rozdíl nabití. Méně přesný.
    Nabití z napětí: AGM klidové napětí, opraveno o pokles odběrem (~10 mV/A). Výsledek days[k]["qc"]
    (m = "full" / "2b"); eff_cap bere medián úspěšných testů."""
    fts = fix_ts(cfg)
    idle = (cfg.get("menic_vlastni_W") or 6) + (cfg.get("desulfator_W") or 0)
    pts = [p for p in data.get("points", []) if p.get("q") is not None and p.get("bat_v")]
    if not pts:
        return
    # začátky Float (po opravě spojů)
    fl, prev = [], None
    for p in data.get("points", []):
        s_ = p.get("status")
        if s_ == 1 and prev != 1 and p["t"] >= fts:
            fl.append(p["t"])
        if s_ is not None:
            prev = s_

    def rest(p):                                    # klidové napětí a nabití z bodu
        i_load = ((p.get("mw") or 0) / 0.88 + idle) / p["bat_v"]
        v = p["bat_v"] + 0.01 * i_load
        return round(v, 2), ocv_soc(v)

    def covered(a, b):                              # známý odběr měniče aspoň v 80 % bodů
        w = [p for p in pts if a <= p["t"] <= b]
        return len(w) >= 6 and sum(1 for p in w if p.get("mw") is not None) >= 0.8 * len(w)

    d0 = datetime.fromtimestamp(max(fts, pts[0]["t"]), TZ).date()
    date = d0
    while date <= now.date():
        rise, _ = sun_times(cfg["sirka"], cfg["delka"], date)
        date_k = date.strftime("%Y-%m-%d")
        date = date + timedelta(days=1)
        if not rise or now < rise + timedelta(hours=1):
            continue
        r_ts = rise.timestamp()
        mor = [p for p in pts if r_ts - 2 * 3600 <= p["t"] <= r_ts + 900
               and (p.get("pv_w") or 0) < 5 and (p.get("mw") or 0) < 120 and not p.get("rc")]
        if not mor:
            continue                                # pro tohle ráno body nemáme (nebo už vypadly) – nechat, co je
        pm = min(mor, key=lambda x: x["bat_v"])
        vm, sm = rest(pm)
        res, why = {"ok": False, "m": "full"}, []
        # 1) od plného nabití
        full_t = max((f for f in fl if f < pm["t"]), default=0)
        if not full_t or r_ts - full_t > 30 * 3600:
            why.append("předtím nebyla plně nabitá (Float)")
        elif not covered(full_t, pm["t"]):
            why.append("chybí odběr měniče")
        else:
            ah = -pm["q"]
            res.update({"ah": round(ah, 1), "v": vm, "soc": round(sm), "t": pm["t"], "tf": int(full_t)})
            if ah < 20 or sm > 85:
                why.append(f"od plného nabití vybitá málo ({ah:.0f} Ah)")
            else:
                cap = ah / (1 - sm / 100)
                res.update({"cap": round(cap), "ok": 40 <= cap <= 300})
                if not res["ok"]:
                    why.append("nesmyslný výsledek")
        # 2) dvoubodový: večer → ráno
        if not res["ok"]:
            _, set_y = sun_times(cfg["sirka"], cfg["delka"], rise.date() - timedelta(days=1))
            eve = [p for p in pts if set_y and set_y.timestamp() + 2 * 3600 <= p["t"] <= set_y.timestamp() + 3 * 3600
                   and p["t"] >= fts and (p.get("pv_w") or 0) < 5 and (p.get("mw") or 0) < 120 and not p.get("rc")
                   and p.get("qr") is not None]
            if not eve:
                why.append("chybí večerní měření")
            elif pm.get("qr") is None or not covered(eve[0]["t"], pm["t"]):
                why.append("chybí odběr měniče přes noc")
            else:
                pe = eve[0]
                ve, se = rest(pe)
                ah2 = pe["qr"] - pm["qr"]
                d_soc = se - sm
                r2 = {"ok": False, "m": "2b", "ah": round(ah2, 1), "v": vm, "soc": round(sm), "t": pm["t"],
                      "ve": ve, "soce": round(se), "te": pe["t"]}
                if ah2 < 12 or d_soc < 12:
                    why.append(f"přes noc ubylo málo ({ah2:.0f} Ah, {d_soc:.0f} %)")
                else:
                    cap = ah2 / (d_soc / 100)
                    r2.update({"cap": round(cap), "ok": 40 <= cap <= 300})
                    if not r2["ok"]:
                        why.append("nesmyslný výsledek")
                if r2["ok"] or "ah" not in res:
                    res = r2
        if not res["ok"]:
            res["why"] = " · ".join(why) or "nevyšel"
        res.setdefault("t", int(pm["t"]))
        day = data["days"].setdefault(date_k, {})
        if day.get("qc") != res:
            day["qc"] = res
            print("Test kapacity", date_k, res)


def ecoflow_reminder(data, st, now, topic):
    """Jednorázová připomínka (přání 16. 10. 2026): až poběží EcoFlow, vrátit se k ovládání nabíjení River
    a k optimalizaci běhu generátoru (viz docs/napady.md)."""
    if st.get("ef_remind") or not data.get("rivers") or now.timestamp() - (data.get("rivers_t") or 0) > 3600:
        return
    ntfy(topic, "🔔 Připomínka: EcoFlow funguje",
         "Data z EcoFlow už chodí. Domluvili jsme se, že se pak vrátíme k ovládání nabíjení River a k optimalizaci "
         "nabíjení z generátoru (aby všechny River dobily najednou a generátor běžel co nejkratší dobu). "
         "Napiš o tom Claudovi – podrobnosti jsou v docs/napady.md.", 3, "bell")
    st["ef_remind"] = int(now.timestamp())


def river_for_plug(pid, pname, rivers, cfg):
    """5.04: EcoFlow River k zásuvce na jejím výstupu – podle nastavení river_sn („2:1167, 3:0035“), jinak podle
    prvních 3 písmen jména bez diakritiky (ZLUTA ECFLW (2) ↔ ŽLUT. VELKÁ ECFLW)."""
    import re as _re, unicodedata as _ud
    norm = lambda x: _re.sub(r"[^a-z0-9 ]", " ", _ud.normalize("NFD", str(x or "")).encode("ascii", "ignore").decode().lower())
    for part in str(cfg.get("river_sn") or "").split(","):
        if ":" in part:
            a, b = (x.strip() for x in part.split(":", 1))
            if a == str(pid) and b:
                m = next((r for r in rivers if str(r.get("sn", "")).upper().endswith(b.upper())), None)
                if m:
                    return m
    w = [x for x in norm(_re.sub(r"\([^)]*\)", " ", str(pname or ""))).split() if x]
    if not w:
        return None
    hits = [r for r in rivers if norm(r.get("name")).split()[:1] and norm(r.get("name")).split()[0][:3] == w[0][:3]]
    return hits[0] if len(hits) == 1 else None


def river_supply(data, st, now, topic, cfg, rise, set_):
    """Která River teď napájí chatu, kolik má a na jak dlouho vydrží při průměrném odběru (poslední 3 h).
    data["river_sup"] = {name, soc, w, h, until}; večer upozorní, když nevydrží do zítřejšího rána."""
    rv = data.get("rivers") or []
    act = []
    if now.timestamp() - (data.get("rivers_t") or 0) <= 3600:
        # 4.82: chatu napájí jen velká River (malá nikdy – ta jen spotřebiče); a jen když chata nejede ze soláru
        inv_ = data.get("inverter") or {}
        on_solar = now.timestamp() - inv_.get("t", 0) < 1800 and (inv_.get("mw") or 0) > 3
        act = [(i, r) for i, r in enumerate(rv) if r.get("online") and r.get("soc") is not None and not on_solar
               and (r.get("wh") or 768) >= 500 and (r.get("out_w") or 0) - (r.get("in_w") or 0) > 3]
    plug_extra = {}
    if not act:
        river_supply_plugs(data, now, cfg)      # bez EcoFlow: pozná se ze zásuvek na výstupu River
        # 5.04: zásuvka ukáže, která River napájí; % a výdrž doplnit z EcoFlow podle spárování (jinak hodinky
        # i web psaly „% až z EcoFlow“, i když EcoFlow % posílá)
        ps = data.get("river_sup")
        r = river_for_plug(ps.get("id"), ps.get("name"), rv, cfg) if ps and ps.get("plug") else None
        if not r or r.get("soc") is None or not r.get("online"):
            return
        avg = ps.get("w") or 0
        plug_extra = {k: ps.get(k) for k in ("now", "t0", "wh", "id")}
    else:
        i, r = max(act, key=lambda x: x[1].get("out_w") or 0)
        cur = (r.get("out_w") or 0) - (r.get("in_w") or 0)
        # 5.39: průměr jen od chvíle, kdy River chatu napájí (souvislý úsek s výstupem > 3 W, nejvýš 3 h). Dřív se
        # brali celé 3 h – po přepnutí ze soláru na River se do průměru počítaly i nuly („🏠 4 W“ místo 19 W
        # a moc optimistická výdrž).
        ts_ = now.timestamp()
        seg, t0, wh, nxt = [], ts_, 0.0, (ts_, cur)
        k6 = str(r.get("sn", ""))[-6:]
        for p in reversed(data.get("points", [])):
            if p["t"] < ts_ - 3 * 3600:
                break
            e_ = next((x for x in p.get("rv") or [] if x.get("k") == k6), None) if k6 else None
            if e_ is None and len(p.get("rv") or []) > i and not k6:
                e_ = p["rv"][i]
            if e_ is None:
                continue                                 # v tomhle bodě EcoFlow nepřečtený
            o = e_.get("o")
            if o is None or o <= 3:
                break
            seg.append(o)
            wh += (nxt[1] + o) / 2 * min(nxt[0] - p["t"], 1800) / 3600
            t0, nxt = p["t"], (p["t"], o)
        avg = sum(seg) / len(seg) if len(seg) >= 3 else cur
        plug_extra = {"now": round(cur), "t0": int(t0), "wh": round(wh)}
    if avg < 3:
        data.pop("river_sup", None)
        return
    cap = r.get("wh") or cfg.get("river_Wh") or 768                 # 4.62: kapacita podle modelu z EcoFlow
    res = cfg.get("river_rezerva_pct") or 5
    left = max(0.0, r["soc"] - res) / 100 * cap * 0.9          # 0,9 = ztráty měniče v River
    h = left / avg
    # 5.45: výdrž hlavně podle skutečného úbytku % (od kdy River chatu napájí, nejvýš 12 h) – zahrnuje ztráty
    # i lednici a vše, co výkon v jednotlivých měřeních nezachytí. Z výkonu (W) jen když úbytek ještě nejde změřit.
    k6 = str(r.get("sn", ""))[-6:]
    ser = []                                                    # (t, soc) od teď zpátky, dokud % neklesá zpátky v čase
    for p in reversed(data.get("points", [])):
        if p["t"] < now.timestamp() - 12 * 3600:
            break
        e_ = next((x for x in p.get("rv") or [] if x.get("k") == k6), None) if k6 else None
        if not e_ or e_.get("s") is None:
            continue
        if (e_.get("i") or 0) > 20:                             # tehdy se nabíjela
            break
        if ser and e_["s"] < ser[-1][1] - 1:                    # dřív měla méně % = mezitím se nabila
            break
        ser.append((p["t"], e_["s"]))
    rate, r_t0 = None, None
    if len(ser) >= 3:
        (t1, s1), (t0, s0) = ser[0], ser[-1]
        hrs = (t1 - t0) / 3600
        if hrs >= 1.5 and s0 - s1 >= 3:
            rate, r_t0 = (s0 - s1) / hrs, t0
            h = max(0.0, r["soc"] - res) / rate
    until = int(now.timestamp() + h * 3600)
    data["river_sup"] = {"name": r["name"], "soc": round(r["soc"]), "w": round(avg), "h": round(h, 1), "until": until,
                         "rate": round(rate, 1) if rate else None, "r_t0": int(r_t0) if r_t0 else None,
                         "cap": cap, "res": res, "sn": str(r.get("sn", ""))[-6:], **plug_extra}
    # večer: vydrží do zítřejšího rána?
    if not (rise and set_):
        return
    evening = now >= set_ + timedelta(hours=1)
    if not evening and not now < rise:
        st["rv_night_warned"] = False
        return
    morning = (rise + timedelta(days=1) if evening else rise) + timedelta(hours=1)
    if until < morning.timestamp() and not st.get("rv_night_warned"):
        ntfy(topic, f"🔋 {r['name']} {do_rana(morning.timestamp(), now)} nevydrží",
             f"{r['name']} má {fmt(r['soc'])} %, chata bere průměrně ~{fmt(avg)} W → vybije se {rel_day(until, now)} "
             f"~{datetime.fromtimestamp(until, TZ).strftime('%H:%M')} (rezerva {res} %).\nPřepoj chatu na druhou River nebo omez odběr.",
             4, "battery,warning")
        st["rv_night_warned"] = True


def river_supply_plugs(data, now, cfg):
    """Záloha, když z EcoFlow nic nepřichází: kterou River chata právě tahne, se pozná ze zásuvky Tapo
    na jejím výstupu (zasuvky_river). data["river_sup"] = {name, w, t0, wh, plug: True} – bez % a výdrže."""
    data.pop("river_sup", None)
    inv = data.get("inverter") or {}
    ts = now.timestamp()
    if not inv or ts - inv.get("t", 0) > 1800:
        return
    ids = ips(cfg.get("zasuvky_river"))
    act = [p for p in inv.get("tp", []) if str(p.get("ip")) in ids and (p.get("w") or 0) > 3 and not p.get("gone")]
    if not act or (inv.get("mw") or 0) > 3:     # měnič dodává = chata jede ze soláru, River jen napájí nějaký spotřebič
        return
    p = max(act, key=lambda x: x.get("w") or 0)
    pid = str(p["ip"])
    import re as _re
    name = _re.sub(r"^\s*(\([^)]*\)\s*)+", "", str(p.get("n") or "")).strip() or f"River ({pid})"
    # od kdy napájí (souvislý úsek bodů s odběrem > 3 W) a kolik za tu dobu dodala
    pts = [q for q in data.get("points", []) if q["t"] >= ts - 36 * 3600]
    t0, wh, nxt = ts, 0.0, (ts, p.get("w") or 0)
    for q in reversed(pts):
        w = (q.get("tp") or {}).get(pid)
        if w is None or w <= 3:
            break
        wh += (nxt[1] + w) / 2 * min(nxt[0] - q["t"], 1800) / 3600
        t0, nxt = q["t"], (q["t"], w)
    vals = [(q.get("tp") or {}).get(pid) for q in pts if q["t"] >= max(t0, ts - 3 * 3600)]
    vals = [x for x in vals if x is not None]
    avg = sum(vals) / len(vals) if len(vals) >= 3 else (p.get("w") or 0)
    data["river_sup"] = {"name": name, "w": round(avg), "now": round(p.get("w") or 0), "t0": int(t0),
                         "wh": round(wh), "id": pid, "plug": True}


def gen_sessions(data, st, now, topic, cfg):
    """Záznam běhů generátoru: od kdy do kdy, kolik dodal (zásuvka Tapo generátoru) a o kolik se nabily River.
    data["gen_log"] = [{t0, t1, wh, rv: {sn: {name, s0, s1}}, src}], poslední běh zůstane vidět i po vypnutí."""
    ts = int(now.timestamp())
    inv = data.get("inverter") or {}
    fresh = inv and ts - inv.get("t", 0) < 1800
    gip = str(cfg.get("zasuvka_generator") or "").strip()
    g = (inv.get("gen") or {}) if fresh else {}
    gen_on = (g.get("w") or 0) > 5
    rv_fresh = ts - (data.get("rivers_t") or 0) < 3600
    rivers = [r for r in (data.get("rivers") or []) if r.get("online")] if rv_fresh else []
    auto_on = bool((data.get("river_auto") or {}).get("on"))
    chg = [r for r in rivers if (r.get("in_w") or 0) > 20]
    # 4.77: běh generátoru jen podle jeho zásuvky. Dřív stačilo, že se nějaká River nabíjí – jenže River se
    # nabíjí i z jiné River (červená z malé) a web pak všude psal „nabíjí se z generátoru“ / „generátor běží“.
    # Podle River jen když zásuvka generátoru není nastavená.
    active = gen_on or (not gip and bool(chg) and not auto_on)
    log_ = data.setdefault("gen_log", [])
    if not st.get("gen_bf"):                          # jednorázově: dohledat dřívější běhy z uložených bodů (14 dní)
        st["gen_bf"] = True
        try:
            pts = data.get("points", [])
            on = [p for p in pts if ((p.get("tp") or {}).get(gip) or 0) > 5]
            runs, run = [], []
            for p_ in on:
                if run and p_["t"] - run[-1]["t"] > 2400:
                    runs.append(run); run = []
                run.append(p_)
            if run:
                runs.append(run)
            names = [r.get("name") for r in (data.get("rivers") or [])]
            for run in runs:
                t0, t1 = run[0]["t"], run[-1]["t"]
                if t1 - t0 < 600 or (cur := st.get("gen_cur")) and cur.get("t0", 0) <= t1:
                    continue
                wh = 0.0
                for a_, b_ in zip(run, run[1:]):
                    wh += a_["tp"][gip] * min(b_["t"] - a_["t"], 1800) / 3600
                before = next((p_ for p_ in reversed(pts) if p_["t"] <= t0 and p_.get("rv")), None)
                after = next((p_ for p_ in pts if p_["t"] >= t1 and p_.get("rv")), None)
                rv = {}
                if before and after:
                    for i, (x, y) in enumerate(zip(before["rv"], after["rv"])):
                        if x.get("s") is not None and y.get("s") is not None and y["s"] > x["s"]:
                            rv[str(i)] = {"name": names[i] if i < len(names) else "River", "s0": x["s"], "s1": y["s"], "chg": True}
                log_.append({"t0": t0, "t1": t1, "wh": round(wh, 1), "rv": rv, "src": "body"})
            log_.sort(key=lambda r: r["t0"])
        except Exception as e:
            print("Generátor – zpětně:", e)
    cur = st.get("gen_cur")
    day_wh = lambda: ((data.get("days", {}).get(now.strftime("%Y-%m-%d")) or {}).get("tp") or {}).get(gip)
    # 4.34: výchozí stav počítadla = co dnes dodaly už UKONČENÉ běhy. Dřív se brala hodnota počítadla v chvíli, kdy
    # hlídač běh poprvé uviděl – když běh začal v mezeře (Flip nemohl posílat), energie z té doby se ztratila
    # (19. 10.: web 0,29 kWh, zásuvka 1,3 kWh). Zásuvka generátoru měří jen generátor, takže zbytek patří tomuto běhu.
    d0 = now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    prev_today = lambda: sum(r.get("wh") or 0 for r in log_ if (r.get("t0") or 0) >= d0)
    if cur and not cur.get("w0fix") and cur.get("d") == now.strftime("%Y-%m-%d") and cur.get("src") == "tapo":
        cur["w0"] = min(cur.get("w0") or 0.0, prev_today())
        cur["w0fix"] = True
    if active:
        if not cur:
            t0 = int(g.get("since") or ts) if gen_on else ts       # Flip ví, kdy se zásuvka objevila
            dw0 = day_wh()
            cur = {"t0": min(t0, ts), "src": "tapo" if gen_on else "river", "rv": {}, "wh": 0.0, "w0fix": True,
                   "d": now.strftime("%Y-%m-%d"), "w0": min(dw0, prev_today()) if dw0 is not None else None}
            log("ev", "Generátor: začátek nabíjení" + (f" ({fmt(g.get('w'))} W)" if gen_on else ""))
        # energie z generátoru: přírůstek denního počítadla zásuvky (přes půlnoc se počítá znovu od nuly)
        dw = day_wh()
        if dw is not None:
            if cur.get("d") != now.strftime("%Y-%m-%d"):
                cur["wh_prev"] = cur.get("wh", 0.0)
                cur["d"], cur["w0"] = now.strftime("%Y-%m-%d"), 0.0
            cur["wh"] = round(cur.get("wh_prev", 0.0) + max(0.0, dw - (cur.get("w0") or 0.0)), 1)
        for r in rivers:
            k = str(r.get("sn", ""))[-6:]
            e = cur["rv"].setdefault(k, {"name": r.get("name"), "s0": r.get("soc"), "wh": r.get("wh")})
            e["s1"] = r.get("soc")
            if (r.get("in_w") or 0) > 20:
                e["chg"] = True
        cur["t1"] = ts
        cur["w"] = g.get("w") if gen_on else None
        st["gen_cur"] = cur
        data["gen_cur"] = {k: v for k, v in cur.items() if k not in ("w0", "wh_prev", "d", "w0fix")}
        return
    if cur and not fresh and ts - cur.get("t1", ts) < 3600:
        return                                         # Flip chvíli mlčí – běh ještě neukončovat
    if cur:                                            # konečné % River (nabíjení právě skončilo)
        for r in rivers:
            e = cur["rv"].get(str(r.get("sn", ""))[-6:])
            if e is not None and r.get("soc") is not None:
                e["s1"] = r["soc"]
    if cur and g.get("gone"):                          # Flip ví, kdy zásuvka zmizela (generátor se vypnul)
        cur["t1"] = max(cur.get("t0", 0), min(int(g["gone"]), ts))
        dw = day_wh()
        if dw is not None and cur.get("d") == now.strftime("%Y-%m-%d"):
            cur["wh"] = round(cur.get("wh_prev", 0.0) + max(0.0, dw - (cur.get("w0") or 0.0)), 1)
    if cur and cur.get("src") == "river" and gip:      # 4.77: „běh“ vzniklý jen z nabíjení River – nebyl to generátor
        st["gen_cur"] = None
        data.pop("gen_cur", None)
        return
    if cur:                                            # běh skončil → uložit a poslat souhrn
        cur["rv"] = {k: v for k, v in cur["rv"].items() if v.get("chg")}
        rec = {k: v for k, v in cur.items() if k not in ("w0", "wh_prev", "d", "w", "w0fix")}
        log_.append(rec)
        del log_[:-60]
        st["gen_cur"] = None
        data.pop("gen_cur", None)
        cap = cfg.get("river_Wh") or 768
        rv_txt, got = [], 0.0
        for v in rec["rv"].values():
            if v.get("s0") is not None and v.get("s1") is not None:
                d_ = (v["s1"] - v["s0"]) / 100 * (v.get("wh") or cap)
                got += max(0.0, d_)
                rv_txt.append(f"{v.get('name') or 'River'} {fmt(v['s0'])} → {fmt(v['s1'])} % (+{fmt(d_ / 1000, 2)} kWh)")
        dur = (rec["t1"] - rec["t0"]) / 3600
        eff = f" · účinnost ~{fmt(got / rec['wh'] * 100)} %" if rec.get("wh") and got > 0 else ""
        msg = (f"Běžel ~{fmt(dur, 1)} h, dodal {fmt((rec.get('wh') or 0) / 1000, 2)} kWh." if rec.get("wh") else f"Běžel ~{fmt(dur, 1)} h.") + \
              ("\n" + "\n".join(rv_txt) if rv_txt else "") + eff
        log("ev", "Generátor: konec – " + msg.replace("\n", " · "))
        ntfy(topic, "⛽ Generátor doběhl", msg, 2, "fuelpump")


def plug_watch(data, st, now, topic, cfg):
    """4.72: zásuvky, které mají být vidět pořád (zasuvky_stale, např. 1 měnič, 4 lednice, 5 router, 9 Flip).
    Když ji Flip nepřečte ve 2 měřeních po sobě a aspoň zasuvky_stale_min minut → upozornění podle jména.
    Zásuvka měniče jen když Victron hlásí, že měnič běží (vypnutý měnič = zásuvka bez proudu, to je v pořádku).
    data["plug_miss"] = [{id, n, since, why}]"""
    ids_ = ips(cfg.get("zasuvky_stale"))
    inv = data.get("inverter") or {}
    ts = int(now.timestamp())
    if not ids_ or not inv or ts - inv.get("t", 0) > 1800:
        return                                         # Flip mlčí – to hlídá jiná kontrola
    pw = st.setdefault("plug_watch", {})
    names = pw.setdefault("names", {})
    by = {str(p.get("ip")): p for p in inv.get("tp") or []}
    for i, p in by.items():
        if p.get("n") and not p.get("off") and p.get("err") is None:
            names[i] = str(p["n"])[:40]
    new_msg = inv.get("t") != pw.get("t")
    pw["t"] = inv.get("t")
    mip = str(cfg.get("zasuvka_menic") or inv.get("mip") or "1")
    inv_on = str(inv.get("st") or "").upper() == "INVERTING"
    # 5.03: chata jede z River (zásuvka na výstupu River bere) → zásuvka měniče je odpojená přepínačem, to je v pořádku
    rids = ips(cfg.get("zasuvky_river"))
    on_river = any(str(p.get("ip")) in rids and (p.get("w") or 0) > 3 for p in inv.get("tp") or [])
    if on_river:
        inv_on = False
    miss = []
    for i in ids_:
        p = by.get(i)
        bad = p is None or p.get("off") or p.get("gone") or p.get("err") is not None
        if i == mip and not inv_on:
            bad = False                                # měnič vypnutý / chata na River → zásuvka měniče bez proudu
            if pw.get(i, {}).get("warned"):            # 5.03: rozběhnuté upozornění tiše zrušit (bez „je zase vidět“)
                pw[i] = {}
        e = pw.setdefault(i, {})
        if not bad:
            if e.get("warned"):
                ntfy(topic, f"🔌 {names.get(i, f'Zásuvka ({i})')} je zase vidět",
                     f"Flip ji znovu čte (nebyla vidět od {datetime.fromtimestamp(e['since'], TZ).strftime('%H:%M')}).", 2, "electric_plug")
                log("ev", f"Zásuvka ({i}) zase vidět")
            pw[i] = {}
            continue
        why = "Flip ji v síti nenašel" if p is None else "nedostupná (bez proudu nebo mimo Wi-Fi)" if p.get("off") or p.get("gone") \
            else f"chyba: {str(p.get('err'))[:60]}"
        if "401" in why:
            why = "odmítá přihlášení (aktualizace softwaru zásuvky / Kompatibilita s třetími stranami v Tapo)"
        e.setdefault("since", inv.get("t") or ts)
        if new_msg:
            e["n"] = e.get("n", 0) + 1
        e["why"] = why
        nm = names.get(i, f"Zásuvka ({i})")
        miss.append({"id": i, "n": nm, "since": e["since"], "why": why})
        if not e.get("warned") and e.get("n", 0) >= 2 and ts - e["since"] >= (cfg.get("zasuvky_stale_min") or 8) * 60:
            extra = " Bez ní hlídač nezná odběr chaty ze solární baterie." if i == mip else ""
            ntfy(topic, f"🔌 {nm} není vidět",
                 f"Flip ji nečte od {datetime.fromtimestamp(e['since'], TZ).strftime('%H:%M')} – {why}.{extra}\n"
                 "Zkontroluj, jestli má proud a Wi-Fi (v aplikaci Tapo je online?).", 4, "electric_plug,warning")
            log("ev", f"Zásuvka ({i}) není vidět – {why}")
            e["warned"] = True
    data["plug_miss"] = miss

PRO_CHG_W = (200, 940)     # River 2 Pro: rozsah nabíjecího výkonu ze sítě (AC)
SMALL_CHG_W = (100, 360)   # River 2 (malá): rozsah nabíjecího výkonu ze sítě (AC) – ovládá se přes aplikaci


def gen_charge_ctl(data, st, now, topic, cfg):
    """4.68 / 4.87: nabíjení River z generátoru.
    • Tlačítko na webu „Spustit nabíjení z generátoru“ (GEN_CMD=start) zahájí relaci: hlídač pak běží ve smyčce
      a každých 30 s čte EcoFlow (přes aplikaci – živě) a přenastavuje výkony; na konci běhu spustí další běh sám.
      Bez tlačítka se relace zahájí sama, když se River začnou nabíjet (pomaleji – po měřeních Flipu).
    • Klid: velké River na gen_po_behu_W (200 W), ať start generátoru nic nepřetíží. Nabíjení běží 30 s → vypočítané
      výkony (všechny skončí zároveň, generátor naplno: max podle paliva − rezerva − malá River).
    • Jakmile se River přestane nabíjet (plná / odpojená), hned zpět na 200 W. Konec relace: 10 min nic nenabíjí,
      nebo tlačítko „Ukončit“ → všem 200 W; „Generátor běží naprázdno“, když generátor dál dodává.
    • Počet River je libovolný (1–3, malá se ovládat nedá – odečte se, kolik bere)."""
    gs = st.setdefault("gen_ctl", {})
    sets = gs.setdefault("w", {})                       # co hlídač naposledy nastavil (SN → W)
    cmd = os.environ.get("GEN_CMD", "").strip().lower()
    # 5.25: povel z tlačítka i přes nastavení („gen_povel = start:lpg:čas“) – ruční spuštění hlídače GitHub zahodí, když
    # mezitím přijde běh z Flipu (čekat smí jen jeden); nastavení si přečte každý další běh
    pv_ = str(cfg.get("gen_povel") or "").strip().lower().split(":")
    if len(pv_) == 3 and pv_[2].isdigit():
        pt_ = int(pv_[2])
        if pt_ > (gs.get("cmd_t") or 0) and now.timestamp() - pt_ < 2 * 3600:
            gs["cmd_t"] = pt_
            if not cmd:
                cmd = pv_[0] + (":" + pv_[1] if pv_[1] else "")
            log("ev", f"Nabíjení z generátoru: povel z webu „{pv_[0]}{(' ' + pv_[1]) if pv_[1] else ''}“")
        elif cmd and cmd.startswith(pv_[0]) and now.timestamp() - pt_ < 600:
            cmd = ""                                       # stejné zmáčknutí už převzal dřívější běh – nespouštět znovu
    if ":" in cmd:                                       # 4.91: „start:lpg“ – palivo rovnou z tlačítka
        cmd, f_ = cmd.split(":", 1)
        if f_ in ("lpg", "plyn", "benzin"):
            cfg["gen_palivo"] = f_
    ts0 = int(now.timestamp())
    if cmd == "start":                                   # i během nabíjení = nový start (např. po přepnutí na plyn)
        gs.update({"btn": ts0, "first": None, "idle": None, "t_on": ts0, "active": True, "idle_warned": False, "ever": False,
                   "restart": True})
        gs.pop("stop", None)
        for k_ in ("con", "low", "chg_t", "sig", "wh", "e_t", "e_w"):
            gs.pop(k_, None)
        log("ev", f"Nabíjení z generátoru: spuštěno tlačítkem ({'plyn' if str(cfg.get('gen_palivo')).startswith(('lpg', 'plyn')) else 'benzín'})")
    elif cmd == "stop" and gs.get("active"):
        gs["stop"] = True
        log("ev", "Nabíjení z generátoru: ukončeno tlačítkem")
    if not cfg.get("gen_rizeni"):
        data.pop("gen_plan", None)
        return
    ak = os.environ.get("ECOFLOW_ACCESS_KEY", "").strip()
    sk = os.environ.get("ECOFLOW_SECRET_KEY", "").strip()
    host = st.get("eco_host")
    fuel = "lpg" if str(cfg.get("gen_palivo") or "").lower().startswith(("lpg", "plyn")) else "benzin"
    gmax = cfg.get("gen_max_lpg_W" if fuel == "lpg" else "gen_max_benzin_W") or (1600 if fuel == "lpg" else 1800)
    budget = gmax - (cfg.get("gen_rezerva_W") or 0)
    safe_pro = max(PRO_CHG_W[0], min(PRO_CHG_W[1], int(cfg.get("gen_po_behu_W") or 200)))
    safe_small = max(SMALL_CHG_W[0], min(SMALL_CHG_W[1], int(cfg.get("gen_mala_po_behu_W") or 100)))
    acw = lambda r: r.get("ac_in_w") if r.get("ac_in_w") is not None else (r.get("in_w") or 0)
    is_pro = lambda r: "pro" in str(r.get("model") or "").lower() and not r.get("qerr")
    is_small = lambda r: (r.get("wh") or 768) < 500 and not r.get("gen")
    # 4.88: ovládat jde i malá – přes aplikaci (src app); velké přes vývojářské rozhraní
    ctl_ok = lambda r: is_pro(r) or (is_small(r) and r.get("src") == "app")
    rng = lambda r: SMALL_CHG_W if is_small(r) else PRO_CHG_W
    safe_of = lambda r: safe_small if is_small(r) else safe_pro
    byid = lambda sn: next((r for r in data.get("rivers") or [] if r.get("sn") == sn), {})
    for r in data.get("rivers") or []:                   # skutečně nastavený výkon (když ho River hlásí)
        if r.get("cfg_w") is not None:
            sets[r["sn"]] = r["cfg_w"]

    def apply(plan_w):
        """Nastavit výkony – nejdřív snížení, pak zvýšení (ať generátor ani na chvíli nepřetíží)."""
        done = []
        if not (ak and sk and host) and not st.get("efp"):
            return ["EcoFlow klíče chybí"]
        import ecoflow
        for sn, w in sorted(plan_w.items(), key=lambda x: x[1] - (sets.get(x[0]) or 9999)):
            if sets.get(sn) is not None and abs(sets[sn] - w) < 20:
                continue
            try:
                if is_small(byid(sn)):
                    import ecoflow_app
                    res = ecoflow_app.set_ac_charge(st.get("efp") or {}, sn, w) if st.get("efp") else {"code": "?", "message": "bez přihlášení aplikace"}
                else:
                    res = ecoflow.set_ac_charge(host, ak, sk, sn, w)
                ok = str(res.get("code")) == "0"
            except Exception as e:
                ok, res = False, {"message": str(e)[:80]}
            nm = next((r.get("name") for r in data.get("rivers") or [] if r.get("sn") == sn), sn[-4:])
            if ok:
                sets[sn] = w
                done.append(f"{nm} {w} W")
            else:
                done.append(f"{nm}: chyba {str(res.get('message'))[:60]}")
        if done:
            log("ev", "Nabíjení z generátoru: " + ", ".join(done))
        return done

    def step(tnow):
        """Jedno vyhodnocení. Vrací True, když relace pokračuje."""
        rivers = data.get("rivers") or []
        gens = data.get("ef_gens") or []
        inv = data.get("inverter") or {}
        g = (inv.get("gen") or {}) if inv and tnow - inv.get("t", 0) < 600 else {}
        ctl = [r for r in rivers if r.get("online") and r.get("soc") is not None and ctl_ok(r)]
        small = next((r for r in rivers if is_small(r) and r.get("online") and r.get("in_w") is not None), None)
        # 4.94: kdo se nabíjí – stabilně. Po změně výkonu River chvíli „náběh“ (příjem na chvíli ~0) → dřív vypadla
        # z výpočtu, druhá dostala všechno, pak zase naopak (kolísání; jedna naplno, druhá 150 W). Teď River vypadne
        # až když je plná (≥ 99 %), nebo nebere nic aspoň 2 min.
        low = gs.setdefault("low", {})
        insess = gs.setdefault("con", [])
        for r in ctl:
            if acw(r) > 20:
                low.pop(r["sn"], None)
                if r["sn"] not in insess:
                    insess.append(r["sn"])
            else:
                low.setdefault(r["sn"], tnow)
        for sn in list(insess):
            rr = byid(sn)
            # 5.27: plná až když přestane brát (dřív při 99 % → 200 W a poslední procento se zdrželo)
            # 5.28: na 99–100 % a nebere → hned plná (bez čekání); jinak 2 min (krátký „náběh“ po změně výkonu)
            full_ = (rr.get("soc") or 0) >= 99 and sn in low
            if not rr or full_ or (sn in low and tnow - low[sn] >= 120) or not rr.get("online"):
                insess.remove(sn)
                low.pop(sn, None)
        con = [r for r in ctl if r["sn"] in insess]
        con_in = sum(acw(r) for r in con)
        gd = next((x.get("gd") for x in gens if x.get("gd")), None) or {}
        gw = g.get("w") if g.get("w") is not None else gd.get("w")
        # malá, kterou ovládat nejde (bez aplikace): odečíst, kolik bere
        small_w = 0.0 if small and ctl_ok(small) else (small.get("in_w") or 0) if small else max(0.0, (gw or 0) - con_in)
        if small_w < 20:
            small_w = 0.0
        charging = bool(con) or small_w > 0 or (gw or 0) > 20
        out = []
        # River, která se přestala nabíjet (plná / odpojená) → hned zpět na bezpečný výkon
        idle_pros = {r["sn"]: safe_of(r) for r in ctl if r["sn"] not in insess and sets.get(r["sn"]) not in (None, safe_of(r))}
        if idle_pros:
            out += apply(idle_pros)
        if not gs.get("active") and charging:              # relace sama (bez tlačítka) – River se nabíjejí
            gs.update({"active": True, "first": None, "idle": None, "t_on": tnow, "idle_warned": False})
            log("ev", "Nabíjení z generátoru: začátek (River se nabíjejí)")
        if not gs.get("active"):
            return False
        if charging:
            gs["idle"] = None
            gs["first"] = gs.get("first") or tnow
        else:
            gs["idle"] = gs.get("idle") or tnow
            gs["first"] = None                         # 4.89: po výpadku (došlo palivo) zase 30 s na klidových výkonech
            # 4.97: generátor vypadl / došlo palivo → hned všem klidový výkon, ať je nový start nepřetíží
            back = {r["sn"]: safe_of(r) for r in ctl if sets.get(r["sn"]) not in (None, safe_of(r))}
            if back:
                out += apply(back)
            gs.pop("sig", None)
            insess.clear()
        plan = {}
        # 4.90: generátor sám hlásí max. výkon (pd.oilMaxOutPower – nejspíš podle zvoleného paliva: benzín / plyn).
        # Bere se menší z obou (nastavení × generátor) – bezpečné, i kdyby údaj znamenal něco jiného.
        gm = gd.get("max_w")
        try:
            gm = float(gm) if gm is not None else None
        except (TypeError, ValueError):
            gm = None
        gmax_eff = min(gmax, gm) if gm and 1400 <= gm <= 2500 else gmax     # 4.94: jen věrohodná hodnota
        budget_eff = gmax_eff - (cfg.get("gen_rezerva_W") or 0)
        avail = max(0.0, budget_eff - small_w)
        need = {r["sn"]: max(0.0, (100 - r["soc"]) / 100 * (r.get("wh") or 768)) for r in con}
        if con and tnow - gs["first"] >= 30:               # 30 s po začátku nabíjení → vypočítané výkony
            left, todo = avail, dict(need)
            while todo:
                tot = sum(todo.values())
                cand = {sn: left * n / tot if tot > 0 else left / len(todo) for sn, n in todo.items()}
                clamp = {sn: max(rng(byid(sn))[0], min(rng(byid(sn))[1], w)) for sn, w in cand.items()}
                fixed = [sn for sn in todo if clamp[sn] != cand[sn]]
                if not fixed:
                    plan.update(clamp)
                    break
                for sn in fixed:
                    plan[sn] = clamp[sn]
                    left -= clamp[sn]
                    del todo[sn]
                left = max(0.0, left)
            if sum(plan.values()) > avail and len(plan) > 1:   # minima všech by přetížila → zbytek nejprázdnější
                keep = max(plan, key=lambda sn: need[sn])
                mins = sum(rng(byid(sn))[0] for sn in plan if sn != keep)
                plan = {sn: (min(rng(byid(sn))[1], max(rng(byid(sn))[0], avail - mins)) if sn == keep
                             else rng(byid(sn))[0]) for sn in plan}
            plan = {sn: int(round(w / 10) * 10) for sn, w in plan.items()}
            # 4.97: nastavit a nechat. Přepočítá se jen při změně: start (30 s po začátku nabíjení), River přibyla,
            # River odešla (plná / odpojená – její výkon dostanou ostatní), změna paliva / rezervy. Žádné průběžné
            # dorovnávání – River bere přesně nastavený výkon, korekce jen zbytečně cukaly a generátor jednou vypadl.
            sig = [sorted(plan), round(budget_eff)]
            plan_go = plan if gs.get("sig") != sig else {}
            res_ = apply(plan_go)
            if plan_go and all(sets.get(sn) == w for sn, w in plan_go.items()):
                gs["sig"] = sig
            out += res_
        rv, fins = [], []
        for r in con:
            w = sets.get(r["sn"]) or plan.get(r["sn"])
            fin = tnow + need[r["sn"]] / (w * 0.9) * 3600 if w and need[r["sn"]] > 0 else tnow
            fins.append(fin)
            rv.append({"n": r.get("name"), "sn": r["sn"][-4:], "soc": round(r["soc"]), "need": round(need[r["sn"]]),
                       "w": w, "in": round(acw(r)), "fin": int(fin)})
        # 4.101: kolik dodal do River za toto nabíjení (součet příjmů River × čas, z EcoFlow – nezávisle na Flipu)
        tot_in = round(sum(acw(r) for r in con) + small_w)
        if gs.get("e_t") and 0 < tnow - gs["e_t"] <= 300:
            de = (gs.get("e_w", 0) + tot_in) / 2 * (tnow - gs["e_t"]) / 3600
            gs["wh"] = gs.get("wh", 0.0) + de
            dk = datetime.fromtimestamp(tnow, TZ).strftime("%Y-%m-%d")      # 5.06: denní součet i bez zásuvky (7)
            dd_ = data.setdefault("days", {}).setdefault(dk, {})
            dd_["gq"] = round(dd_.get("gq", 0.0) + de, 1)
        # 5.26: energie generátoru podle paliva (výkon generátoru – zásuvka (7) / generátor; jinak součet příjmů River)
        gwe = gw if gw is not None and gw > 0 else tot_in
        if gs.get("f_t") and 0 < tnow - gs["f_t"] <= 300:
            fe_ = st.setdefault("fuel_e", {})
            de2 = (gs.get("f_w", 0) + gwe) / 2 * (tnow - gs["f_t"]) / 3600
            fe_[fuel] = round(fe_.get(fuel, 0.0) + de2, 1)
            gs["fwh"] = gs.get("fwh", 0.0) + de2
        gs["f_t"], gs["f_w"] = tnow, gwe
        gs["fuel"] = fuel
        gs["e_t"], gs["e_w"] = tnow, tot_in
        gp_ = data.setdefault("gen_pts", [])                # 5.06: výkon generátoru po 30 s (graf i bez Flipu)
        gp_.append([tnow, round(gw) if gw is not None else None, tot_in])
        gp_[:] = [x for x in gp_ if x[0] >= tnow - 7 * 86400][-3000:]
        data["gen_plan"] = {"t": tnow, "fuel": fuel, "tot_in": tot_in, "wh": round(gs.get("wh", 0.0)), "gmax": gmax_eff, "gmax_set": gmax, "gmax_gen": gm, "budget": budget_eff, "gw": round(gw) if gw is not None else None,
                            "small": round(small_w), "small_soc": round(small["soc"]) if small and small.get("soc") is not None else None,
                            "avail": round(avail), "rv": rv, "fin": int(max(fins)) if fins else None, "t_on": gs.get("t_on"),
                            "btn": bool(gs.get("btn")), "wait": bool(con) and tnow - gs["first"] < 30,
                            "set": out or (data.get("gen_plan") or {}).get("set"), "gd": gd or None, "fwh": round(gs.get("fwh") or 0)}
        # konec relace: tlačítko, nebo 10 min nic nenabíjí (po tlačítku bez nabíjení až po 30 min)
        idle_lim = 1800 if gs.get("btn") and not gs.get("ever") else 600
        # 5.28: všechny River plné (≥ 99 %) a nic nenabíjí → konec hned („vypni generátor“), ne až za 10 min
        if gs.get("ever") and not con and ctl and all((r.get("soc") or 0) >= 99 for r in ctl) and small_w <= 0:
            idle_lim = 0
            gs["idle"] = gs.get("idle") or tnow
        if charging:
            gs["ever"] = True
        if gs.get("stop") or (gs.get("idle") and tnow - gs["idle"] >= idle_lim):
            out2 = apply({r["sn"]: safe_of(r) for r in rivers if ctl_ok(r) and r.get("online")})
            gs["reset"] = [r["sn"] for r in rivers if ctl_ok(r) and sets.get(r["sn"]) != safe_of(r)]
            if (gw or 0) > 20 and not gs.get("idle_warned"):
                ntfy(topic, "⛽ Generátor běží naprázdno", "Nic se nenabíjí – River jsou nabité (nebo odpojené). Vypni generátor.",
                     4, "fuelpump,white_check_mark")
                gs["idle_warned"] = True
            log("ev", "Nabíjení z generátoru: konec" + (f" – {', '.join(out2)}" if out2 else ""))
            fr_ = data.setdefault("fuel_runs", [])          # 5.26: záznam nabíjení s palivem a energií (cena se dopočítá)
            if (gs.get("fwh") or 0) > 20:
                fr_.append({"t0": gs.get("t_on"), "t1": tnow, "fuel": gs.get("fuel") or fuel, "wh": round(gs["fwh"])})
                del fr_[:-30]
            gs.pop("fwh", None)
            data["gen_plan"]["end"] = tnow
            for k in ("active", "btn", "first", "idle", "stop", "ever", "con", "low", "chg_t", "sig", "f_t", "f_w"):
                gs.pop(k, None)
            return False
        return True

    # nastavit bezpečný výkon River, kterým se to minule nepovedlo (byly offline)
    if gs.get("reset") and not gs.get("active"):
        onl = {r["sn"]: r for r in data.get("rivers") or [] if r.get("online")}
        apply({sn: safe_of(onl[sn]) for sn in gs["reset"] if sn in onl})
        gs["reset"] = [sn for sn in gs["reset"] if sets.get(sn) != safe_of(byid(sn))]
    # klid: River drží bezpečný výkon (první nastavení po zavedení / změně hodnoty, nebo když ho někdo změnil v aplikaci)
    if not gs.get("active"):
        idle_set = {r["sn"]: safe_of(r) for r in data.get("rivers") or [] if ctl_ok(r) and r.get("online")
                    and (gs.get("safe") != [safe_pro, safe_small] or (r.get("cfg_w") is not None and r["cfg_w"] != safe_of(r)))}
        if idle_set:
            apply(idle_set)
        if all(sets.get(r["sn"]) == safe_of(r) for r in data.get("rivers") or [] if ctl_ok(r) and r.get("online")):
            gs["safe"] = [safe_pro, safe_small]
    if gs.pop("restart", None):                          # nový start → všem hned klidový výkon, výpočet až 30 s po nabíjení
        apply({r["sn"]: safe_of(r) for r in data.get("rivers") or [] if ctl_ok(r) and r.get("online")})
    t_start = time.time()
    go = step(int(t_start))
    # smyčka po 30 s (jen během relace) – v jednom běhu hlídače nejvýš ~3 min, pak další běh spustí hlídač sám
    while go and time.time() - t_start < 150:
        time.sleep(30)
        try:                                           # 4.89: nastavení (palivo!) změněné na webu během běhu
            import subprocess
            subprocess.run(["git", "fetch", "-q", "origin", "main", "--depth", "1"], timeout=20, check=True)
            txt = subprocess.run(["git", "show", "origin/main:" + CONFIG_FILE], capture_output=True, text=True, timeout=10).stdout
            if txt:
                import tempfile
                tmp = os.path.join(tempfile.gettempdir(), "nastaveni_nove.txt")
                open(tmp, "w", encoding="utf-8").write(txt)
                c2 = load_config(tmp)
                for k in ("gen_palivo", "gen_max_benzin_W", "gen_max_lpg_W", "gen_rezerva_W", "gen_rizeni"):
                    if c2.get(k) != cfg.get(k):
                        log("ev", f"Nastavení během nabíjení: {k} = {c2.get(k)}")
                        cfg[k] = c2.get(k)
                fuel = "lpg" if str(cfg.get("gen_palivo") or "").lower().startswith(("lpg", "plyn")) else "benzin"
                gmax = cfg.get("gen_max_lpg_W" if fuel == "lpg" else "gen_max_benzin_W") or (1600 if fuel == "lpg" else 1800)
                budget = gmax - (cfg.get("gen_rezerva_W") or 0)
        except Exception as e:
            print("Nastavení – načtení během smyčky:", e)
        try:
            read_ecoflow_app((data.get("rivers") or []) + (data.get("ef_gens") or []), data, st, datetime.now(TZ), force=True)
        except Exception as e:
            print("Generátor – čtení EcoFlow:", e)
        go = step(int(time.time()))
    data["gen_cont"] = bool(gs.get("active"))

def check_river(r, st, topic, cfg):
    soc, k = r.get("soc"), "rv_" + str(r["sn"])[-6:]
    if soc is None or not r["online"]:
        return
    name = r["name"]
    io = f"{name}: {fmt(soc)} %, nabíjení {fmt(r.get('in_w'))} W, odběr {fmt(r.get('out_w'))} W"
    # Skoro vybitá -> vyměnit
    lim = cfg["river_vymenit_pod"]
    if cfg["river_vymenit"] and lim is not None and (r.get("wh") or 768) >= 500:   # 4.82: malá chatu nenapájí
        mins = r.get("dsg_min")
        rest = f" Zbývá asi {fmt(mins / 60, 1)} h." if mins and mins < 6000 else ""
        if soc <= lim and not st.get(k + "_low"):
            ntfy(topic, f"🔄 Vyměň River ({fmt(soc)} %)", f"{io}.{rest}\nPřepoj spotřebiče na druhou River a tuhle nabij.", 4, "battery,warning")
            st[k + "_low"] = True
        # 5.68: další stupně – 10 % a 5 % (nejvyšší priorita), a když River přestane dodávat, protože je prázdná
        sent = set(st.get(k + "_lv") or [])
        for lv in (10, 5):
            if lv < lim and soc <= lv and lv not in sent:
                ntfy(topic, f"🚨 River {name} jen {fmt(soc)} % – brzy se vypne",
                     f"{io}.{rest}\nTeď přepoj chatu na druhou River (nebo solár), jinak zůstane bez 230 V.", 5, "rotating_light,battery")
                sent.add(lv)
                break
        out_now = r.get("out_w") or 0
        if soc <= 5 and st.get(k + "_out", 0) > 20 and out_now <= 3 and "empty" not in sent:
            ntfy(topic, f"🔴 River {name} se vypnula ({fmt(soc)} %)",
                 f"{io}.\nRiver přestala dodávat – pokud z ní jela chata, je teď bez 230 V (lednice, Wi‑Fi, Flip).", 5, "rotating_light,warning")
            sent.add("empty")
        st[k + "_out"] = out_now
        st[k + "_lv"] = sorted(sent, key=str)
        if soc > lim + 10:
            st[k + "_low"] = False
            st[k + "_lv"] = []
    # Nabitá při nabíjení (generátor) -> vypnout generátor
    charging = (r.get("in_w") or 0) > 20
    if cfg["river_nabita"]:
        if soc >= 100 and (charging or st.get(k + "_chg")) and not st.get(k + "_full"):
            ntfy(topic, f"⛽ {name} nabitá na 100 %", f"Můžeš vypnout generátor (nebo přepojit nabíjení na druhou River).\n{io}", 4, "fuelpump,white_check_mark")
            st[k + "_full"] = True
        if soc < 95:
            st[k + "_full"] = False
    st[k + "_chg"] = charging


def check(v, st, now, topic, cfg, rise, set_, data_ref=None):
    data_ref = data_ref or {}
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
        inv = data_ref.get("inverter") or {}
        flip_ok = inv and now.timestamp() - inv.get("t", 0) < 1800
        last_t = data_ref.get("updated")
        since = f"od {rel_day(last_t, now)} {datetime.fromtimestamp(last_t, TZ).strftime('%H:%M')}" if last_t else ""
        import re
        rt = next((p for p in inv.get("tp", []) if re.search(r"router|wi-?fi", str(p.get("n", "")), re.I)), None) if flip_ok else None
        rtx = ""
        if rt:
            rtx = (f" Zásuvka „{rt.get('n')}“ je bez odběru – router nejspíš nejede." if rt.get("off") or (rt.get("w") is not None and rt["w"] < 1)
                   else f" Router má proud ({fmt(rt.get('w'))} W).")
        why = (("Flip data posílá." + rtx) if flip_ok else "Nechodí ani data z Flipu.") + (
            "\nMožné příčiny: zaseknutý Wi‑Fi modul regulátoru, vypadlá Wi‑Fi / router na chatě, regulátor bez napájení, výpadek cloudu Solar Guardian."
            "\n💡 Tip: často pomůže vypnout a zapnout Wi‑Fi modul regulátoru.")
        vv = f"\nNapětí teď podle Victronu: {fmt(inv.get('v'), 2)} V." if flip_ok and inv.get("v") is not None else ""
        ntfy(topic, "📡 Regulátor neposílá data", f"Poslední údaje {since} (před {v['age_min'] or 0:.0f} min). {why}{vv}", 4, "warning")
    if not stale and st.get("stale"):
        ntfy(topic, "📡 Regulátor zase posílá data", f"Údaje z regulátoru jsou zase aktuální.\n{line}", 2, "white_check_mark")
    st["stale"] = stale
    if stale or bv is None:
        return

    # Baterie na 100 % (fáze Float, 2 kontroly po sobě)
    st["float_n"] = min(st.get("float_n", 0) + 1, 2) if status == 1 else 0
    if cfg["nabito"] and st["float_n"] >= 2 and not st.get("full_sent"):
        ntfy(topic, "🔋 Baterie nabitá (Float)", f"Regulátor přešel do Float – baterie je plná. Můžeš zapojit náročnější spotřebič.\n{line}", 2, "battery,sunny")
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
    riv = cabin_on_river(data_ref, cfg, now, st) if data_ref else False      # 5.43
    for key, name, title, text, prio in levels:
        lim, reset = cfg[name + "_V"], cfg[name + "_reset_V"]
        if lim is None:
            continue
        st[key + "_n"] = min(st.get(key + "_n", 0) + 1, 2) if bv < lim else 0
        if st[key + "_n"] >= 2 and not st.get(key + "_sent"):
            if riv and key == "warn":
                continue                         # chata na River: „šetři spotřebu“ nedává smysl (pošle se po návratu na solár)
            if riv:
                title = f"⚠️ Solární baterie pod {fmt(lim, 2)} V, i když chata jede z River"
                text = ("Chata jede z River, a solární baterie přesto klesla pod {lim} V – něco ji vybíjí "
                        "(měnič zapnutý naprázdno?) nebo je poškozená.")
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
            st["night_cut"] = False
        f = st.get("_forecast")
        if data_ref and cabin_on_river(data_ref, cfg, now, st):
            f = None                             # 5.43: chata jede z River – „solár nevydrží / sniž odběr“ nedává smysl
        hold = bool(f and f.get("ok_base") and f.get("cut_by") and now.timestamp() < f["cut_by"] - 600)
        if night and f and f.get("t_crit") and hold and not st.get("night_cut") and not st.get("night_warned"):
            # 4.50: nejdřív rada (zvýšený odběr je možná jen chvilkový), „nevydrží“ až když se do té doby nesníží
            cb = datetime.fromtimestamp(f["cut_by"], TZ).strftime("%H:%M")
            ntfy(topic, f"🌙 Aby solár vydržel do rána, sniž odběr do {cb}",
                 f"Teď chata bere ~{f['now_w']} W, běžně v noci ~{f['base_w']} W. Když do {cb} odběr vrátíš na běžný "
                 f"(vypneš PC a podobně), solární baterie do rána vydrží. Jinak přijde upozornění, že nevydrží – a přepnout na River.\n{line}",
                 3, "crescent_moon")
            st["night_cut"] = True
        if night and f and f.get("t_crit") and not hold and not st.get("night_warned"):
            ntfy(topic, f"🌙 Solární baterie {do_rana(f['until'], now)} nevydrží – přepni chatu na River",
                 f"{forecast_text(f)}.\nPřepoj chatu na River (nebo hned odpoj, co nejde nutně). Pokud chata ve {cfg.get('nutne_river_v') or '22:00'} pořád pojede ze solární baterie, přijde naléhavé opakované upozornění.\n{line}", 4, "crescent_moon,warning")
            st["night_warned"] = True
    if data_ref is not None:
        urgent_river(data_ref, st, now, topic, cfg, rise, set_)


def urgent_river(data, st, now, topic, cfg, rise, set_):
    """„TEĎ TO UDĚLEJ“ (přání 18. 10. 2026): od nutne_river_v (22:00) do rána – když chata jede ze solární baterie
    a předpověď říká, že baterie v noci klesne pod alarm (12,0 V) → naléhavé upozornění „Přepni chatu na River“,
    opakované po ~5 min, dokud: nepotvrdíš tlačítkem „Přepínám“ (ntfy <téma>-ack), chata nepřejde na River
    (zásuvka měniče ≤ 3 W a River dodává), nebo nevyjde slunce. Jednou za noc."""
    hhmm = str(cfg.get("nutne_river_v") or "").strip()
    if not hhmm or hhmm.lower() in ("vypnuto", "ne", "off") or not rise or not set_:
        return
    try:
        hh, mm = (int(x) for x in hhmm.split(":")[:2])
    except ValueError:
        return
    ts = now.timestamp()
    start_today = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if now >= start_today:
        key = now.strftime("%Y-%m-%d")
    elif now < rise:
        key = (now - timedelta(days=1)).strftime("%Y-%m-%d")      # po půlnoci = noc začala včera
    else:
        return                                                     # den / večer před 22:00
    if st.get("ur_done") == key:
        return
    inv = data.get("inverter") or {}
    fresh = inv and ts - inv.get("t", 0) < 1800
    rids = ips(cfg.get("zasuvky_river"))
    on_river = fresh and (inv.get("mw") or 0) <= 3 and any(
        str(p.get("ip")) in rids and (p.get("w") or 0) > 3 for p in inv.get("tp", []))
    active = st.get("ur_active") == key
    # potvrzení tlačítkem („ok“) nebo odložení („30“ / „60“ minut – 5.30)
    if active:
        try:
            u = f"https://ntfy.sh/{topic}-ack/json?poll=1&since={int(st.get('ur_t0', ts))}"
            got = urllib.request.urlopen(u, timeout=15).read().decode()
            for ln in got.splitlines():
                try:
                    m = json.loads(ln)
                except ValueError:
                    continue
                if m.get("event") != "message":
                    continue
                txt = str(m.get("message") or "").strip()
                if txt.isdigit():
                    until = int(m.get("time") or ts) + int(txt) * 60
                    if until > (st.get("ur_snooze") or 0):
                        st["ur_snooze"] = until
                        log("ev", f"Přepnutí na River odloženo do {datetime.fromtimestamp(until, TZ).strftime('%H:%M')}")
                else:
                    st["ur_done"], st["ur_active"] = key, None
                    log("ev", "Přepnutí na River potvrzeno")
                    return
        except Exception as e:
            print("Potvrzení (ntfy):", e)
    if on_river:
        if active:
            ntfy(topic, "✓ Chata jede z River", "Solární baterie je teď v klidu – díky.", 2, "white_check_mark")
        st["ur_done"], st["ur_active"] = key, None
        st.pop("ur_snooze", None)
        return
    f = st.get("_forecast") or {}
    if not active and not f.get("t_crit"):
        return                                                     # baterie do rána vydrží → nic
    if not active and f.get("ok_base") and f.get("cut_by") and ts < f["cut_by"] - 600:
        return                                                     # 4.50: ještě je čas snížit odběr (rada už odešla)
    if active and ts - st.get("ur_last", 0) < 4 * 60:
        return                                                     # nejvýš jednou za ~5 min
    if ts < (st.get("ur_snooze") or 0):
        return                                                     # 5.30: odloženo tlačítkem „+30 min / +1 h“
    if not active:
        st["ur_active"], st["ur_t0"] = key, int(ts)
    st["ur_last"] = int(ts)
    bv = (data.get("last") or {}).get("bat_v")
    hq = (data.get("hq") or {}).get("pct")
    hm = lambda t: datetime.fromtimestamp(t, TZ).strftime("%H:%M")
    msg = (f"Solární baterie do rána nevydrží: pod 12,0 V {rel_day(f['t_crit'], now)} ~{hm(f['t_crit'])}"
           + (f", měnič se vypne ~{hm(f['t_off'])}" if f.get("t_off") else "") + ".\n"
           + f"Teď {fmt(bv, 2)} V" + (f" · {hq} #" if hq is not None else "") + ".\n"
           + "Přepoj chatu na River. Upozornění se opakuje, dokud neťukneš na „Přepínám“ nebo dokud chata nepřejde na River.") if f.get("t_crit") else (
           "Přepoj chatu na River – solární baterie do rána nevydrží. Upozornění se opakuje, dokud neťukneš na „Přepínám“.")
    # 5.30: tlačítka Přepínám / za 30 min / za 1 h (ntfy dovolí 3 – „Přehled“ tu vynechán). Připomenutí s každým během
    # hlídače (~10 min); naplánované připomenutí za 5 min zrušeno – po odložení by stejně dorazilo.
    act = lambda lb, b: {"action": "http", "label": lb, "url": f"https://ntfy.sh/{topic}-ack", "method": "POST", "body": b, "clear": True}
    ack = [act("Přepínám", "ok"), act("Za 30 min", "30"), act("Za 1 h", "60")]
    ntfy(topic, "⚠️ TEĎ přepni chatu na River", msg + "\nNechceš teď? Odlož o 30 min nebo 1 h – zítra se ozve zase ve " + hhmm + ".",
         5, "rotating_light,warning", actions=ack, view=False)



if __name__ == "__main__":
    main()
