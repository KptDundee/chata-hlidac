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


def read_rivers(ak, sk, host_hint=None):
    """Vrátí (host, [ {sn, name, online, soc, in_w, out_w, ...}, ... ])."""
    err = None
    for host in ([host_hint] if host_hint else []) + [h for h in HOSTS if h != host_hint]:
        try:
            devs = _get(host, "/iot-open/sign/device/list", ak, sk) or []
            break
        except Exception as e:  # špatný region => zkusit druhý
            err = e
    else:
        raise RuntimeError(f"EcoFlow nedostupný: {err}")
    out = []
    for dv in devs:
        sn = dv.get("sn")
        r = {"sn": sn, "name": dv.get("deviceName") or dv.get("productName") or sn,
             "online": bool(dv.get("online"))}
        try:
            q = _get(host, "/iot-open/sign/device/quota/all", ak, sk, {"sn": sn}) or {}
        except Exception as e:
            print("EcoFlow quota", sn, e)
            q = {}
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
        out.append(r)
    return host, out
