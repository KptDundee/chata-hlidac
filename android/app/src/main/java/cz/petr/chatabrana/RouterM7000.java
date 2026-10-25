package cz.petr.chatabrana;

import org.json.JSONObject;

import java.io.OutputStream;
import java.math.BigInteger;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.KeyFactory;
import java.security.MessageDigest;
import java.security.PublicKey;
import java.security.SecureRandom;
import java.security.spec.RSAPublicKeySpec;

import javax.crypto.Cipher;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;

/**
 * 1.8: baterie routeru TP-Link M7000 – šifrované webové rozhraní (jako jeho vlastní stránka):
 *   1. POST /cgi-bin/auth_cgi {"data": base64({"module":"authenticator","action":0})} → nonce, rsaMod, rsaPubKey, seqNum
 *   2. náhodný AES klíč a IV (16 znaků), h = md5("admin" + heslo), digest = md5(heslo + ":" + nonce)
 *   3. přihlášení: data = AES-128-CBC({"module":"authenticator","action":1,"digest":…}) base64,
 *      sign = RSA PKCS#1 v1.5 (po kouscích, hex) z "key=…&iv=…&h=…&s=" + (seqNum + délka data) → token
 *   4. stav: {"module":"status","action":0,"token":…}, sign z "h=…&s=…" → odpověď AES base64 → battery.voltage = %
 *   5. odhlášení (router dovolí jen jedno přihlášení správce – ať nezablokuje aplikaci tpMiFi)
 * Postup podle projektů tplink-battery-monitor (gioelerosana) a mimif-battery (M7000). Jen čtení.
 */
public final class RouterM7000 {
    private RouterM7000() {}

    public static final class Result { public Integer pct; public Boolean charging; public String err;
        public JSONObject net;                                         // 1.9.3: přenesená data (wan.*Statistics) + seznam klíčů
    }

    private static final String AB = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";

    public static Result read(String host, String password) {
        Result r = new Result();
        String base = "http://" + host;
        Session s = new Session();
        try {
            // 1) nonce a veřejný klíč
            JSONObject a0 = decode(s, post(base, "/cgi-bin/auth_cgi",
                    new JSONObject().put("data", b64(new JSONObject().put("module", "authenticator").put("action", 0).toString().getBytes(StandardCharsets.UTF_8))).toString()));
            String nonce = a0.optString("nonce", "");
            s.n = a0.optString("rsaMod", ""); s.e = a0.optString("rsaPubKey", "");
            s.seq = a0.optLong("seqNum", 0);
            if (nonce.isEmpty() || s.n.isEmpty()) { r.err = "router: nečekaná odpověď na přihlášení (" + trim(a0.toString()) + ")"; return r; }
            // 2) klíče
            SecureRandom rnd = new SecureRandom();
            StringBuilder k = new StringBuilder(), v = new StringBuilder();
            for (int i = 0; i < 16; i++) { k.append(AB.charAt(rnd.nextInt(AB.length()))); v.append(AB.charAt(rnd.nextInt(AB.length()))); }
            s.key = k.toString(); s.iv = v.toString();
            s.h = md5("admin" + password);
            // 3) přihlášení
            JSONObject a1 = call(s, base, "/cgi-bin/auth_cgi",
                    new JSONObject().put("module", "authenticator").put("action", 1).put("digest", md5(password + ":" + nonce)), true);
            int res = a1.optInt("result", -999);
            if (res == 1) { r.err = "router: špatné heslo správce"; return r; }
            String token = a1.optString("token", "");
            if (res != 0 || token.isEmpty()) { r.err = "router: přihlášení odmítnuto (výsledek " + res + ")" + (res == -999 ? " " + trim(a1.toString()) : ""); return r; }
            // 4) stav
            try {
                JSONObject st = call(s, base, "/cgi-bin/web_cgi", new JSONObject().put("module", "status").put("action", 0).put("token", token), false);
                // 1.9.3: přenesená data – wan.totalStatistics / dailyStatistics / … (bajty); a pro jistotu názvy klíčů,
                // ať je vidět, co router posílá, kdyby se to jmenovalo jinak
                try {
                    JSONObject net = new JSONObject();
                    JSONObject wan = st.optJSONObject("wan");
                    if (wan != null) {
                        java.util.Iterator<String> it = wan.keys();
                        StringBuilder wk = new StringBuilder();
                        while (it.hasNext()) {
                            String wkey = it.next(); wk.append(wkey).append(',');
                            String kl = wkey.toLowerCase(java.util.Locale.ROOT);
                            if (kl.contains("statistic") || kl.contains("flow") || kl.contains("speed")) {
                                double dv = wan.optDouble(wkey, Double.NaN);
                                if (!Double.isNaN(dv)) net.put(wkey, dv);
                            }
                        }
                        net.put("_wk", trim(wk.toString()));
                    }
                    java.util.Iterator<String> it2 = st.keys();
                    StringBuilder tk = new StringBuilder();
                    while (it2.hasNext()) tk.append(it2.next()).append(',');
                    net.put("_k", trim(tk.toString()));
                    JSONObject cd = st.optJSONObject("connectedDevices");
                    if (cd != null && cd.has("number")) net.put("dev", cd.optInt("number"));
                    r.net = net;
                } catch (Exception ignored) { }
                JSONObject bat = st.optJSONObject("battery");
                if (bat == null) { r.err = "router: ve stavu není baterie (" + trim(st.toString()) + ")"; return r; }
                double pv = bat.has("voltage") ? bat.optDouble("voltage", -1) : bat.optDouble("percent", -1);   // M7000: „voltage“ = %
                if (pv >= 0 && pv <= 100) r.pct = (int) Math.round(pv);
                else r.err = "router: baterie " + trim(bat.toString());
                if (bat.has("charging")) { Object c = bat.opt("charging"); r.charging = c instanceof Boolean ? (Boolean) c : bat.optInt("charging", 0) != 0; }
            } finally {
                // 5) odhlášení (nejde-li, router relaci sám ukončí po pár minutách)
                try { call(s, base, "/cgi-bin/auth_cgi", new JSONObject().put("module", "authenticator").put("action", 3).put("token", token), false); }
                catch (Exception ignored) { }
            }
        } catch (Exception e) {
            r.err = "router: " + e.getMessage();
        }
        return r;
    }

