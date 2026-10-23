package cz.petr.chatabrana;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Iterator;

/**
 * 1.7: stav baterie mobilního routeru TP-Link M7000 (rodina M7200/M7350) z jeho webového rozhraní na místní síti.
 * Zatím JEN ČTENÍ – nic nepřepíná. Přihlášení: nonce → digest = md5(heslo + ":" + nonce) → token → status.
 * Protokol není ověřený na tvém kuse, proto se do záznamu zapíše, co router odpověděl (bez hesla a tokenu).
 */
public final class RouterM7000 {
    private RouterM7000() {}

    public static final class Result { public Integer pct; public Boolean charging; public String err; }

    public static Result read(String host, String password) {
        Result r = new Result();
        try {
            String base = "http://" + host;
            JSONObject a0 = post(base + "/cgi-bin/auth_cgi", new JSONObject().put("module", "authenticator").put("action", 0));
            String nonce = a0.optString("nonce", "");
            if (nonce.isEmpty()) { r.err = "router nevrátil nonce (jiný způsob přihlášení?) – klíče: " + keys(a0); return r; }
            String digest = md5(password + ":" + nonce);
            JSONObject a1 = post(base + "/cgi-bin/auth_cgi", new JSONObject().put("module", "authenticator").put("action", 1).put("digest", digest));
            String token = a1.optString("token", "");
            if (token.isEmpty()) { r.err = "přihlášení odmítnuto (výsledek " + a1.optInt("result", -1) + ") – heslo?"; return r; }
            JSONObject st = post(base + "/cgi-bin/web_cgi", new JSONObject().put("token", token).put("module", "status").put("action", 0));
            JSONObject bat = findObj(st, "battery");
            if (bat == null) { r.err = "ve stavu routeru není baterie – klíče: " + keys(st); return r; }
            for (String k : new String[]{"capacity", "percent", "level", "voltage"}) {
                if (bat.has(k) && !"voltage".equals(k)) { r.pct = (int) Math.round(bat.optDouble(k, -1)); break; }
            }
            for (String k : new String[]{"chargeStatus", "charging", "charge", "isCharging"}) {
                if (bat.has(k)) { Object v = bat.opt(k); r.charging = v instanceof Boolean ? (Boolean) v : bat.optInt(k, 0) != 0; break; }
            }
            if (r.pct == null || r.pct < 0 || r.pct > 100) { r.pct = null; r.err = "baterie routeru: " + trim(bat.toString()); }
        } catch (Exception e) {
            r.err = "router: " + e.getMessage();
        }
        return r;
    }

    private static JSONObject post(String url, JSONObject body) throws Exception {
        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
        c.setConnectTimeout(6000);
        c.setReadTimeout(8000);
        c.setRequestMethod("POST");
        c.setDoOutput(true);
        c.setRequestProperty("Content-Type", "application/json");
        try (OutputStream o = c.getOutputStream()) { o.write(body.toString().getBytes(StandardCharsets.UTF_8)); }
        int code = c.getResponseCode();
        java.io.InputStream in = code < 400 ? c.getInputStream() : c.getErrorStream();
        java.io.ByteArrayOutputStream bo = new java.io.ByteArrayOutputStream();
        if (in != null) { byte[] b = new byte[4096]; int n; while ((n = in.read(b)) > 0) bo.write(b, 0, n); in.close(); }
        c.disconnect();
        if (code >= 400) throw new Exception("HTTP " + code);
        return new JSONObject(bo.toString("UTF-8"));
    }

    private static JSONObject findObj(JSONObject o, String name) {
        if (o.optJSONObject(name) != null) return o.optJSONObject(name);
        for (Iterator<String> it = o.keys(); it.hasNext(); ) {
            Object v = o.opt(it.next());
            if (v instanceof JSONObject) { JSONObject f = findObj((JSONObject) v, name); if (f != null) return f; }
            if (v instanceof JSONArray) for (int i = 0; i < ((JSONArray) v).length(); i++) {
                Object x = ((JSONArray) v).opt(i);
                if (x instanceof JSONObject) { JSONObject f = findObj((JSONObject) x, name); if (f != null) return f; }
            }
        }
        return null;
    }

    private static String keys(JSONObject o) {
        StringBuilder sb = new StringBuilder();
        for (Iterator<String> it = o.keys(); it.hasNext(); ) { String k = it.next(); if (!k.toLowerCase().contains("token")) sb.append(k).append(' '); }
        return trim(sb.toString().trim());
    }

    private static String trim(String s) { return s.length() > 160 ? s.substring(0, 160) + "…" : s; }

    private static String md5(String s) throws Exception {
        byte[] d = MessageDigest.getInstance("MD5").digest(s.getBytes(StandardCharsets.UTF_8));
        StringBuilder sb = new StringBuilder();
        for (byte x : d) sb.append(String.format("%02x", x));
        return sb.toString();
    }
}
