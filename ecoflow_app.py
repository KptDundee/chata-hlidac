"""4.76: EcoFlow stejnou cestou jako aplikace EcoFlow (přihlášení e-mailem a heslem) – pro zařízení, která
vývojářské rozhraní nepouští (chyba 1006: Smart Generator, malá River 2).

Neoficiální (stejně jako doplněk tolwi/hassio-ecoflow-cloud pro Home Assistant): přihlášení
POST /auth/login → token, ID uživatele; GET /iot-auth/app/certification → přihlašovací údaje MQTT;
MQTT /app/{uid}/{sn}/thing/property/get „latestQuotas“ → odpověď get_reply se všemi údaji (quotaMap)
a průběžná data /app/device/property/{sn}.

Přihlašovací údaje: GitHub Secrets ECOFLOW_EMAIL, ECOFLOW_PASSWORD (zadává Petr sám, nikde se nevypisují).
Token a údaje MQTT se pamatují ve stavu hlídače (šifrovaná data), přihlásí se znovu jen když přestanou platit.
"""
import base64
import json
import random
import time
import urllib.request
import uuid

HOSTS = ("api-e.ecoflow.com", "api.ecoflow.com")


def _req(url, data=None, headers=None, method=None, timeout=25):
    h = {"lang": "en_US", "content-type": "application/json"}
    h.update(headers or {})
    body = json.dumps(data).encode() if data is not None else None
    r = urllib.request.Request(url, data=body, headers=h, method=method or ("POST" if body else "GET"))
    return json.loads(urllib.request.urlopen(r, timeout=timeout).read())


def login(email, password):
    """→ {host, token, uid, acct, pw, url, port, t}. Chyba = výjimka s textem od EcoFlow (bez hesla)."""
    errs = []
    for host in HOSTS:
        try:
            d = _req(f"https://{host}/auth/login", {"email": email, "password": base64.b64encode(password.encode()).decode(),
                                                    "scene": "IOT_APP", "userType": "ECOFLOW"})
        except Exception as e:
            errs.append(f"{host}: {str(e)[:80]}")
            continue
        if str(d.get("code")) != "0" or not d.get("data"):
            errs.append(f"{host}: {d.get('code')} {str(d.get('message'))[:80]}")
            continue
        tok, uid = d["data"].get("token"), (d["data"].get("user") or {}).get("userId")
        c = _req(f"https://{host}/iot-auth/app/certification?userId={uid}", headers={"authorization": f"Bearer {tok}"})
        if str(c.get("code")) != "0" or not c.get("data"):
            errs.append(f"{host} certifikát: {c.get('code')} {str(c.get('message'))[:80]}")
            continue
        cd = c["data"]
        return {"host": host, "token": tok, "uid": str(uid), "acct": cd.get("certificateAccount"),
                "pw": cd.get("certificatePassword"), "url": cd.get("url"), "port": int(cd.get("port") or 8883),
                "t": int(time.time())}
    raise RuntimeError("přihlášení EcoFlow (aplikace) nejde – " + " | ".join(errs))


def read(sess, sns, secs=14):
    """Přečte zařízení přes MQTT aplikace. → {sn: {"online": 0/1/None, "q": {klíč: hodnota}, "n": zpráv, "bin": binárních}}
    nebo {"_auth": True} při odmítnutém přihlášení (pak znovu login)."""
    import paho.mqtt.client as mqtt
    res = {sn: {"online": None, "q": {}, "n": 0} for sn in sns}
    uid, state = sess["uid"], {"auth": None, "replies": set()}

    def on_msg(cl, ud, m):
        sn = next((s for s in sns if s in m.topic), None)
        if not sn:
            return
        try:
            js = json.loads(m.payload.decode("utf-8"))
        except Exception:
            res[sn]["bin"] = res[sn].get("bin", 0) + 1         # protobuf (některé modely) – zatím neumíme
            return
        res[sn]["n"] += 1
        if m.topic.endswith("get_reply"):
            d = js.get("data") or {}
            if isinstance(d, dict):
                if d.get("online") is not None:
                    res[sn]["online"] = int(d.get("online") or 0)
                qm = d.get("quotaMap")
                if isinstance(qm, dict):
                    res[sn]["q"].update(qm)
            state["replies"].add(sn)
        else:
            p = js.get("params")
            if isinstance(p, dict):
                res[sn]["q"].update(p)
                res[sn]["online"] = 1

    def on_conn(cl, ud, flags, rc, props=None):
        ok = (rc == 0) if isinstance(rc, int) else not rc.is_failure
        state["auth"] = ok
        if not ok:
            return
        for sn in sns:
            cl.subscribe(f"/app/device/property/{sn}", 1)
            cl.subscribe(f"/app/{uid}/{sn}/thing/property/get_reply", 1)
            cl.publish(f"/app/{uid}/{sn}/thing/property/get",
                       json.dumps({"from": "Android", "id": str(999900000 + random.randint(10000, 99999)), "version": "1.1",
                                   "moduleType": 0, "operateType": "latestQuotas", "params": {}}), 1)

    cid = f"ANDROID_{uuid.uuid4().hex.upper()}_{uid}"
    try:
        cl = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cid)
    except AttributeError:
        cl = mqtt.Client(client_id=cid)
    cl.username_pw_set(sess["acct"], sess["pw"])
    cl.tls_set()
    cl.on_message, cl.on_connect = on_msg, on_conn
    cl.connect(sess["url"], sess["port"], 30)
    cl.loop_start()
    t0 = time.time()
    while time.time() - t0 < secs:
        time.sleep(0.5)
        if state["auth"] is False or (state["replies"] >= set(sns) and time.time() - t0 > 4):
            break
    cl.loop_stop()
    cl.disconnect()
    if state["auth"] is False:
        return {"_auth": True}
    if state["auth"] is None:
        raise RuntimeError("MQTT aplikace: spojení se nenavázalo")
    return res
