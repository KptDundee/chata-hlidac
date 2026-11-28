package cz.petr.chatabrana;

import android.content.Context;
import android.os.SystemClock;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

/**
 * 1.9.22 (Petr: „živě to celé“): kromě světel i zásuvky (zap/vyp, W), Victron (W, V), teploměry a baterie Flipu.
 * Posílá se jen při podstatné změně – světlo / zásuvka zap/vyp hned (kontrola po 20 s), výkon zásuvky nebo Victronu
 * o 15 W a zároveň o 20 % a víc nejvýš 1× za minutu;
 * teploty a baterie jen jako doplněk. Spojení s ntfy zůstává otevřené (bez opakovaného navazování – méně dat).
 * 1.9.20 (Petr: světla živě a zapínání z webu). Světla Tapo (L900…) se po Wi‑Fi chaty kontrolují každých 20 s
 * (mobilní data to nestojí); když se některé rozsvítí nebo zhasne, pošle se jejich stav (pár set bajtů) do ntfy
 * <téma>-lt – web ho má hned. Povel z webu přijde přes <téma>-ltc (poslouchá ho trvalé spojení v GatewayService):
 * {"n":"(S4) terasa","on":true} → světlo se přepne a hned se pošle nový stav.
 * Seznam světel (jméno → IP) si průběžně ukládá Collector při každém měření.
 */
final class LightWatch {
    static final long PERIOD_MS = 20_000L;
    private final Context ctx;
    private volatile Thread th;
    private final Map<String, TapoKlap> tapo = new HashMap<>();
    private String lastState = "", lastErr = "";
    private long lastSend = 0;
    private final BleListener ble;
    private final Map<String, Double> sentW = new HashMap<>();   // naposledy poslané W (zásuvky, „~v“ = Victron)
    static final double DW = 15.0;

    LightWatch(Context c, BleListener b) { ctx = c.getApplicationContext(); ble = b; }

    /** Collector: zásuvka „jméno“ je na IP; meas = měří výkon. */
    static synchronized void rememberPlug(Context c, String name, String ip, boolean meas) {
        try {
            JSONObject m = new JSONObject(Prefs.get(c).getString("pl_map", "{}"));
            String v = ip + (meas ? "|1" : "|0");
            if (v.equals(m.optString(name))) return;
            m.put(name, v);
            Prefs.get(c).edit().putString("pl_map", m.toString()).apply();
        } catch (Exception ignored) {}
    }

    /** Collector: světlo „jméno“ je teď na IP adrese ip. */
    static synchronized void remember(Context c, String name, String ip) {
        try {
            JSONObject m = new JSONObject(Prefs.get(c).getString("lt_map", "{}"));
            if (ip.equals(m.optString(name))) return;
            m.put(name, ip);
            Prefs.get(c).edit().putString("lt_map", m.toString()).apply();
        } catch (Exception ignored) {}
    }

    void start() {
        if (th != null && th.isAlive()) return;
        Thread t = new Thread(() -> {
            while (th == Thread.currentThread()) {
                try { poll(false); } catch (Exception ignored) {}
                SystemClock.sleep(PERIOD_MS);
            }
        }, "lights");
        t.setDaemon(true);
        th = t;
        t.start();
    }

    void stop() { Thread t = th; th = null; if (t != null) t.interrupt(); }

    private TapoKlap klap(String ip) {
        TapoKlap t = tapo.get(ip);
        if (t == null) {
            t = new TapoKlap(ip, Prefs.s(ctx, Prefs.TAPO_EMAIL), Prefs.s(ctx, Prefs.TAPO_PASSWORD));
            tapo.put(ip, t);
        }
        return t;
    }

