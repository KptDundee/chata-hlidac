package cz.petr.chatabrana;

import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.BatteryManager;
import android.util.Base64;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

/** Jeden cyklus: posbírá měnič + zásuvky + baterii telefonu a pošle to do ntfy. */
public final class Collector {
    private final Context ctx;
    private final BleListener ble;
    private final Map<String, TapoKlap> tapo = new HashMap<>();
    private final Map<String, String> names = new HashMap<>();

    public Collector(Context ctx, BleListener ble) {
        this.ctx = ctx.getApplicationContext();
        this.ble = ble;
    }

    /** @return krátký popis výsledku do notifikace */
    public String runOnce() {
        try {
            JSONObject o = new JSONObject();
            o.put("ver", 1);
            StringBuilder sum = new StringBuilder();

            // 1) měnič Victron (Bluetooth)
            if (ble.samples() == 0) ble.burst(20_000);   // trvalý poslech nic nechytil → 20 s intenzivně
            BleListener.Snapshot s = ble.takeSnapshot();
            if (s.avgVa != null) {
                o.put("w", round(s.avgVa, 1));
                o.put("max", s.maxVa);
                sum.append(String.format(Locale.US, "měnič %.0f W", s.avgVa));
            } else {
                o.put("w", -1);
                sum.append("měnič: ").append(s.error != null ? s.error : "žádná data");
            }
            if (s.last != null && s.ageSec >= 0 && s.ageSec < 900) {
                if (s.last.batteryV != null) o.put("v", s.last.batteryV);
                o.put("st", s.last.stateName());
                o.put("al", s.last.alarmName());
            }
            o.put("n", s.samples);

            // 2) zásuvky Tapo (místní Wi-Fi)
            JSONArray plugs = new JSONArray();
            String email = Prefs.s(ctx, Prefs.TAPO_EMAIL), pass = Prefs.s(ctx, Prefs.TAPO_PASSWORD);
            int ok = 0, total = 0;
            if (!email.isEmpty()) {
                for (String ip : Prefs.tapoIps(ctx)) {
                    total++;
                    JSONObject p = readPlug(ip, email, pass);
                    if (p != null) { plugs.put(p); if (!p.has("err")) ok++; }
                }
                if (plugs.length() > 0) o.put("tp", plugs);
                sum.append(", zásuvky ").append(ok).append('/').append(total);
            }

            // 3) baterie telefonu
            Intent b = ctx.registerReceiver(null, new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
            if (b != null) {
                int lvl = b.getIntExtra(BatteryManager.EXTRA_LEVEL, -1);
                int scale = b.getIntExtra(BatteryManager.EXTRA_SCALE, 100);
                int plugged = b.getIntExtra(BatteryManager.EXTRA_PLUGGED, 0);
                int temp = b.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, Integer.MIN_VALUE);
                JSONObject ph = new JSONObject();
                int pct = lvl >= 0 ? Math.round(100f * lvl / scale) : -1;
                ph.put("b", pct);
                ph.put("c", plugged != 0 ? 1 : 0);
                if (temp != Integer.MIN_VALUE) ph.put("t", temp / 10.0);
                o.put("ph", ph);
                sum.append(", telefon ").append(pct).append(" %");
            }

            // 4) odeslat
            String topic = Prefs.s(ctx, Prefs.NTFY_TOPIC);
            if (topic.isEmpty()) return "Chybí ntfy téma v nastavení";
            post("https://ntfy.sh/" + topic + "-menic", o.toString());
            Prefs.get(ctx).edit().putLong(Prefs.LAST_SENT, System.currentTimeMillis()).apply();
            Prefs.log(ctx, "Odesláno: " + sum);
            return sum.toString();
        } catch (Exception e) {
            String m = "Chyba: " + e.getMessage();
            Prefs.log(ctx, m);
            return m;
        }
    }

    private JSONObject readPlug(String ip, String email, String pass) {
        JSONObject p = new JSONObject();
        try {
            p.put("ip", ip.substring(ip.lastIndexOf('.') + 1));
            TapoKlap t = tapo.get(ip);
            if (t == null) { t = new TapoKlap(ip, email, pass); tapo.put(ip, t); }
            if (!names.containsKey(ip)) {
                JSONObject info = new JSONObject(t.call("get_device_info")).optJSONObject("result");
                if (info != null) {
                    String nick = info.optString("nickname", "");
                    try { nick = new String(Base64.decode(nick, Base64.DEFAULT), StandardCharsets.UTF_8); } catch (Exception ignored) {}
                    names.put(ip, nick.isEmpty() ? ip : nick);
                    p.put("on", info.optBoolean("device_on") ? 1 : 0);
                    p.put("m", info.optString("model", ""));
                }
            }
            p.put("n", names.containsKey(ip) ? names.get(ip) : ip);
            JSONObject res = new JSONObject(t.call("get_energy_usage"));
            JSONObject e = res.optJSONObject("result");
            if (res.optInt("error_code", 0) == 0 && e != null) {
                if (e.has("current_power")) p.put("w", round(e.getDouble("current_power") / 1000.0, 1));
                if (e.has("today_energy")) p.put("wh", e.getInt("today_energy"));
            }
        } catch (Exception ex) {
            tapo.remove(ip);   // příště nové přihlášení
            try { p.put("err", String.valueOf(ex.getMessage())); } catch (Exception ignored) {}
            Prefs.log(ctx, "Zásuvka " + ip + ": " + ex.getMessage());
        }
        return p;
    }

    /** Po hodině se znovu načtou názvy zásuvek (kdyby se přejmenovaly). */
    public void forgetNames() { names.clear(); }

    private static void post(String url, String body) throws Exception {
        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
        c.setConnectTimeout(15000);
        c.setReadTimeout(15000);
        c.setRequestMethod("POST");
        c.setDoOutput(true);
        c.setRequestProperty("Title", "data");
        c.setRequestProperty("Priority", "1");
        try (OutputStream o = c.getOutputStream()) { o.write(body.getBytes(StandardCharsets.UTF_8)); }
        int code = c.getResponseCode();
        c.disconnect();
        if (code >= 300) throw new Exception("ntfy HTTP " + code);
    }

    private static double round(double v, int d) {
        double f = Math.pow(10, d);
        return Math.round(v * f) / f;
    }
}