    private static final class Session { String n, e, key, iv, h; long seq; }

    private static JSONObject call(Session s, String base, String path, JSONObject obj, boolean login) throws Exception {
        String data = aesEnc(s, obj.toString());
        long seq = s.seq + data.length();
        String msg = login ? "key=" + s.key + "&iv=" + s.iv + "&h=" + s.h + "&s=" + seq : "h=" + s.h + "&s=" + seq;
        String body = new JSONObject().put("data", data).put("sign", rsa(s, msg)).toString();
        return decode(s, post(base, path, body));
    }

    private static String post(String base, String path, String body) throws Exception {
        HttpURLConnection c = (HttpURLConnection) new URL(base + path).openConnection();
        c.setConnectTimeout(6000);
        c.setReadTimeout(8000);
        c.setRequestMethod("POST");
        c.setDoOutput(true);
        c.setRequestProperty("Content-Type", "application/json");
        c.setRequestProperty("Referer", base + "/");
        c.setRequestProperty("Origin", base);
        try (OutputStream o = c.getOutputStream()) { o.write(body.getBytes(StandardCharsets.UTF_8)); }
        int code = c.getResponseCode();
        java.io.InputStream in = code < 400 ? c.getInputStream() : c.getErrorStream();
        java.io.ByteArrayOutputStream bo = new java.io.ByteArrayOutputStream();
        if (in != null) { byte[] b = new byte[4096]; int n; while ((n = in.read(b)) > 0) bo.write(b, 0, n); in.close(); }
        c.disconnect();
        if (code >= 400) throw new Exception("HTTP " + code);
        return bo.toString("UTF-8").trim();
    }

    /** Odpověď: JSON, nebo AES base64 (po přihlášení), nebo base64 JSON. */
    private static JSONObject decode(Session s, String txt) throws Exception {
        if (txt.startsWith("{")) return new JSONObject(txt);
        if (s.key != null) {
            try { String d = aesDec(s, txt); if (d.trim().startsWith("{")) return new JSONObject(d); } catch (Exception ignored) { }
        }
        try {
            String d = new String(android.util.Base64.decode(txt, android.util.Base64.DEFAULT), StandardCharsets.UTF_8).trim();
            if (d.startsWith("{")) return new JSONObject(d);
        } catch (Exception ignored) { }
        throw new Exception("neznámá odpověď: " + trim(txt));
    }

    private static String aesEnc(Session s, String plain) throws Exception {
        Cipher c = Cipher.getInstance("AES/CBC/PKCS5Padding");
        c.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(s.key.getBytes(StandardCharsets.US_ASCII), "AES"),
                new IvParameterSpec(s.iv.getBytes(StandardCharsets.US_ASCII)));
        return b64(c.doFinal(plain.getBytes(StandardCharsets.UTF_8)));
    }

    private static String aesDec(Session s, String b64txt) throws Exception {
        Cipher c = Cipher.getInstance("AES/CBC/PKCS5Padding");
        c.init(Cipher.DECRYPT_MODE, new SecretKeySpec(s.key.getBytes(StandardCharsets.US_ASCII), "AES"),
                new IvParameterSpec(s.iv.getBytes(StandardCharsets.US_ASCII)));
        return new String(c.doFinal(android.util.Base64.decode(b64txt, android.util.Base64.DEFAULT)), StandardCharsets.UTF_8);
    }

    /** RSA PKCS#1 v1.5 po kouscích (délka klíče − 11 bajtů), výsledek hex za sebou. */
    private static String rsa(Session s, String msg) throws Exception {
        BigInteger n = new BigInteger(s.n, 16), e = new BigInteger(s.e, 16);
        PublicKey pk = KeyFactory.getInstance("RSA").generatePublic(new RSAPublicKeySpec(n, e));
        Cipher c = Cipher.getInstance("RSA/ECB/PKCS1Padding");
        int kb = (n.bitLength() + 7) / 8, chunk = kb - 11;
        byte[] m = msg.getBytes(StandardCharsets.UTF_8);
        StringBuilder out = new StringBuilder();
        for (int i = 0; i < m.length; i += chunk) {
            c.init(Cipher.ENCRYPT_MODE, pk);
            byte[] ct = c.doFinal(m, i, Math.min(chunk, m.length - i));
            for (byte b : ct) out.append(String.format("%02x", b));
        }
        return out.toString();
    }

    private static String b64(byte[] b) { return android.util.Base64.encodeToString(b, android.util.Base64.NO_WRAP); }

    private static String trim(String s) { return s.length() > 160 ? s.substring(0, 160) + "…" : s; }

    private static String md5(String s) throws Exception {
        byte[] d = MessageDigest.getInstance("MD5").digest(s.getBytes(StandardCharsets.UTF_8));
        StringBuilder sb = new StringBuilder();
        for (byte x : d) sb.append(String.format("%02x", x));
        return sb.toString();
    }
}
