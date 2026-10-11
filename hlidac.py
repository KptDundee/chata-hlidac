#!/usr/bin/env python3
"""Hlídač chaty: čte Solar Guardian (EPEVER cloud) a posílá upozornění přes ntfy."""
import hashlib
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

API_BASE = "https://hncloudapi.epsolarpv.com/usrCloud"
DISPATCH = "https://hncomm.epsolarpv.com:7100/"
APP_ID = "po246089zkljagiusdgq"
DEVICE_NO = "05070616093TM23Y-00076"  # brána regulátoru XTRA-N
TZ = ZoneInfo("Europe/Prague")
STATE_FILE = "state.json"

# Hranice pro AGM 12 V (lze upravit)
WARN_V, WARN_RESET_V = 12.2, 12.5
CRIT_V, CRIT_RESET_V = 12.0, 12.4
STALE_MIN = 120          # data z cloudu starší než 2 h => regulátor offline
SUMMARY_HOUR = 20        # večerní souhrn po 20:00

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
    req = urllib.request.Request("https://ntfy.sh/", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    urllib.request.urlopen(req, timeout=30).read()
    print("NTFY:", title, "|", msg)


def fmt(x, d=0):
    return "?" if x is None else f"{x:.{d}f}".replace(".", ",")


def main():
    acc, pw, topic = os.environ["SG_ACCOUNT"], os.environ["SG_PASSWORD"], os.environ["NTFY_TOPIC"]
    st = json.load(open(STATE_FILE)) if os.path.exists(STATE_FILE) else {}
    before = json.dumps(st, sort_keys=True)
    v = read_values(login(acc, pw))
    now = datetime.now(TZ)
    bv, status = v["bat_v"], int(v["status"]) if v["status"] is not None else None
    line = (f"Baterie {fmt(bv, 2)} V, {fmt(v['bat_soc'])} %, panely {fmt(v['pv_w'])} W, "
            f"{STATUS.get(status, status)}, dnes {fmt(v['day_kwh'], 2)} kWh")
    print(now.isoformat(), line, f"(stáří dat {v['age_min']:.0f} min)" if v["age_min"] is not None else "")

    if os.environ.get("TEST") == "1":
        ntfy(topic, "🔔 Hlídač chaty – test", line, 3, "white_check_mark")

    # Regulátor offline
    stale = v["age_min"] is None or v["age_min"] > STALE_MIN
    if stale and not st.get("stale"):
        ntfy(topic, "📡 Regulátor neposílá data", f"Poslední data z cloudu před {v['age_min'] or 0:.0f} min. Zkontroluj Wi‑Fi modul / internet.", 4, "warning")
    st["stale"] = stale
    if stale or bv is None:
        return save(st, before)

    # Nabitá baterie (fáze Float, 2 kontroly po sobě)
    st["float_n"] = min(st.get("float_n", 0) + 1, 2) if status == 1 else 0
    if st["float_n"] >= 2 and not st.get("full_sent"):
        ntfy(topic, "☀️ Solární baterie nabitá", f"Regulátor je ve fázi Float. {line}. Můžeš ji zase připojit.", 4, "sunny")
        st["full_sent"] = True
    if status != 1:
        st["full_sent"] = False

    # Nízké napětí (2 kontroly po sobě, s hysterezí)
    for key, lim, reset, title, text, prio in (
        ("crit", CRIT_V, CRIT_RESET_V, "🛑 Odpoj solární baterii", "Napětí pod 12,0 V – nevybíjej dál, přepni na EcoFlow.", 5),
        ("warn", WARN_V, WARN_RESET_V, "⚠️ Solární baterie slábne", "Napětí pod 12,2 V (~50 %). Šetři spotřebu.", 4),
    ):
        st[key + "_n"] = min(st.get(key + "_n", 0) + 1, 2) if bv < lim else 0
        if st[key + "_n"] >= 2 and not st.get(key + "_sent"):
            ntfy(topic, title, f"{text}\n{line}", prio, "warning")
            st[key + "_sent"] = True
            if key == "crit":
                st["warn_sent"] = True  # nespamovat i varováním
        if bv > reset:
            st[key + "_sent"] = False

    # Večerní souhrn
    today = now.strftime("%Y-%m-%d")
    if now.hour >= SUMMARY_HOUR and st.get("summary_day") != today:
        ntfy(topic, "📊 Chata – dnešní souhrn",
             f"Výroba dnes {fmt(v['day_kwh'], 2)} kWh\nBaterie {fmt(bv, 2)} V ({fmt(v['bat_soc'])} %), dnes min {fmt(v['min_v'], 2)} V / max {fmt(v['max_v'], 2)} V\nTeplota baterie {fmt(v['bat_t'], 1)} °C", 2, "bar_chart")
        st["summary_day"] = today
    return save(st, before)


def save(st, before):
    if json.dumps(st, sort_keys=True) != before:
        json.dump(st, open(STATE_FILE, "w"), indent=1, sort_keys=True)
        print("state changed")


if __name__ == "__main__":
    main()