    /** Přečte všechna světla; při změně (nebo force) pošle stav do ntfy. */
    synchronized void poll(boolean force) throws Exception {
        if (Prefs.s(ctx, Prefs.TAPO_EMAIL).isEmpty()) return;
        JSONObject m = new JSONObject(Prefs.get(ctx).getString("lt_map", "{}"));
        List<String> names = new ArrayList<>();
        for (Iterator<String> it = m.keys(); it.hasNext(); ) names.add(it.next());
        Collections.sort(names);
        JSONArray arr = new JSONArray();
        StringBuilder st = new StringBuilder();
        for (String n : names) {
            String ip = m.optString(n);
            if (ip.isEmpty()) continue;
            try {
                JSONObject info = new JSONObject(klap(ip).call("get_device_info")).optJSONObject("result");
                if (info == null || !info.has("device_on")) continue;
                boolean on = info.optBoolean("device_on");
                arr.put(new JSONObject().put("n", n).put("ip", ip.substring(ip.lastIndexOf('.') + 1)).put("on", on ? 1 : 0));
                st.append(n).append('=').append(on ? 1 : 0).append(';');
            } catch (Exception e) {
                tapo.remove(ip);                                   // příště nové přihlášení
                err("Světla: " + n + " nejde přečíst (" + e.getClass().getSimpleName() + " " + e.getMessage() + ")");
            }
        }
        if (arr.length() == 0 && m.length() > 0) err("Světla: žádné nepřečteno (seznam: " + m.length() + ")");
        // 1.9.22: zásuvky
        JSONObject pm = new JSONObject(Prefs.get(ctx).getString("pl_map", "{}"));
        JSONArray tp = new JSONArray();
        Map<String, Double> nowW = new HashMap<>();
        List<String> pn = new ArrayList<>();
        for (Iterator<String> it = pm.keys(); it.hasNext(); ) pn.add(it.next());
        Collections.sort(pn);
        for (String n : pn) {
            String[] v = pm.optString(n).split("\\|");
            String ip = v[0];
            if (ip.isEmpty()) continue;
            try {
                JSONObject x = new JSONObject().put("n", n);
                JSONObject info = new JSONObject(klap(ip).call("get_device_info")).optJSONObject("result");
                if (info != null && info.has("device_on")) {
                    boolean on = info.optBoolean("device_on");
                    x.put("on", on ? 1 : 0);
                    st.append(n).append('=').append(on ? 1 : 0).append(';');
                }
                if (v.length > 1 && "1".equals(v[1])) {
                    JSONObject e = new JSONObject(klap(ip).call("get_energy_usage")).optJSONObject("result");
                    if (e != null && e.has("current_power")) {
                        double w = Math.round(e.getDouble("current_power") / 100.0) / 10.0;
                        x.put("w", w);
                        nowW.put(n, w);
                    }
                }
                tp.put(x);
            } catch (Exception e) {
                tapo.remove(ip);
            }
        }
        // Victron (Bluetooth – co Flip právě zachytil)
        JSONObject vic = null;
        VictronParser.Inverter iv = ble != null ? ble.peekVictron() : null;
        if (iv != null) {
            vic = new JSONObject();
            if (iv.acVa != null) { vic.put("w", iv.acVa); nowW.put("~v", (double) iv.acVa); }
            if (iv.batteryV != null) vic.put("v", iv.batteryV);
        }
        if (arr.length() == 0 && tp.length() == 0 && vic == null) return;
        String s = st.toString();
        boolean big = false;                                        // výkon se změnil o 15 W a víc
        for (Map.Entry<String, Double> e : nowW.entrySet()) {
            Double was = sentW.get(e.getKey());
            double d = Math.abs((was == null ? 0 : was) - e.getValue());
            if (was == null || (d >= DW && d >= 0.2 * Math.max(Math.abs(was), Math.abs(e.getValue())))) { big = true; break; }
        }
        if (!force && s.equals(lastState) && !big) return;
        // jen změna výkonu (nic se nezaplo / nevyplo) → nejvýš 1× za minutu (šetří data)
        if (!force && s.equals(lastState) && SystemClock.elapsedRealtime() - lastSend < 60_000) return;
        JSONObject o = new JSONObject().put("t", System.currentTimeMillis() / 1000).put("lt", arr);
        if (tp.length() > 0) o.put("tp", tp);
        if (vic != null) o.put("v", vic);
        try {                                                       // doplněk: teploty a baterie Flipu
            JSONArray th = new JSONArray();
            if (ble != null) for (BleListener.Thermo t : ble.thermo()) {
                if (t.ageSec < 0 || t.ageSec > 1800 || t.t == null) continue;
                JSONObject x = new JSONObject().put("n", t.name).put("t", t.t);
                if (t.h != null) x.put("h", t.h);
                th.put(x);
            }
            if (th.length() > 0) o.put("th", th);
            android.os.BatteryManager bm = ctx.getSystemService(android.os.BatteryManager.class);
            if (bm != null) o.put("ph", new JSONObject().put("b", bm.getIntProperty(android.os.BatteryManager.BATTERY_PROPERTY_CAPACITY))
                    .put("c", bm.isCharging() ? 1 : 0));
        } catch (Exception ignored) {}
        String r = post(o);
        if (r == null) {
            boolean lightChg = !lightPart(s).equals(lightPart(lastState));
            lastState = s; lastErr = ""; sentW.clear(); sentW.putAll(nowW); lastSend = SystemClock.elapsedRealtime();
            if (lightChg) Prefs.log(ctx, "Světla → web: " + lightPart(s).replace(";", " ").trim());
        }
        else err("Živé hodnoty → web: nepovedlo se odeslat (" + r + ")");
    }

