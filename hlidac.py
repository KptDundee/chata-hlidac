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


def ntfy(topic, title, msg, prio=3, tags=""):
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
            return
        except Exception as e:  # výpadek ntfy nesmí shodit hlídače
            print("NTFY chyba:", e)
            time.sleep(5)


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
    for k, src in (("solar_kwh", "day_kwh"), ("min_v", "min_v"), ("max_v", "max_v")):
        if v.get(src) is not None:
            day[k] = round(v[src], 2)
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
        v = read_values(login(acc, pw))
    except (Exception, SystemExit) as e:  # výpadek cloudu: nespadnout, po ~2 h upozornit
        print("Chyba čtení cloudu:", e)
        st["err_n"] = st.get("err_n", 0) + 1
        if st["err_n"] == 12:
            ntfy(topic, "📡 Hlídač nemůže číst Solar Guardian", f"Už ~2 hodiny selhává čtení cloudu: {str(e)[:150]}", 4, "warning")
        save_data(key, data)
        return
    st["err_n"] = 0
    data["last"] = {k: (round(x, 2) if isinstance(x, float) else x) for k, x in v.items()}
    if v.get("age_min") is not None and v["age_min"] <= cfg["regulator_offline_min"]:
        record(data, v, now)
    try:
        check(v, st, now, topic, cfg, rise, set_)
    finally:
        save_data(key, data)


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
        ("off", "odpojeni", "🔌 Regulátor odpojuje zátěž",
         "Napětí na úrovni ochranného odpojení regulátoru ({lim} V). Zátěž se vrátí až nad {reset} V.", 5),
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

    # Večerní souhrn
    h = cfg["vecerni_souhrn_hodina"]
    today = now.strftime("%Y-%m-%d")
    if h is not None and now.hour >= h and st.get("summary_day") != today:
        sun = f"\nSlunce zítra cca {hm(rise)}–{hm(set_)}" if rise else ""
        ntfy(topic, "📊 Chata – dnešní souhrn",
             f"Výroba dnes {fmt(v['day_kwh'], 2)} kWh\nBaterie {fmt(bv, 2)} V ({fmt(v['bat_soc'])} %), dnes min {fmt(v['min_v'], 2)} V / max {fmt(v['max_v'], 2)} V\nTeplota baterie {fmt(v['bat_t'], 1)} °C{sun}", 2, "bar_chart")
        st["summary_day"] = today


if __name__ == "__main__":
    main()
