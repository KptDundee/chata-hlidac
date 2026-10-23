"""EcoFlow (River 2 Pro) přes oficiální EcoFlow Developer API.

Klíče: https://developer-eu.ecoflow.com → Access Key + Secret Key (GitHub Secrets
ECOFLOW_ACCESS_KEY, ECOFLOW_SECRET_KEY). Bez klíčů se nic neděje.
"""
import hashlib
import hmac
import json
import os
import random
import time
import urllib.parse
import urllib.request

HOSTS = ("https://api-e.ecoflow.com", "https://api.ecoflow.com")

# Různé modely/firmware hlásí stejné údaje pod různými klíči – bere se první nalezený.
KEYS = {
    "soc": ("pd.soc", "bms_bmsStatus.soc", "bms_emsStatus.lcdShowSoc", "bms_emsStatus.f32LcdShowSoc"),
    "in_w": ("pd.wattsInSum", "inv.inputWatts"),
    "out_w": ("pd.wattsOutSum", "inv.outputWatts"),
    "ac_in_w": ("inv.inputWatts",),
    "ac_out_w": ("inv.outputWatts",),
    "dsg_min": ("bms_emsStatus.dsgRemainTime", "pd.remainTime"),
    "chg_min": ("bms_emsStatus.chgRemainTime",),
    "temp": ("bms_bmsStatus.temp",),
}


# 4.62: kapacita podle modelu (Wh) – River 2 Pro 768, ostatní menší
MODEL_WH = (("river 2 pro", 768), ("river 2 max", 512), ("river 2", 256), ("river 3 plus", 286), ("river 3", 245),
            ("river pro", 720), ("river max", 576), ("river mini", 210))


def _sign(ak, sk, params):
    nonce, ts = str(random.randint(100000, 999999)), str(int(time.time() * 1000))
    base = "&".join(f"{k}={params[k]}" for k in sorted(params))
    msg = (base + "&" if base else "") + f"accessKey={ak}&nonce={nonce}&timestamp={ts}"
    sig = hmac.new(sk.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return {"accessKey": ak, "nonce": nonce, "timestamp": ts, "sign": sig}


def _get(host, path, ak, sk, params=None):
    params = params or {}
    url = host + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers=_sign(ak, sk, params))
    d = json.loads(urllib.request.urlopen(req, timeout=30).read())
    if str(d.get("code")) != "0":
        raise RuntimeError(f"EcoFlow {path}: {d.get('code')} {d.get('message')}")
    return d.get("data")