    /** Část stavu jen se světly (do Deníku jen změny světel, ne každou zásuvku). */
    private String lightPart(String s) {
        StringBuilder b = new StringBuilder();
        try {
            JSONObject m = new JSONObject(Prefs.get(ctx).getString("lt_map", "{}"));
            for (String x : s.split(";")) { int i = x.indexOf('='); if (i > 0 && m.has(x.substring(0, i))) b.append(x).append(';'); }
        } catch (Exception ignored) {}
        return b.toString();
    }

    /** 1.9.21: chybu zapsat do Deníku jen jednou (ne každých 20 s). */
    private void err(String e) {
        if (e.equals(lastErr)) return;
        lastErr = e;
        Prefs.log(ctx, e);
    }

    /** Povel z webu: světlo podle jména zapnout / vypnout, pak hned poslat nový stav. */
    synchronized void command(String name, boolean on) {
        try {
            JSONObject m = new JSONObject(Prefs.get(ctx).getString("lt_map", "{}"));
            String ip = m.optString(name);
            if (ip.isEmpty()) { Prefs.log(ctx, "Světlo z webu: „" + name + "“ neznám"); return; }
            JSONObject r = new JSONObject(klap(ip).call("set_device_info", "{\"device_on\":" + on + "}"));
            if (r.optInt("error_code", -1) == 0) Prefs.log(ctx, "Světlo " + name + " " + (on ? "ROZSVÍCENO" : "ZHASNUTO") + " (z webu)");
            else Prefs.log(ctx, "Světlo " + name + " z webu: selhalo " + r);
            SystemClock.sleep(600);
            poll(true);
        } catch (Exception e) {
            tapo.clear();
            Prefs.log(ctx, "Světlo z webu: " + e.getMessage());
        }
    }

    /** null = odesláno, jinak důvod chyby. */
    private String post(JSONObject o) {
        String topic = Prefs.s(ctx, Prefs.NTFY_TOPIC).trim();
        if (topic.isEmpty()) return "chybí téma ntfy";
        HttpURLConnection c = null;
        try {
            c = (HttpURLConnection) new URL("https://ntfy.sh/" + topic + "-lt").openConnection();
            c.setConnectTimeout(15000); c.setReadTimeout(15000);
            c.setRequestMethod("POST"); c.setDoOutput(true);
            try (OutputStream out = c.getOutputStream()) { out.write(o.toString().getBytes(StandardCharsets.UTF_8)); }
            int code = c.getResponseCode();
            try (java.io.InputStream in = code < 400 ? c.getInputStream() : c.getErrorStream()) {   // dočíst → spojení se znovu použije
                if (in != null) { byte[] b = new byte[1024]; while (in.read(b) > 0) { } }
            }
            return code == 200 ? null : "HTTP " + code;
        } catch (Exception e) {
            if (c != null) c.disconnect();
            return e.getClass().getSimpleName() + " " + e.getMessage();
        }
    }
}