def _flat(obj, prefix=""):
    """Vnořený JSON → ploché „a.b=v“ / „a[0]=v“ (EcoFlow podepisuje tělo PUT takhle)."""
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(_flat(v, f"{prefix}.{k}" if prefix else k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(_flat(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


def set_quota(host, ak, sk, body):
    """4.66: nastavení zařízení (PUT /iot-open/sign/device/quota). Vrací odpověď EcoFlow (dict)."""
    flat = _flat(body)
    hdr = _sign(ak, sk, flat)
    hdr["Content-Type"] = "application/json;charset=UTF-8"
    req = urllib.request.Request(host + "/iot-open/sign/device/quota", data=json.dumps(body).encode(), headers=hdr, method="PUT")
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def set_ac_charge(host, ak, sk, sn, watts):
    """River 2 Pro: nabíjecí výkon ze sítě (AC) ve W."""
    body = {"id": int(time.time() * 1000) % 1000000000, "version": "1.0", "sn": sn, "moduleType": 5,
            "operateType": "acChgCfg", "params": {"chgWatts": int(watts), "chgPauseFlag": 0}}
    return set_quota(host, ak, sk, body)


# 4.67: zkouška jiných cest pro zařízení, kde quota/all vrací 1006 (generátor, malá River 2)
PROBE_Q = {
    "gen": ["pd.oilVal", "pd.type", "pd.acPower", "pd.totalPower", "pd.motorState", "pd.oilMaxOutPower",
            "pd.sysMode", "pd.ecoMode", "pd.remainTime", "pd.motorUseTime", "pd.errCode"],
    "river": ["pd.soc", "pd.wattsInSum", "pd.wattsOutSum", "bms_bmsStatus.soc", "inv.cfgSlowChgWatts"],
}


def get_quota(host, ak, sk, sn, quotas):
    """Vybrané údaje (POST /iot-open/sign/device/quota) – jiná cesta než quota/all. Vrací odpověď EcoFlow (dict)."""
    body = {"sn": sn, "params": {"quotas": list(quotas)}}
    hdr = _sign(ak, sk, _flat(body))
    hdr["Content-Type"] = "application/json;charset=UTF-8"
    req = urllib.request.Request(host + "/iot-open/sign/device/quota", data=json.dumps(body).encode(), headers=hdr, method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def _short(d, n=30):
    out = {k: v for k, v in sorted(d.items()) if isinstance(v, (int, float, str)) and len(str(v)) < 24}
    return dict(list(out.items())[:n])


def mqtt_listen(host, ak, sk, sns, secs=35):
    """Poslech EcoFlow MQTT (oficiální cesta pro vývojáře) – co jednotlivá zařízení sama posílají.
    Vrací {sn: {"n": počet zpráv, "q": vzorek údajů, "st": online/offline}} nebo {"_err": text}."""
    try:
        import paho.mqtt.client as mqtt
    except Exception as e:
        return {"_err": f"chybí paho-mqtt ({e})"}
    try:
        c = _get(host, "/iot-open/sign/certification", ak, sk) or {}
    except Exception as e:
        return {"_err": f"certifikát: {str(e)[:100]}"}
    acct, pw = c.get("certificateAccount"), c.get("certificatePassword")
    url, port = c.get("url"), int(c.get("port") or 8883)
    if not (acct and pw and url):
        return {"_err": "certifikát bez údajů"}
    res = {sn: {"n": 0, "q": {}} for sn in sns}

    def on_msg(cl, ud, m):
        parts = m.topic.split("/")
        sn = parts[3] if len(parts) > 4 else None
        if sn not in res:
            return
        try:
            js = json.loads(m.payload.decode("utf-8", "replace"))
        except Exception:
            res[sn]["bin"] = res[sn].get("bin", 0) + 1
            return
        if parts[-1] == "status":
            res[sn]["st"] = (js.get("params") or {}).get("status", js.get("status"))
            return
        res[sn]["n"] += 1
        p = js.get("params") or js.get("data") or {}
        if isinstance(p, dict):
            pre = js.get("typeCode") or js.get("moduleType") or ""
            for k, v in _flat(p).items():
                res[sn]["q"][(f"{pre}." if pre and "." not in k else "") + k] = v
        if js.get("code") not in (None, 0, "0"):
            res[sn]["code"] = f"{js.get('code')} {js.get('message', '')}"[:80]

    def on_conn(cl, ud, flags, rc, props=None):
        for sn in sns:
            for t in ("quota", "status", "get_reply"):
                cl.subscribe(f"/open/{acct}/{sn}/{t}", 1)
            q = PROBE_Q["gen"] if str(sn).upper().startswith("DG") else PROBE_Q["river"]
            cl.publish(f"/open/{acct}/{sn}/get", json.dumps({"id": random.randint(10**8, 10**9), "version": "1.0",
                                                               "sn": sn, "operateType": "latestQuotas",
                                                               "params": {"quotas": q}}), 1)

    try:
        try:
            cl = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"{acct}_{random.randint(10**6, 10**7)}")
        except AttributeError:
            cl = mqtt.Client(client_id=f"{acct}_{random.randint(10**6, 10**7)}")
        cl.username_pw_set(acct, pw)
        cl.tls_set()
        cl.on_message, cl.on_connect = on_msg, on_conn
        cl.connect(url, port, 30)
        cl.loop_start()
        time.sleep(secs)
        cl.loop_stop()
        cl.disconnect()
    except Exception as e:
        return {"_err": f"MQTT: {str(e)[:100]}"}
    for sn in res:
        res[sn]["q"] = _short(res[sn]["q"])
    return res


def probe(host, ak, sk, devs):
    """4.67: pro zařízení s chybou údajů zkusí vybrané údaje přes HTTP a poslech MQTT. Zapisuje do r["probe"]."""
    for r in devs:
        if not r.get("qerr"):
            continue
        q = PROBE_Q["gen"] if r.get("gen") else PROBE_Q["river"]
        pr = {}
        for h in HOSTS:
            try:
                d = get_quota(h, ak, sk, r["sn"], q)
                pr[h.replace("https://", "")] = (f"{d.get('code')} {d.get('message') or ''}"[:90] if str(d.get("code")) != "0"
                                                 else _short(d.get("data") or {}))
            except Exception as e:
                pr[h.replace("https://", "")] = f"chyba {str(e)[:80]}"
        r["probe"] = {"http": pr}
    sns = [r["sn"] for r in devs]
    mq = mqtt_listen(host, ak, sk, sns, 35)
    for r in devs:
        r.setdefault("probe", {})["mqtt"] = mq.get("_err") or mq.get(r["sn"])
    return devs


def read_rivers(ak, sk, host_hint=None):
    """Vrátí (host, [ {sn, name, online, soc, in_w, out_w, ...}, ... ])."""
    errs = []
    for host in ([host_hint] if host_hint else []) + [h for h in HOSTS if h != host_hint]:
        try:
            devs = _get(host, "/iot-open/sign/device/list", ak, sk) or []
            break
        except Exception as e:  # špatný region => zkusit druhý
            errs.append(f"{host.replace('https://', '')}: {e}")
    else:
        raise RuntimeError("EcoFlow nedostupný – " + " | ".join(errs))   # 4.60: chyby z obou oblastí
    out = []
    for dv in devs:
        sn = dv.get("sn")
        r = {"sn": sn, "name": dv.get("deviceName") or dv.get("productName") or sn,
             "online": bool(dv.get("online")), "model": dv.get("productName")}
        pm = str(dv.get("productName") or "").lower()
        r["wh"] = next((w for m, w in MODEL_WH if m in pm), None)
        try:
            q = _get(host, "/iot-open/sign/device/quota/all", ak, sk, {"sn": sn}) or {}
        except Exception as e:
            print("EcoFlow quota", sn, e)
            q = {}
            r["qerr"] = str(e)[:120]                                 # 4.64: diagnostika na web
        if os.environ.get("ECOFLOW_DEBUG") == "1":
            print("EcoFlow klíče", sn, json.dumps({k: q[k] for k in sorted(q)
                                                     if any(x in k.lower() for x in ("soc", "watt", "remain", "temp"))}))
        if str(sn or "").upper().startswith("DG"):          # generátor EcoFlow Smart Generator (SN „DG…“)
            r["gen"] = True
            # klíče generátoru zatím neznáme → poslat výběr podle názvu (zobrazí se na webu, pak se zpřesní)
            r["q"] = {k: v for k, v in sorted(q.items())
                      if isinstance(v, (int, float, str)) and len(str(v)) < 24
                      and any(x in k.lower() for x in ("watt", "oil", "fuel", "lpg", "gas", "engine", "run", "temp",
                                                       "state", "mode", "err", "volt", "amp", "hour", "time", "level"))}
            if len(r["q"]) > 40:
                r["q"] = dict(list(r["q"].items())[:40])
        for key, names in KEYS.items():
            for n in names:
                if q.get(n) is not None:
                    try:
                        r[key] = float(q[n])
                    except (TypeError, ValueError):
                        pass
                    break
        r["nq"] = len(q)                                                # 4.64: kolik údajů EcoFlow vrátil
        r["chgk"] = {k: v for k, v in sorted(q.items()) if isinstance(v, (int, float)) and "chg" in k.lower()
                     and "watt" in k.lower()}                           # 4.66: nastavený nabíjecí výkon (ověření)
        if len(r["chgk"]) > 8:
            r["chgk"] = dict(list(r["chgk"].items())[:8])
        r["socs"] = {k: q[k] for k in KEYS["soc"] if q.get(k) is not None}   # všechny zdroje % (porovnání s displejem)
        if r.get("soc") is None and not r.get("gen") and q:          # 4.62: neznámé klíče (jiný model) → poslat výběr na web
            r["qk"] = {k: v for k, v in sorted(q.items()) if isinstance(v, (int, float)) and
                       any(x in k.lower() for x in ("soc", "batt", "watt", "remain", "cap"))}
            if len(r["qk"]) > 25:
                r["qk"] = dict(list(r["qk"].items())[:25])
        out.append(r)
    return host, out
